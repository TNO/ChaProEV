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


class Trip:
    '''
    This class defines the  trips and their properties, from a scenario
    file that contains a list of instances and their properties.
    Trips are collections of legs that take place on a given day.
    Note that this day does not necessarily start (and end) at minight,
    but can start (and end) at an hour that is more logical/significant for the
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
        vehicle_parameters: ty.Dict = scenario['vehicle']
        vehicle_name: str = vehicle_parameters['name']

        location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
            'locations'
        ]
        location_names: ty.List[str] = [
            location_name
            for location_name in location_parameters
            if location_parameters[location_name]['vehicle'] == vehicle_name
        ]
        trip_parameters: ty.Dict = scenario['trips'][name]
        trip.legs: ty.List[str] = trip_parameters['legs']
        trip.time_between_legs: ty.List[float] = trip_parameters[
            'time_between_legs'
        ]
        trip.percentage_station_users: float = trip_parameters[
            'percentage_station_users'
        ]

        trip.start_probabilities: np.ndarray = np.array(
            trip_parameters['start_probabilities']
        )
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

        trip_legs_store: ty.List[str] = trip.legs.copy()
        time_between_legs_store: ty.List[float] = trip.time_between_legs.copy()
        if len(trip.repeated_sequence) > 0:
            trip.legs = []
            trip.time_between_legs = []
            repetition_iteration_index: int = 0
            for leg_index, leg in enumerate(trip_legs_store):

                if leg not in trip.repeated_sequence:
                    trip.legs.append(leg)
                    if leg_index < len(trip_legs_store) - 1:
                        trip.time_between_legs.append(
                            time_between_legs_store[leg_index]
                        )
                elif leg == trip.repeated_sequence[0]:
                    for repetition in range(
                        trip.repetition_amounts[repetition_iteration_index]
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
                        if (
                            repetition
                            < trip.repetition_amounts[
                                repetition_iteration_index
                            ]
                            - 1
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

        # We want to track the probabilities and time driving of previous
        # legs
        previous_leg_start_probabilities: np.ndarray = np.array(
            trip.start_probabilities
        )
        time_driving_previous_leg: float = float(0)

        # We want to track where the vehicle is
        trip.location_split: pd.DataFrame = pd.DataFrame(
            np.zeros((HOURS_IN_A_DAY, len(location_names))),
            columns=location_names,
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
            at_location_in_departure_hour: np.ndarray = (
                trip.start_probabilities / 2
            )
            vehicles_staying_put_whole_hour: np.ndarray = (
                1 - trip.start_probabilities.cumsum()
            )
            vehicles_that_did_not_start_trip_yet: np.ndarray = (
                at_location_in_departure_hour + vehicles_staying_put_whole_hour
            )
            trip.location_split[initial_location] = (
                vehicles_that_did_not_start_trip_yet
            )

        # To fill in the mobility matrix, we iterate over the legs of the trip
        for leg_index, leg_name in enumerate(trip.legs):
            # moki = False
            # maak = False
            # if trip.name == 'bus_weekday_in_holiday_week':
            #     # print(trip.legs)
            #     maak = True
            #     # exit()
            #     if leg_name == 'bus_from_route_start_to_depot':
            #         moki = True
            #         print(leg_name)
            #         print(leg_index)
            #     # exit()
            leg_parameters: ty.Dict = scenario['legs'][leg_name]
            start_location: str = leg_parameters['locations']['start']
            end_location: str = leg_parameters['locations']['end']
            time_driving: float = leg_parameters['duration']
            # We want to know the percentage of time driving due to this
            # leg in the current (hour) interval and subsequent ones
            # We first fill the intervals that are fully filled by the driving
            # e.g four ones if the driving is 4.2 hours
            time_driving_in_intervals: list[float] = [1] * math.floor(
                time_driving
            )
            # We then append the remainder (which is the duration if the
            # duration is smaller than the (hour) interval)
            remainder: float = time_driving - math.floor(time_driving)
            # But only if it is not zero (to avoid adding an unnecessary index)
            if remainder > 0:
                time_driving_in_intervals.append(remainder)
            distance: float = leg_parameters['distance']
            road_type_mix: np.ndarray = np.array(
                leg_parameters['road_type_mix']['mix']
            )
            road_type_weights: np.ndarray = np.array(
                scenario['transport_factors']['weights']
            )
            road_type_factor: float = float(
                sum(road_type_mix * road_type_weights)
            )
            weighted_distance: float = road_type_factor * distance

            if leg_index == 0:
                # The first leg is not shifted, by definition of the trip
                # start probabilities, as the trip starts with the first leg
                time_shift: float = 0
                current_leg_start_probabilities: np.ndarray = (
                    trip.start_probabilities
                )
            else:
                # We want to know how much time there is between legs
                # so that we can shift the start probabilities accordingly.
                # To get the time between a leg and the previous leg, we need
                # to know two things: the time spent driving in the
                # previous leg, and the
                # time spent between legs (i.e. the idle time)
                time_spent_at_location: float = trip.time_between_legs[
                    leg_index - 1
                ]
                # We can now increment the time shift
                time_shift = time_driving_previous_leg + time_spent_at_location
                # The leg departueres
                # take place into two time slots. These two slots
                # have numbers slot_shift and slot_shift+1
                slot_shift: int = math.floor(time_shift)
                # For example, if the time shift is 9.25 slots from the
                # day start, (9.25 hours if
                # hours are your units), then arrivals will occur in time
                # slots (hours if you use them) 9 and 10
                # The portion in the first slot is:
                first_slot_proportion: float = 1 - time_shift % 1
                # In the example above, the decimal part is 0.25, so the
                # proportion is (1-0.25)=0.75
                current_leg_start_probabilities = (
                    first_slot_proportion
                    * np.roll(previous_leg_start_probabilities, slot_shift)
                    + (1 - first_slot_proportion)
                    * np.roll(previous_leg_start_probabilities, slot_shift + 1)
                )
                # if maak:
                #     print(leg_index, leg_name)
                #     print(current_leg_start_probabilities)
                # if moki:
                #     print(leg_index, leg_name)
                #     print(current_leg_start_probabilities)
                #     exit()

            # if leg_index > 0:
            #     # We want to know how much time there is between legs
            #     # so that we can shift the start probabilities accordingly.
            #     # To get the time between a leg and the previous leg, we need
            #     # to know two things: the time spent driving in the
            #     # previous leg, and the
            #     # time spent between legs (i.e. the idle time)
            #     time_spent_at_location: float = trip.time_between_legs[
            #         leg_index - 1
            #     ]
            #     time_shift: float = (
            #         time_driving_previous_leg + time_spent_at_location
            #     )
            #     if maak:
            #         print(time_shift)
            #     # For previous leg departures in slot N, the corresponding
            #     # current leg departures.
            #     # take place into two time slots. These two slots
            #     # have numbers N+slot_shift and N+slot_shift+1
            #     slot_shift: int = math.floor(time_shift)
            #     # For example, if the time shift is 9.25 slots (9.25 hours if
            #     # hours are your units), then arrivals will occur in time
            #     # slots (hours if you use them) N+9 and N+10
            #     # The portion in the first slot is:
            #     first_slot_proportion: float = 1 - time_shift % 1
            #     # In the example above, the decimal part is 0.25, so the
            #     # proportion is (1-0.25)=0.75
            #     current_leg_start_probabilities: (
            #         np.ndarray
            #     ) = first_slot_proportion * np.roll(
            #         previous_leg_start_probabilities, slot_shift
            #     ) + (
            #         1 - first_slot_proportion
            #     ) * np.roll(
            #         previous_leg_start_probabilities, slot_shift + 1
            #     )
            #     if maak:
            #         print(leg_index, leg_name)
            #         print(current_leg_start_probabilities)
            #     if moki:
            #         print(leg_index, leg_name)
            #         print(current_leg_start_probabilities)
            #         exit()

            # else:
            #     # The first leg is not shifted, by definition of the trip
            #     # start probabilities, as the trip starts with the first leg
            #     time_shift = 0
            #     current_leg_start_probabilities = (
            #         previous_leg_start_probabilities
            #     )

            # For a departure shifted by timne shift, the corresponding
            # arrivals are shifted by the time driving and
            # take place into two time slots. These two slots
            # have numbers slot_shift and slot_shift+1
            arrival_slot_shift: int = math.floor(time_driving)
            # For example, if the time driving is 1.25 slots (1.25 hours if
            # hours are your units), then arrivals will occur in time
            # slots (hours if you use them) +1 and +2
            # The portion in the first slot is:
            first_slot_proportion = 1 - time_driving % 1
            # In the example above, the decimal part is 0.25, so the proportion
            # is (1-0.25)=0.75
            current_leg_end_probabilities: (
                np.ndarray
            ) = first_slot_proportion * np.roll(
                current_leg_start_probabilities, arrival_slot_shift
            ) + (
                1 - first_slot_proportion
            ) * np.roll(
                current_leg_start_probabilities, arrival_slot_shift + 1
            )
            # if moki:
            #     print(current_leg_end_probabilities)
            #     exit()
            # if moki:
            #     print(start_location, end_location)
            #     print(trip.mobility_matrix.loc[start_location, end_location])
            #     # exit()

            # With this, we can add this leg's contribution to the
            # mobility matrix

            trip.mobility_matrix.loc[
                (start_location, end_location), 'Departures amount'
            ] = (
                pd.Series(
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 'Departures amount'
                    ]
                ).values
                + current_leg_start_probabilities
            )

            # We need to convert the first element to Series for type hinting
            # reasons, as MyPy does not know it is a Series otherwise

            trip.mobility_matrix.loc[
                (start_location, end_location), 'Arrivals amount'
            ] = (
                pd.Series(
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 'Arrivals amount'
                    ]
                ).values
                + current_leg_end_probabilities
            )
            # We need to convert the first element to Series for type hinting
            # reasons, as MyPy does not know it is a Series otherwise

            # if moki:
            #     print(trip.name)
            #     print('<<<<')
            #     print(trip.mobility_matrix.loc[start_location, end_location])
            #     # exit()

            start_distance_probabilities: np.ndarray = np.array(
                [
                    current_leg_start_probability * distance
                    for (
                        current_leg_start_probability
                    ) in current_leg_start_probabilities
                ]
            )

            # print(start_distance_probabilities)
            # print(current_leg_start_probabilities)
            # exit()
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Departures kilometers'
            ] = (
                pd.Series(
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 'Departures kilometers'
                    ]
                ).values
                + start_distance_probabilities
            )
            # We need to convert the first element to Series for type hinting
            # reasons, as MyPy does not know it is a Series otherwise

            start_weighted_distance_probabilities: np.ndarray = np.array(
                np.array(current_leg_start_probabilities) * weighted_distance
            )
            trip.mobility_matrix.loc[
                (start_location, end_location),
                'Departures weighted kilometers',
            ] = (
                pd.Series(
                    trip.mobility_matrix.loc[
                        (start_location, end_location),
                        'Departures weighted kilometers',
                    ]
                ).values
                + start_weighted_distance_probabilities
            )
            # We need to convert the first element to Series for type hinting
            # reasons, as MyPy does not know it is a Series otherwise

            end_distance_probabilities: np.ndarray = np.array(
                current_leg_end_probabilities * distance
            )
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Arrivals kilometers'
            ] = (
                pd.Series(
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 'Arrivals kilometers'
                    ]
                ).values
                + end_distance_probabilities
            )
            # We need to convert the first element to Series for type hinting
            # reasons, as MyPy does not know it is a Series otherwise

            end_weighted_distance_probabilities: np.ndarray = np.array(
                np.array(current_leg_end_probabilities) * weighted_distance
            )
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Arrivals weighted kilometers'
            ] = (
                pd.Series(
                    trip.mobility_matrix.loc[
                        (start_location, end_location),
                        'Arrivals weighted kilometers',
                    ]
                ).values
                + end_weighted_distance_probabilities
            )
            # We need to convert the first element to Series for type hinting
            # reasons, as MyPy does not know it is a Series otherwise

            # We also track the duration, distance, and wrighted distance
            # Note that these could change with time as well (for example
            # with a correction factor added at the run level)
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Duration (hours)'
            ] = time_driving
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Distance (km)'
            ] = distance
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Weighted distance (km)'
            ] = weighted_distance

            # Finally, we update the previous leg values with the current
            # ones
            previous_leg_start_probabilities = current_leg_start_probabilities

            # exit()
            time_driving_previous_leg = time_driving

            # start_time_at_destination: float = time_shift + time_driving
            if leg_index < len(trip.legs) - 1:
                time_spent_at_destination: float = trip.time_between_legs[
                    leg_index
                ]
            else:
                time_spent_at_destination = (
                    8
                    # HOURS_IN_A_DAY - start_time_at_destination - 6
                )
            time_slots_at_destination: int = math.ceil(
                time_spent_at_destination
            )
            full_time_slots_at_destination: int = math.floor(
                time_spent_at_destination
            )
            remainder_in_partial_slot: float = time_spent_at_destination % 1

            if leg_index < len(trip.legs) - 1:
                # if len(trip.legs) > 2:
                #     print(leg_index)
                #     print(current_leg_start_probabilities)
                #     print(current_leg_end_probabilities)
                #     if leg_index == 2:
                #         exit()
                for arriving_group_slot, arriving_group_size in enumerate(
                    current_leg_end_probabilities
                ):

                    if (
                        arriving_group_slot + full_time_slots_at_destination
                        < HOURS_IN_A_DAY
                    ):  # This should not matter, as the trips end before the
                        # day ends, by definition, but we can have issues due
                        # to the way we iterate.

                        # print(arriving_group_slot, arriving_group_size)
                        for stay_slot in range(time_slots_at_destination):
                            if stay_slot < full_time_slots_at_destination:
                                trip.location_split.loc[
                                    arriving_group_slot + stay_slot,
                                    end_location,
                                ] = (
                                    trip.location_split.loc[
                                        arriving_group_slot + stay_slot
                                    ][end_location]
                                    + arriving_group_size
                                )
                            else:
                                trip.location_split.loc[
                                    arriving_group_slot + stay_slot,
                                    end_location,
                                ] = trip.location_split.loc[
                                    arriving_group_slot + stay_slot
                                ][
                                    end_location
                                ] + (
                                    arriving_group_size
                                    * remainder_in_partial_slot
                                )
                            # if remainder_in_partial_slot > 0:
                            # print(leg_name)
                            # if arriving_group_size > 0:
                            #     print(leg_name)
                            #     print(arriving_group_size)
                            #     print(time_slots_at_destination)
                            #     print(end_location)
                            #         print(trip.location_split)

                        # The vehicles arrive uniformaly in the first slot
                        first_slot_correction: float = arriving_group_size / 2

                        trip.location_split.loc[
                            arriving_group_slot, end_location
                        ] = (
                            trip.location_split.loc[arriving_group_slot][
                                end_location
                            ]
                            - first_slot_correction
                        )

                        # This propagates through to the first non-full slot:
                        trip.location_split.loc[
                            arriving_group_slot
                            + full_time_slots_at_destination,
                            end_location,
                        ] = (
                            trip.location_split.loc[
                                arriving_group_slot
                                + full_time_slots_at_destination
                            ][end_location]
                            + first_slot_correction
                        )

                        # For partial stays (less than an hour), there is
                        # another correction:
                        partial_stay_correction = arriving_group_size * (
                            remainder_in_partial_slot
                            * (remainder_in_partial_slot)
                            / 2
                        )
                        # Example: if the vehicle satys for X.25 hours,
                        # 3/4 of vehicles will use that in the first
                        # non-full slot. For the remaining 1/4, half will be in
                        # that slot, and half in the next one
                        if partial_stay_correction > 0:
                            # We do not necessarily need that filter, but it
                            # avoids using elements beyond the end of the day

                            # print(partial_stay_correction)
                            # print(remainder_in_partial_slot)
                            # exit()
                            trip.location_split.loc[
                                arriving_group_slot
                                + full_time_slots_at_destination,
                                end_location,
                            ] = (
                                trip.location_split.loc[
                                    arriving_group_slot
                                    + full_time_slots_at_destination
                                ][end_location]
                                - partial_stay_correction
                            )

                            trip.location_split.loc[
                                arriving_group_slot
                                + full_time_slots_at_destination
                                + 1,
                                end_location,
                            ] = (
                                trip.location_split.loc[
                                    arriving_group_slot
                                    + full_time_slots_at_destination
                                    + 1
                                ][end_location]
                                + partial_stay_correction
                            )

                        # if remainder_in_partial_slot > 0:
                        #     if arriving_group_size > 0:
                        #         print(leg_name)
                        #         print(arriving_group_size)
                        #         print(trip.location_split)
                        #         print(trip.location_split.sum())
                        #         exit()

            else:
                arriving_in_first_time_slot: np.ndarray = (
                    current_leg_end_probabilities / 2
                )
                arriving_in_next_time_slot: np.ndarray = np.roll(
                    arriving_in_first_time_slot, 1
                )
                arrivals_together: np.ndarray = (
                    arriving_in_first_time_slot + arriving_in_next_time_slot
                )
                cumuluative_arrivals: np.ndarray = arrivals_together.cumsum()

                trip.location_split[end_location] = (
                    trip.location_split[end_location] + cumuluative_arrivals
                )

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

        for location_name in location_names:
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

        trip.run_mobility_matrix: pd.DataFrame = pd.DataFrame(
            columns=mobility_quantities, index=run_mobility_index
        )
        trip.run_mobility_matrix = trip.run_mobility_matrix.sort_index()

        for leg_tuple in leg_tuples:
            cloned_mobility_matrix: pd.DataFrame = run_time.from_day_to_run(
                trip.mobility_matrix.loc[
                    (leg_tuple[0], leg_tuple[1]), mobility_quantities
                ],
                run_time_tags,
                trip.day_start_hour,
                scenario,
                general_parameters,
            )
            for mobility_quantity in mobility_quantities:
                trip.run_mobility_matrix.at[
                    (leg_tuple[0], leg_tuple[1]), mobility_quantity
                ] = cloned_mobility_matrix[mobility_quantity].values

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
            np.zeros((HOURS_IN_A_DAY, len(location_names))),
            columns=location_names,
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

    return legs, locations, trips


if __name__ == '__main__':
    start_: datetime.datetime = datetime.datetime.now()
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: ty.Dict = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    case_name = 'Mopo'
    test_scenario_name: str = 'XX_car'
    scenario_file_name: str = (
        f'scenarios/{case_name}/{test_scenario_name}.toml'
    )
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
    scenario['scenario_name'] = test_scenario_name
    legs, locations, trips = declare_all_instances(
        scenario, case_name, general_parameters
    )

    for leg in legs:
        print(
            leg.name,
            leg.distance,
            leg.duration,
            leg.hour_in_day_factors,
            leg.start_location,
            leg.end_location,
            leg.road_type_mix,
        )

    for location in locations:
        print(location.name, location.connectivity, location.charging_power)

    for trip in trips:
        print(
            trip.name,
            trip.legs,
            trip.percentage_station_users,
            trip.start_probabilities,
            trip.time_between_legs,
            # trip.location_split
        )
        print(trip.name)
        print(trip.location_split)
        print(trip.connectivity)
        print(trip.percentage_driving)
        print(trip.percentage_driving.sum())
        # if trip.name == 'bus_weekday_in_holiday_week':
        #     print(trip.mobility_matrix.loc['bus_route_start',
        # 'bus_route_end'])
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
