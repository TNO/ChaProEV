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


def mobility_matrix_to_run_mobility_matrix(
    matrix_to_expand,  # It is a DataFRame, but MyPy seems to have issues
    # with DataFrmes with a MultiIndex
    leg_tuples: ty.List[ty.Tuple[str, str]],
    run_index: pd.MultiIndex,
    run_time_tags: pd.DatetimeIndex,
    start_hour: int,
    scenario: ty.Dict,
    general_parameters: ty.Dict,
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
) -> ty.Tuple[float, float, float]:

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
    battery_space_shifts: ty.Dict,
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


# def compute_arrivals_impact(
#     impact_of_arrivals: ty.Dict[str, pd.DataFrame],
#     travelling_group_size: float,
#     travelling_group_first_slot: int,
#     percent_in_first_slot: float,
#     leg_origin: str,
#     leg_destination: str,
# ) -> pd.DataFrame:

#     first_slot_impact, second_slot_impact, third_slot_impact =
#            get_slot_split(
#         percent_in_first_slot, travelling_group_size
#     )

#     impact_of_arrivals[leg_origin].loc[
#         travelling_group_first_slot, leg_destination
#     ] = (
#         impact_of_arrivals[leg_origin].loc[travelling_group_first_slot][
#             leg_destination
#         ]
#         + first_slot_impact
#     )
#     impact_of_arrivals[leg_origin].loc[
#         travelling_group_first_slot + 1, leg_destination
#     ] = (
#         impact_of_arrivals[leg_origin].loc[travelling_group_first_slot + 1][
#             leg_destination
#         ]
#         + second_slot_impact
#     )
#     impact_of_arrivals[leg_origin].loc[
#         travelling_group_first_slot + 2, leg_destination
#     ] = (
#         impact_of_arrivals[leg_origin].loc[travelling_group_first_slot + 2][
#             leg_destination
#         ]
#         + third_slot_impact
#     )

#     return impact_of_arrivals[leg_origin]


def get_travelling_group_travel_impact(
    mobility_matrix: pd.DataFrame,
    travelling_group_size: float,
    travelling_group_start_slot: int,
    time_between_legs_used: ty.List[float],
    leg_driving_times: ty.List[float],
    start_locations_of_legs: ty.List[str],
    end_locations_of_legs: ty.List[str],
    leg_distances: ty.List[float],
    leg_weighted_distances: ty.List[float],
    battery_space_shifts: ty.Dict[ty.Tuple[str, str], pd.DataFrame],
    vehicle_electricity_consumption: float,
    HOURS_IN_A_DAY: int,
) -> pd.DataFrame:

    travelling_group_first_slot: int = travelling_group_start_slot
    percent_in_first_slot: float = 1
    if travelling_group_first_slot + 2 >= HOURS_IN_A_DAY:

        print('Trip extending beond day end. Check your entry')
        exit()
    # The trips start uniformly within the first slot

    # print(travelling_group_first_slot)
    # print(percent_in_first_slot)

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

            print('Trip extending beond day end. Check your entry')
            exit()

        # if leg_index == 2:
        #     print(travelling_group_size)
        #     print(percent_in_first_slot)
        #     print(travelling_group_first_slot)
        #     print(mobility_matrix.loc['truck_hub', 'truck_customer']
        # .iloc[0:15])
        # exit()
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
        # if leg_index == 2:
        #     print(mobility_matrix.loc['truck_hub', 'truck_customer']
        # .iloc[0:15])
        #     exit()

        # We update the slots of the group
        travelling_group_first_slot += math.floor(time_after_leg)
        percent_in_first_slot -= time_after_leg % 1

        if percent_in_first_slot <= 0:
            travelling_group_first_slot += 1
            percent_in_first_slot = 1 + percent_in_first_slot
        # print(travelling_group_first_slot)
        # print(percent_in_first_slot)

        if travelling_group_first_slot + 2 >= HOURS_IN_A_DAY:

            print('Trip extending beond day end. Check your entry')
            exit()
    # exit()
    return mobility_matrix


def get_location_split_and_impact_of_departures_and_arrivals(
    location_names: ty.List[str],
    location_split: pd.DataFrame,
    mobility_matrix,  # It is a DataFrame, but Mypy has issues with
    # assigning MultiIndex DataFrames
    start_probabilities: ty.List[float],
    time_between_legs: ty.List[float],
    leg_driving_times: ty.List[float],
    start_locations_of_legs: ty.List[str],
    end_locations_of_legs: ty.List[str],
    leg_distances: ty.List[float],
    weighted_leg_distances: ty.List[float],
    battery_space_shifts: ty.Dict[ty.Tuple[str, str], pd.DataFrame],
    vehicle_electricity_consumption: float,
    HOURS_IN_A_DAY: int,
) -> ty.Tuple[pd.DataFrame, pd.DataFrame]:
    if len(leg_driving_times) > 0:
        # If there are no legs, the arrays stay full of zeroes
        dummy_time_between_legs: float = 0
        # This dummy value is added so that we can iterate through a
        # zip of driving times and times between legs that have the
        # same length as the amount of legs
        time_between_legs_used: ty.List[float] = time_between_legs.copy()
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
        # print(mobility_matrix.loc['truck_hub'])
        print(location_split)
        print(mobility_matrix)
        print(location_names)
        possible_origins: ty.List[str] = list(
            set(mobility_matrix.index.get_level_values('From'))
        )
        # print(possible_origins)
        # exit()
        # exit()
        for start_location in possible_origins:
            possible_destinations: ty.List[str] = list(
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
        leg, name: str, scenario: ty.Dict, general_parameters: ty.Dict
    ) -> None:
        leg.name: str = name

        leg_parameters: ty.Dict = scenario['legs'][name]
        leg.vehicle: str = leg_parameters['vehicle']
        leg.distance: float = leg_parameters['distance']
        leg.duration: float = leg_parameters['duration']
        leg.hour_in_day_factors: ty.List[float] = leg_parameters[
            'hour_in_day_factors'
        ]
        locations: ty.Dict[str, str] = leg_parameters['locations']
        leg.start_location: str = locations['start']
        leg.end_location: str = locations['end']
        road_type_parameters: ty.Dict[str, ty.List[float]] = leg_parameters[
            'road_type_mix'
        ]
        leg.road_type_mix: ty.List[float] = road_type_parameters['mix']


class Location:
    '''
    This class defines the locations where the vehicles are
    and their properties,  from a scenario
    file that contains a list of instances and their properties.
    '''

    class_name: str = 'locations'

    def __init__(
        location, name: str, scenario: ty.Dict, general_parameters: ty.Dict
    ) -> None:
        location.name: str = name

        location_parameters: ty.Dict = scenario['locations'][name]
        location.vehicle: str = location_parameters['vehicle']
        location.connectivity: float = location_parameters['connectivity']
        location.charging_power: float = location_parameters['charging_power']
        location.latitude: float = location_parameters['latitude']
        location.longitude: float = location_parameters['longitude']
        location.base_charging_price: float = location_parameters[
            'base_charging_price'
        ]
        location.charging_desirability: float = location_parameters[
            'charging_desirability'
        ]


# def update_partial_time_stay_corrections(
#     partial_time_stay_corrections: pd.DataFrame,
#     arriving_group_slot: int,
#     arriving_group_size: float,
#     full_time_slots_at_destination: int,
#     remainder_in_partial_slot: float,
#     destination,
# ) -> pd.DataFrame:

