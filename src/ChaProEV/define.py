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

    def __init__(leg, name: str, scenario: ty.Dict) -> None:
        leg.name: str = name

        leg_parameters: ty.Dict = scenario['legs'][name]
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

    def __init__(location, name: str, scenario: ty.Dict) -> None:
        location.name: str = name

        location_parameters: ty.Dict[str, float] = scenario['locations'][name]
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

    def __init__(trip, name: str, scenario: ty.Dict) -> None:
        trip.name: str = name

        location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
            'locations'
        ]
        location_names: ty.List[str] = [
            location_name for location_name in location_parameters
        ]
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
        trip.day_start_hour: int = scenario['mobility_module'][
            'day_start_hour'
        ]
        # We want to create a mobility matrix for the trip. This matrix will
        # have start and end locations (plus hour in day, starting
        # at day start) as an index, and departures, arrivals as columns (
        # each with amounts, distances, weighted distances)
        HOURS_IN_A_DAY: int = scenario['time']['HOURS_IN_A_DAY']
        mobility_index_tuples: ty.List[ty.Tuple[str, str, int]] = [
            (start_location, end_location, hour_number)
            for start_location in location_names
            for end_location in location_names
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

        # We want to track the probabilities and time driving of previous legs
        previous_leg_start_probabilities: np.ndarray = np.array(
            trip.start_probabilities
        )
        time_driving_previous_leg: float = float(0)

        # To fill in the mobility matrix, we iterate over the legs of the trip
        for leg_index, leg_name in enumerate(trip.legs):
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

            if leg_index > 0:
                # We want to know how much time there is between legs
                # so that we can shift the start probabilities accordingly.
                # To get the time between a leg and the previous leg, we need
                # to know two things: the time spent driving in the
                # previous leg, and the
                # time spent between legs (i.e. the idle time)
                time_spent_at_location: float = trip.time_between_legs[
                    leg_index - 1
                ]
                time_shift: float = (
                    time_driving_previous_leg + time_spent_at_location
                )
                # For previous leg departures in slot N, the corresponding
                # current leg departures.
                # take place into two time slots. These two slots
                # have numbers N+slot_shift and N+slot_shift+1
                slot_shift: int = math.floor(time_shift)
                # For example, if the time shift is 9.25 slots (9.25 hours if
                # hours are your units), then arrivals will occur in time
                # slots (hours if you use them) N+9 and N+10
                # The portion in the first slot is:
                first_slot_proportion: float = 1 - time_shift % 1
                # In the example above, the decimal part is 0.25, so the
                # proportion is (1-0.25)=0.75
                current_leg_start_probabilities: (
                    np.ndarray
                ) = first_slot_proportion * np.roll(
                    previous_leg_start_probabilities, slot_shift
                ) + (
                    1 - first_slot_proportion
                ) * np.roll(
                    previous_leg_start_probabilities, slot_shift + 1
                )

            else:
                # The first leg is not shifted, by definition of the trip
                # start probabilities, as the trip starts with the first leg
                time_shift = 0
                current_leg_start_probabilities = (
                    previous_leg_start_probabilities
                )

            # For a departure in slot N, the corresponding arrivals
            # take place into two time slots. These two slots
            # have numbers N+slot_shift and N+slot_shift+1
            slot_shift = math.floor(time_driving)
            # For example, if the time driving is 1.25 slots (1.25 hours if
            # hours are your units), then arrivals will occur in time
            # slots (hours if you use them) N+1 and N+2
            # The portion in the first slot is:
            first_slot_proportion = 1 - time_driving % 1
            # In the example above, the decimal part is 0.25, so the proportion
            # is (1-0.25)=0.75
            current_leg_end_probabilities: (
                np.ndarray
            ) = first_slot_proportion * np.roll(
                current_leg_start_probabilities, slot_shift
            ) + (
                1 - first_slot_proportion
            ) * np.roll(
                current_leg_start_probabilities, slot_shift + 1
            )

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

            start_distance_probabilities: np.ndarray = np.array(
                current_leg_start_probabilities * distance
            )
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

            # Finally, we update the previous leg values with the current ones
            previous_leg_start_probabilities = current_leg_start_probabilities
            time_driving_previous_leg = time_driving

        # We now can create a mobility matrix for the whole run
        run_time_tags: pd.DatetimeIndex = run_time.get_time_range(scenario)[0]

        run_mobility_index_tuples: ty.List[
            ty.Tuple[str, str, datetime.datetime]
        ] = [
            (start_location, end_location, time_tag)
            for start_location in location_names
            for end_location in location_names
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

        for start_location in location_names:
            for end_location in location_names:
                cloned_mobility_matrix: pd.DataFrame = (
                    run_time.from_day_to_run(
                        trip.mobility_matrix.loc[
                            (start_location, end_location), mobility_quantities
                        ],
                        run_time_tags,
                        trip.day_start_hour,
                        scenario,
                    )
                )
                for mobility_quantity in mobility_quantities:
                    trip.run_mobility_matrix.at[
                        (start_location, end_location), mobility_quantity
                    ] = cloned_mobility_matrix[mobility_quantity].values

        # frequency_parameters = scenario['run']['frequency']
        # trip_frequency_size = frequency_parameters['size']
        # trip_frequency_type = frequency_parameters['type']
        # trip_frequency = f'{trip_frequency_size}{trip_frequency_type}'

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
            # print(trip.name)
            # print(leg_name)
            leg_parameters = scenario['legs'][leg_name]
            start_location = leg_parameters['locations']['start']
            end_location = leg_parameters['locations']['end']
            # print(start_location)
            # print(trip.mobility_matrix.loc[start_location, end_location])
            if leg_index == 0:
                previous_leg_arrivals_amount: ty.List[float] = []
                for hour_index in range(HOURS_IN_A_DAY - 1):
                    # We skip the last time slot, as this should wrap the trip
                    # and we are not looking into the next day
                    # with this apporach

                    # For the standard version, we look if the vehicle
                    # is set to depart in the next time
                    upcoming_departures = trip.mobility_matrix.loc[
                        (start_location, end_location, hour_index + 1),
                        'Departures kilometers',
                    ]

                    trip.next_leg_kilometers.loc[
                        hour_index, start_location
                    ] = (
                        trip.next_leg_kilometers.loc[hour_index][
                            start_location
                        ]
                        + upcoming_departures
                    )

                    # For the other version, we look at all future departures

                    all_future_departures = trip.mobility_matrix.loc[
                        (
                            start_location,
                            end_location,
                            list(range(hour_index + 1, HOURS_IN_A_DAY)),
                        ),
                        'Departures kilometers',
                    ].sum()

                    trip.next_leg_kilometers_cumulative.loc[
                        hour_index, start_location
                    ] = (
                        trip.next_leg_kilometers_cumulative.loc[hour_index][
                            start_location
                        ]
                        + all_future_departures
                    )

                    # trip.next_leg_kilometers.loc[
                    #     hour_index, start_location
                    # ] += upcoming_departures

                    # trip.next_leg_kilometers.loc[
                    #     hour_index, start_location
                    # ] += trip.mobility_matrix.loc[
                    #     (start_location, end_location, hour_index + 1),
                    #     'Departures kilometers'
                    # ]

                    # trip.next_leg_kilometers.loc[
                    #     hour_index, start_location
                    # ] += trip.mobility_matrix.loc[
                    #     start_location, end_location
                    # ][
                    #     'Departures kilometers'
                    # ].values[
                    #     hour_index + 1
                    # ]
                    # For the other version, we look at all future departures
                    # trip.next_leg_kilometers_cumulative.loc[
                    #     hour_index, start_location
                    # ] += (
                    #     trip.mobility_matrix.loc[start_location,
                    #       end_location][
                    #         'Departures kilometers'
                    #     ]
                    #     .values[hour_index + 1 :]
                    #     .sum()
                    # )
            else:
                for hour_index in range(HOURS_IN_A_DAY - 1):
                    # We skip the last time slot, as this should wrap the trip
                    # and we are not looking into the next day
                    # with this apporach

                    # We do the same as for the first leg, but we need
                    # to limit that to the vehicles that already have
                    # arrived at the end location
                    upcoming_departures_raw: float = trip.mobility_matrix[
                        'Departures amount'
                    ].loc[start_location, end_location, hour_index + 1]
                    # print(

                    previous_arrivals_to_use: float = sum(
                        previous_leg_arrivals_amount[: hour_index + 1]
                    )
                    actual_upcoming_departures = (
                        upcoming_departures_raw * previous_arrivals_to_use
                    )

                    trip.next_leg_kilometers.loc[
                        hour_index, start_location
                    ] = (
                        trip.next_leg_kilometers.loc[hour_index][
                            start_location
                        ]
                        + actual_upcoming_departures
                    )
                    # trip.next_leg_kilometers.loc[
                    #     hour_index, start_location
                    # ] += (
                    #     trip.mobility_matrix.loc[start_location,
                    #           end_location][
                    #         'Departures kilometers'
                    #     ].values[hour_index + 1]
                    # ) * (
                    #     previous_leg_arrivals_amount[: hour_index + 1].sum()
                    # )

                    # Once again, the variant applies to all future departures

                    all_future_departures_raw: float = (
                        trip.mobility_matrix['Departures amount']
                        .loc[start_location, end_location][
                            list(range(hour_index + 1, HOURS_IN_A_DAY))
                        ]
                        .sum()
                    )

                    actual_all_future_departures = (
                        previous_arrivals_to_use * all_future_departures_raw
                    )

                    trip.next_leg_kilometers_cumulative.loc[
                        hour_index, start_location
                    ] = (
                        trip.next_leg_kilometers_cumulative.loc[hour_index][
                            start_location
                        ]
                        + actual_all_future_departures
                    )

                    # trip.next_leg_kilometers_cumulative.loc[
                    #     hour_index, start_location
                    # ] += (
                    #     trip.mobility_matrix.loc[start_location,
                    # end_location][
                    #         'Departures kilometers'
                    #     ]
                    #     .values[hour_index + 1 :]
                    #     .sum()
                    # ) * (
                    #     previous_leg_arrivals_amount[: hour_index + 1].sum()
                    # )

            previous_leg_arrivals_amount = trip.mobility_matrix[
                'Arrivals amount'
            ].loc[start_location, end_location]

        trip.run_next_leg_kilometers: pd.DataFrame = run_time.from_day_to_run(
            trip.next_leg_kilometers,
            run_time_tags,
            trip.day_start_hour,
            scenario,
        )
        trip.run_next_leg_kilometers_cumulative: pd.DataFrame = (
            run_time.from_day_to_run(
                trip.next_leg_kilometers_cumulative,
                run_time_tags,
                trip.day_start_hour,
                scenario,
            )
        )

        # # For these, the year, month and day are not important,
        # # as they will be omitted, so we put generic values.
        # trip_start = datetime.datetime(2001, 1, 1, trip.day_start_hour)
        # trip_end = datetime.datetime(2001, 1, 2, trip.day_start_hour)
        # trip_time_tags = pd.date_range(
        #     start=trip_start,
        #     end=trip_end,
        #     freq=trip_frequency,
        #     inclusive='left'
        #     # We want the start timetag, but not the end one, so we need
        #     # to say it is closed left
        # )
        # trip_time_index_tuples = [
        #     (time_tag.hour, time_tag.minute, time_tag.second)
        #     for time_tag in trip_time_tags
        # ]

        # trip.time_index = pd.MultiIndex.from_tuples(
        #     trip_time_index_tuples, name=['Hour', 'Minute', 'Second']
        # )

        # trip.base_dataframe = pd.DataFrame(index=trip.time_index)

        # empty_values = np.empty((len(trip.time_index), len(location_names)))
        # empty_values[:] = np.nan
        # trip.base_dataframe[location_names] = empty_values
        # trip.located_at = trip.base_dataframe.copy()
        # trip.connected = trip.base_dataframe.copy()
        # trip.available_power_kW = trip.base_dataframe.copy()
        # trip.battery_space_kWh = trip.base_dataframe.copy()
        # trip.drawn_charge_kWh = trip.base_dataframe.copy()
        # trip.energy_necessary_for_next_leg = trip.base_dataframe.copy()


def declare_class_instances(
    Chosen_class: ty.Type, scenario: ty.Dict
) -> ty.List[ty.Type]:
    '''
    This function creates the instances of a class (Chosen_class),
    based on a scenario file name where the instances and their properties
    are given.
    '''

    class_name: str = Chosen_class.class_name

    class_instances: ty.List[str] = scenario[class_name]

    instances: ty.List[ty.Type] = []

    for class_instance in class_instances:
        append_instance: bool = True
        if class_name == 'trips':
            scenario_vehicle: str = scenario['vehicle']['name']
            trip_vehicle: str = scenario['trips'][class_instance]['vehicle']
            if trip_vehicle != scenario_vehicle:
                append_instance = False

        if append_instance:
            instances.append(Chosen_class(class_instance, scenario))

    return instances


def declare_all_instances(
    scenario: ty.Dict, case_name: str
) -> ty.Tuple[ty.List[ty.Type], ...]:
    '''
    This declares all instances of the various objects
    (legs, locations,  trips).
    '''
    scenario_name: str = scenario['scenario_name']
    file_parameters: ty.Dict = scenario['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    groupfile_root: str = file_parameters['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'
    # loc_start = datetime.datetime.now()
    locations: ty.List[ty.Type] = declare_class_instances(Location, scenario)
    # print('Loc', (datetime.datetime.now()-loc_start).total_seconds())
    # leg_start = datetime.datetime.now()
    legs: ty.List[ty.Type] = declare_class_instances(Leg, scenario)
    # print('Leg', (datetime.datetime.now()-leg_start).total_seconds())
    # loc_conn_start = datetime.datetime.now()
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

    cook.save_dataframe(
        location_connections,
        f'{scenario_name}_location_connections',
        groupfile_name,
        output_folder,
        scenario,
    )

    # print('Loc', (datetime.datetime.now()-loc_conn_start).total_seconds())

    # tri_start = datetime.datetime.now()

    trips: ty.List[ty.Type] = declare_class_instances(Trip, scenario)
    # print('Trip', (datetime.datetime.now()-tri_start).total_seconds())
    # matrix_start = datetime.datetime.now()
    # We want to save the moblity matrixes
    for trip in trips:
        mobility_table_name: str = (
            f'{scenario_name}_{trip.name}_mobility_matrix'
        )
        cook.save_dataframe(
            trip.mobility_matrix,
            mobility_table_name,
            groupfile_name,
            output_folder,
            scenario,
        )
        run_mobility_table_name: str = (
            f'{scenario_name}_{trip.name}_run_mobility_matrix'
        )
        cook.save_dataframe(
            trip.run_mobility_matrix,
            run_mobility_table_name,
            groupfile_name,
            output_folder,
            scenario,
        )
        cook.save_dataframe(
            trip.next_leg_kilometers,
            f'{scenario_name}_{trip.name}_next_leg_kilometers',
            groupfile_name,
            output_folder,
            scenario,
        )
        cook.save_dataframe(
            trip.run_next_leg_kilometers,
            f'{scenario_name}_{trip.name}_run_next_leg_kilometers',
            groupfile_name,
            output_folder,
            scenario,
        )
        cook.save_dataframe(
            trip.next_leg_kilometers_cumulative,
            f'{scenario_name}_{trip.name}_next_leg_kilometers_cumulative',
            groupfile_name,
            output_folder,
            scenario,
        )
        cook.save_dataframe(
            trip.run_next_leg_kilometers_cumulative,
            f'{scenario_name}_{trip.name}'
            f'_run_next_leg_kilometers_cumulative',
            groupfile_name,
            output_folder,
            scenario,
        )
    # print('Mat', (datetime.datetime.now()-matrix_start).total_seconds())

    return legs, locations, trips


if __name__ == '__main__':
    case_name: str = 'local_impact_BEVs'
    scenario_file_name: str = f'scenarios/{case_name}/baseline.toml'
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
    legs, locations, trips = declare_all_instances(scenario, case_name)

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
            trip.mobility_matrix.loc['home'],
        )
        # exit()


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
