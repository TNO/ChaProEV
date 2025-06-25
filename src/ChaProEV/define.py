'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This module defines and declares classes for the different objects
that define the system (the parameters/defintions come from a scenario file),
namely:
1. **Legs:** Legs are point-to-point vehicle movements (i.e. movements where
    the vehicle goes from a start location and ends/stops at an end location).
2. **Location:** This class defines the locations where the vehicles are
(available charger power, connectivity, latitude, longitude, etc.).
3. **Trips:** Trips are collections of legs that take place on a given day.
    Note that this day does not necessarily start (and end) at minight,
    but can start (and end) at an hour that is more logical/significant for the
    user (it could for example be 06:00 for car drivers). This day_start_hour
    parameter is universal for all trips

This module also includes two functions to declare a chosen class, and
to run that function for all class types.
'''

import datetime
import math
import typing as ty

import numpy as np
import pandas as pd
from box import Box
from ETS_CookBook import ETS_CookBook as cook

try:
    import run_time  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import run_time  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


def get_trip_charging_sessions(
    end_locations_of_legs: list[str],
    start_probabilities: list[float],
    time_between_legs_used: list[float],
    leg_driving_times: list[float],
    leg_distances: list[float],
    weighted_leg_distances: list[float],
    scenario: Box,
    general_parameters: Box,
) -> list:
    trip_charging_sessions: list[TripChargingSession] = []
    charging_session_resolution: int = scenario.charging_sessions.resolution
    vehicle_electricity_consumption: float = (
        scenario.vehicle.base_consumption_per_km.electricity_kWh
    )

    for travelling_group_start_slot, travelling_group_size in enumerate(
        start_probabilities
    ):
        if travelling_group_size > 0:
            number_of_legs: int = len(leg_driving_times)
            if number_of_legs > 0:
                session_first_start: float = travelling_group_start_slot
                for leg_index, (
                    leg_destination,
                    time_after_leg,
                    time_driving,
                    distance,
                    weighted_distance,
                ) in enumerate(
                    zip(
                        end_locations_of_legs,
                        time_between_legs_used,
                        leg_driving_times,
                        leg_distances,
                        weighted_leg_distances,
                    )
                ):

                    session_first_start += time_driving
                    session_location: str = leg_destination
                    session_size: float = (
                        travelling_group_size / charging_session_resolution
                    )
                    incoming_consumption: float = (
                        distance * vehicle_electricity_consumption
                    )
                    if leg_index == number_of_legs - 1:
                        next_leg_consumption: float = 0
                        session_duration: float = (
                            general_parameters.time.HOURS_IN_A_DAY
                        ) - session_first_start
                    else:
                        next_leg_consumption = (
                            leg_distances[leg_index + 1]
                            * vehicle_electricity_consumption
                        )
                        session_duration = time_after_leg

                    location_connectivity: float = scenario.locations[
                        session_location
                    ].connectivity
                    location_charging_power_to_vehicle: float = (
                        scenario.locations[session_location].charging_power
                        * location_connectivity
                    )
                    location_charging_power_from_network: float = (
                        scenario.locations[session_location].charging_power
                        * location_connectivity
                        / scenario.locations[
                            session_location
                        ].charger_efficiency
                    )
                    location_discharge_power_from_vehicle: float = (
                        scenario.locations[
                            session_location
                        ].vehicle_discharge_power
                        * location_connectivity
                    )
                    location_discharge_power_to_network: float = (
                        scenario.locations[
                            session_location
                        ].vehicle_discharge_power
                        * location_connectivity
                        * scenario.locations[
                            session_location
                        ].proportion_of_discharge_to_network
                    )

                    for sessions_substep_index in range(
                        charging_session_resolution
                    ):
                        substep_shift: float = 1 - 1 / (
                            sessions_substep_index + 1
                        )
                        session_start: float = (
                            session_first_start + substep_shift
                        )
                        session_end: float = session_start + session_duration
                        substep_charging_session: TripChargingSession = (
                            TripChargingSession(
                                session_location,
                                session_size,
                                session_start,
                                session_end,
                                incoming_consumption,
                                next_leg_consumption,
                                location_connectivity,
                                location_charging_power_to_vehicle,
                                location_charging_power_from_network,
                                location_discharge_power_from_vehicle,
                                location_discharge_power_to_network,
                            )
                        )
                        trip_charging_sessions.append(substep_charging_session)

    return trip_charging_sessions


def mobility_matrix_to_run_mobility_matrix(
    matrix_to_expand,  # It is a DataFRame, but MyPy seems to have issues
    # with DataFrmes with a MultiIndex
    leg_tuples: list[tuple[str, str]],
    run_index: pd.MultiIndex,
    run_time_tags: pd.DatetimeIndex,
    start_hour: int,
    scenario: Box,
    general_parameters: Box,
) -> pd.DataFrame:
    run_matrix: pd.DataFrame = pd.DataFrame(
        columns=matrix_to_expand.columns, index=run_index
    )
    run_matrix = run_matrix.sort_index()
    for leg_tuple in leg_tuples:
        cloned_matrix: pd.DataFrame = run_time.from_day_to_run(
            matrix_to_expand.loc[
                (leg_tuple[0], leg_tuple[1]), matrix_to_expand.columns
            ],
            run_time_tags,
            start_hour,
            scenario,
            general_parameters,
        )
        for matrix_quantity in matrix_to_expand.columns:
            run_matrix.at[(leg_tuple[0], leg_tuple[1]), matrix_quantity] = (
                cloned_matrix[matrix_quantity].values
            )
    return run_matrix


def get_slot_split(
    percent_in_first_slot, travelling_group_size
) -> tuple[float, float, float]:

    percent_in_next_slot: float = 1 - percent_in_first_slot

    first_slot_impact_in_first_slot: float = (
        percent_in_first_slot * percent_in_first_slot / 2
    )

    first_slot_impact_in_second_slot: float = (
        percent_in_first_slot - first_slot_impact_in_first_slot
    )
    second_slot_impact_in_second_slot: float = (
        percent_in_next_slot * (1 + percent_in_first_slot) / 2
    )
    second_slot_impact_in_third_slot: float = (
        percent_in_next_slot - second_slot_impact_in_second_slot
    )

    first_slot_impact: float = (
        first_slot_impact_in_first_slot * travelling_group_size
    )

    second_slot_impact: float = (
        first_slot_impact_in_second_slot + second_slot_impact_in_second_slot
    ) * travelling_group_size
    third_slot_impact: float = (
        second_slot_impact_in_third_slot * travelling_group_size
    )

    return first_slot_impact, second_slot_impact, third_slot_impact


def compute_travel_impact(
    impacted_type: str,
    mobility_matrix,  # It is a DataFrame, but MyPy has issues with MultiIndex
    # DataFrames (and using loc on them)
    travelling_group_size: float,
    travelling_group_first_slot: int,
    percent_in_first_slot: float,
    leg_origin: str,
    leg_destination: str,
    distance: float,
    weighted_distance: float,
    battery_space_shifts: dict,
    vehicle_electricity_consumption: float,
) -> pd.DataFrame:

    leg_consumption: float = vehicle_electricity_consumption * distance
    weighted_leg_consumption: float = (
        vehicle_electricity_consumption * weighted_distance
    )

    first_slot_impact, second_slot_impact, third_slot_impact = get_slot_split(
        percent_in_first_slot, travelling_group_size
    )

    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        f'{impacted_type} impact',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][f'{impacted_type} impact']
        + first_slot_impact
    )
    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        f'{impacted_type} amount',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][f'{impacted_type} amount']
        + travelling_group_size * percent_in_first_slot
    )
    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        f'{impacted_type} impact kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][f'{impacted_type} impact kilometers']
        + first_slot_impact * distance
    )
    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        f'{impacted_type} kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][f'{impacted_type} kilometers']
        + travelling_group_size * percent_in_first_slot * distance
    )

    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        f'{impacted_type} impact weighted kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][f'{impacted_type} impact weighted kilometers']
        + first_slot_impact * weighted_distance
    )
    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        f'{impacted_type} weighted kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][f'{impacted_type} weighted kilometers']
        + travelling_group_size * percent_in_first_slot * weighted_distance
    )

    battery_space_shifts[(impacted_type, 'Impact')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        leg_consumption,
    ] = (
        battery_space_shifts[(impacted_type, 'Impact')].loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][leg_consumption]
        + first_slot_impact
    )
    battery_space_shifts[(impacted_type, 'Amount')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        leg_consumption,
    ] = (
        battery_space_shifts[(impacted_type, 'Amount')].loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][leg_consumption]
        + travelling_group_size * percent_in_first_slot
    )
    battery_space_shifts[(impacted_type, 'Impact Weighted')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        weighted_leg_consumption,
    ] = (
        battery_space_shifts[(impacted_type, 'Impact Weighted')].loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][weighted_leg_consumption]
        + first_slot_impact
    )
    battery_space_shifts[(impacted_type, 'Amount Weighted')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot),
        weighted_leg_consumption,
    ] = (
        battery_space_shifts[(impacted_type, 'Amount Weighted')].loc[
            leg_origin, leg_destination, travelling_group_first_slot
        ][weighted_leg_consumption]
        + travelling_group_size * percent_in_first_slot
    )

    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        f'{impacted_type} impact',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot + 1
        ][f'{impacted_type} impact']
        + second_slot_impact
    )
    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        f'{impacted_type} amount',
    ] = mobility_matrix.loc[
        leg_origin, leg_destination, travelling_group_first_slot + 1
    ][
        f'{impacted_type} amount'
    ] + travelling_group_size * (
        1 - percent_in_first_slot
    )
    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        f'{impacted_type} impact kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot + 1
        ][f'{impacted_type} impact kilometers']
        + second_slot_impact * distance
    )
    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        f'{impacted_type} kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot + 1
        ][f'{impacted_type} kilometers']
        + travelling_group_size * (1 - percent_in_first_slot) * distance
    )

    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        f'{impacted_type} impact weighted kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot + 1
        ][f'{impacted_type} impact weighted kilometers']
        + second_slot_impact * weighted_distance
    )
    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        f'{impacted_type} weighted kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot + 1
        ][f'{impacted_type} weighted kilometers']
        + travelling_group_size
        * (1 - percent_in_first_slot)
        * weighted_distance
    )

    battery_space_shifts[(impacted_type, 'Impact')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        leg_consumption,
    ] = (
        battery_space_shifts[(impacted_type, 'Impact')].loc[
            leg_origin, leg_destination, travelling_group_first_slot + 1
        ][leg_consumption]
        + second_slot_impact
    )
    battery_space_shifts[(impacted_type, 'Amount')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        leg_consumption,
    ] = battery_space_shifts[(impacted_type, 'Amount')].loc[
        leg_origin, leg_destination, travelling_group_first_slot + 1
    ][
        leg_consumption
    ] + travelling_group_size * (
        1 - percent_in_first_slot
    )
    battery_space_shifts[(impacted_type, 'Impact Weighted')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        weighted_leg_consumption,
    ] = (
        battery_space_shifts[(impacted_type, 'Impact Weighted')].loc[
            leg_origin, leg_destination, travelling_group_first_slot + 1
        ][weighted_leg_consumption]
        + second_slot_impact
    )
    battery_space_shifts[(impacted_type, 'Amount Weighted')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 1),
        weighted_leg_consumption,
    ] = battery_space_shifts[(impacted_type, 'Amount Weighted')].loc[
        leg_origin, leg_destination, travelling_group_first_slot + 1
    ][
        weighted_leg_consumption
    ] + travelling_group_size * (
        1 - percent_in_first_slot
    )

    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 2),
        f'{impacted_type} impact',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot + 2
        ][f'{impacted_type} impact']
        + third_slot_impact
    )

    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 2),
        f'{impacted_type} impact kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot + 2
        ][f'{impacted_type} impact kilometers']
        + third_slot_impact * distance
    )

    mobility_matrix.loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 2),
        f'{impacted_type} impact weighted kilometers',
    ] = (
        mobility_matrix.loc[
            leg_origin, leg_destination, travelling_group_first_slot + 2
        ][f'{impacted_type} impact weighted kilometers']
        + third_slot_impact * weighted_distance
    )

    battery_space_shifts[(impacted_type, 'Impact')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 2),
        leg_consumption,
    ] = (
        battery_space_shifts[(impacted_type, 'Impact')].loc[
            leg_origin, leg_destination, travelling_group_first_slot + 2
        ][leg_consumption]
        + third_slot_impact
    )

    battery_space_shifts[(impacted_type, 'Impact Weighted')].loc[
        (leg_origin, leg_destination, travelling_group_first_slot + 2),
        weighted_leg_consumption,
    ] = (
        battery_space_shifts[(impacted_type, 'Impact Weighted')].loc[
            leg_origin, leg_destination, travelling_group_first_slot + 2
        ][weighted_leg_consumption]
        + third_slot_impact
    )

    return mobility_matrix


def get_travelling_group_travel_impact(
    mobility_matrix: pd.DataFrame,
    travelling_group_size: float,
    travelling_group_start_slot: int,
    time_between_legs_used: list[float],
    leg_driving_times: list[float],
    start_locations_of_legs: list[str],
    end_locations_of_legs: list[str],
    leg_distances: list[float],
    leg_weighted_distances: list[float],
    battery_space_shifts: dict[tuple[str, str], pd.DataFrame],
    vehicle_electricity_consumption: float,
    HOURS_IN_A_DAY: int,
) -> pd.DataFrame:

    travelling_group_first_slot: int = travelling_group_start_slot
    percent_in_first_slot: float = 1
    if travelling_group_first_slot + 2 >= HOURS_IN_A_DAY:

        print('Trip extending beyond day end. Check your entry')
        exit()
    # The trips start uniformly within the first slot

    for leg_index, (
        leg_origin,
        leg_destination,
        time_after_leg,
        time_driving,
        distance,
        weighted_distance,
    ) in enumerate(
        zip(
            start_locations_of_legs,
            end_locations_of_legs,
            time_between_legs_used,
            leg_driving_times,
            leg_distances,
            leg_weighted_distances,
        )
    ):
        # We begin with the impact of departures

        mobility_matrix = compute_travel_impact(
            'Departures',
            mobility_matrix,
            travelling_group_size,
            travelling_group_first_slot,
            percent_in_first_slot,
            leg_origin,
            leg_destination,
            distance,
            weighted_distance,
            battery_space_shifts,
            vehicle_electricity_consumption,
        )

        # We update the slots of the group
        travelling_group_first_slot += math.floor(time_driving)
        percent_in_first_slot -= time_driving % 1

        if percent_in_first_slot <= 0:
            travelling_group_first_slot += 1
            percent_in_first_slot = 1 + percent_in_first_slot

        if travelling_group_first_slot + 2 >= HOURS_IN_A_DAY:
            print('Trip extending beyond day end. Check your entry')
            exit()

        # We now look at the impact of arrivals
        mobility_matrix = compute_travel_impact(
            'Arrivals',
            mobility_matrix,
            travelling_group_size,
            travelling_group_first_slot,
            percent_in_first_slot,
            leg_origin,
            leg_destination,
            distance,
            weighted_distance,
            battery_space_shifts,
            vehicle_electricity_consumption,
        )

        # We update the slots of the group
        travelling_group_first_slot += math.floor(time_after_leg)
        percent_in_first_slot -= time_after_leg % 1

        if percent_in_first_slot <= 0:
            travelling_group_first_slot += 1
            percent_in_first_slot = 1 + percent_in_first_slot
        if travelling_group_first_slot + 2 >= HOURS_IN_A_DAY:
            print('Trip extending beyond day end. Check your entry')
            print('dddd')
            exit()

    return mobility_matrix


def get_location_split_and_impact_of_departures_and_arrivals(
    location_names: list[str],
    location_split: pd.DataFrame,
    mobility_matrix,  # It is a DataFrame, but Mypy has issues with
    # assigning MultiIndex DataFrames
    start_probabilities: list[float],
    time_between_legs: list[float],
    leg_driving_times: list[float],
    start_locations_of_legs: list[str],
    end_locations_of_legs: list[str],
    leg_distances: list[float],
    weighted_leg_distances: list[float],
    battery_space_shifts: dict[tuple[str, str], pd.DataFrame],
    vehicle_electricity_consumption: float,
    HOURS_IN_A_DAY: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(leg_driving_times) > 0:
        # If there are no legs, the arrays stay full of zeroes
        dummy_time_between_legs: float = 0
        # This dummy value is added so that we can iterate through a
        # zip of driving times and times between legs that have the
        # same length as the amount of legs
        time_between_legs_used: list[float] = time_between_legs.copy()
        time_between_legs_used.append(dummy_time_between_legs)
        for travelling_group_start_slot, travelling_group_size in enumerate(
            start_probabilities
        ):
            if travelling_group_size > 0:
                mobility_matrix = get_travelling_group_travel_impact(
                    mobility_matrix,
                    travelling_group_size,
                    travelling_group_start_slot,
                    time_between_legs_used,
                    leg_driving_times,
                    start_locations_of_legs,
                    end_locations_of_legs,
                    leg_distances,
                    weighted_leg_distances,
                    battery_space_shifts,
                    vehicle_electricity_consumption,
                    HOURS_IN_A_DAY,
                )

        possible_origins: list[str] = list(
            set(mobility_matrix.index.get_level_values('From'))
        )

        for start_location in possible_origins:
            possible_destinations: list[str] = list(
                set(
                    (
                        mobility_matrix.loc[
                            start_location
                        ].index.get_level_values('To')
                    )
                )
            )
            for destination in possible_destinations:
                location_split[destination] = (
                    location_split[destination].values
                    + mobility_matrix.loc[start_location, destination][
                        'Arrivals impact'
                    ]
                    .cumsum()
                    .values
                )
                location_split[start_location] = (
                    location_split[start_location].values
                    - mobility_matrix.loc[start_location, destination][
                        'Departures impact'
                    ]
                    .cumsum()
                    .values
                )

    return location_split, mobility_matrix


class Leg:
    '''
    This class defines the legs and their properties, from a scenario
    file that contains a list of instances and their properties.
    Legs are point-to-point vehicle movements (i.e. movements where
    the vehicle goes from a start location and ends/stops at an end location).
    '''

    class_name: str = 'legs'

    def __init__(
        self, name: str, scenario: Box, general_parameters: Box
    ) -> None:
        self.name: str = name

        leg_parameters: Box = scenario.legs[name]
        self.vehicle: str = leg_parameters.vehicle
        self.distance: float = leg_parameters.distance
        self.duration: float = leg_parameters.duration
        self.hour_in_day_factors: list[float] = (
            leg_parameters.hour_in_day_factors
        )
        locations: Box = leg_parameters.locations
        self.start_location: str = locations.start
        self.end_location: str = locations.end
        road_type_parameters: Box = leg_parameters.road_type_mix
        self.road_type_mix: list[float] = road_type_parameters.mix


class Location:
    '''
    This class defines the locations where the vehicles are
    and their properties,  from a scenario
    file that contains a list of instances and their properties.
    '''

    class_name: str = 'locations'

    def __init__(
        self, name: str, scenario: Box, general_parameters: Box
    ) -> None:
        self.name: str = name

        this_location_parameters: Box = scenario.locations[name]
        self.vehicle: str = this_location_parameters.vehicle
        self.connectivity: float = this_location_parameters.connectivity
        self.charging_power: float = this_location_parameters.charging_power
        self.latitude: float = this_location_parameters.latitude
        self.longitude: float = this_location_parameters.longitude
        self.charging_price: float = this_location_parameters.charging_price
        self.charging_desirability: float = (
            this_location_parameters.charging_desirability
        )


class Trip:
    '''
    This class defines the  trips and their properties, from a scenario
    file that contains a list of instances and their properties.
    Trips are collections of legs that take place on a given day.
    Note that this day does not necessarily start (and end) at minight,
    but can start (and end) at an hour that is more logical/significant for
    the
    vehicle user (it could for example be 06:00 for car drivers).
    This day_start_hour
    parameter is universal for all trips
    This value is set in the scenario files.
    '''

    class_name: str = 'trips'

    def __init__(
        self, name: str, scenario: Box, general_parameters: Box
    ) -> None:
        self.name: str = name

        trip_parameters: Box = scenario.trips[name]
        self.legs: list[str] = trip_parameters.legs
        self.time_between_legs: list[float] = trip_parameters.time_between_legs
        self.percentage_station_users: float = (
            trip_parameters.percentage_station_users
        )

        self.start_probabilities: list[float] = (
            trip_parameters.start_probabilities
        )
        self.repeated_sequence: list[str] = trip_parameters.repeated_sequence
        self.repetition_amounts: list[int] = trip_parameters.repetition_amounts
        self.time_between_repetitions: list[float] = (
            trip_parameters.time_between_repetitions
        )

        self.day_start_hour: int = scenario.mobility_module.day_start_hour
        self.leg_driving_times: list[float] = [
            scenario.legs[leg_name].duration for leg_name in self.legs
        ]

        trip_legs_store: list[str] = self.legs.copy()

        time_between_legs_store: list[float] = self.time_between_legs.copy()
        leg_driving_times_store: list[float] = self.leg_driving_times.copy()
        if len(self.repeated_sequence) > 0:
            self.legs = []
            self.time_between_legs = []
            self.leg_driving_times = []
            repetition_iteration_index: int = 0
            for leg_index, leg in enumerate(trip_legs_store):

                if leg not in self.repeated_sequence:
                    self.legs.append(leg)
                    if leg_index < len(trip_legs_store) - 1:
                        self.time_between_legs.append(
                            time_between_legs_store[leg_index]
                        )
                    self.leg_driving_times.append(
                        leg_driving_times_store[leg_index]
                    )
                elif leg == self.repeated_sequence[0]:
                    for repetition in range(
                        self.repetition_amounts[repetition_iteration_index] + 1
                    ):
                        for leg_to_add_index, leg_to_add in enumerate(
                            self.repeated_sequence
                        ):
                            self.legs.append(leg_to_add)
                            if (
                                leg_to_add_index
                                < len(self.repeated_sequence) - 1
                            ):
                                self.time_between_legs.append(
                                    time_between_legs_store[leg_index]
                                )
                            self.leg_driving_times.append(
                                leg_driving_times_store[leg_index]
                            )
                        if (
                            repetition
                            < self.repetition_amounts[
                                repetition_iteration_index
                            ]
                        ):
                            self.time_between_legs.append(
                                self.time_between_repetitions[
                                    repetition_iteration_index
                                ]
                            )

                        else:

                            add_final_time_between_legs: bool = True

                            if leg_index == (
                                len(trip_legs_store)
                                - len(self.repeated_sequence)
                            ):

                                if (
                                    trip_legs_store[-1]
                                    == self.repeated_sequence[-1]
                                ):
                                    add_final_time_between_legs = False
                                    # If the last leg of the trip
                                    # is also the last leg of the repeated
                                    # sequence, we don't need to add
                                    # the time after it (since it is the
                                    # last leg of the trip).

                            if add_final_time_between_legs:
                                self.time_between_legs.append(
                                    time_between_legs_store[
                                        leg_index
                                        + len(self.repeated_sequence)
                                        - 1
                                    ]
                                )

                    repetition_iteration_index += 1

        self.start_locations_of_legs: list[str] = [
            scenario.legs[leg_name].locations.start for leg_name in self.legs
        ]
        self.end_locations_of_legs: list[str] = [
            scenario.legs[leg_name].locations.end for leg_name in self.legs
        ]
        self.location_names: list[str] = sorted(
            list(
                set(self.start_locations_of_legs + self.end_locations_of_legs)
            )
        )
        if self.name.startswith('stay_put_'):
            stay_put_location: str = self.name.split('stay_put_')[1]
            self.location_names = [stay_put_location]
        # sorted so that the order is always the same

        self.leg_distances: list[float] = [
            scenario.legs[leg_name].distance for leg_name in self.legs
        ]

        self.weighted_leg_distances: list[float] = []
        for leg_name in self.legs:
            road_type_mix: np.ndarray = np.array(
                scenario.legs[leg_name].road_type_mix.mix
            )
            road_type_weights: np.ndarray = np.array(
                scenario.transport_factors.weights
            )
            road_type_factor: float = float(
                sum(road_type_mix * road_type_weights)
            )
            leg_distance: float = scenario.legs[leg_name].distance
            leg_weighted_distance: float = leg_distance * road_type_factor
            self.weighted_leg_distances.append(leg_weighted_distance)

        self.unique_leg_distances: list[float] = list(set(self.leg_distances))
        self.unique_weighted_leg_distances: list[float] = list(
            set(self.weighted_leg_distances)
        )
        vehicle_electricity_consumption: float = (
            scenario.vehicle.base_consumption_per_km.electricity_kWh
        )

        self.unique_leg_consumptions: list[float] = [
            unique_distance * vehicle_electricity_consumption
            for unique_distance in self.unique_leg_distances
        ]

        self.unique_weighted_leg_consumptions: list[float] = [
            unique_distance * vehicle_electricity_consumption
            for unique_distance in self.unique_weighted_leg_distances
        ]

        # We want to create a mobility matrix for the trip. This matrix will
        # have start and end locations (plus hour in day, starting
        # at day start) as an index, and departures, arrivals as columns (
        # each with amounts, distances, weighted distances)
        HOURS_IN_A_DAY: int = general_parameters.time.HOURS_IN_A_DAY
        parameters_of_legs: Box = scenario.legs
        unique_legs: list[str] = []
        for trip_leg in self.legs:
            if trip_leg not in unique_legs:
                unique_legs.append(trip_leg)

        leg_tuples: list[tuple[str, str]] = [
            (
                parameters_of_legs[trip_leg].locations.start,
                parameters_of_legs[trip_leg].locations.end,
            )
            for trip_leg in unique_legs
        ]

        # We only want the start and end locations that are in the legs
        mobility_index_tuples: list[tuple[str, str, int]] = [
            (leg_tuple[0], leg_tuple[1], hour_number)
            for leg_tuple in leg_tuples
            for hour_number in range(HOURS_IN_A_DAY)
        ]

        mobility_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
            mobility_index_tuples,
            names=['From', 'To', 'Hour number (from day start)'],
        )
        mobility_quantities: list[str] = (
            scenario.mobility_module.mobility_quantities
        )

        self.mobility_matrix: pd.DataFrame = pd.DataFrame(
            np.zeros((len(mobility_index), len(mobility_quantities))),
            columns=mobility_quantities,
            index=mobility_index,
        )

        self.mobility_matrix = self.mobility_matrix.sort_index()

        # We also want to store the battery space shifts true to legs.
        # We track this as departure and arrivals (including a version with
        # impact versions).
        base_dataframe_for_battery_space_shifts: pd.DataFrame = pd.DataFrame(
            np.zeros((len(mobility_index), len(self.unique_leg_consumptions))),
            columns=self.unique_leg_consumptions,
            index=mobility_index,
        )
        base_dataframe_for_weighted_battery_space_shifts: pd.DataFrame = (
            pd.DataFrame(
                np.zeros(
                    (
                        len(mobility_index),
                        len(self.unique_weighted_leg_consumptions),
                    )
                ),
                columns=self.unique_weighted_leg_consumptions,
                index=mobility_index,
            )
        )
        base_dataframe_for_weighted_battery_space_shifts = (
            base_dataframe_for_weighted_battery_space_shifts.sort_index()
        )
        self.battery_space_shifts_departures: pd.DataFrame = (
            base_dataframe_for_battery_space_shifts.copy()
        )
        self.battery_space_shifts_departures = (
            self.battery_space_shifts_departures.sort_index()
        )
        self.battery_space_shifts_departures_impact: pd.DataFrame = (
            base_dataframe_for_battery_space_shifts.copy()
        )
        self.battery_space_shifts_departures_impact = (
            self.battery_space_shifts_departures_impact.sort_index()
        )
        self.battery_space_shifts_arrivals: pd.DataFrame = (
            base_dataframe_for_battery_space_shifts.copy()
        )
        self.battery_space_shifts_arrivals = (
            self.battery_space_shifts_arrivals.sort_index()
        )
        self.battery_space_shifts_arrivals_impact: pd.DataFrame = (
            base_dataframe_for_battery_space_shifts.copy()
        )
        self.battery_space_shifts_arrivals_impact = (
            self.battery_space_shifts_arrivals_impact.sort_index()
        )
        self.battery_space_shifts_departures_weighted: pd.DataFrame = (
            base_dataframe_for_weighted_battery_space_shifts.copy()
        )
        self.battery_space_shifts_departures_weighted = (
            self.battery_space_shifts_departures_weighted.sort_index()
        )
        self.battery_space_shifts_departures_impact_weighted: pd.DataFrame = (
            base_dataframe_for_weighted_battery_space_shifts.copy()
        )
        self.battery_space_shifts_departures_impact_weighted = (
            self.battery_space_shifts_departures_impact_weighted.sort_index()
        )
        self.battery_space_shifts_arrivals_weighted: pd.DataFrame = (
            base_dataframe_for_weighted_battery_space_shifts.copy()
        )
        self.battery_space_shifts_arrivals_weighted = (
            self.battery_space_shifts_arrivals_weighted.sort_index()
        )
        self.battery_space_shifts_arrivals_impact_weighted: pd.DataFrame = (
            base_dataframe_for_weighted_battery_space_shifts.copy()
        )
        self.battery_space_shifts_arrivals_impact_weighted = (
            self.battery_space_shifts_arrivals_impact_weighted.sort_index()
        )
        self.battery_space_shifts: dict[tuple[str, str], pd.DataFrame] = {}
        self.battery_space_shifts[('Departures', 'Amount')] = (
            self.battery_space_shifts_departures
        )
        self.battery_space_shifts[('Departures', 'Impact')] = (
            self.battery_space_shifts_departures_impact
        )
        self.battery_space_shifts[('Departures', 'Amount Weighted')] = (
            self.battery_space_shifts_departures_weighted
        )
        self.battery_space_shifts[('Departures', 'Impact Weighted')] = (
            self.battery_space_shifts_departures_impact_weighted
        )
        self.battery_space_shifts[('Arrivals', 'Amount')] = (
            self.battery_space_shifts_arrivals
        )
        self.battery_space_shifts[('Arrivals', 'Impact')] = (
            self.battery_space_shifts_arrivals_impact
        )
        self.battery_space_shifts[('Arrivals', 'Amount Weighted')] = (
            self.battery_space_shifts_arrivals_weighted
        )
        self.battery_space_shifts[('Arrivals', 'Impact Weighted')] = (
            self.battery_space_shifts_arrivals_impact_weighted
        )

        # We want to track where the vehicle is
        self.location_split: pd.DataFrame = pd.DataFrame(
            np.zeros((HOURS_IN_A_DAY, len(self.location_names))),
            columns=self.location_names,
            index=range(HOURS_IN_A_DAY),
        )
        self.location_split.index.name = 'Hour in day (from day start)'

        if self.name.startswith('stay_put_'):
            stay_put_location = self.name.split('stay_put_')[1]
            self.location_split[stay_put_location] = 1
        else:
            first_leg: str = self.legs[0]
            initial_location: str = scenario.legs[first_leg].locations.start
            self.location_split[initial_location] = 1
        self.location_split, self.mobility_matrix = (
            get_location_split_and_impact_of_departures_and_arrivals(
                self.location_names,
                self.location_split,
                self.mobility_matrix,
                self.start_probabilities,
                self.time_between_legs,
                self.leg_driving_times,
                self.start_locations_of_legs,
                self.end_locations_of_legs,
                self.leg_distances,
                self.weighted_leg_distances,
                self.battery_space_shifts,
                vehicle_electricity_consumption,
                HOURS_IN_A_DAY,
            )
        )

        # We can also get the percentage driving

        self.percentage_driving: pd.Series[float] = (
            1 - self.location_split.sum(axis=1)
        )

        # We also get the connectivity:
        self.connectivity_per_location: pd.DataFrame = (
            self.location_split.copy()
        )
        self.maximal_delivered_power_per_location: pd.DataFrame = (
            self.location_split.copy()
        )  # How much the network can discharge
        self.maximal_received_power_per_location: pd.DataFrame = (
            self.location_split.copy()
        )  # How much of tht the vehicles can receive
        self.vehicle_discharge_power_per_location: pd.DataFrame = (
            self.location_split.copy()
        )
        self.discharge_power_to_network_per_location: pd.DataFrame = (
            self.location_split.copy()
        )

        for location_name in self.location_names:
            this_location_parameters: Box = scenario.locations[location_name]
            location_connectivity: float = (
                this_location_parameters.connectivity
            )
            charging_power: float = this_location_parameters.charging_power
            charger_efficiency: float = (
                this_location_parameters.charger_efficiency
            )
            this_location_maximal_delivered_power: float = (
                location_connectivity * charging_power / charger_efficiency
            )
            this_location_maximal_received_power: float = (
                location_connectivity * charging_power
            )
            this_location_vehicle_discharge_power: float = (
                this_location_parameters.vehicle_discharge_power
            )
            this_location_proportion_of_discharge_to_network: float = (
                this_location_parameters.proportion_of_discharge_to_network
            )
            this_location_discharge_power_to_network: float = (
                this_location_vehicle_discharge_power
                * this_location_proportion_of_discharge_to_network
            )

            self.connectivity_per_location[location_name] = (
                self.connectivity_per_location[location_name]
                * location_connectivity
            )
            self.maximal_delivered_power_per_location[location_name] = (
                self.maximal_delivered_power_per_location[location_name]
                * this_location_maximal_delivered_power
            )
            self.maximal_received_power_per_location[location_name] = (
                self.maximal_received_power_per_location[location_name]
                * this_location_maximal_received_power
            )

            self.vehicle_discharge_power_per_location[location_name] = (
                self.vehicle_discharge_power_per_location[location_name]
                * this_location_vehicle_discharge_power
            )
            self.discharge_power_to_network_per_location[location_name] = (
                self.discharge_power_to_network_per_location[location_name]
                * this_location_discharge_power_to_network
            )
        self.connectivity: pd.Series = self.connectivity_per_location.sum(
            axis=1
        )
        self.maximal_delivered_power: pd.Series = (
            self.maximal_delivered_power_per_location.sum(axis=1)
        )
        self.maximal_received_power: pd.Series = (
            self.maximal_received_power_per_location.sum(axis=1)
        )
        self.vehicle_discharge_power: pd.Series = (
            self.vehicle_discharge_power_per_location.sum(axis=1)
        )
        self.discharge_power_to_network: pd.Series = (
            self.discharge_power_to_network_per_location.sum(axis=1)
        )
        dummy_time_between_legs: float = 0
        # This dummy value is added so that we can iterate through a
        # zip of driving times and times between legs that have the
        # same length as the amount of legs
        time_between_legs_used: list[float] = self.time_between_legs.copy()
        time_between_legs_used.append(dummy_time_between_legs)

        self.charging_sessions: list[TripChargingSession] = (
            get_trip_charging_sessions(
                self.end_locations_of_legs,
                self.start_probabilities,
                time_between_legs_used,
                self.leg_driving_times,
                self.leg_distances,
                self.weighted_leg_distances,
                scenario,
                general_parameters,
            )
        )

        # We now can create a mobility matrix for the whole run
        run_time_tags: pd.DatetimeIndex = run_time.get_time_range(
            scenario, general_parameters
        )[0]

        # We only want the start and end locations that are in the legs
        run_mobility_index_tuples: list[tuple[str, str, datetime.datetime]] = [
            (leg_tuple[0], leg_tuple[1], time_tag)
            for leg_tuple in leg_tuples
            for time_tag in run_time_tags
        ]

        mobility_index_names: list[str] = (
            scenario.mobility_module.mobility_index_names
        )
        run_mobility_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
            run_mobility_index_tuples, names=mobility_index_names
        )

        self.run_mobility_matrix: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                self.mobility_matrix,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        ).astype(float)

        self.run_battery_space_shifts_departures: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                self.battery_space_shifts_departures,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_battery_space_shifts_departures_impact: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                self.battery_space_shifts_departures_impact,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_battery_space_shifts_arrivals: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                self.battery_space_shifts_arrivals,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_battery_space_shifts_arrivals_impact: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                self.battery_space_shifts_arrivals_impact,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )

        self.run_battery_space_shifts_departures_weighted: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                self.battery_space_shifts_departures_weighted,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_battery_space_shifts_departures_impact_weighted: (
            pd.DataFrame
        ) = mobility_matrix_to_run_mobility_matrix(
            self.battery_space_shifts_departures_impact_weighted,
            leg_tuples,
            run_mobility_index,
            run_time_tags,
            self.day_start_hour,
            scenario,
            general_parameters,
        )
        self.run_battery_space_shifts_arrivals_weighted: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                self.battery_space_shifts_arrivals_weighted,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_battery_space_shifts_arrivals_impact_weighted: (
            pd.DataFrame
        ) = mobility_matrix_to_run_mobility_matrix(
            self.battery_space_shifts_arrivals_impact_weighted,
            leg_tuples,
            run_mobility_index,
            run_time_tags,
            self.day_start_hour,
            scenario,
            general_parameters,
        )

        # We also do this for some other quantities
        day_start_hour: int = scenario.mobility_module.day_start_hour
        self.run_location_split: pd.DataFrame = run_time.from_day_to_run(
            self.location_split,
            run_time_tags,
            day_start_hour,
            scenario,
            general_parameters,
        )

        self.run_connectivity_per_location: pd.DataFrame = (
            run_time.from_day_to_run(
                self.connectivity_per_location,
                run_time_tags,
                day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_maximal_delivered_power_per_location: pd.DataFrame = (
            run_time.from_day_to_run(
                self.maximal_delivered_power_per_location,
                run_time_tags,
                day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_maximal_received_power_per_location: pd.DataFrame = (
            run_time.from_day_to_run(
                self.maximal_received_power_per_location,
                run_time_tags,
                day_start_hour,
                scenario,
                general_parameters,
            )
        )

        self.run_vehicle_discharge_power_per_location: pd.DataFrame = (
            run_time.from_day_to_run(
                self.vehicle_discharge_power_per_location,
                run_time_tags,
                day_start_hour,
                scenario,
                general_parameters,
            )
        )

        self.run_discharge_power_to_network_per_location: pd.DataFrame = (
            run_time.from_day_to_run(
                self.discharge_power_to_network_per_location,
                run_time_tags,
                day_start_hour,
                scenario,
                general_parameters,
            )
        )

        self.run_percentage_driving: pd.Series = (
            1 - self.run_location_split.sum(axis=1)
        )

        self.run_connectivity: pd.Series = (
            self.run_connectivity_per_location.sum(axis=1)
        )
        self.run_maximal_delivered_power: pd.Series = (
            self.run_maximal_delivered_power_per_location.sum(axis=1)
        )
        self.run_maximal_received_power: pd.Series = (
            self.run_maximal_received_power_per_location.sum(axis=1)
        )

        self.run_vehicle_discharge_power: pd.Series = (
            self.run_vehicle_discharge_power_per_location.sum(axis=1)
        )

        self.run_discharge_power_to_network: pd.Series = (
            self.run_discharge_power_to_network_per_location.sum(axis=1)
        )

        self.next_leg_kilometers: pd.DataFrame = pd.DataFrame(
            np.zeros((HOURS_IN_A_DAY, len(self.location_names))),
            columns=self.location_names,
            index=range(HOURS_IN_A_DAY),
        )
        self.next_leg_kilometers.index.name = 'Hour number (from day start)'
        # The standard version sets the kilometers in the time slot
        # before departure, this second, cumulative, version does so from
        # the moment the vehicles arrive
        # (or day start for the first leg of the trip)
        self.next_leg_kilometers_cumulative: pd.DataFrame = (
            self.next_leg_kilometers.copy()
        )

        previous_leg_arrivals_amount: list[float] = []
        for leg_index, leg_name in enumerate(self.legs):

            leg_parameters = scenario.legs[leg_name]
            start_location = leg_parameters.locations.start
            end_location = leg_parameters.locations.end

            if leg_index == 0:

                for hour_index in range(HOURS_IN_A_DAY - 1):
                    # We skip the last time slot, as this should wrap the trip
                    # and we are not looking into the next day
                    # with this apporach

                    # For the standard version, we look if the vehicle
                    # is set to depart in the next time
                    upcoming_departures_kilometers = self.mobility_matrix.loc[
                        (start_location, end_location, hour_index + 1),
                        'Departures kilometers',
                    ]

                    self.next_leg_kilometers.loc[
                        hour_index, start_location
                    ] = (
                        self.next_leg_kilometers.loc[hour_index][
                            start_location
                        ]
                        + upcoming_departures_kilometers
                    )

                    # For the other version, we look at all future departures

                    all_future_departures_kilometers = (
                        self.mobility_matrix.loc[
                            (
                                start_location,
                                end_location,
                                list(range(hour_index + 1, HOURS_IN_A_DAY)),
                            ),
                            'Departures kilometers',
                        ].sum()
                    )

                    self.next_leg_kilometers_cumulative.loc[
                        hour_index, start_location
                    ] = (
                        self.next_leg_kilometers_cumulative.loc[hour_index][
                            start_location
                        ]
                        + all_future_departures_kilometers
                    )

            else:
                for hour_index in range(HOURS_IN_A_DAY - 1):
                    # We skip the last time slot, as this should wrap the trip
                    # and we are not looking into the next day
                    # with this approach

                    # We do the same as for the first leg, but we need
                    # to limit that to the vehicles that already have
                    # arrived at the end location
                    upcoming_departures_kilometers_raw: float = (
                        self.mobility_matrix['Departures kilometers'].loc[
                            start_location, end_location, hour_index + 1
                        ]
                    )

                    previous_arrivals_to_use: float = sum(
                        previous_leg_arrivals_amount[: hour_index + 1]
                    )
                    actual_upcoming_departures_kilometers = (
                        upcoming_departures_kilometers_raw
                        * previous_arrivals_to_use
                    )

                    self.next_leg_kilometers.loc[
                        hour_index, start_location
                    ] = (
                        self.next_leg_kilometers.loc[hour_index][
                            start_location
                        ]
                        + actual_upcoming_departures_kilometers
                    )

                    # Once again, the variant applies to all future departures

                    all_future_departures_kilometers_raw: float = (
                        self.mobility_matrix['Departures kilometers']
                        .loc[start_location, end_location][
                            list(range(hour_index + 1, HOURS_IN_A_DAY))
                        ]
                        .sum()
                    )

                    actual_all_future_departures_kilometers = (
                        previous_arrivals_to_use
                        * all_future_departures_kilometers_raw
                    )

                    self.next_leg_kilometers_cumulative.loc[
                        hour_index, start_location
                    ] = (
                        self.next_leg_kilometers_cumulative.loc[hour_index][
                            start_location
                        ]
                        + actual_all_future_departures_kilometers
                    )

            previous_leg_arrivals_amount = self.mobility_matrix[
                'Arrivals amount'
            ].loc[start_location, end_location]

        self.next_leg_charge_to_vehicle: pd.DataFrame = (
            self.next_leg_kilometers.copy()
        )
        self.next_leg_charge_from_network: pd.DataFrame = (
            self.next_leg_kilometers.copy()
        )
        self.next_leg_charge_to_vehicle_cumulative: pd.DataFrame = (
            self.next_leg_kilometers_cumulative.copy()
        )
        self.next_leg_charge_from_network_cumulative: pd.DataFrame = (
            self.next_leg_kilometers_cumulative.copy()
        )

        for location_name in self.location_names:
            vehicle_consumption_per_km: float = (
                scenario.vehicle.base_consumption_per_km.electricity_kWh
            )
            charger_efficiency = scenario.locations[
                location_name
            ].charger_efficiency

            draw_from_network_per_km: float = (
                vehicle_consumption_per_km / charger_efficiency
            )
            self.next_leg_charge_to_vehicle[location_name] = (
                self.next_leg_charge_to_vehicle[location_name]
                * vehicle_consumption_per_km
            )
            self.next_leg_charge_to_vehicle_cumulative[location_name] = (
                self.next_leg_charge_to_vehicle_cumulative[location_name]
                * vehicle_consumption_per_km
            )
            self.next_leg_charge_from_network[location_name] = (
                self.next_leg_charge_from_network[location_name]
                * draw_from_network_per_km
            )
            self.next_leg_charge_from_network_cumulative[location_name] = (
                self.next_leg_charge_from_network_cumulative[location_name]
                * draw_from_network_per_km
            )

        self.run_next_leg_kilometers: pd.DataFrame = run_time.from_day_to_run(
            self.next_leg_kilometers,
            run_time_tags,
            self.day_start_hour,
            scenario,
            general_parameters,
        )
        self.run_next_leg_kilometers_cumulative: pd.DataFrame = (
            run_time.from_day_to_run(
                self.next_leg_kilometers_cumulative,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )

        self.run_next_leg_charge_to_vehicle: pd.DataFrame = (
            run_time.from_day_to_run(
                self.next_leg_charge_to_vehicle,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_next_leg_charge_to_vehicle_cumulative: pd.DataFrame = (
            run_time.from_day_to_run(
                self.next_leg_charge_to_vehicle_cumulative,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )

        self.run_next_leg_charge_from_network: pd.DataFrame = (
            run_time.from_day_to_run(
                self.next_leg_charge_from_network,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        self.run_next_leg_charge_from_network_cumulative: pd.DataFrame = (
            run_time.from_day_to_run(
                self.next_leg_charge_from_network_cumulative,
                run_time_tags,
                self.day_start_hour,
                scenario,
                general_parameters,
            )
        )


class TripChargingSession:
    '''
    This class defines the charging sessions of an incoming group in a Trip.
    The quantities other than start time, end time, and location
    are proprtional to the size of the session (the group travelling).
    '''

    class_name: str = 'trip_charging_session'

    def __init__(
        self,
        location_name: str,
        session_size: float,
        session_start: float,
        session_end: float,
        incoming_consumption: float,
        outgoing_consumption: float,
        location_connectivity: float,
        location_charging_power_to_vehicle: float,
        location_charging_power_from_network: float,
        location_discharge_power_from_vehicle: float,
        location_discharge_power_to_network: float,
    ) -> None:

        self.start_time: float = session_start
        self.end_time: float = session_end
        self.location: str = location_name
        self.previous_leg_consumption: float = (
            incoming_consumption * session_size
        )
        self.next_leg_consumption: float = outgoing_consumption * session_size
        self.connectivity: float = location_connectivity * session_size
        self.power_to_vehicle: float = (
            location_charging_power_to_vehicle * session_size
        )
        self.power_from_network: float = (
            location_charging_power_from_network * session_size
        )
        self.power_from_vehicle: float = (
            location_discharge_power_from_vehicle * session_size
        )
        self.power_to_network: float = (
            location_discharge_power_to_network * session_size
        )


def declare_class_instances(
    ChosenClass: ty.Type, scenario: Box, general_parameters: Box
) -> list[ty.Type]:
    '''
    This function creates the instances of a class (ChosenClass),
    based on a scenario file name where the instances and their properties
    are given.
    '''
    scenario_vehicle: str = scenario.vehicle.name
    class_name: str = ChosenClass.class_name

    class_instances: list[str] = scenario[class_name]

    instances: list[ty.Type] = []

    for class_instance in class_instances:
        append_instance: bool = True
        if class_name == 'trips':
            trip_vehicle: str = scenario.trips[class_instance].vehicle
            if trip_vehicle != scenario_vehicle:
                append_instance = False
        elif class_name == 'locations':
            location_vehicle: str = scenario.locations[class_instance].vehicle
            if location_vehicle != scenario_vehicle:
                append_instance = False
        elif class_name == 'legs':
            leg_vehicle: str = scenario.legs[class_instance].vehicle
            if leg_vehicle != scenario_vehicle:
                append_instance = False

        if append_instance:
            instances.append(
                ChosenClass(class_instance, scenario, general_parameters)
            )

    return instances


# @cook.function_timer
def declare_all_instances(
    scenario: Box, case_name: str, general_parameters: Box
) -> tuple[pd.DataFrame, list[ty.Type], list[ty.Type], list[ty.Type]]:
    '''
    This declares all instances of the various objects
    (legs, locations,  trips).
    '''
    scenario_name: str = scenario.name
    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'
    locations: list[ty.Type] = declare_class_instances(
        Location, scenario, general_parameters
    )

    legs: list[ty.Type] = declare_class_instances(
        Leg, scenario, general_parameters
    )

    # We want to get the location connections
    location_connections_headers: list[str] = (
        scenario.mobility_module.location_connections_headers
    )
    location_connections_index_tuples: list[tuple[str, str]] = [
        (start_location.name, end_location.name)
        for start_location in locations
        for end_location in locations
    ]
    location_connections_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
        location_connections_index_tuples, names=['From', 'To']
    )
    location_connections: pd.DataFrame = pd.DataFrame(
        columns=location_connections_headers, index=location_connections_index
    )
    road_type_weights: np.ndarray = np.array(
        scenario.transport_factors.weights
    )
    for leg in legs:
        road_type_factor: float = sum(leg.road_type_mix * road_type_weights)
        fill_values: list[float] = [
            leg.duration,
            leg.distance,
            road_type_factor * leg.distance,
        ]
        for fill_value, location_connection_header in zip(
            fill_values, location_connections_headers
        ):
            location_connections.loc[
                (leg.start_location, leg.end_location),
                location_connection_header,
            ] = fill_value
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    if pickle_interim_files:
        location_connections.to_pickle(
            f'{output_folder}/{scenario_name}_location_connections.pkl'
        )

    trips: list[ty.Type] = declare_class_instances(
        Trip, scenario, general_parameters
    )

    # We want to save the moblity matrixes
    if pickle_interim_files:
        for trip in trips:

            mobility_table_name: str = (
                f'{scenario_name}_{trip.name}_mobility_matrix'
            )

            trip.mobility_matrix.to_pickle(
                f'{output_folder}/{mobility_table_name}.pkl'
            )

            run_mobility_table_name: str = (
                f'{scenario_name}_{trip.name}_run_mobility_matrix'
            )
            trip.run_mobility_matrix.to_pickle(
                f'{output_folder}/{run_mobility_table_name}.pkl'
            )
            trip.next_leg_kilometers.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                'next_leg_kilometers.pkl'
            )
            trip.run_next_leg_kilometers.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_next_leg_kilometers.pkl'
            )
            trip.next_leg_kilometers_cumulative.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}'
                f'_next_leg_kilometers_cumulative.pkl'
            )
            trip.run_next_leg_kilometers_cumulative.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_next_leg_kilometers_cumulative.pkl'
            )
            trip.next_leg_charge_to_vehicle.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_next_leg_charge_to_vehicle.pkl'
            )
            trip.next_leg_charge_from_network.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_next_leg_charge_from_network.pkl'
            )
            trip.run_next_leg_charge_to_vehicle.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_next_leg_charge_to_vehicle.pkl'
            )
            trip.run_next_leg_charge_from_network.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_next_leg_charge_from_network.pkl'
            )
            trip.next_leg_charge_to_vehicle_cumulative.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_next_leg_charge_to_vehicle_cumulative.pkl'
            )
            trip.next_leg_charge_from_network_cumulative.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}'
                f'_next_leg_charge_from_network_cumulative.pkl'
            )
            trip.run_next_leg_charge_to_vehicle_cumulative.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}'
                f'_run_next_leg_charge_to_vehicle_cumulative.pkl'
            )
            trip.run_next_leg_charge_from_network_cumulative.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}'
                f'_run_next_leg_charge_from_network_cumulative.pkl'
            )
            trip.location_split.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_location_split.pkl'
            )
            trip.run_location_split.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_location_split.pkl'
            )
            trip.percentage_driving.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_percentage_driving.pkl'
            )
            trip.run_percentage_driving.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_percentage_driving.pkl'
            )

            trip.connectivity_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_connectivity_per_location.pkl'
            )

            trip.run_connectivity_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_connectivity_per_location.pkl'
            )

            trip.connectivity.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_connectivity.pkl'
            )

            trip.run_connectivity.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_connectivity.pkl'
            )

            trip.maximal_delivered_power_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_maximal_delivered_power_per_location.pkl'
            )
            trip.run_maximal_delivered_power_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_maximal_delivered_power_per_location.pkl'
            )

            trip.maximal_delivered_power.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_maximal_delivered_power.pkl'
            )
            trip.run_maximal_delivered_power.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_maximal_delivered_power.pkl'
            )

            trip.maximal_received_power_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_maximal_received_power_per_location.pkl'
            )
            trip.run_maximal_received_power_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_maximal_received_power_per_location.pkl'
            )

            trip.maximal_received_power.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_maximal_received_power.pkl'
            )
            trip.run_maximal_received_power.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_maximal_received_power.pkl'
            )

            trip.vehicle_discharge_power_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_vehicle_discharge_power_per_location.pkl'
            )
            trip.run_vehicle_discharge_power_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_vehicle_discharge_power_per_location.pkl'
            )

            trip.vehicle_discharge_power.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_vehicle_discharge_power.pkl'
            )
            trip.run_vehicle_discharge_power.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_vehicle_discharge_power.pkl'
            )

            trip.discharge_power_to_network_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_discharge_power_to_network_per_location.pkl'
            )
            trip.run_discharge_power_to_network_per_location.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_discharge_power_to_network_per_location.pkl'
            )

            trip.discharge_power_to_network.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_discharge_power_to_network.pkl'
            )
            trip.run_discharge_power_to_network.to_pickle(
                f'{output_folder}/{scenario_name}_'
                f'{trip.name}_run_discharge_power_to_network.pkl'
            )

            trip.battery_space_shifts_departures.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'battery_space_shifts_departures'
                f'.pkl'
            )

            trip.battery_space_shifts_departures_impact.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'battery_space_shifts_departures_impact'
                f'.pkl'
            )

            trip.battery_space_shifts_arrivals.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'battery_space_shifts_arrivals'
                f'.pkl'
            )

            trip.battery_space_shifts_arrivals_impact.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'battery_space_shifts_arrivals_impact'
                f'.pkl'
            )

            trip.battery_space_shifts_departures_weighted.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'battery_space_shifts_departures_weighted'
                f'.pkl'
            )

            trip.battery_space_shifts_departures_impact_weighted.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'battery_space_shifts_departures_impact_weighted'
                f'.pkl'
            )

            trip.battery_space_shifts_arrivals_weighted.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'battery_space_shifts_arrivals_weighted'
                f'.pkl'
            )

            trip.battery_space_shifts_arrivals_impact_weighted.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'battery_space_shifts_arrivals_impact_weighted'
                f'.pkl'
            )

            trip.run_battery_space_shifts_departures.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'run_battery_space_shifts_departures'
                f'.pkl'
            )

            trip.run_battery_space_shifts_departures_impact.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'run_battery_space_shifts_departures_impact'
                f'.pkl'
            )

            trip.run_battery_space_shifts_arrivals.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'run_battery_space_shifts_arrivals'
                f'.pkl'
            )

            trip.run_battery_space_shifts_arrivals_impact.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'run_battery_space_shifts_arrivals_impact'
                f'.pkl'
            )

            trip.run_battery_space_shifts_departures_weighted.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'run_battery_space_shifts_departures_weighted'
                f'.pkl'
            )

            trip.run_battery_space_shifts_departures_impact_weighted.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'run_battery_space_shifts_departures_impact_weighted'
                f'.pkl'
            )

            trip.run_battery_space_shifts_arrivals_weighted.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'run_battery_space_shifts_arrivals_weighted'
                f'.pkl'
            )

            trip.run_battery_space_shifts_arrivals_impact_weighted.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'run_battery_space_shifts_arrivals_impact_weighted'
                f'.pkl'
            )
            charging_sessions_headers: list[str] = (
                general_parameters.sessions_dataframe.dataframe_headers
            )

            charging_sessions_dataframe: pd.DataFrame = (
                get_charging_sessions_dataframe(
                    trip.charging_sessions,
                    general_parameters,
                    charging_sessions_headers,
                )
            )

            charging_sessions_dataframe.to_pickle(
                f'{output_folder}/{scenario_name}_{trip.name}_'
                f'charging_sessions'
                f'.pkl'
            )

    return location_connections, legs, locations, trips


def get_charging_sessions_dataframe(
    charging_sessions: list,
    general_parameters: Box,
    chosen_headers: list[str],
) -> pd.DataFrame:
    charging_sessions_dataframe: pd.DataFrame = pd.DataFrame(
        index=range(len(charging_sessions))
    )

    charging_sessions_properties: list[str] = (
        general_parameters.sessions_dataframe.properties
    )
    for session_index, session in enumerate(charging_sessions):
        for charging_session_header, charging_session_property in zip(
            chosen_headers, charging_sessions_properties
        ):

            charging_sessions_dataframe.loc[
                session_index, charging_session_header
            ] = getattr(session, charging_session_property)

    return charging_sessions_dataframe


if __name__ == '__main__':
    start_: datetime.datetime = datetime.datetime.now()
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: Box = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    case_name = 'Mopo'
    test_scenario_name: str = 'XX_bus'
    scenario_file_name: str = (
        f'scenarios/{case_name}/{test_scenario_name}.toml'
    )
    scenario: Box = cook.parameters_from_TOML(scenario_file_name)
    scenario.name = test_scenario_name
    location_connecions, legs, locations, trips = declare_all_instances(
        scenario, case_name, general_parameters
    )
    for trip in trips:
        print(trip.name)
        print(trip.mobility_matrix)
        trip.mobility_matrix.to_csv(
            f'test_bus_moility_matrices/{trip.name}.csv'
        )
        print(trip.next_leg_kilometers)
        exit()

    print((datetime.datetime.now() - start_).total_seconds())