#     first_slot_correction: float = (-remainder_in_partial_slot) / 2
#     last_slot_correction: float = 1 - first_slot_correction
#     partial_time_stay_corrections.loc[
#         arriving_group_slot + full_time_slots_at_destination, destination
#     ] = (
#         partial_time_stay_corrections.loc[
#             arriving_group_slot
#             # + full_time_slots_at_destination
#         ][destination]
#         + first_slot_correction
#     ) % 1
#     partial_time_stay_corrections.loc[
#         arriving_group_slot + full_time_slots_at_destination + 1, destination
#     ] = (
#         partial_time_stay_corrections.loc[
#             arriving_group_slot + full_time_slots_at_destination + 1
#         ][destination]
#         + last_slot_correction
#     ) % 1
#     return partial_time_stay_corrections


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
        trip, name: str, scenario: ty.Dict, general_parameters: ty.Dict
    ) -> None:
        trip.name: str = name

        trip_parameters: ty.Dict = scenario['trips'][name]
        trip.legs: ty.List[str] = trip_parameters['legs']
        trip.time_between_legs: ty.List[float] = trip_parameters[
            'time_between_legs'
        ]
        trip.percentage_station_users: float = trip_parameters[
            'percentage_station_users'
        ]

        trip.start_probabilities: ty.List[float] = trip_parameters[
            'start_probabilities'
        ]
        trip.repeated_sequence: ty.List[str] = trip_parameters[
            'repeated_sequence'
        ]
        trip.repetition_amounts: ty.List[int] = trip_parameters[
            'repetition_amounts'
        ]
        trip.time_between_repetitions: ty.List[float] = trip_parameters[
            'time_between_repetitions'
        ]

        trip.day_start_hour: int = scenario['mobility_module'][
            'day_start_hour'
        ]
        trip.leg_driving_times: ty.List[float] = [
            scenario['legs'][leg_name]['duration'] for leg_name in trip.legs
        ]

        trip_legs_store: ty.List[str] = trip.legs.copy()

        time_between_legs_store: ty.List[float] = trip.time_between_legs.copy()
        leg_driving_times_store: ty.List[float] = trip.leg_driving_times.copy()
        if len(trip.repeated_sequence) > 0:
            trip.legs = []
            trip.time_between_legs = []
            trip.leg_driving_times = []
            repetition_iteration_index: int = 0
            for leg_index, leg in enumerate(trip_legs_store):

                if leg not in trip.repeated_sequence:
                    trip.legs.append(leg)
                    if leg_index < len(trip_legs_store) - 1:
                        trip.time_between_legs.append(
                            time_between_legs_store[leg_index]
                        )
                    trip.leg_driving_times.append(
                        leg_driving_times_store[leg_index]
                    )
                elif leg == trip.repeated_sequence[0]:
                    for repetition in range(
                        trip.repetition_amounts[repetition_iteration_index] + 1
                    ):
                        for leg_to_add_index, leg_to_add in enumerate(
                            trip.repeated_sequence
                        ):
                            trip.legs.append(leg_to_add)
                            if (
                                leg_to_add_index
                                < len(trip.repeated_sequence) - 1
                            ):
                                trip.time_between_legs.append(
                                    time_between_legs_store[leg_index]
                                )
                            trip.leg_driving_times.append(
                                leg_driving_times_store[leg_index]
                            )
                        if (
                            repetition
                            < trip.repetition_amounts[
                                repetition_iteration_index
                            ]
                        ):
                            trip.time_between_legs.append(
                                trip.time_between_repetitions[
                                    repetition_iteration_index
                                ]
                            )

                        else:

                            add_final_time_between_legs: bool = True

                            if leg_index == (
                                len(trip_legs_store)
                                - len(trip.repeated_sequence)
                            ):

                                if (
                                    trip_legs_store[-1]
                                    == trip.repeated_sequence[-1]
                                ):
                                    add_final_time_between_legs = False
                                    # If the last leg of the trip
                                    # is also the last leg of the repeated
                                    # sequence, we don't need to add
                                    # the time after it (since it is the
                                    # last leg of the trip).

                            if add_final_time_between_legs:
                                trip.time_between_legs.append(
                                    time_between_legs_store[
                                        leg_index
                                        + len(trip.repeated_sequence)
                                        - 1
                                    ]
                                )

                    repetition_iteration_index += 1

        trip.start_locations_of_legs: ty.List[str] = [
            scenario['legs'][leg_name]['locations']['start']
            for leg_name in trip.legs
        ]
        trip.end_locations_of_legs: ty.List[str] = [
            scenario['legs'][leg_name]['locations']['end']
            for leg_name in trip.legs
        ]
        trip.location_names: ty.List[str] = list(
            set(trip.start_locations_of_legs + trip.end_locations_of_legs)
        )

        trip.leg_distances: ty.List[float] = [
            scenario['legs'][leg_name]['distance'] for leg_name in trip.legs
        ]

        trip.weighted_leg_distances: ty.List[float] = []
        for leg_name in trip.legs:
            road_type_mix: np.ndarray = np.array(
                scenario['legs'][leg_name]['road_type_mix']['mix']
            )
            road_type_weights: np.ndarray = np.array(
                scenario['transport_factors']['weights']
            )
            road_type_factor: float = float(
                sum(road_type_mix * road_type_weights)
            )
            leg_distance: float = scenario['legs'][leg_name]['distance']
            leg_weighted_distance: float = leg_distance * road_type_factor
            trip.weighted_leg_distances.append(leg_weighted_distance)

        trip.unique_leg_distances: ty.List[float] = list(
            set(trip.leg_distances)
        )
        trip.unique_weighted_leg_distances: ty.List[float] = list(
            set(trip.weighted_leg_distances)
        )
        vehicle_electricity_consumption: float = scenario['vehicle'][
            'base_consumption_per_km'
        ]['electricity_kWh']

        trip.unique_leg_consumptions: ty.List[float] = [
            unique_distance * vehicle_electricity_consumption
            for unique_distance in trip.unique_leg_distances
        ]

        trip.unique_weighted_leg_consumptions: ty.List[float] = [
            unique_distance * vehicle_electricity_consumption
            for unique_distance in trip.unique_weighted_leg_distances
        ]

        # We want to create a mobility matrix for the trip. This matrix will
        # have start and end locations (plus hour in day, starting
        # at day start) as an index, and departures, arrivals as columns (
        # each with amounts, distances, weighted distances)
        HOURS_IN_A_DAY: int = general_parameters['time']['HOURS_IN_A_DAY']
        parameters_of_legs: ty.Dict = scenario['legs']
        unique_legs: ty.List[str] = []
        for trip_leg in trip.legs:
            if trip_leg not in unique_legs:
                unique_legs.append(trip_leg)

        leg_tuples: ty.List[ty.Tuple[str, str]] = [
            (
                parameters_of_legs[trip_leg]['locations']['start'],
                parameters_of_legs[trip_leg]['locations']['end'],
            )
            for trip_leg in unique_legs
        ]

        # We only want the start and end locations that are in the legs
        mobility_index_tuples: ty.List[ty.Tuple[str, str, int]] = [
            (leg_tuple[0], leg_tuple[1], hour_number)
            for leg_tuple in leg_tuples
            for hour_number in range(HOURS_IN_A_DAY)
        ]

        mobility_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
            mobility_index_tuples,
            names=['From', 'To', 'Hour number (from day start)'],
        )
        mobility_quantities: ty.List[str] = scenario['mobility_module'][
            'mobility_quantities'
        ]

        trip.mobility_matrix: pd.DataFrame = pd.DataFrame(
            np.zeros((len(mobility_index), len(mobility_quantities))),
            columns=mobility_quantities,
            index=mobility_index,
        )

        trip.mobility_matrix = trip.mobility_matrix.sort_index()

        # We also want to store the battery space shifts true to legs.
        # We track this as departure and arrivals (including a version with
        # impact versions).
        base_dataframe_for_battery_space_shifts: pd.DataFrame = pd.DataFrame(
            np.zeros((len(mobility_index), len(trip.unique_leg_consumptions))),
            columns=trip.unique_leg_consumptions,
            index=mobility_index,
        )
        base_dataframe_for_weighted_battery_space_shifts: pd.DataFrame = (
            pd.DataFrame(
                np.zeros(
                    (
                        len(mobility_index),
                        len(trip.unique_weighted_leg_consumptions),
                    )
                ),
                columns=trip.unique_weighted_leg_consumptions,
                index=mobility_index,
            )
        )
        base_dataframe_for_weighted_battery_space_shifts = (
            base_dataframe_for_weighted_battery_space_shifts.sort_index()
        )
        trip.battery_space_shifts_departures: pd.DataFrame = (
            base_dataframe_for_battery_space_shifts.copy()
        )
        trip.battery_space_shifts_departures = (
            trip.battery_space_shifts_departures.sort_index()
        )
        trip.battery_space_shifts_departures_impact: pd.DataFrame = (
            base_dataframe_for_battery_space_shifts.copy()
        )
        trip.battery_space_shifts_departures_impact = (
            trip.battery_space_shifts_departures_impact.sort_index()
        )
        trip.battery_space_shifts_arrivals: pd.DataFrame = (
            base_dataframe_for_battery_space_shifts.copy()
        )
        trip.battery_space_shifts_arrivals = (
            trip.battery_space_shifts_arrivals.sort_index()
        )
        trip.battery_space_shifts_arrivals_impact: pd.DataFrame = (
            base_dataframe_for_battery_space_shifts.copy()
        )
        trip.battery_space_shifts_arrivals_impact = (
            trip.battery_space_shifts_arrivals_impact.sort_index()
        )
        trip.battery_space_shifts_departures_weighted: pd.DataFrame = (
            base_dataframe_for_weighted_battery_space_shifts.copy()
        )
        trip.battery_space_shifts_departures_weighted = (
            trip.battery_space_shifts_departures_weighted.sort_index()
        )
        trip.battery_space_shifts_departures_impact_weighted: pd.DataFrame = (
            base_dataframe_for_weighted_battery_space_shifts.copy()
        )
        trip.battery_space_shifts_departures_impact_weighted = (
            trip.battery_space_shifts_departures_impact_weighted.sort_index()
        )
        trip.battery_space_shifts_arrivals_weighted: pd.DataFrame = (
            base_dataframe_for_weighted_battery_space_shifts.copy()
        )
        trip.battery_space_shifts_arrivals_weighted = (
            trip.battery_space_shifts_arrivals_weighted.sort_index()
        )
        trip.battery_space_shifts_arrivals_impact_weighted: pd.DataFrame = (
            base_dataframe_for_weighted_battery_space_shifts.copy()
        )
        trip.battery_space_shifts_arrivals_impact_weighted = (
            trip.battery_space_shifts_arrivals_impact_weighted.sort_index()
        )
        trip.battery_space_shifts: ty.Dict[
            ty.Tuple[str, str], pd.DataFrame
        ] = {}
        trip.battery_space_shifts[('Departures', 'Amount')] = (
            trip.battery_space_shifts_departures
        )
        trip.battery_space_shifts[('Departures', 'Impact')] = (
            trip.battery_space_shifts_departures_impact
        )
        trip.battery_space_shifts[('Departures', 'Amount Weighted')] = (
            trip.battery_space_shifts_departures_weighted
        )
        trip.battery_space_shifts[('Departures', 'Impact Weighted')] = (
            trip.battery_space_shifts_departures_impact_weighted
        )
        trip.battery_space_shifts[('Arrivals', 'Amount')] = (
            trip.battery_space_shifts_arrivals
        )
        trip.battery_space_shifts[('Arrivals', 'Impact')] = (
            trip.battery_space_shifts_arrivals_impact
        )
        trip.battery_space_shifts[('Arrivals', 'Amount Weighted')] = (
            trip.battery_space_shifts_arrivals_weighted
        )
        trip.battery_space_shifts[('Arrivals', 'Impact Weighted')] = (
            trip.battery_space_shifts_arrivals_impact_weighted
        )

        # # We want to track the probabilities and time driving of previous
        # # legs
        # previous_leg_start_probabilities: np.ndarray = np.array(
        # #     trip.start_probabilities
        # # )
        # time_driving_previous_leg: float = float(0)

        # We want to track where the vehicle is
        trip.location_split: pd.DataFrame = pd.DataFrame(
            np.zeros((HOURS_IN_A_DAY, len(trip.location_names))),
            columns=trip.location_names,
            index=range(HOURS_IN_A_DAY),
        )
        trip.location_split.index.name = 'Hour in day (from day start)'

        if trip.name.startswith('stay_put_'):
            stay_put_location: str = trip.name.split('stay_put_')[1]
            trip.location_split[stay_put_location] = 1
        else:
            start_leg_name: str = trip.legs[0]
            initial_location: str = scenario['legs'][start_leg_name][
                'locations'
            ]['start']
            trip.location_split[initial_location] = 1

        trip.location_split, trip.mobility_matrix = (
            get_location_split_and_impact_of_departures_and_arrivals(
                trip.location_names,
                trip.location_split,
                trip.mobility_matrix,
                trip.start_probabilities,
                trip.time_between_legs,
                trip.leg_driving_times,
                trip.start_locations_of_legs,
                trip.end_locations_of_legs,
                trip.leg_distances,
                trip.weighted_leg_distances,
                trip.battery_space_shifts,
                vehicle_electricity_consumption,
                HOURS_IN_A_DAY,
            )
        )

        # # exit()

        # # at_location_in_departure_hour: np.ndarray = (
        # #     trip.start_probabilities / 2
        # # )
        # # vehicles_staying_put_whole_hour: np.ndarray = (
        # #     1 - trip.start_probabilities.cumsum()
        # # )
        # # vehicles_that_did_not_start_trip_yet: np.ndarray = (
        # #     at_location_in_departure_hour +
        # # vehicles_staying_put_whole_hour
        # # )
        # # trip.location_split[initial_location] = (
        # #     vehicles_that_did_not_start_trip_yet
        # # )
        # # # The departures have half their impact in their first slot and
        # # # half in their second
        # # trip.departures_impact[initial_location] = -(
        # #     trip.start_probabilities / 2
        # #     + np.roll(trip.start_probabilities / 2, 1)
        # # )

        # # We want to track the partial time corrections,
        # # which tells us how much the vehicles stay before departing
        # # trip.partial_time_stay_corrections: pd.DataFrame = pd.DataFrame(
        # #     0.5 * np.ones((HOURS_IN_A_DAY, len(location_names))),
        # #     index=range(HOURS_IN_A_DAY),
        # #     columns=location_names,
        # # )
        # # trip.partial_time_stay_corrections.index.name = (
        # #     'Hour in day (from day start)'
        # # )
        # # To store partial stay corrections
        # # To fill in the mobility matrix, we iterate over the legs of the
        # trip
        # for leg_index, leg_name in enumerate(trip.legs):
        #     # moki = False
        #     # maak = False
        #     # if trip.name == 'bus_weekday_in_holiday_week':
        #     #     # print(trip.legs)
        #     #     maak = True
        #     #     # exit()
        #     #     if leg_name == 'bus_from_route_start_to_depot':
        #     #         moki = True
        #     #         print(leg_name)
        #     #         print(leg_index)
        #     #     # exit()
        #     leg_parameters: ty.Dict = scenario['legs'][leg_name]
        #     start_location: str = leg_parameters['locations']['start']
        #     end_location: str = leg_parameters['locations']['end']
        #     time_driving: float = leg_parameters['duration']
        #     # We want to know the percentage of time driving due to this
        #     # leg in the current (hour) interval and subsequent ones
        #     # We first fill the intervals that are fully filled by the
        # driving
        #     # e.g four ones if the driving is 4.2 hours
        #     # time_driving_in_intervals: list[float] = [1] * math.floor(
        #     #     time_driving
        #     # )
        #     # # We then append the remainder (which is the duration if the
        #     # # duration is smaller than the (hour) interval)
        #     # remainder: float = time_driving - math.floor(time_driving)
        #     # But only if it is not zero (to avoid adding an unnecessary
        # index)
        #     # if remainder > 0:
        #     #     time_driving_in_intervals.append(remainder)
        #     distance: float = leg_parameters['distance']
        #     road_type_mix: np.ndarray = np.array(
        #         leg_parameters['road_type_mix']['mix']
        #     )
        #     road_type_weights: np.ndarray = np.array(
        #         scenario['transport_factors']['weights']
        #     )
        #     road_type_factor: float = float(
        #         sum(road_type_mix * road_type_weights)
        #     )
        #     weighted_distance: float = road_type_factor * distance

        #     if leg_index == 0:
        #         # The first leg is not shifted, by definition of the trip
        #         # start probabilities, as the trip starts with the first leg
        #         time_shift: float = 0
        #         current_leg_start_probabilities: np.ndarray = (
        #             trip.start_probabilities
        #         )
        #     else:
        #         # We want to know how much time there is between legs
        #         # so that we can shift the start probabilities accordingly.
        #         # To get the time between a leg and the previous leg, we need
        #         # to know two things: the time spent driving in the
        #         # previous leg, and the
        #         # time spent between legs (i.e. the idle time)
        #         time_spent_at_location: float = trip.time_between_legs[
        #             leg_index - 1
        #         ]
        #         # We can now increment the time shift
        #         time_shift = time_driving_previous_leg +
        #
        # time_spent_at_location
        #         # The leg departueres
        #         # take place into two time slots. These two slots
        #         # have numbers slot_shift and slot_shift+1
        #         slot_shift: int = math.floor(time_shift)
        #         # For example, if the time shift is 9.25 slots from the
        #         # day start, (9.25 hours if
        #         # hours are your units), then arrivals will occur in time
        #         # slots (hours if you use them) 9 and 10
        #         # The portion in the first slot is:
        #         first_slot_proportion: float = 1 - time_shift % 1
        #         # In the example above, the decimal part is 0.25, so the
        #         # proportion is (1-0.25)=0.75
        #         current_leg_start_probabilities = (
        #             first_slot_proportion
        #             * np.roll(previous_leg_start_probabilities, slot_shift)
        #             + (1 - first_slot_proportion)
        #             * np.roll(previous_leg_start_probabilities,
        #
        # slot_shift + 1)
        #         )
        #         # if maak:
        #         #     print(leg_index, leg_name)
        #         #     print(current_leg_start_probabilities)
        #         # if moki:
        #         #     print(leg_index, leg_name)
        #         #     print(current_leg_start_probabilities)
        #         #     exit()

        #     # if leg_index > 0:
        #     #     # We want to know how much time there is between legs
        #     #     # so that we can shift the start probabilities accordingly.
        #     #     # To get the time between a leg and the previous leg, we
        # need
        #     #     # to know two things: the time spent driving in the
        #     #     # previous leg, and the
        #     #     # time spent between legs (i.e. the idle time)
        #     #     time_spent_at_location: float = trip.time_between_legs[
        #     #         leg_index - 1
        #     #     ]
        #     #     time_shift: float = (
        #     #         time_driving_previous_leg + time_spent_at_location
        #     #     )
        #     #     if maak:
        #     #         print(time_shift)
        #     #     # For previous leg departures in slot N, the corresponding
        #     #     # current leg departures.
        #     #     # take place into two time slots. These two slots
        #     #     # have numbers N+slot_shift and N+slot_shift+1
        #     #     slot_shift: int = math.floor(time_shift)
        #     #     # For example, if the time shift is 9.25 slots
        # (9.25 hours if
        #     #     # hours are your units), then arrivals will occur in time
        #     #     # slots (hours if you use them) N+9 and N+10
        #     #     # The portion in the first slot is:
        #     #     first_slot_proportion: float = 1 - time_shift % 1
        #     #     # In the example above, the decimal part is 0.25, so the
        #     #     # proportion is (1-0.25)=0.75
        #     #     current_leg_start_probabilities: (
        #     #         np.ndarray
        #     #     ) = first_slot_proportion * np.roll(
        #     #         previous_leg_start_probabilities, slot_shift
        #     #     ) + (
        #     #         1 - first_slot_proportion
        #     #     ) * np.roll(
        #     #         previous_leg_start_probabilities, slot_shift + 1
        #     #     )
        #     #     if maak:
        #     #         print(leg_index, leg_name)
        #     #         print(current_leg_start_probabilities)
        #     #     if moki:
        #     #         print(leg_index, leg_name)
        #     #         print(current_leg_start_probabilities)
        #     #         exit()

        #     # else:
        #     #     # The first leg is not shifted, by definition of the trip
        #     #     # start probabilities, as the trip starts with the
        # first leg
        #     #     time_shift = 0
        #     #     current_leg_start_probabilities = (
        #     #         previous_leg_start_probabilities
        #     #     )

        #     # For a departure shifted by timne shift, the corresponding
        #     # arrivals are shifted by the time driving and
        #     # take place into two time slots. These two slots
        #     # have numbers slot_shift and slot_shift+1
        #     arrival_slot_shift: int = math.floor(time_driving)
        #     # For example, if the time driving is 1.25 slots (1.25 hours if
        #     # hours are your units), then arrivals will occur in time
        #     # slots (hours if you use them) +1 and +2
        #     # The portion in the first slot is:
        #     first_slot_proportion = 1 - time_driving % 1
        #     # In the example above, the decimal part is 0.25, so the
        # proportion
        #     # is (1-0.25)=0.75
        #     current_leg_end_probabilities: (
        #         np.ndarray
        #     ) = first_slot_proportion * np.roll(
        #         current_leg_start_probabilities, arrival_slot_shift
        #     ) + (
        #         1 - first_slot_proportion
        #     ) * np.roll(
        #         current_leg_start_probabilities, arrival_slot_shift + 1
        #     )
        #     # if moki:
        #     #     print(current_leg_end_probabilities)
        #     #     exit()
        #     # if moki:
        #     #     print(start_location, end_location)
        #     #     print(trip.mobility_matrix.loc[start_location,
        # end_location])
        #     #     # exit()

        #     # With this, we can add this leg's contribution to the
        #     # mobility matrix

        #     trip.mobility_matrix.loc[
        #         (start_location, end_location), 'Departures amount'
        #     ] = (
        #         pd.Series(
        #             trip.mobility_matrix.loc[
        #                 (start_location, end_location), 'Departures amount'
        #             ]
        #         ).values
        #         + current_leg_start_probabilities
        #     )

        #     # We need to convert the first element to Series for type hinting
        #     # reasons, as MyPy does not know it is a Series otherwise

        #     trip.mobility_matrix.loc[
        #         (start_location, end_location), 'Arrivals amount'
        #     ] = (
        #         pd.Series(
        #             trip.mobility_matrix.loc[
        #                 (start_location, end_location), 'Arrivals amount'
        #             ]
        #         ).values
        #         + current_leg_end_probabilities
        #     )
        #     # We need to convert the first element to Series for type hinting
        #     # reasons, as MyPy does not know it is a Series otherwise

        #     # if moki:
        #     #     print(trip.name)
        #     #     print('<<<<')
        #     #     print(trip.mobility_matrix.loc[start_location,
        # end_location])
        #     #     # exit()

        #     start_distance_probabilities: np.ndarray = np.array(
        #         [
        #             current_leg_start_probability * distance
        #             for (
        #                 current_leg_start_probability
        #             ) in current_leg_start_probabilities
        #         ]
        #     )

        #     # print(start_distance_probabilities)
        #     # print(current_leg_start_probabilities)
        #     # exit()
        #     trip.mobility_matrix.loc[
        #         (start_location, end_location), 'Departures kilometers'
        #     ] = (
        #         pd.Series(
        #             trip.mobility_matrix.loc[
        #                 (start_location, end_location), 'Departures
        # '
        #             ]
        #         ).values
        #         + start_distance_probabilities
        #     )
        #     # We need to convert the first element to Series for type hinting
        #     # reasons, as MyPy does not know it is a Series otherwise

        #     start_weighted_distance_probabilities: np.ndarray = np.array(
        #         np.array(current_leg_start_probabilities) * weighted_distance
        #     )
        #     trip.mobility_matrix.loc[
        #         (start_location, end_location),
        #         'Departures weighted kilometers',
        #     ] = (
        #         pd.Series(
        #             trip.mobility_matrix.loc[
        #                 (start_location, end_location),
        #                 'Departures weighted kilometers',
        #             ]
        #         ).values
        #         + start_weighted_distance_probabilities
        #     )
        #     # We need to convert the first element to Series for type hinting
        #     # reasons, as MyPy does not know it is a Series otherwise

        #     end_distance_probabilities: np.ndarray = np.array(
        #         current_leg_end_probabilities * distance
        #     )
        #     trip.mobility_matrix.loc[
        #         (start_location, end_location), 'Arrivals kilometers'
        #     ] = (
        #         pd.Series(
        #             trip.mobility_matrix.loc[
        #                 (start_location, end_location), 'Arrivals kilometers'
        #             ]
        #         ).values
        #         + end_distance_probabilities
        #     )
        #     # We need to convert the first element to Series for type hinting
        #     # reasons, as MyPy does not know it is a Series otherwise

        #     end_weighted_distance_probabilities: np.ndarray = np.array(
        #         np.array(current_leg_end_probabilities) * weighted_distance
        #     )
        #     trip.mobility_matrix.loc[
        #         (start_location, end_location), 'Arrivals weighted
        # kilometers'
        #     ] = (
        #         pd.Series(
        #             trip.mobility_matrix.loc[
        #                 (start_location, end_location),
        #                 'Arrivals weighted kilometers',
        #             ]
        #         ).values
        #         + end_weighted_distance_probabilities
        #     )
        #     # We need to convert the first element to Series for type hinting
        #     # reasons, as MyPy does not know it is a Series otherwise

        #     # We also track the duration, distance, and wrighted distance
        #     # Note that these could change with time as well (for example
        #     # with a correction factor added at the run level)
        #     trip.mobility_matrix.loc[
        #         (start_location, end_location), 'Duration (hours)'
        #     ] = time_driving
        #     trip.mobility_matrix.loc[
        #         (start_location, end_location), 'Distance (km)'
        #     ] = distance
        #     trip.mobility_matrix.loc[
        #         (start_location, end_location), 'Weighted distance (km)'
        #     ] = weighted_distance

        #     # Finally, we update the previous leg values with the current
        #     # ones
        #     previous_leg_start_probabilities =
        # current_leg_start_probabilities

        #     # exit()
        #     time_driving_previous_leg = time_driving

        #     # # start_time_at_destination: float = time_shift + time_driving
        #     # if leg_index < len(trip.legs) - 1:
        #     #     time_spent_at_destination: float = trip.time_between_legs[
        #     #         leg_index
        #     #     ]
        #     # # else:
        #     # #     time_spent_at_destination = (
        #     # #         8
        #     # #         # HOURS_IN_A_DAY - start_time_at_destination - 6
        #     # #     )
        #     # time_slots_at_destination: int = math.ceil(
        #     #     time_spent_at_destination
        #     # )
        #     # full_time_slots_at_destination: int = math.floor(
        #     #     time_spent_at_destination
        #     # )
        #     # remainder_in_partial_slot: float =
        # time_spent_at_destination % 1

        #     if leg_index < len(trip.legs) - 1:
        #         time_spent_at_destination: float = trip.time_between_legs[
        #             leg_index
        #         ]
        #         time_slots_at_destination: int = math.ceil(
        #             time_spent_at_destination
        #         )
        #         full_time_slots_at_destination: int = math.floor(
        #             time_spent_at_destination
        #         )
        #         remainder_in_partial_slot: float = (
        #             time_spent_at_destination % 1
        #         )
        #         # if len(trip.legs) > 2:
        #         #     print(leg_index)
        #         #     print(current_leg_start_probabilities)
        #         #     print(current_leg_end_probabilities)
        #         #     if leg_index == 2:
        #         #         exit()

        #         for arriving_group_slot, arriving_group_size in enumerate(
        #             current_leg_end_probabilities
        #         ):

        #             if (
        #                 arriving_group_slot
        #                 + full_time_slots_at_destination
        #                 + 2
        #                 < HOURS_IN_A_DAY
        #             ):  # This should not matter, as the trips end before the
        #                 # day ends, by definition, but we can have issues due
        #                 # to the way we iterate.

        #                 # print(arriving_group_slot, arriving_group_size)
        #                 for stay_slot in range(time_slots_at_destination):
        #                     # print(stay_slot)
        #                     # print(trip.location_split)
        #                     if stay_slot < full_time_slots_at_destination:

        #                         trip.location_split.loc[
        #                             arriving_group_slot + stay_slot,
        #                             end_location,
        #                         ] = (
        #                             trip.location_split.loc[
        #                                 arriving_group_slot + stay_slot
        #                             ][end_location]
        #                             + arriving_group_size
        #                         )

        #                     else:
        #                         trip.location_split.loc[
        #                             arriving_group_slot + stay_slot,
        #                             end_location,
        #                         ] = trip.location_split.loc[
        #                             arriving_group_slot + stay_slot
        #                         ][
        #                             end_location
        #                         ] + (
        #                             arriving_group_size
        #                             * remainder_in_partial_slot
        #                         )
        #                         # trip.departures_impact.loc[
        #                         #     arriving_group_slot + stay_slot,
        #                         #     end_location,
        #                         # ] = trip.departures_impact.loc[
        #                         #     arriving_group_slot + stay_slot
        #                         # ][
        #                         #     end_location
        #                         # ] - (
        #                         #     arriving_group_size
        #                         #     * remainder_in_partial_slot
        #                         # )

        #                     # if remainder_in_partial_slot > 0:
        #                     # print(leg_name)
        #                     # if arriving_group_size > 0:
        #                     #     print(leg_name)
        #                     #     print(arriving_group_size)
        #                     #     print(time_slots_at_destination)
        #                     #     print(end_location)
        #                 #     #         print(trip.location_split)
        #                 # USE TIME SLOTS INCLUDING PARTIAL TIME TRTAVEL
        #                 # IS MATCH WITH FULL TT EXACT?
        #                 print(time_driving)
        #                 print(time_driving % 1)
        #                 non_integer_time_driving: float = time_driving % 1
        #                 arriving_group_slot_factor: float = 1 - (
        #                     (1 - non_integer_time_driving) / 2
        #                 )
        #                 trailing_slot_factor: float = (
        #                     non_integer_time_driving
        #                     # * non_integer_time_driving
        #                     / 2
        #                 )
        #                 # if non_integer_time_driving >0:
        #                 #     print(arriving_group_slot_factor)
        #                 #     print(trip.location_split)
        #                 #     exit()
        #                 # exit()
        #                 # print(arriving_group_slot_factor)
        #                 # exit()
        #                 # The vehicles arrive uniformaly in the first slot
        #                 travel_time_correction_factor: float = 0.5
        #                 first_slot_correction: float = (
        #                     arriving_group_size *
        # travel_time_correction_factor
        #                 )
        #                 print('No, they do not (if travel time is
        # non-integer')
        #                 # print(trip.location_split)
        #                 # if arriving_group_size >0 :

        #                 #     print(arriving_group_size)
        #                 #     print(arriving_group_slot)
        #                 #     if arriving_group_slot > 4:
        #                 #         exit()
        #                 trip.location_split.loc[
        #                     arriving_group_slot, end_location
        #                 ] = (
        #                     trip.location_split.loc[arriving_group_slot][
        #                         end_location
        #                     ]
        #                     - arriving_group_slot_factor *

        #                 )

        #                 # trip.location_split.loc[
        #                 #     arriving_group_slot+1, end_location
        #                 # ] = (
        #                 #     trip.location_split.loc[arriving_group_slot+1][
        #                 #         end_location
        #                 #     ]
        #                 #     - 1/8
        #                 # )

        #                 # trip.location_split.loc[
        #                 #     arriving_group_slot + 1, end_location
        #                 # ] = (
        #                 #     trip.location_split.loc[
        # arriving_group_slot + 1][
        #                 #         end_location
        #                 #     ]
        #                 #     + (1 - arriving_group_slot_factor)
        #                 #     * arriving_group_size
        #                 # )
        #                 # print(trip.location_split)
        #                 # if non_integer_time_driving *
        # arriving_group_size > 0:
        #                 #     print(non_integer_time_driving)
        #                 #     print(arriving_group_size)
        #                 #     exit()

        #                 trip.location_split.loc[
        #                     arriving_group_slot
        #                     + full_time_slots_at_destination
        #                     + 1,
        #                     end_location,
        #                 ] = (
        #                     trip.location_split.loc[
        #                         arriving_group_slot
        #                         + full_time_slots_at_destination
        #                         + 1
        #                     ][end_location]
        #                     + arriving_group_size * trailing_slot_factor
        #                     # - arriving_group_slot_factor *
        # arriving_group_size
        #                 )

        #                 # trip.location_split.loc[
        #                 #     full_time_slots_at_destination + 2,
        # end_location
        #                 # ] = (
        #                 #     trip.location_split.loc[
        # full_time_slots_at_destination + 2][
        #                 #         end_location
        #                 #     ]
        #                 #     + (1-next_slot_factor) * arriving_group_size
        #                 # )

        #                 # This propagates through to the first non-full slot:
        #                 trip.location_split.loc[
        #                     arriving_group_slot
        #                     + full_time_slots_at_destination,
        #                     end_location,
        #                 ] = trip.location_split.loc[
        #                     arriving_group_slot
        #                     + full_time_slots_at_destination
        #                 ][
        #                     end_location
        #                 ] + (
        #                     arriving_group_size - first_slot_correction
        #                 )

        #                 # For the arrivals impact, we have:
        #                 trip.arrivals_impact.loc[
        #                     arriving_group_slot, end_location
        #                 ] = (
        #                     trip.arrivals_impact.loc[arriving_group_slot][
        #                         end_location
        #                     ]
        #                     + arriving_group_size * first_slot_correction
        #                     # - first_slot_correction
        #                 )
        #                 trip.arrivals_impact.loc[
        #                     arriving_group_slot + 1, end_location
        #                 ] = (
        #                     trip.arrivals_impact.loc[
        # arriving_group_slot + 1][
        #                         end_location
        #                     ]
        #                     + arriving_group_slot_factor *

        #                 )
        #                 # print(trip.location_split)
        #                 # input()
        #                 # exit()

        #                 # # Each of these has a corresponding departure
        #  impact:
        #                 # # print(time_slots_at_destination)
        #                 # # print(arriving_group_slot)
        #                 # trip.departures_impact.loc[
        #                 #     arriving_group_slot +
        # time_slots_at_destination,
        #                 #     end_location,
        #                 # ] = (
        #                 #     trip.departures_impact.loc[
        #                 #         arriving_group_slot +

        #                 #     - arriving_group_size
        #                 #     + first_slot_correction
        #                 # )
        #                 # trip.departures_impact.loc[
        #                 #     arriving_group_slot
        #                 #     + time_slots_at_destination
        #                 #     + 1,
        #                 #     end_location,
        #                 # ] = (
        #                 #     trip.departures_impact.loc[
        #                 #         arriving_group_slot
        #                 #         + time_slots_at_destination
        #                 #         + 1
        #                 #     ][end_location]
        #                 #     - first_slot_correction
        #                 # )

        #                 # For partial stays (less than an hour), there is
        #                 # another correction:
        #                 partial_stay_correction: float = (
        #                     arriving_group_size
        #                     * (
        #                         remainder_in_partial_slot
        #                         * (remainder_in_partial_slot)
        #                         / 2
        #                     )
        #                 )

        #                 # The impact on departures is:
        #                 trip.departures_impact.loc[
        #                     arriving_group_slot
        #                     + full_time_slots_at_destination,
        #                     end_location,
        #                 ] = (
        #                     trip.departures_impact.loc[
        #                         arriving_group_slot
        #                         + full_time_slots_at_destination
        #                     ][end_location]
        #                     - arriving_group_size
        #                     * (1 - remainder_in_partial_slot)
        #                     * (1 - remainder_in_partial_slot)
        #                     / 2
        #                 )

        #                 trip.departures_impact.loc[
        #                     arriving_group_slot
        #                     + full_time_slots_at_destination
        #                     + 1,
        #                     end_location,
        #                 ] = trip.departures_impact.loc[
        #                     arriving_group_slot
        #                     + full_time_slots_at_destination
        #                     + 1
        #                 ][
        #                     end_location
        #                 ] - arriving_group_size * (
        #                     1
        #                     - (1 - remainder_in_partial_slot)
        #                     * (1 - remainder_in_partial_slot)
        #                     / 2
        #                     - remainder_in_partial_slot
        #                     * remainder_in_partial_slot
        #                     / 2
        #                 )

        #                 trip.departures_impact.loc[
        #                     arriving_group_slot
        #                     + full_time_slots_at_destination
        #                     + 2,
        #                     end_location,
        #                 ] = trip.departures_impact.loc[
        #                     arriving_group_slot
        #                     + full_time_slots_at_destination
        #                     + 2
        #                 ][
        #                     end_location
        #                 ] - arriving_group_size * (
        #                     (remainder_in_partial_slot)
        #                     * (remainder_in_partial_slot)
        #                     / 2
        #                 )

        #                 # WHih=ch is right? This or the loc split one?
        #                 # Most probably loc split
        #                 # trip.departures_impact.loc[
        #                 #     arriving_group_slot
        #                 #     + time_slots_at_destination
        #                 #     + 1,
        #                 #     end_location,
        #                 # ] = (
        #                 #     trip.departures_impact.loc[
        #                 #         arriving_group_slot
        #                 #         + time_slots_at_destination
        #                 #         + 1
        #                 #     ][end_location]
        #                 #     - first_slot_correction
        #                 # )
        #                 # trip.departures_impact.loc[
        #                 #     arriving_group_slot
        #                 #     + full_time_slots_at_destination,
        #                 #     end_location,
        #                 # ] = (
        #                 #     trip.departures_impact.loc[
        #                 #         arriving_group_slot
        #                 #         + full_time_slots_at_destination
        #                 #     ][end_location]
        #                 #     - partial_stay_correction
        #                 # )
        #                 # trip.departures_impact.loc[
        #                 #     arriving_group_slot
        #                 #     + full_time_slots_at_destination
        #                 #     + 1,
        #                 #     end_location,
        #                 # ] = (
        #                 #     trip.departures_impact.loc[
        #                 #         arriving_group_slot
        #                 #         + full_time_slots_at_destination
        #                 #         + 1
        #                 #     ][end_location]
        #                 #     + partial_stay_correction
        #                 # )
        #                 # trip.departures_impact.loc[
        #                 #     arriving_group_slot +
        # full_time_slots_at_destination+1,
        #                 #     end_location,
        #                 # ] = (
        #                 #     trip.departures_impact.loc[
        #                 #         arriving_group_slot +
        #  +1
        #                 #     ][end_location]
        #                 #     + partial_stay_correction

        #                 # )
        #                 # trip.departures_impact.loc[
        #                 #     arriving_group_slot
        #                 #     + time_slots_at_destination
        #                 #     + 1,
        #                 #     end_location,
        #                 # ] = (
        #                 #     trip.departures_impact.loc[
        #                 #         arriving_group_slot
        #                 #         + time_slots_at_destination
        #                 #         + 1
        #                 #     ][end_location]
        #                 #     - first_slot_correction
        #                 # )

        #                 # if partial_stay_correction > 0:
        #                 #     if arriving_group_size > 0:
        #                 #         trip.partial_time_stay_corrections = (
        #                 #             update_partial_time_stay_corrections(
        #                 #                 trip.partial_time_stay_corrections,
        #                 #                 arriving_group_slot,
        #                 #                 arriving_group_size,
        #                 #                 full_time_slots_at_destination,
        #                 #                 remainder_in_partial_slot,
        #                 #                 end_location,
        #                 #             )
        #                 #         )
        #                 # print(zooka)
        #                 # exit()
        #                 # trip.partial_time_stay_corrections.loc[
        #                 #     arriving_group_slot
        #                 #     + full_time_slots_at_destination,
        #                 #     end_location,
        #                 # ] = (
        #                 #     partial_stay_correction * 2
        #                 # )
        #                 # trip.partial_time_stay_corrections.loc[
        #                 #     arriving_group_slot
        #                 #     + full_time_slots_at_destination
        #                 #     + 1,
        #                 #     end_location,
        #                 # ] = (
        #                 #     1 - partial_stay_correction * 2
        #                 # )
        #                 # print(trip.partial_time_stay_corrections)
        #                 # exit()
        #                 # partial_time_correction_factor: float = (
        #                 #     remainder_in_partial_slot
        #                 #     * remainder_in_partial_slot
        #                 #     / 2
        #                 #     + remainder_in_partial_slot
        #                 #     * (1 - remainder_in_partial_slot)
        #                 # # )
        #                 # if partial_time_correction_factor > 0:
        #                 #     if arriving_group_size > 0:
        #                 #         print(partial_time_correction_factor)

        #                 #         exit()
        #                 # print(remainder_in_partial_slot)
        #                 # exit()
        #                 # print(
        #                 #     remainder_in_partial_slot
        #                 #     * remainder_in_partial_slot
        #                 #     / 2
        #                 # )
        #                 # # exit()
        #                 # print(remainder_in_partial_slot)
        #                 # print(partial_time_correction_factor)
        #                 # print(leg_name)
        #                 # print(arriving_group_slot)
        #                 # print(full_time_slots_at_destination)

        #                 # trip.partial_time_stay_corrections.loc[
        #                 #     arriving_group_slot
        #                 #     # + full_time_slots_at_destination
        #                 #     ,
        #                 #     end_location,
        #                 # ] = (
        #                 #     # trip.partial_time_stay_corrections.loc[
        #                 #     #     arriving_group_slot
        #                 #     #     + full_time_slots_at_destination
        #                 #     # ][end_location]
        #                 #     # + partial_time_correction_factor
        #                 #     (1 - remainder_in_partial_slot)
        #                 #     / 2
        #                 # )
        #                 # # trip.partial_time_stay_corrections.loc[
        #                 # #     arriving_group_slot
        #                 # #     + full_time_slots_at_destination+1,
        #                 # #     end_location,
        #                 # # ] = (
        #                 # #     trip.partial_time_stay_corrections.loc[
        #                 # #         arriving_group_slot
        #                 # #         + full_time_slots_at_destination+1
        #                 # #     ][end_location]

        #                 # #     + (remainder_in_partial_slot
        #                 # # - partial_time_correction_factor)
        #                 # # )
        #                 # print(arriving_group_slot)
        #                 # print(trip.partial_time_stay_corrections)
        #                 # exit()

        #                 # Example: if the vehicle stays for X.25 hours,
        #                 # 3/4 of vehicles will use that in the first
        #                 # non-full slot. For the remaining 1/4, half
        # will be in
        #                 # that slot, and half in the next one
        #                 if partial_stay_correction > 0:
        #                     # We do not necessarily need that filter, but it
        #                     # avoids using elements beyond the end of the day

        #                     # print(partial_stay_correction)
        #                     # print(remainder_in_partial_slot)
        #                     # exit()
        #                     trip.location_split.loc[
        #                         arriving_group_slot
        #                         + full_time_slots_at_destination,
        #                         end_location,
        #                     ] = (
        #                         trip.location_split.loc[
        #                             arriving_group_slot
        #                             + full_time_slots_at_destination
        #                         ][end_location]
        #                         - partial_stay_correction
        #                     )

        #                     trip.location_split.loc[
        #                         arriving_group_slot
        #                         + full_time_slots_at_destination
        #                         + 1,
        #                         end_location,
        #                     ] = (
        #                         trip.location_split.loc[
        #                             arriving_group_slot
        #                             + full_time_slots_at_destination
        #                             + 1
        #                         ][end_location]
        #                         + partial_stay_correction
        #                     )
        #                     # print(trip.departures_impact)
        #                     # print(partial_stay_correction)
        #                     # # exit()
        #                     # if (
        #                     #     end_location == 'truck_hub'
        #                     #     and arriving_group_slot > 5
        #                     # ):
        #                     #     print(trip.departures_impact)
        #                     # trip.departures_impact.loc[
        #                     #     arriving_group_slot
        #                     #     + full_time_slots_at_destination,
        #                     #     end_location,
        #                     # ] = (
        #                     #     trip.departures_impact.loc[
        #                     #         arriving_group_slot
        #                     #         + full_time_slots_at_destination
        #                     #     ][end_location]
        #                     #     - partial_stay_correction
        #                     #     # + arriving_group_size
        #                     #     # * remainder_in_partial_slot
        #                     # )

        #                     # trip.departures_impact.loc[
        #                     #     arriving_group_slot
        #                     #     + full_time_slots_at_destination
        #                     #     + 1,
        #                     #     end_location,
        #                     # ] = (
        #                     #     trip.departures_impact.loc[
        #                     #         arriving_group_slot
        #                     #         + full_time_slots_at_destination
        #                     #         + 1
        #                     #     ][end_location]
        #                     #     + partial_stay_correction
        #                     #     # - arriving_group_size
        #                     #     # * remainder_in_partial_slot
        #                     # )

        #                     # trip.departures_impact.loc[
        #                     #     arriving_group_slot
        #                     #     + time_slots_at_destination
        #                     #     ,
        #                     #     end_location,
        #                     # ] = (
        #                     #     trip.departures_impact.loc[
        #                     #         arriving_group_slot
        #                     #         + time_slots_at_destination

        #                     #     ][end_location]
        #                     #     + partial_stay_correction
        #                     #     # + arriving_group_size
        #                     #     # * remainder_in_partial_slot
        #                     # )

        #                     # trip.departures_impact.loc[
        #                     #     arriving_group_slot
        #                     #     + time_slots_at_destination
        #                     #     + 1,
        #                     #     end_location,
        #                     # ] = (
        #                     #     trip.departures_impact.loc[
        #                     #         arriving_group_slot
        #                     #         + time_slots_at_destination
        #                     #         + 1
        #                     #     ][end_location]
        #                     #     # + arriving_group_size
        #                     #     # - first_slot_correction
        #                     #     + partial_stay_correction
        #                     #     # - arriving_group_size
        #                     #     # * remainder_in_partial_slot
        #                     # )
        #                     # print(partial_stay_correction)
        #                     # print(arriving_group_size)
        #                     # print(remainder_in_partial_slot)
        #                     # exit()
        #                     print('Rrrrrrrrr')
        #                     if (
        #                         end_location == 'truck_hub'
        #                         and arriving_group_slot > 5
        #                     ):
        #                         print(
        #                             arriving_group_slot
        #                             + full_time_slots_at_destination
        #                         )
        #                         print(
        #                             arriving_group_slot
        #                             + time_slots_at_destination
        #                             + 1
        #                         )
        #                     # print(trip.departures_impact)
        #                     # # exit()
        #                     # print(partial_stay_correction)
        #                     # print(trip.arrivals_impact)
        #                     # print(trip.location_split)
        #                     # exit()

        #                 # if remainder_in_partial_slot > 0:
        #                 #     if arriving_group_size > 0:
        #                 #         print(leg_name)
        #                 #         print(arriving_group_size)
        #                 #         print(trip.location_split)
        #                 #         print(trip.location_split.sum())
        #                 #         exit()

        #     else:
        #         travel_time_correction_factor = 0.5
        #         arriving_in_first_time_slot: np.ndarray = (
        #             current_leg_end_probabilities
        #             * travel_time_correction_factor
        #         )
        #         print('Correct this too?')
        #         arriving_in_next_time_slot: np.ndarray = np.roll(
        #             current_leg_end_probabilities
        #             * (1 - travel_time_correction_factor),
        #             1,
        #         )

        #         arrivals_together: np.ndarray = (
        #             arriving_in_first_time_slot + arriving_in_next_time_slot
        #         )
        #         cumuluative_arrivals: np.ndarray = arrivals_together.cumsum()

        #         trip.location_split[end_location] = (
        #             trip.location_split[end_location] + cumuluative_arrivals
        #         )
        #         trip.arrivals_impact[end_location] = (
        #             trip.arrivals_impact[end_location] + arrivals_together
        #         )
        # print(trip.name)
        # # # print(trip.partial_time_stay_corrections)
        # print(trip.location_split)
        # print(trip.location_split.sum())
        # exit()
        # # exit()
        # # print(trip.arrivals_impact)
        # # print(trip.departures_impact)
        # zooki = pd.DataFrame(
        #     np.zeros((24, 2)), columns=location_names, index=range(24)
        # )
        # zooki.loc[0, 'truck_hub'] = 1
        # rouki = (
        #     zooki.cumsum(axis=0)
        #     + trip.arrivals_impact.cumsum(axis=0)
        #     + trip.departures_impact.cumsum(axis=0)
        # )
        # rox = trip.location_split - rouki
        # print(rouki)
        # print(rox)
        # # exit()
        # # print(trip.departures_impact)
        # print('ooooo')
        # print(rox.max(axis=0))
        # print(rox.min(axis=0))
        # exit()
        # print(trip.arrivals_impact)
        # exit()

        # We can also get the percentage driving

        trip.percentage_driving: pd.Series[float] = (
            1 - trip.location_split.sum(axis=1)
        )

        # We also get the connectivity:
        trip.connectivity_per_location: pd.DataFrame = (
            trip.location_split.copy()
        )
        trip.maximal_delivered_power_per_location: pd.DataFrame = (
            trip.location_split.copy()
        )

        for location_name in trip.location_names:
            location_connectivity: float = scenario['locations'][
                location_name
            ]['connectivity']
            charging_power: float = scenario['locations'][location_name][
                'charging_power'
            ]
            charger_efficiency: float = scenario['locations'][location_name][
                'charger_efficiency'
            ]
            this_location_maximal_delivered_power: float = (
                location_connectivity * charging_power / charger_efficiency
            )
            trip.connectivity_per_location[location_name] = (
                trip.connectivity_per_location[location_name]
                * location_connectivity
            )
            trip.maximal_delivered_power_per_location[location_name] = (
                trip.maximal_delivered_power_per_location[location_name]
                * this_location_maximal_delivered_power
            )
        trip.connectivity: pd.Series = trip.connectivity_per_location.sum(
            axis=1
        )
        trip.maximal_delivered_power: pd.Series = (
            trip.maximal_delivered_power_per_location.sum(axis=1)
        )

        # We now can create a mobility matrix for the whole run
        run_time_tags: pd.DatetimeIndex = run_time.get_time_range(
            scenario, general_parameters
        )[0]

        # We only want the start and end locations that are in the legs
        run_mobility_index_tuples: ty.List[
            ty.Tuple[str, str, datetime.datetime]
        ] = [
            (leg_tuple[0], leg_tuple[1], time_tag)
            for leg_tuple in leg_tuples
            for time_tag in run_time_tags
        ]

        mobility_index_names: ty.List[str] = scenario['mobility_module'][
            'mobility_index_names'
        ]
        run_mobility_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
            run_mobility_index_tuples, names=mobility_index_names
        )

        # trip.run_mobility_matrix: pd.DataFrame = pd.DataFrame(
        #     columns=mobility_quantities, index=run_mobility_index
        # )
        # trip.run_mobility_matrix = trip.run_mobility_matrix.sort_index()

        # for leg_tuple in leg_tuples:
        #     cloned_mobility_matrix: pd.DataFrame = run_time.from_day_to_run(
        #         trip.mobility_matrix.loc[
        #             (leg_tuple[0], leg_tuple[1]), mobility_quantities
        #         ],
        #         run_time_tags,
        #         trip.day_start_hour,
        #         scenario,
        #         general_parameters,
        #     )
        #     for mobility_quantity in mobility_quantities:
        #         trip.run_mobility_matrix.at[
        #             (leg_tuple[0], leg_tuple[1]), mobility_quantity
        #         ] = cloned_mobility_matrix[mobility_quantity].values

        trip.run_mobility_matrix: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                trip.mobility_matrix,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
        )

        trip.run_battery_space_shifts_departures: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                trip.battery_space_shifts_departures,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        trip.run_battery_space_shifts_departures_impact: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                trip.battery_space_shifts_departures_impact,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        trip.run_battery_space_shifts_arrivals: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                trip.battery_space_shifts_arrivals,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        trip.run_battery_space_shifts_arrivals_impact: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                trip.battery_space_shifts_arrivals_impact,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
        )

        trip.run_battery_space_shifts_departures_weighted: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                trip.battery_space_shifts_departures_weighted,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        trip.run_battery_space_shifts_departures_impact_weighted: (
            pd.DataFrame
        ) = mobility_matrix_to_run_mobility_matrix(
            trip.battery_space_shifts_departures_impact_weighted,
            leg_tuples,
            run_mobility_index,
            run_time_tags,
            trip.day_start_hour,
            scenario,
            general_parameters,
        )
        trip.run_battery_space_shifts_arrivals_weighted: pd.DataFrame = (
            mobility_matrix_to_run_mobility_matrix(
                trip.battery_space_shifts_arrivals_weighted,
                leg_tuples,
                run_mobility_index,
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
        )
        trip.run_battery_space_shifts_arrivals_impact_weighted: (
            pd.DataFrame
        ) = mobility_matrix_to_run_mobility_matrix(
            trip.battery_space_shifts_arrivals_impact_weighted,
            leg_tuples,
            run_mobility_index,
            run_time_tags,
            trip.day_start_hour,
            scenario,
            general_parameters,
        )

        # We also do this for some other quantities
        day_start_hour: int = scenario['mobility_module']['day_start_hour']
        trip.run_location_split: pd.DataFrame = run_time.from_day_to_run(
            trip.location_split,
            run_time_tags,
            day_start_hour,
            scenario,
            general_parameters,
        )

        trip.run_connectivity_per_location: pd.DataFrame = (
            run_time.from_day_to_run(
                trip.connectivity_per_location,
                run_time_tags,
                day_start_hour,
                scenario,
                general_parameters,
            )
        )
        trip.run_maximal_delivered_power_per_location: pd.DataFrame = (
            run_time.from_day_to_run(
                trip.maximal_delivered_power_per_location,
                run_time_tags,
                day_start_hour,
                scenario,
                general_parameters,
            )
        )
        # trip.run_partial_time_stay_corrections: pd.DataFrame = (
        #     run_time.from_day_to_run(
        #         trip.partial_time_stay_corrections,
        #         run_time_tags,
        #         day_start_hour,
        #         scenario,
        #         general_parameters,
        #     )
        # )

        trip.run_percentage_driving: pd.Series = (
            1 - trip.run_location_split.sum(axis=1)
        )

        trip.run_connectivity: pd.Series = (
            trip.run_connectivity_per_location.sum(axis=1)
        )
        trip.run_maximal_delivered_power: pd.Series = (
            trip.run_maximal_delivered_power_per_location.sum(axis=1)
        )

        trip.next_leg_kilometers: pd.DataFrame = pd.DataFrame(
            np.zeros((HOURS_IN_A_DAY, len(trip.location_names))),
            columns=trip.location_names,
            index=range(HOURS_IN_A_DAY),
        )
        trip.next_leg_kilometers.index.name = 'Hour number (from day start)'
        # The standard version sets the kilometers in the time slot
        # before departure, this second, cumulative, version does so from
        # the moment the vehicles arrive
        # (or day start for the first leg of the trip)
        trip.next_leg_kilometers_cumulative: pd.DataFrame = (
            trip.next_leg_kilometers.copy()
        )

        for leg_index, leg_name in enumerate(trip.legs):

            leg_parameters = scenario['legs'][leg_name]
            start_location = leg_parameters['locations']['start']
            end_location = leg_parameters['locations']['end']

            if leg_index == 0:
                previous_leg_arrivals_amount: ty.List[float] = []
                for hour_index in range(HOURS_IN_A_DAY - 1):
                    # We skip the last time slot, as this should wrap the trip
                    # and we are not looking into the next day
                    # with this apporach

                    # For the standard version, we look if the vehicle
                    # is set to depart in the next time
                    upcoming_departures_kilometers = trip.mobility_matrix.loc[
                        (start_location, end_location, hour_index + 1),
                        'Departures kilometers',
                    ]

                    trip.next_leg_kilometers.loc[
                        hour_index, start_location
                    ] = (
                        trip.next_leg_kilometers.loc[hour_index][
                            start_location
                        ]
                        + upcoming_departures_kilometers
                    )

                    # For the other version, we look at all future departures

                    all_future_departures_kilometers = (
                        trip.mobility_matrix.loc[
                            (
                                start_location,
                                end_location,
                                list(range(hour_index + 1, HOURS_IN_A_DAY)),
                            ),
                            'Departures kilometers',
                        ].sum()
                    )

                    trip.next_leg_kilometers_cumulative.loc[
                        hour_index, start_location
                    ] = (
                        trip.next_leg_kilometers_cumulative.loc[hour_index][
                            start_location
                        ]
                        + all_future_departures_kilometers
                    )

            else:
                for hour_index in range(HOURS_IN_A_DAY - 1):
                    # We skip the last time slot, as this should wrap the trip
                    # and we are not looking into the next day
                    # with this apporach

                    # We do the same as for the first leg, but we need
                    # to limit that to the vehicles that already have
                    # arrived at the end location
                    upcoming_departures_kilometers_raw: float = (
                        trip.mobility_matrix['Departures kilometers'].loc[
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

                    trip.next_leg_kilometers.loc[
                        hour_index, start_location
                    ] = (
                        trip.next_leg_kilometers.loc[hour_index][
                            start_location
                        ]
                        + actual_upcoming_departures_kilometers
                    )

                    # Once again, the variant applies to all future departures

                    all_future_departures_kilometers_raw: float = (
                        trip.mobility_matrix['Departures kilometers']
                        .loc[start_location, end_location][
                            list(range(hour_index + 1, HOURS_IN_A_DAY))
                        ]
                        .sum()
                    )

                    actual_all_future_departures_kilometers = (
                        previous_arrivals_to_use
                        * all_future_departures_kilometers_raw
                    )

                    trip.next_leg_kilometers_cumulative.loc[
                        hour_index, start_location
                    ] = (
                        trip.next_leg_kilometers_cumulative.loc[hour_index][
                            start_location
                        ]
                        + actual_all_future_departures_kilometers
                    )

            previous_leg_arrivals_amount = trip.mobility_matrix[
                'Arrivals amount'
            ].loc[start_location, end_location]

        trip.run_next_leg_kilometers: pd.DataFrame = run_time.from_day_to_run(
            trip.next_leg_kilometers,
            run_time_tags,
            trip.day_start_hour,
            scenario,
            general_parameters,
        )
        trip.run_next_leg_kilometers_cumulative: pd.DataFrame = (
            run_time.from_day_to_run(
                trip.next_leg_kilometers_cumulative,
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
        )


def declare_class_instances(
    Chosen_class: ty.Type, scenario: ty.Dict, general_parameters: ty.Dict
) -> ty.List[ty.Type]:
    '''
    This function creates the instances of a class (Chosen_class),
    based on a scenario file name where the instances and their properties
    are given.
    '''
    scenario_vehicle: str = scenario['vehicle']['name']
    class_name: str = Chosen_class.class_name

    class_instances: ty.List[str] = scenario[class_name]

    instances: ty.List[ty.Type] = []

    for class_instance in class_instances:
        append_instance: bool = True
        if class_name == 'trips':
            trip_vehicle: str = scenario['trips'][class_instance]['vehicle']
            if trip_vehicle != scenario_vehicle:
                append_instance = False
        elif class_name == 'locations':
            location_vehicle: str = scenario['locations'][class_instance][
                'vehicle'
            ]
            if location_vehicle != scenario_vehicle:
                append_instance = False
        elif class_name == 'legs':
            leg_vehicle: str = scenario['legs'][class_instance]['vehicle']
            if leg_vehicle != scenario_vehicle:
                append_instance = False

        if append_instance:
            instances.append(
                Chosen_class(class_instance, scenario, general_parameters)
            )

    return instances


def declare_all_instances(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> ty.Tuple[ty.List[ty.Type], ...]:
    '''
    This declares all instances of the various objects
    (legs, locations,  trips).
    '''
    scenario_name: str = scenario['scenario_name']
    file_parameters: ty.Dict = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    locations: ty.List[ty.Type] = declare_class_instances(
        Location, scenario, general_parameters
    )

    legs: ty.List[ty.Type] = declare_class_instances(
        Leg, scenario, general_parameters
    )

    # We want to get the location connections
    location_connections_headers: ty.List[str] = scenario['mobility_module'][
        'location_connections_headers'
    ]
    location_connections_index_tuples: ty.List[ty.Tuple[str, str]] = [
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
        scenario['transport_factors']['weights']
    )
    for leg in legs:
        road_type_factor: float = sum(leg.road_type_mix * road_type_weights)
        fill_values: ty.List[float] = [
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
        # location_connections.loc[leg.start_location, leg.end_location] = (
        #     leg.duration,
        #     leg.distance,
        #     road_type_factor * leg.distance,
        # )
    location_connections.to_pickle(
        f'{output_folder}/{scenario_name}_location_connections.pkl'
    )

    trips: ty.List[ty.Type] = declare_class_instances(
        Trip, scenario, general_parameters
    )

    # We want to save the moblity matrixes
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
            f'{output_folder}/{scenario_name}_' f'{trip.name}_connectivity.pkl'
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

        # trip.partial_time_stay_corrections.to_pickle(
        #     f'{output_folder}/{scenario_name}_'
        #     f'{trip.name}_partial_time_stay_corrections.pkl'
        # )
        # trip.run_partial_time_stay_corrections.to_pickle(
        #     f'{output_folder}/{scenario_name}_'
        #     f'{trip.name}_run_partial_time_stay_corrections.pkl'
        # )

    return legs, locations, trips


if __name__ == '__main__':
    start_: datetime.datetime = datetime.datetime.now()
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: ty.Dict = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    case_name = 'Mopo'
    test_scenario_name: str = 'XX_van'
    scenario_file_name: str = (
        f'scenarios/{case_name}/{test_scenario_name}.toml'
    )
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
    scenario['scenario_name'] = test_scenario_name
    legs, locations, trips = declare_all_instances(
        scenario, case_name, general_parameters
    )

    # for leg in legs:
    #     print(
    #         leg.name,
    #         leg.distance,
    #         leg.duration,
    #         leg.hour_in_day_factors,
    #         leg.start_location,
    #         leg.end_location,
    #         leg.road_type_mix,
    #     )

    # for location in locations:
    #     print(location.name, location.connectivity, location.charging_power)

    # for trip in trips:
    #     # print(
    #     #     trip.name,
    #     #     trip.legs,
    #     #     trip.percentage_station_users,
    #     #     trip.start_probabilities,
    #     #     trip.time_between_legs,
    #     #     # trip.location_split
    #     # )
    #     # print(trip.name)
    #     # print(trip.location_split)
    #     # print(trip.connectivity)
    #     # print(trip.percentage_driving)
    #     # print(trip.percentage_driving.sum())
    #     # print(trip.partial_time_stay_corrections)
    #     print(trip.time_between_legs)
    #     print(trip.location_split)
    #     print(trip.location_split.sum(axis=0))
    #     # if trip.name == 'bus_weekday_in_holiday_week':
    #     #     print(trip.mobility_matrix.loc['bus_route_start',
    #     # 'bus_route_end'])
    #     exit()

    print((datetime.datetime.now() - start_).total_seconds())


# 1) Identify next leg (with prob)
# at H next leg = legs[0] * sumprobs[H+1:]
# departure probs legs[1] = dparture probs.roll(time at loc+duration)
# or use departures/arrivals from other module


# in LOCx legN until

# for leg in trip.legs:
#     start_location
#     end_location
#     trip_run_mobility_matrix.loc[start, end]
#     get sum over next hours of departures amount
#     sum goes from arrivals to departures
#     then make a run version
#     in mobility use trip probabilities to make run version
#     in consumption get energy for next leg
