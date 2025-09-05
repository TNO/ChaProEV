'''
This module computes the various functions related to mobility.
It contains the following functions:
1. **get_trip_probabilities_per_day_type:** This function computes the trip
probabilities per day type.
2. **get_run_trip_probabilities:** Gets a DataFrame containing the trip
probabilities for the whole run.
3. **get_run_mobility_matrix:**Takes the matrices for different trips and adds
them up (weighed on probability) to get a matrix for the whole run.
4. **get_day_type_start_location:** Tells us the proportion of vehicles
that start their day at a given location (per day type)
5. **get_location_split:** Produces the location split of the vehicles
for the whole run
6. **get_starting_location_split:** Gets the location split at run start
'''

import datetime

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

try:
    import define  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import define  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


class ChargingSession:
    '''
    This class defines the charging sessions for a whole run.
    The quantities other than start time, end time, and location
    are proprtional to the size of the session (the group travelling).
    We scale the travelling group soze (and associated quantities)
    according to the trip probability.
    '''

    class_name: str = 'charging_session'

    def __init__(
        self,
        trip_charging_session: define.TripChargingSession,
        day_start_time_tag: datetime.datetime,
        trip_probability: float,
    ) -> None:

        self.start_time: datetime.datetime = (
            day_start_time_tag
            + datetime.timedelta(hours=trip_charging_session.start_time)
        )
        self.end_time: datetime.datetime = (
            day_start_time_tag
            + datetime.timedelta(hours=trip_charging_session.end_time)
        )

        self.location: str = trip_charging_session.location
        self.previous_leg_consumption: float = (
            trip_charging_session.previous_leg_consumption * trip_probability
        )
        self.next_leg_consumption: float = (
            trip_charging_session.next_leg_consumption * trip_probability
        )
        self.connectivity: float = (
            trip_charging_session.connectivity * trip_probability
        )
        self.power_to_vehicle: float = (
            trip_charging_session.power_to_vehicle * trip_probability
        )
        self.power_from_network: float = (
            trip_charging_session.power_from_network * trip_probability
        )
        self.power_from_vehicle: float = (
            trip_charging_session.power_from_vehicle * trip_probability
        )
        self.power_to_network: float = (
            trip_charging_session.power_to_network * trip_probability
        )


class NextDayStartChargingSession:
    '''
    This class defines the charging sessions fon the next day after a trip.
    These represent the sessions before the first leg of the next day.
    '''

    class_name: str = 'charging_session'

    def __init__(
        self,
        day_start_location: str,
        next_day_start_session_start: datetime.datetime,
        next_day_start_session_end: datetime.datetime,
        previous_leg_consumption: float,
        next_leg_consumption: float,
        group_size: float,
        location_connectivity: float,
        location_power_to_vehicle: float,
        location_power_from_network: float,
        location_power_from_vehicle: float,
        location_power_to_network: float,
    ) -> None:

        self.start_time: datetime.datetime = (
            next_day_start_session_start
        )
        self.end_time: datetime.datetime = (
            next_day_start_session_end
        )
        self.location: str = day_start_location

        self.previous_leg_consumption: float = (
            previous_leg_consumption * group_size
        )
        self.next_leg_consumption: float = (
            next_leg_consumption * group_size
        )
        self.connectivity: float = (
            location_connectivity * group_size
        )
        self.power_to_vehicle: float = (
            location_power_to_vehicle * group_size
        )
        self.power_from_network: float = (
            location_power_from_network * group_size
        )
        self.power_from_vehicle: float = (
            location_power_from_vehicle * group_size
        )
        self.power_to_network: float = (
            location_power_to_network * group_size
        )


def get_run_charging_sessions(
    trips: list[define.Trip],
    trip_probabilities_per_day_type: pd.DataFrame,
    scenario: Box,
    general_parameters: Box,
) -> list[ChargingSession]:
    # day_start_location_split: pd.DataFrame = (
    # get_day_type_start_location_split(
    #     scenario, general_parameters
    # ))
    # vehicle_consumption: float = (
    #     scenario.vehicle.base_consumption_per_km.electricity_kWh
    # )
    charging_sessions: list = []
    time_tags_and_types: list[tuple[datetime.datetime, str]] = (
        run_time.get_day_start_time_tags_and_types(
            scenario, general_parameters
        )
    )
    for day_tag_index, (day_start_time_tag, day_type) in enumerate(
        time_tags_and_types
    ):
        for trip in trips:
            trip_probability: float = trip_probabilities_per_day_type.loc[
                trip.name
            ][
                day_type
            ]  # type: ignore
            if trip_probability > 0:

                for trip_charging_session in trip.charging_sessions:

                    charging_sessions.append(
                        ChargingSession(
                            trip_charging_session,
                            day_start_time_tag,
                            trip_probability,
                        )
                    )

                # # We now look at the next day's start charging sessions
                # # There are none after the last day of the run
                # previous_leg_consumption: float = 0
                # # We set it top zero, as the last leg consumption
                # # goes to the last session of the original day
                # # (but this can change later, as the last session might
                # # spillover into the next day, which will be managed
                # # in the charging module)
                # next_day_start_sessions: list[
                #     NextDayStartChargingSession
                # ] = []
                # if len(trip.end_locations_of_legs) > 0:
                #     end_location: str = trip.end_locations_of_legs[-1]
                # else:
                #     end_location = trip.location_names[0]

                # loc_connectivity: float = scenario.locations[
                #     end_location
                # ].connectivity
                # loc_power_to_vehicle: float = scenario.locations[
                #     end_location
                # ].charging_power
                # loc_power_from_network: float = (
                #     loc_power_to_vehicle
                #     / scenario.locations[end_location].charger_efficiency
                # )
                # loc_power_from_vehicle: float = scenario.locations[
                #     end_location
                # ].vehicle_discharge_power
                # loc_power_to_network: float = (
                #     loc_power_from_vehicle
                #     * scenario.locations[
                #         end_location
                #     ].proportion_of_discharge_to_network
                # )
                # if day_tag_index < len(time_tags_and_types) - 1:
                #     next_day_session_start, next_day_type = (
                #         time_tags_and_types[day_tag_index + 1]
                #     )
                #     next_day_all_start_sessions_amount: float = float(
                #         day_start_location_split.loc[end_location][
                #             next_day_type
                #         ]
                #     )

                #     for next_day_trip in trips:
                #         amount_for_that_trip: float = (
                #             next_day_all_start_sessions_amount
                #             * trip_probabilities_per_day_type.loc[
                #                 next_day_trip.name
                #             ][next_day_type]
                #         )
                #         if amount_for_that_trip > 0:

                #             if sum(next_day_trip.start_probabilities) == 0:
                #                 if (
                #                     next_day_trip.location_names[0]
                #                     == end_location
                #                 ):
                #                     next_day_session_end: datetime.datetime =
                #                       (
                #                         next_day_session_start
                #                         + datetime.timedelta(days=1)
                #                     )
                #                     group_size: float = amount_for_that_trip
                #                     next_leg_distance: float = 0
                #                     next_leg_consumption: float = (
                #                         vehicle_consumption
                #                         * next_leg_distance
                #                     )
                #                     next_day_start_sessions.append(
                #                         NextDayStartChargingSession(
                #                             end_location,
                #                             next_day_session_start,
                #                             next_day_session_end,
                #                             previous_leg_consumption,
                #                             next_leg_consumption,
                #                             group_size,
                #                             loc_connectivity,
                #                             loc_power_to_vehicle,
                #                             loc_power_from_network,
                #                             loc_power_from_vehicle,
                #                             loc_power_to_network,
                #                         )
                #                     )

                #             else:
                #                 if (
                #                     next_day_trip.start_locations_of_legs[0]
                #                     == end_location
                #                 ):
                #                     for (
                #                         departure_slot,
                #                         departure_probability,
                #                     ) in enumerate(
                #                         next_day_trip.start_probabilities
                #                     ):
                #                         if departure_probability > 0:
                #                             next_day_session_end = (
                #                                 next_day_session_start
                #                                 + datetime.timedelta(
                #                                     hours=departure_slot
                #                                 )
                #                             )
                #                             group_size = (
                #                                 amount_for_that_trip
                #                                 * departure_probability
                #                             )

                #                             next_leg_distance = (
                #                                 next_day_trip.leg_distances[0]
                #                             )
                #                             next_leg_consumption = (
                #                                 vehicle_consumption
                #                                 * next_leg_distance
                #                             )

                #                             next_day_start_sessions.append(
                #                                 NextDayStartChargingSession(
                #                                     end_location,
                #                                     next_day_session_start,
                #                                     next_day_session_end,
                #                                     previous_leg_consumption,
                #                                     next_leg_consumption,
                #                                     group_size,
                #                                     loc_connectivity,
                #                                     loc_power_to_vehicle,
                #                                     loc_power_from_network,
                #                                     loc_power_from_vehicle,
                #                                     loc_power_to_network,
                #                                 )
                #                             )

                # # We sort these extra session by putting the longer ones
                # # first (so that these get the spillover first)
                # next_day_start_sessions = sorted(
                #     next_day_start_sessions,
                #     key=lambda session: (
                #         session.end_time - session.start_time
                #     ).total_seconds(),
                #     reverse=True,
                # )
                # for next_day_start_session in next_day_start_sessions:
                #     charging_sessions.append(next_day_start_session)

    return charging_sessions


def get_run_mobility_matrix(
    trips: list[define.Trip],
    location_connections: pd.DataFrame,
    matrix_columns: list,
    run_trip_probabilities: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> pd.DataFrame:
    '''
    Takes the matrices for different trips and adds them up (weighed on
    probability) to get a matrix for the whole run.
    '''

    run_time_tags: pd.DatetimeIndex = run_time.get_time_range(
        scenario, general_parameters
    )[0]

    location_tuples: list[tuple[str, str]] = get_mobility_location_tuples(
        scenario
    )
    run_index_tuples: list[tuple[str, str, datetime.datetime]] = [
        (location_tuple[0], location_tuple[1], time_tag)
        for location_tuple in location_tuples
        for time_tag in run_time_tags
    ]

    mobility_index_names: list[str] = scenario.mobility_module[
        'mobility_index_names'
    ]
    run_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
        run_index_tuples, names=mobility_index_names
    )

    run_mobility_matrix: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_index), len(matrix_columns))),
        columns=matrix_columns,
        index=run_index,
    )
    run_mobility_matrix = run_mobility_matrix.sort_index()

    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'

    for trip in trips:
        unique_trip_legs: list[str] = list(set(trip.legs))

        if len(unique_trip_legs) > 0:

            trip_location_tuples: list[tuple[str, str]] = []

            for trip_leg in unique_trip_legs:
                leg_start: str = scenario.legs[trip_leg].locations.start
                leg_end: str = scenario.legs[trip_leg].locations.end
                leg_tuple: tuple[str, str] = (leg_start, leg_end)
                # We wante to only have unique tuples
                if leg_tuple not in trip_location_tuples:
                    trip_location_tuples.append(leg_tuple)

            this_trip_run_probabilities: pd.DataFrame = pd.DataFrame(
                run_trip_probabilities[trip.name]
            )

            location_connections_headers: list[str] = (
                scenario.mobility_module.location_connections_headers
            )

            # We need a version for each start/end location combination
            # that appears in our trip mobility matrix. This is also the
            # amount of (unique) legs or the trip location tuples
            this_trip_run_probabilities_extended: pd.DataFrame = pd.DataFrame()
            for _ in range(len(trip_location_tuples)):
                # -1 to get the right length
                this_trip_run_probabilities_extended = pd.concat(
                    (
                        this_trip_run_probabilities,
                        this_trip_run_probabilities_extended,
                    ),
                    ignore_index=True,
                )

            probability_values_to_use = this_trip_run_probabilities_extended[
                trip.name
            ].values

            for quantity in run_mobility_matrix.columns:

                if quantity not in location_connections_headers:
                    weighted_mobility_quantity_to_use = (
                        trip.run_mobility_matrix[quantity]
                        * probability_values_to_use
                    )

                    # We need to place it at the right places in the run

                    for trip_location_tuple in trip_location_tuples:

                        run_mobility_matrix.loc[
                            (trip_location_tuple),
                            quantity,
                        ] = (
                            pd.Series(
                                run_mobility_matrix.loc[
                                    trip_location_tuple, quantity
                                ]
                            ).values
                            + weighted_mobility_quantity_to_use.loc[
                                trip_location_tuple
                            ].values
                        )

        for location_tuple in location_tuples:
            these_locations_connections: pd.Series = pd.Series(
                location_connections.loc[location_tuple]
            )
            run_mobility_matrix.loc[
                (location_tuple), location_connections_headers  # type: ignore
            ] = these_locations_connections.values
        pickle_interim_files: bool = general_parameters.interim_files['pickle']
        if pickle_interim_files:
            run_mobility_matrix.to_pickle(
                f'{output_folder}/{scenario.name}_run_mobility_matrix.pkl'
            )
    return run_mobility_matrix


def get_possible_destinations_and_origins(
    scenario: Box,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    '''
    For each location, this gets the possible destinations
    '''
    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name
    location_parameters: Box = scenario.locations
    location_names: list[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name].vehicle == vehicle_name
    ]
    possible_destinations: dict[str, list[str]] = {}
    possible_origins: dict[str, list[str]] = {}
    for location_name in location_names:
        possible_destinations[location_name] = []
        possible_origins[location_name] = []
    mobility_location_tuples: list[tuple[str, str]] = (
        get_mobility_location_tuples(scenario)
    )
    for mobility_location_tuple in mobility_location_tuples:
        start_location: str = mobility_location_tuple[0]
        destination: str = mobility_location_tuple[1]
        if destination not in possible_destinations[start_location]:
            possible_destinations[start_location].append(destination)
        if start_location not in possible_origins[destination]:
            possible_origins[destination].append(start_location)

    return possible_destinations, possible_origins


def get_mobility_location_tuples(
    scenario: Box,
) -> list[tuple[str, str]]:
    '''
    This creates a list of tuples. These tuples are all the possible
    start and end locations of trips. This is done to avoid creating too
    large mobility matrices (with all possible combinations of locations).
    '''
    scenario_vehicle: str = scenario.vehicle.name
    mobility_location_tuples: list[tuple[str, str]] = []
    leg_parameters: Box = scenario.legs

    for leg_name in leg_parameters.keys():
        leg_vehicle: str = leg_parameters[leg_name].vehicle
        if leg_vehicle == scenario_vehicle:
            leg_tuple: tuple[str, str] = (
                leg_parameters[leg_name].locations.start,
                leg_parameters[leg_name].locations.end,
            )
            if leg_tuple not in mobility_location_tuples:
                mobility_location_tuples.append(leg_tuple)

    return mobility_location_tuples


def get_trip_probabilities_per_day_type(
    scenario: Box, case_name: str, general_parameters: Box
) -> pd.DataFrame:
    vehicle: str = scenario.vehicle.name
    if vehicle == 'car':
        trip_probabilities_per_day_type: pd.DataFrame = (
            get_car_trip_probabilities_per_day_type(
                scenario, case_name, general_parameters
            )
        )
    else:
        trip_probabilities_per_day_type = (
            get_trip_probabilities_per_day_type_other_vehicles(
                scenario, case_name
            )
        )

    return trip_probabilities_per_day_type


def get_trip_probabilities_per_day_type_other_vehicles(
    scenario: Box, case_name: str
) -> pd.DataFrame:
    '''
    This function computes the trip probabilities per day type for vehicles
    other than cars
    '''
    scenario_vehicle: str = scenario.vehicle.name
    mobility_module_parameters = scenario.mobility_module
    day_types: list[str] = mobility_module_parameters.day_types
    trip_list: list[str] = []
    for trip_to_add in list(scenario.trips.keys()):
        trip_vehicle = scenario.trips[trip_to_add].vehicle
        if trip_vehicle == scenario_vehicle:
            trip_list.append(trip_to_add)
    # We build a Dataframe to store the trip probabilities per day type

    trip_probabilities_per_day_type: pd.DataFrame = pd.DataFrame(
        0, columns=day_types, index=trip_list
    )
    trip_probabilities_per_day_type.index.name = 'Trip'

    trips_per_day_type: list[str] = (
        mobility_module_parameters.trips_per_day_type[scenario_vehicle]
    )

    for day_type, trip_name in zip(day_types, trips_per_day_type):
        trip_probabilities_per_day_type.loc[trip_name, day_type] = 1

    trip_probabilities_per_day_type = trip_probabilities_per_day_type.astype(
        float
    )
    return trip_probabilities_per_day_type


def get_car_trip_probabilities_per_day_type(
    scenario: Box, case_name: str, general_parameters: Box
) -> pd.DataFrame:
    '''
    This function computes the trip probabilities per day type for cars
    '''
    day_type_start_location_split: pd.DataFrame = (
        get_day_type_start_location_split(scenario, general_parameters)
    )
    scenario_vehicle: str = scenario.vehicle.name
    trip_list: list[str] = []
    for trip_to_add in list(scenario.trips.keys()):
        trip_vehicle = scenario.trips[trip_to_add].vehicle
        if trip_vehicle == scenario_vehicle:
            trip_list.append(trip_to_add)

    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'

    time_parameters: Box = general_parameters.time
    DAYS_IN_A_YEAR: float = time_parameters.DAYS_IN_A_YEAR
    DAYS_IN_A_WEEK: int = time_parameters.DAYS_IN_A_WEEK
    weeks_in_a_year: float = DAYS_IN_A_YEAR / DAYS_IN_A_WEEK
    weekend_day_numbers: list[int] = time_parameters.weekend_day_numbers
    number_weekdays: int = DAYS_IN_A_WEEK - len(weekend_day_numbers)

    mobility_module_parameters: Box = scenario.mobility_module
    worked_hours_per_year: float = (
        mobility_module_parameters.worked_hours_per_year
    )

    work_hours_in_a_work_day: float = (
        mobility_module_parameters.work_hours_in_a_work_day
    )

    day_types: list[str] = mobility_module_parameters.day_types
    percentage_working_on_a_work_week: float = (
        mobility_module_parameters.percentage_working_on_a_work_week
    )
    hours_worked_per_work_week: float = (
        mobility_module_parameters.hours_worked_per_work_week
    )

    hours_in_a_standard_work_week: float = (
        mobility_module_parameters.hours_in_a_standard_work_week
    )

    number_of_holiday_weeks: float = (
        mobility_module_parameters.number_of_holiday_weeks
    )

    holiday_trips_taken: float = mobility_module_parameters.holiday_trips_taken

    weekend_days_per_year: float = (
        DAYS_IN_A_YEAR * len(weekend_day_numbers) / DAYS_IN_A_WEEK
    )
    weekend_trips_per_year: float = (
        mobility_module_parameters.weekend_trips_per_year
    )

    leisure_trips_per_weekend: float = (
        mobility_module_parameters.leisure_trips_per_weekend
    )

    leisure_trips_per_week_outside_weekends: float = (
        mobility_module_parameters.leisure_trips_per_week_outside_weekends
    )

    maximal_fill_percentage_leisure_trips_on_non_work_weekdays: float = (
        mobility_module_parameters.maximal_fill_percentage_leisure_trips_on_non_work_weekdays
    )

    # Some useful quantities telling us how many of which day type there are
    # per year
    weekday_proportion: float = number_weekdays / DAYS_IN_A_WEEK
    workweek_proportion: float = number_of_holiday_weeks / weeks_in_a_year
    weekdays_in_work_weeks: float = (
        weekday_proportion * workweek_proportion * DAYS_IN_A_YEAR
    )
    weekdays_in_holiday_weeks: float = (
        weekday_proportion * (1 - workweek_proportion) * DAYS_IN_A_YEAR
    )

    holiday_departures_in_weekend_week_numbers: list[int] = (
        scenario.mobility_module.holiday_departures_in_weekend_week_numbers
    )
    number_of_holiday_departure_weekends: int = len(
        holiday_departures_in_weekend_week_numbers
    )
    holiday_returns_in_weekend_week_numbers: list[int] = (
        scenario.mobility_module.holiday_returns_in_weekend_week_numbers
    )
    number_of_holiday_return_weekends: int = len(
        holiday_returns_in_weekend_week_numbers
    )

    # We build a Dataframe to store the trip probabilities per day type
    trip_probabilities_per_day_type: pd.DataFrame = pd.DataFrame(
        columns=day_types, index=trip_list
    )
    trip_probabilities_per_day_type.index.name = 'Trip'
    trip_probabilities_per_day_type = trip_probabilities_per_day_type.astype(
        float
    )

    # We start with trips that are independent of others,
    # and holiday trips

    # We assume that holiday trips occur on certain weekends
    # (some for departures, some for returns))
    trip_probabilities_per_day_type.loc[
        'holiday_outward', 'weekday_in_work_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_outward', 'weekend_in_work_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_back', 'weekday_in_work_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_back', 'weekend_in_work_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_outward', 'weekday_in_holiday_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_outward', 'weekend_in_holiday_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_back', 'weekday_in_holiday_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_back', 'weekend_in_holiday_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_outward', 'weekend_holiday_returns'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_back', 'weekend_holiday_departures'
    ] = 0

    # The only non-zero values are for holidays outward in departure
    # weekends and for holidays back in return weekends,
    # and in overlap weekends.
    # These are simply given by the amount of holiday trips taken
    # divided by the amount of respective weekends and
    # by the length of a weekend
    holiday_departure_probability: float = holiday_trips_taken / (
        number_of_holiday_departure_weekends * len(weekend_day_numbers)
    )
    on_holiday_in_a_holiday_period: float = (
        holiday_departure_probability * len(weekend_day_numbers)
    )

    holiday_return_probability: float = holiday_trips_taken / (
        number_of_holiday_return_weekends * len(weekend_day_numbers)
    )
    trip_probabilities_per_day_type.loc[
        'holiday_outward', 'weekend_holiday_departures'
    ] = holiday_departure_probability
    trip_probabilities_per_day_type.loc[
        'holiday_back', 'weekend_holiday_returns'
    ] = holiday_return_probability
    trip_probabilities_per_day_type.loc[
        'holiday_outward', 'holiday_overlap_weekend'
    ] = holiday_departure_probability
    trip_probabilities_per_day_type.loc[
        'holiday_back', 'holiday_overlap_weekend'
    ] = holiday_return_probability

    # Weekend trips occur on the weekend and their probability is the amount
    # of such trips divided by the amount of weekend days (both per year)
    # but only in weekends where there are no holiday departures
    # or returns
    weekend_days_per_year_without_holiday_trips: (
        float
    ) = weekend_days_per_year - len(weekend_day_numbers) * (
        len(holiday_departures_in_weekend_week_numbers)
        + len(holiday_departures_in_weekend_week_numbers)
    )

    trip_probabilities_per_day_type.loc[
        'weekend_trip', 'weekday_in_work_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'weekend_trip', 'weekday_in_holiday_week'
    ] = 0

    # This is needed for MyPy to understand this is a float
    # and be able to use it in operations below

    trip_probabilities_per_day_type.loc[
        'weekend_trip', 'weekend_in_work_week'
    ] = (
        weekend_trips_per_year / weekend_days_per_year_without_holiday_trips
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekend_in_work_week'
        ]  # type: ignore
    )
    trip_probabilities_per_day_type.loc[
        'weekend_trip', 'weekend_in_holiday_week'
    ] = (
        weekend_trips_per_year / weekend_days_per_year_without_holiday_trips
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekend_in_holiday_week'
        ]  # type: ignore
    )
    trip_probabilities_per_day_type.loc[
        'weekend_trip', 'weekend_holiday_departures'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'weekend_trip', 'weekend_holiday_returns'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'weekend_trip', 'holiday_overlap_weekend'
    ] = 0
    # We compute the probability to go to work on a given day in a work week.
    # It is given by the probability that peple work in that week times
    # the number of hours worked in that week divided by
    # the length of a standard work week.
    probability_of_going_to_work_in_a_work_week: float = (
        percentage_working_on_a_work_week
        * hours_worked_per_work_week
        / hours_in_a_standard_work_week
    )
    if probability_of_going_to_work_in_a_work_week > 1:
        probability_of_going_to_work_in_a_work_week = 1
        # This  is there if some scenarios have more hours per week
        # than in a standard week.

    # To compute the probability to go to work in a holiday week,
    # we need a few steps.
    # We first look at how many weekdays there are in both week types

    worked_days_in_work_weeks: float = (
        probability_of_going_to_work_in_a_work_week * weekdays_in_work_weeks
    )
    # We also need the total amount of worked days per year.
    worked_days_per_year: float = (
        worked_hours_per_year / work_hours_in_a_work_day
    )
    # The number of worked days in holiday weeks
    # is the difference between the above two.
    worked_days_in_holiday_weeks: float = (
        worked_days_per_year - worked_days_in_work_weeks
    )

    # The probability to go to work on a holiday week day is
    # the ratio bewtween the number of worked days (on holiday weekdays)
    # and the total amount of holiday weekdays.
    # This only holds for those that actually are at home during those days
    probability_of_going_to_work_in_a_holiday_week: float = (
        worked_days_in_holiday_weeks / weekdays_in_holiday_weeks
    ) / float(
        day_type_start_location_split.loc['home'][
            'weekday_in_holiday_week'
        ]  # type: ignore
    )

    if probability_of_going_to_work_in_a_holiday_week > 1:
        print('The probability of going t work is larger than one.')
        print('Check your assumptions/inputs')
        print('(e.g. too many work hours and/or holiday trips or not enough )')
        print('holiday weeks)')
        exit()

    worked_days_in_a_work_week: float = (
        number_weekdays * probability_of_going_to_work_in_a_work_week
    )

    weekdays_with_no_work_trip_per_work_week: float = (
        number_weekdays - worked_days_in_a_work_week
    )

    worked_days_in_a_holiday_week: float = (
        number_weekdays * probability_of_going_to_work_in_a_holiday_week
    )

    weekdays_with_no_work_trip_per_holiday_week: float = (
        number_weekdays - worked_days_in_a_holiday_week
    )

    # For work weeks, it's the same as the amount of days
    # where there is no work trip.
    non_work_weekdays_per_work_week_where_a_leisure_trip_can_occur: float = (
        weekdays_with_no_work_trip_per_work_week
    )

    # For holiday weeks, we need to substract weekdays where there is a
    # holiday trip

    non_work_weekdays_per_holiday_week_where_a_leisure_trip_can_occur: (
        float
    ) = (
        weekdays_with_no_work_trip_per_holiday_week
        - number_weekdays
        * (
            float(
                trip_probabilities_per_day_type.loc['holiday_outward'][
                    'weekday_in_holiday_week'
                ]  # type: ignore
            )
            + float(
                trip_probabilities_per_day_type.loc['holiday_back'][
                    'weekday_in_holiday_week'
                ]  # type: ignore
            )
        )
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekday_in_holiday_week'
        ]  # type: ignore
    )

    # The vehicles also need to be home fot that to occur,
    # given that leisure only is between home and leisure

    # We now split the leisure trips across the weekdays.
    # We start with the days where there is no work trip.
    # This will determine the amount of weekday leisure trips taking place
    # on non-work weekdays.
    # The first step is to try and fit the weekday leisure trips into
    # the non-working workdays.
    # We do this separately for work weeks and holiday weeks, since they have
    # different amounts of weekdays without a work trip.
    # We determine this fill level by dividing
    # the amount of weekday leisure trips by the amount of non-work weekdays.
    # Additionally, we cap this with a parameter,
    # namely maximal_fill_percentage_leisure_trips_on_non_work_weekdays.
    # If this parameter is 1 (100%), then we try to fill the non-work weekdays
    # to the maximal possible value.
    # This parameter can also be lower if we want to shift more
    # leisure trips to working weekdays.
    # If the amount of non-work days is zero, then the fill level is zero.
    if non_work_weekdays_per_work_week_where_a_leisure_trip_can_occur == 0:
        # To avoid divisions by zero
        fill_level_non_work_weekdays_with_leisure_trips_in_a_work_week: (
            float
        ) = 0
    else:
        fill_level_non_work_weekdays_with_leisure_trips_in_a_work_week = (
            leisure_trips_per_week_outside_weekends
            / non_work_weekdays_per_work_week_where_a_leisure_trip_can_occur
        )

    if fill_level_non_work_weekdays_with_leisure_trips_in_a_work_week > (
        maximal_fill_percentage_leisure_trips_on_non_work_weekdays
    ):
        # This is where the cap mentioned above occurs
        fill_level_non_work_weekdays_with_leisure_trips_in_a_work_week = (
            maximal_fill_percentage_leisure_trips_on_non_work_weekdays
        )

    if non_work_weekdays_per_holiday_week_where_a_leisure_trip_can_occur == 0:
        # To avoid divisions by zero
        fill_level_non_work_weekdays_with_leisure_trips_in_a_holiday_week: (
            float
        ) = 0
    else:
        fill_level_non_work_weekdays_with_leisure_trips_in_a_holiday_week = (
            leisure_trips_per_week_outside_weekends
            / non_work_weekdays_per_holiday_week_where_a_leisure_trip_can_occur
        )

    if fill_level_non_work_weekdays_with_leisure_trips_in_a_holiday_week > (
        maximal_fill_percentage_leisure_trips_on_non_work_weekdays
    ):
        # This is where the cap mentioned above occurs
        fill_level_non_work_weekdays_with_leisure_trips_in_a_holiday_week = (
            maximal_fill_percentage_leisure_trips_on_non_work_weekdays
        )

    # Note that this fill level is also the probability that a leisure trip
    # takes place on a non-work day.
    # We do not use this directly because we assign probabilities to
    # all weekdays. If we were assigning probabilities to working weekdays
    # and non-working weekdays separately, then we would use this fill
    # percentage directly.

    # The amount of leisure trips on non-work weekdays is then given by
    # the fill level multplied by the amount of non-work weekdays.
    weekday_leisure_trips_on_non_work_days_in_a_work_week: float = (
        fill_level_non_work_weekdays_with_leisure_trips_in_a_work_week
        * non_work_weekdays_per_work_week_where_a_leisure_trip_can_occur
    )
    weekday_leisure_trips_on_non_work_days_in_a_holiday_week: float = (
        fill_level_non_work_weekdays_with_leisure_trips_in_a_holiday_week
        * non_work_weekdays_per_holiday_week_where_a_leisure_trip_can_occur
    )

    # This allows us to set the leisure only trips on weekdays

    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekday_in_work_week'
    ] = (
        weekday_leisure_trips_on_non_work_days_in_a_work_week / number_weekdays
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekday_in_work_week'
        ]  # type: ignore
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekday_in_holiday_week'
    ] = (
        weekday_leisure_trips_on_non_work_days_in_a_holiday_week
        / number_weekdays
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekday_in_holiday_week'
        ]  # type: ignore
    )
    # For weekends, we distribute the leisure trips across the weekemd

    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekend_in_work_week'
    ] = (leisure_trips_per_weekend / len(weekend_day_numbers)) * float(
        day_type_start_location_split.loc['home'][
            'weekend_in_work_week'
        ]  # type: ignore
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekend_in_holiday_week'
    ] = (leisure_trips_per_weekend / len(weekend_day_numbers)) * float(
        day_type_start_location_split.loc['home'][
            'weekend_in_holiday_week'
        ]  # type: ignore
    )
    # For holiday departure and return weekends, we assume
    # that only those who do not travel can have a leisure-only trip
    percentage_not_departing: float = 1 - float(
        trip_probabilities_per_day_type.loc['holiday_outward'][
            'weekend_holiday_departures'
        ]
        * len(weekend_day_numbers)  # type: ignore
        # We need to account for departures on all days
    )

    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekend_holiday_departures'
    ] = (
        percentage_not_departing
        * leisure_trips_per_weekend
        / len(weekend_day_numbers)
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekend_holiday_departures'
        ]  # type: ignore
    )
    percentage_not_returning: float = 1 - float(
        trip_probabilities_per_day_type.loc['holiday_back'][
            'weekend_holiday_returns'
        ]
        * len(weekend_day_numbers)  # type: ignore
        # We need to take into account returns on both days
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekend_holiday_returns'
    ] = (
        percentage_not_returning
        * leisure_trips_per_weekend
        / len(weekend_day_numbers)
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekend_holiday_returns'
        ]  # type: ignore
    )
    # For overlap weekends, we have:

    percentage_not_departing_or_returning: float = 1 - float(
        trip_probabilities_per_day_type.loc['holiday_outward'][
            'holiday_overlap_weekend'
        ]
        * len(weekend_day_numbers)
        + trip_probabilities_per_day_type.loc['holiday_back'][
            'holiday_overlap_weekend'
        ]
        * len(weekend_day_numbers)  # type: ignore
    )

    trip_probabilities_per_day_type.loc[
        'leisure_only', 'holiday_overlap_weekend'
    ] = (
        percentage_not_departing_or_returning
        * leisure_trips_per_weekend
        / len(weekend_day_numbers)
    ) * float(
        day_type_start_location_split.loc['home'][
            'holiday_overlap_weekend'
        ]  # type: ignore
    )

    # The amount of weekday leisure trips taking place on work weekdays is
    # then the difference between the total amount of weekday leisure trips and
    # the amount we just calculated.
    weekday_leisure_trips_on_work_days_in_a_work_week: float = (
        leisure_trips_per_week_outside_weekends
        - weekday_leisure_trips_on_non_work_days_in_a_work_week
    )
    weekday_leisure_trips_on_work_days_in_a_holiday_week: float = (
        leisure_trips_per_week_outside_weekends
        - weekday_leisure_trips_on_non_work_days_in_a_holiday_week
    )

    # We can also compute the probability to have a leisure trip on a
    # working weekday (we do not use the fill parameter).
    leisure_trip_probability_on_a_work_weekday_in_a_work_week: float = (
        weekday_leisure_trips_on_work_days_in_a_work_week
        / worked_days_in_a_work_week
    )

    leisure_trip_probability_on_a_work_weekday_in_a_holiday_week: float = (
        weekday_leisure_trips_on_work_days_in_a_holiday_week
        / worked_days_in_a_holiday_week
    )

    # We can then calculate the trip probabilities per trip type.
    # Going to work and to leisure is the product of the probability
    # of going to work times the leisure trip probability on a work
    # weekday, and the commute without leisure is the product of the
    # probability of going to work times the not to go on a leisure trip on
    # such a work day (so 1- minus the probability to do so).

    # This will be different for work weeks and holiday weeks.
    # We also assume that people don't work on weekends
    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure', 'weekday_in_work_week'
    ] = (
        probability_of_going_to_work_in_a_work_week
        * leisure_trip_probability_on_a_work_weekday_in_a_work_week
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekday_in_work_week'
        ]  # type: ignore
    )
    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekday_in_work_week'
    ] = (
        probability_of_going_to_work_in_a_work_week
        * (1 - leisure_trip_probability_on_a_work_weekday_in_a_work_week)
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekday_in_work_week'
        ]  # type: ignore
    )

    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekend_in_work_week'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure', 'weekend_in_work_week'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekend_holiday_departures'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure', 'weekend_holiday_departures'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'holiday_overlap_weekend'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure', 'holiday_overlap_weekend'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekend_holiday_returns'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure', 'weekend_holiday_returns'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure', 'weekday_in_holiday_week'
    ] = (
        probability_of_going_to_work_in_a_holiday_week
        * leisure_trip_probability_on_a_work_weekday_in_a_holiday_week
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekday_in_holiday_week'
        ]  # type: ignore
    )
    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekday_in_holiday_week'
    ] = (
        probability_of_going_to_work_in_a_holiday_week
        * (1 - leisure_trip_probability_on_a_work_weekday_in_a_holiday_week)
    ) * float(
        day_type_start_location_split.loc['home'][
            'weekday_in_holiday_week'
        ]  # type: ignore
    )

    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekend_in_holiday_week'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure', 'weekend_in_holiday_week'
    ] = 0

    # Now that we computed all travelling trips, we look at the stay_put
    # trips as remainders

    # We do the holidays first:
    # There are none in work weeks
    trip_probabilities_per_day_type.loc[
        'stay_put_holiday', 'weekday_in_work_week'
    ] = 0
    trip_probabilities_per_day_type.loc[
        'stay_put_holiday', 'weekend_in_work_week'
    ] = 0
    # For days without holiday departures and arrivals, we
    # have the amount of people on holidays during that period
    trip_probabilities_per_day_type.loc[
        'stay_put_holiday', 'weekday_in_holiday_week'
    ] = on_holiday_in_a_holiday_period
    trip_probabilities_per_day_type.loc[
        'stay_put_holiday', 'weekend_in_holiday_week'
    ] = on_holiday_in_a_holiday_period
    # For (one-way) departures and arrivals weekends, we have no stay puts
    # on either the first day (for departures on the last day), etc.
    # If the arrivalsare over N days, then we have 0 stays on the first day,
    # 1 unit (of departure probability) on the second day, two units on the
    # third day, etc. This sum is equal to (N-1) * N  / 2. To have
    # the avrage occupancy, we divide this by N, so we have (N-1)/2

    average_occupancy: float = (len(weekend_day_numbers) - 1) / 2
    trip_probabilities_per_day_type.loc[
        'stay_put_holiday', 'weekend_holiday_departures'
    ] = (holiday_departure_probability * average_occupancy)
    trip_probabilities_per_day_type.loc[
        'stay_put_holiday', 'weekend_holiday_returns'
    ] = (holiday_departure_probability * average_occupancy)

    # For the overlap weekends, we hve both (not yet returned on the first day
    # and already arrived on the second day of the weekend)
    trip_probabilities_per_day_type.loc[
        'stay_put_holiday', 'holiday_overlap_weekend'
    ] = (holiday_departure_probability * average_occupancy * 2)

    # Finally, the remainder goes to staying put at home:
    travelling_trip_probabilities_per_day_type: pd.DataFrame = (
        trip_probabilities_per_day_type.drop('stay_put_home', axis=0)
    )
    # We drop the stayp put trips to have the sum of actual trips
    # We will put the stay put trips back later
    stay_put_probabilities: pd.Series = (
        1 - travelling_trip_probabilities_per_day_type.sum()
    )
    trip_probabilities_per_day_type.loc['stay_put_home'] = (
        stay_put_probabilities
    )

    table_name: str = f'{scenario.name}_trip_probabilities_per_day_type'

    # For some file formats (stata, for example), we need to ensure that
    # the values are floats (or something else, but object does seem to be a
    # problem, as the original DataFrame had nan elements).
    trip_probabilities_per_day_type = trip_probabilities_per_day_type.astype(
        'float'
    )
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    if pickle_interim_files:
        trip_probabilities_per_day_type.to_pickle(
            f'{output_folder}/{table_name}.pkl'
        )

    return trip_probabilities_per_day_type


def car_holiday_departures_returns_corrections(
    run_trip_probabilities: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> pd.DataFrame:
    '''
    # For holiday departures and returns weekends, we need to do some
    # shifting, as the probabilities are averages for the
    # whole weekend. Example: if stay put holiday is 4% on average,
    # it should be 0% on Saturdays (where the first batch travels)
    # and 8% on Sundays (where that batch has arrived and stays at the
    # holiday destination), which needs to be balanced with stay_put_home
    # This is only necessary for the one-way shifts. The ones with
    # both departures and returns are already fine
    '''
    run_range = run_time.get_time_range(scenario, general_parameters)[0]
    departures_filter: pd.Series[bool] = (
        run_trip_probabilities['Day Type'] == 'weekend_holiday_departures'
    )

    returns_filter: pd.Series[bool] = (
        run_trip_probabilities['Day Type'] == 'weekend_holiday_returns'
    )

    saturday_filter: pd.Series[bool] = run_range.isocalendar().day == 6
    sunday_filter: pd.Series[bool] = run_range.isocalendar().day == 7
    day_start_hour: int = scenario.mobility_module.day_start_hour
    HOURS_IN_A_DAY: int = general_parameters.time.HOURS_IN_A_DAY
    day_start_hour_filter: pd.Series[bool] = (
        run_range.hour == day_start_hour
    )  # type: ignore

    departure_saturdays_starts: list[datetime.datetime] = run_range[
        departures_filter & saturday_filter & day_start_hour_filter
    ]  # type: ignore

    departure_saturdays: list[pd.DatetimeIndex] = [
        pd.date_range(
            start=departure_saturdays_start, periods=HOURS_IN_A_DAY, freq='h'
        )
        for departure_saturdays_start in departure_saturdays_starts
    ]

    departure_sundays_starts: list[datetime.datetime] = run_range[
        departures_filter & sunday_filter & day_start_hour_filter
    ]  # type: ignore

    departure_sundays: list[pd.DatetimeIndex] = [
        pd.date_range(
            start=departure_sundays_start, periods=HOURS_IN_A_DAY, freq='h'
        )
        for departure_sundays_start in departure_sundays_starts
    ]

    departure_shift_values: list[float] = [
        float(
            run_trip_probabilities.loc[departure_saturdays_start][
                'stay_put_holiday'
            ]  # type: ignore
        )
        for departure_saturdays_start in departure_saturdays_starts
    ]

    for departure_saturday, departure_shift_value in zip(
        departure_saturdays, departure_shift_values
    ):

        run_trip_probabilities.loc[departure_saturday, 'stay_put_home'] = (
            run_trip_probabilities.loc[departure_saturday][
                'stay_put_home'
            ].values[
                0
            ]  # The values are the same across an acitivty day
            + departure_shift_value
        )
        run_trip_probabilities.loc[departure_saturday, 'stay_put_holiday'] = (
            run_trip_probabilities.loc[departure_saturday][
                'stay_put_holiday'
            ].values[
                0
            ]  # The values are the same across an acitivty day
            - departure_shift_value
        )
    for departure_sunday, departure_shift_value in zip(
        departure_sundays, departure_shift_values
    ):

        run_trip_probabilities.loc[departure_sunday, 'stay_put_home'] = (
            run_trip_probabilities.loc[departure_sunday][
                'stay_put_home'
            ].values[
                0
            ]  # The values are the same across an acitivty day
            - departure_shift_value
        )
        run_trip_probabilities.loc[departure_sunday, 'stay_put_holiday'] = (
            run_trip_probabilities.loc[departure_sunday][
                'stay_put_holiday'
            ].values[
                0
            ]  # The values are the same across an acitivty day
            + departure_shift_value
        )

    return_saturdays_starts: list[datetime.datetime] = run_range[
        returns_filter & saturday_filter & day_start_hour_filter
    ]  # type: ignore

    return_saturdays: list[pd.DatetimeIndex] = [
        pd.date_range(
            start=return_saturdays_start, periods=HOURS_IN_A_DAY, freq='h'
        )
        for return_saturdays_start in return_saturdays_starts
    ]

    return_sundays_starts: list[datetime.datetime] = run_range[
        returns_filter & sunday_filter & day_start_hour_filter
    ]  # type: ignore

    return_sundays: list[pd.DatetimeIndex] = [
        pd.date_range(
            start=return_sundays_start, periods=HOURS_IN_A_DAY, freq='h'
        )
        for return_sundays_start in return_sundays_starts
    ]

    return_shift_values: list[float] = [
        float(
            run_trip_probabilities.loc[return_saturdays_start][
                'stay_put_holiday'
            ]  # type: ignore
        )
        for return_saturdays_start in return_saturdays_starts
    ]

    for return_saturday, return_shift_value in zip(
        return_saturdays, return_shift_values
    ):

        run_trip_probabilities.loc[return_saturday, 'stay_put_home'] = (
            run_trip_probabilities.loc[return_saturday][
                'stay_put_home'
            ].values[
                0
            ]  # The values are the same across an acitivty day
            - return_shift_value
        )
        run_trip_probabilities.loc[return_saturday, 'stay_put_holiday'] = (
            run_trip_probabilities.loc[return_saturday][
                'stay_put_holiday'
            ].values[
                0
            ]  # The values are the same across an acitivty day
            + return_shift_value
        )
    for return_sunday, return_shift_value in zip(
        return_sundays, return_shift_values
    ):

        run_trip_probabilities.loc[return_sunday, 'stay_put_home'] = (
            run_trip_probabilities.loc[return_sunday]['stay_put_home'].values[
                0
            ]  # The values are the same across an acitivty day
            + return_shift_value
        )
        run_trip_probabilities.loc[return_sunday, 'stay_put_holiday'] = (
            run_trip_probabilities.loc[return_sunday][
                'stay_put_holiday'
            ].values[
                0
            ]  # The values are the same across an acitivty day
            - return_shift_value
        )
    return run_trip_probabilities


def get_run_trip_probabilities(
    trips: list[define.Trip],
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> pd.DataFrame:
    '''
    Gets a DataFrame containing the trip probabilities for the whole run.
    '''

    # moo = datetime.datetime.now()
    day_types: list[str] = scenario.mobility_module.day_types
    scenario_vehicle: str = scenario.vehicle.name
    trip_list: list[str] = []
    for trip_to_add in list(scenario.trips.keys()):
        trip_vehicle = scenario.trips[trip_to_add].vehicle
        if trip_vehicle == scenario_vehicle:
            trip_list.append(trip_to_add)

    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'

    run_range: pd.DatetimeIndex = run_time.get_time_range(
        scenario, general_parameters
    )[0]

    # print((datetime.datetime.now() - moo).total_seconds())
    # moo = datetime.datetime.now()
    run_trip_probabilities: pd.DataFrame = pd.DataFrame(index=run_range)
    run_trip_probabilities.index.name = 'Time Tag'

    run_trip_probabilities = run_time.add_day_type_to_time_stamped_dataframe(
        run_trip_probabilities, scenario, general_parameters
    )

    # print((datetime.datetime.now() - moo).total_seconds())
    # moo = datetime.datetime.now()
    trip_probabilities_per_day_type: pd.DataFrame = (
        get_trip_probabilities_per_day_type(
            scenario, case_name, general_parameters
        )
    )

    # print((datetime.datetime.now() - moo).total_seconds())
    # moo = datetime.datetime.now()

    for trip in trip_list:
        for day_type in day_types:
            run_trip_probabilities.loc[
                run_trip_probabilities['Day Type'] == day_type, trip
            ] = trip_probabilities_per_day_type.loc[trip, day_type]
    # print((datetime.datetime.now() - moo).total_seconds())
    # moo = datetime.datetime.now()

    table_name: str = f'{scenario.name}_run_trip_probabilities'
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    if pickle_interim_files:
        run_trip_probabilities.to_pickle(f'{output_folder}/{table_name}.pkl')
    # print((datetime.datetime.now() - moo).total_seconds())
    # moo = datetime.datetime.now()

    vehicle_name: str = scenario.vehicle.name
    if vehicle_name == 'car':
        run_trip_probabilities = car_holiday_departures_returns_corrections(
            run_trip_probabilities, scenario, case_name, general_parameters
        )
    # print('Weekend corrs', (datetime.datetime.now() - moo).total_seconds())

    return run_trip_probabilities


def get_day_type_start_location_split(
    scenario: Box, general_parameters: Box
) -> pd.DataFrame:
    '''
    Tells us the proportion of vehicles
    that start their day at a given location (per day type)
    '''
    mobility_module_parameters: Box = scenario.mobility_module
    holiday_trips_taken: float = mobility_module_parameters.holiday_trips_taken

    holiday_departures_in_weekend_week_numbers: list[int] = (
        mobility_module_parameters.holiday_departures_in_weekend_week_numbers
    )
    number_of_holiday_departure_weekends: int = len(
        holiday_departures_in_weekend_week_numbers
    )
    day_types: list[str] = mobility_module_parameters.day_types
    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name
    location_parameters: Box = scenario.locations
    location_names: list[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name].vehicle == vehicle_name
    ]

    day_type_start_location_split: pd.DataFrame = pd.DataFrame(
        np.zeros((len(location_names), len(day_types))),
        columns=day_types,
        index=location_names,
    )
    day_type_start_location_split.index.name = 'Location'

    if vehicle_name == 'car':

        # Outside holidays, the vehicles start at home
        day_types_outside_holidays: list[str] = [
            'weekday_in_work_week',
            'weekend_in_work_week',
        ]
        for day_type in day_types_outside_holidays:
            day_type_start_location_split.loc['home', day_type] = 1

        # Outside of departure and returns, the proportion of vehicles
        # at the holiday destination is the amount of holiday trips taken
        # divided by the opportunities to go on holidays
        percentage_on_holiday_in_holiday_week: float = (
            holiday_trips_taken / number_of_holiday_departure_weekends
        )

        non_travelling_holiday_day_types: list[str] = [
            'weekday_in_holiday_week',
            'weekend_in_holiday_week',
        ]
        for day_type in non_travelling_holiday_day_types:
            day_type_start_location_split.loc['home', day_type] = (
                1 - percentage_on_holiday_in_holiday_week
            )
            day_type_start_location_split.loc['holiday', day_type] = (
                percentage_on_holiday_in_holiday_week
            )

        # For departure and return weekends, this is split across
        # the weekend days (note that this is an approximation, as
        # we ideally should split the weekend in two, but that would make
        # the model complexer)
        weekend_day_numbers: list[int] = general_parameters.time[
            'weekend_day_numbers'
        ]
        travelling_weekend_day_types: list[str] = [
            'weekend_holiday_departures',
            'weekend_holiday_returns',
            'holiday_overlap_weekend',
        ]
        for day_type in travelling_weekend_day_types:
            day_type_start_location_split.loc['home', day_type] = 1 - (
                percentage_on_holiday_in_holiday_week
                / len(weekend_day_numbers)
            )
            day_type_start_location_split.loc['holiday', day_type] = (
                percentage_on_holiday_in_holiday_week
                / len(weekend_day_numbers)
            )
    else:
        vehicle_base_location = vehicle_parameters.base_location
        day_type_start_location_split.loc[vehicle_base_location] = 1

    return day_type_start_location_split


def get_location_split(
    trips: list[define.Trip],
    run_trip_probabilities: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    '''
    Produces the location split of the vehicles for the whole run
    '''
    loop_timer: list[datetime.datetime] = [datetime.datetime.now()]

    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'

    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name

    location_names: list[str] = [
        location_name
        for location_name in scenario.locations.keys()
        if scenario.locations[location_name].vehicle == vehicle_name
    ]
    run_range: pd.Index | pd.DatetimeIndex = run_trip_probabilities.index

    location_split: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )
    connectivity_per_location: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )

    maximal_delivered_power_per_location: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )
    maximal_received_power_per_location: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )
    vehicle_discharge_power_per_location: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )
    discharge_power_to_network_per_location: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )

    percentage_driving: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), 1)),
        columns=['Driving percent'],
        index=run_range,
    )
    connectivity: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), 1)),
        columns=['Connectivity'],
        index=run_range,
    )

    maximal_delivered_power: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), 1)),
        columns=['Maximal Delivered Power (kW)'],
        index=run_range,
    )
    maximal_received_power: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), 1)),
        columns=['Maximal Received Power (kW)'],
        index=run_range,
    )

    vehicle_discharge_power: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), 1)),
        columns=['Vehicle Discharge Power (kW)'],
        index=run_range,
    )
    discharge_power_to_network: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), 1)),
        columns=['Discharge Power to Network (kW)'],
        index=run_range,
    )

    for trip in trips:

        percentage_driving['Driving percent'] = (
            percentage_driving['Driving percent'].values
            + trip.run_percentage_driving.values
            * run_trip_probabilities[trip.name].values  # type: ignore
        )
        connectivity['Connectivity'] = (
            connectivity['Connectivity'].values
            + trip.run_connectivity.values
            * run_trip_probabilities[trip.name].values  # type: ignore
        )
        maximal_delivered_power['Maximal Delivered Power (kW)'] = (
            maximal_delivered_power['Maximal Delivered Power (kW)'].values
            + trip.run_maximal_delivered_power.values
            * run_trip_probabilities[trip.name].values  # type: ignore
        )

        maximal_received_power['Maximal Received Power (kW)'] = (
            maximal_received_power['Maximal Received Power (kW)'].values
            + trip.run_maximal_received_power.values
            * run_trip_probabilities[trip.name].values  # type: ignore
        )
        vehicle_discharge_power['Vehicle Discharge Power (kW)'] = (
            vehicle_discharge_power['Vehicle Discharge Power (kW)'].values
            + trip.run_vehicle_discharge_power.values
            * run_trip_probabilities[trip.name].values  # type: ignore
        )
        discharge_power_to_network['Discharge Power to Network (kW)'] = (
            discharge_power_to_network[
                'Discharge Power to Network (kW)'
            ].values
            + trip.run_discharge_power_to_network.values
            * run_trip_probabilities[trip.name].values  # type: ignore
        )

        for location_name in trip.run_location_split.columns:
            location_split[location_name] = location_split[
                location_name
            ].values + (
                trip.run_location_split[location_name].values
                * run_trip_probabilities[trip.name].values
            )  # type: ignore

            connectivity_per_location[
                location_name
            ] = connectivity_per_location[location_name].values + (
                trip.run_connectivity_per_location[location_name].values
                * run_trip_probabilities[trip.name].values
            )  # type: ignore

            maximal_delivered_power_per_location[
                location_name
            ] = maximal_delivered_power_per_location[location_name].values + (
                trip.run_maximal_delivered_power_per_location[
                    location_name
                ].values
                * run_trip_probabilities[trip.name].values
            )  # type: ignore
            maximal_received_power_per_location[
                location_name
            ] = maximal_received_power_per_location[location_name].values + (
                trip.run_maximal_received_power_per_location[
                    location_name
                ].values
                * run_trip_probabilities[trip.name].values
            )  # type: ignore
            vehicle_discharge_power_per_location[
                location_name
            ] = vehicle_discharge_power_per_location[location_name].values + (
                trip.run_vehicle_discharge_power_per_location[
                    location_name
                ].values
                * run_trip_probabilities[trip.name].values
            )  # type: ignore
            discharge_power_to_network_per_location[
                location_name
            ] = discharge_power_to_network_per_location[
                location_name
            ].values + (
                trip.run_discharge_power_to_network_per_location[
                    location_name
                ].values
                * run_trip_probabilities[trip.name].values
            )  # type: ignore

    loop_timer.append(datetime.datetime.now())
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    if pickle_interim_files:
        location_split.to_pickle(
            f'{output_folder}/{scenario.name}_location_split.pkl'
        )
        percentage_driving.to_pickle(
            f'{output_folder}/{scenario.name}_percentage_driving.pkl'
        )
        connectivity_per_location.to_pickle(
            f'{output_folder}/{scenario.name}_connectivity_per_location.pkl'
        )
        connectivity.to_pickle(
            f'{output_folder}/{scenario.name}_connectivity.pkl'
        )
        maximal_delivered_power_per_location.to_pickle(
            f'{output_folder}/{scenario.name}'
            f'_maximal_delivered_power_per_location.pkl'
        )
        maximal_delivered_power.to_pickle(
            f'{output_folder}/{scenario.name}_maximal_delivered_power.pkl'
        )
        maximal_received_power_per_location.to_pickle(
            f'{output_folder}/{scenario.name}'
            f'_maximal_received_power_per_location.pkl'
        )
        maximal_received_power.to_pickle(
            f'{output_folder}/{scenario.name}_maximal_received_power.pkl'
        )
        vehicle_discharge_power_per_location.to_pickle(
            f'{output_folder}/{scenario.name}'
            f'_vehicle_discharge_power_per_location.pkl'
        )
        vehicle_discharge_power.to_pickle(
            f'{output_folder}/{scenario.name}_vehicle_discharge_power.pkl'
        )
        discharge_power_to_network_per_location.to_pickle(
            f'{output_folder}/{scenario.name}'
            f'_discharge_power_to_network_per_location.pkl'
        )
        discharge_power_to_network.to_pickle(
            f'{output_folder}/{scenario.name}_discharge_power_to_network.pkl'
        )
    return (
        location_split,
        maximal_delivered_power_per_location,
        maximal_delivered_power,
        connectivity_per_location,
        maximal_received_power_per_location,
        vehicle_discharge_power_per_location,
        discharge_power_to_network_per_location,
    )


def get_starting_location_split(
    location_split: pd.DataFrame,
    scenario: Box,
    general_parameters: Box,
) -> pd.DataFrame:
    '''
    Gets the location split at run start
    '''
    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name
    location_parameters: Box = scenario.locations
    location_names: list[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name].vehicle == vehicle_name
    ]
    mobility_module_parameters: Box = scenario.mobility_module
    compute_start_location_split: bool = (
        mobility_module_parameters.compute_start_location_split
    )

    if compute_start_location_split:
        run_range: list[datetime.datetime] = run_time.get_time_range(
            scenario, general_parameters
        )[
            0
        ]  # type: ignore
        run_start_time_tag: datetime.datetime = run_range[0]
        run_start_day_type: str = run_time.get_day_type(
            run_start_time_tag, scenario, general_parameters
        )
        day_type_start_location_split: pd.DataFrame = (
            get_day_type_start_location_split(scenario, general_parameters)
        )

        for location_name in location_names:

            location_split.loc[run_range, location_name] = (
                day_type_start_location_split[run_start_day_type][
                    location_name
                ]
            )

    else:
        for location_name in location_names:
            location_split.loc[run_range, location_name] = (  # type: ignore
                location_parameters[
                    location_name
                ].percentage_in_location_at_run_start
            )

    return location_split


def get_kilometers_for_next_leg(
    trips: list[define.Trip],
    run_trip_probabilities: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'
    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name

    location_parameters: Box = scenario.locations
    location_names: list[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name].vehicle == vehicle_name
    ]
    run_next_leg_kilometers: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_trip_probabilities.index), len(location_names))),
        columns=location_names,
        index=run_trip_probabilities.index,
    )
    run_next_leg_kilometers_cumulative: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_trip_probabilities.index), len(location_names))),
        columns=location_names,
        index=run_trip_probabilities.index,
    )
    run_next_leg_charge_to_vehicle: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_trip_probabilities.index), len(location_names))),
        columns=location_names,
        index=run_trip_probabilities.index,
    )
    run_next_leg_charge_from_network: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_trip_probabilities.index), len(location_names))),
        columns=location_names,
        index=run_trip_probabilities.index,
    )
    run_next_leg_charge_to_vehicle_cumulative: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_trip_probabilities.index), len(location_names))),
        columns=location_names,
        index=run_trip_probabilities.index,
    )
    run_next_leg_charge_from_network_cumulative: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_trip_probabilities.index), len(location_names))),
        columns=location_names,
        index=run_trip_probabilities.index,
    )

    for trip in trips:

        this_trip_probabilities: pd.Series[float] = pd.Series(
            run_trip_probabilities[trip.name]
        )
        for location_name in trip.run_next_leg_kilometers.columns:

            run_next_leg_kilometers[
                location_name
            ] += trip.run_next_leg_kilometers[location_name].mul(
                this_trip_probabilities, axis=0
            )
            run_next_leg_kilometers_cumulative[
                location_name
            ] += trip.run_next_leg_kilometers_cumulative[location_name].mul(
                this_trip_probabilities, axis=0
            )
            run_next_leg_charge_to_vehicle[
                location_name
            ] += trip.run_next_leg_charge_to_vehicle[location_name].mul(
                this_trip_probabilities, axis=0
            )

            run_next_leg_charge_from_network[
                location_name
            ] += trip.run_next_leg_charge_from_network[location_name].mul(
                this_trip_probabilities, axis=0
            )
            run_next_leg_charge_to_vehicle_cumulative[
                location_name
            ] += trip.run_next_leg_charge_to_vehicle_cumulative[
                location_name
            ].mul(
                this_trip_probabilities, axis=0
            )
            run_next_leg_charge_from_network_cumulative[
                location_name
            ] += trip.run_next_leg_charge_from_network_cumulative[
                location_name
            ].mul(
                this_trip_probabilities, axis=0
            )
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    if pickle_interim_files:
        run_next_leg_kilometers.to_pickle(
            f'{output_folder}/{scenario.name}_next_leg_kilometers.pkl'
        )
        run_next_leg_kilometers_cumulative.to_pickle(
            f'{output_folder}/{scenario.name}'
            '_next_leg_kilometers_cumulative.pkl'
        )
        run_next_leg_charge_to_vehicle.to_pickle(
            f'{output_folder}/{scenario.name}_next_leg_charge_to_vehicle.pkl'
        )
        run_next_leg_charge_from_network.to_pickle(
            f'{output_folder}/{scenario.name}_next_leg_charge_from_network.pkl'
        )
        run_next_leg_charge_to_vehicle_cumulative.to_pickle(
            f'{output_folder}/{scenario.name}'
            f'_next_leg_charge_to_vehicle_cumulative.pkl'
        )
        run_next_leg_charge_from_network_cumulative.to_pickle(
            f'{output_folder}/{scenario.name}'
            f'_next_leg_charge_from_network_cumulative.pkl'
        )
    return (
        run_next_leg_kilometers,
        run_next_leg_kilometers_cumulative,
        run_next_leg_charge_from_network,
        run_next_leg_charge_to_vehicle,
    )


# @cook.function_timer
def make_mobility_data(
    location_connections: pd.DataFrame,
    legs: define.Leg,
    locations: define.Location,
    trips: define.Trip,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    list[ChargingSession],
    pd.DataFrame,
]:

    run_trip_probabilities: pd.DataFrame = get_run_trip_probabilities(
        trips, scenario, case_name, general_parameters  # type: ignore
    )
    trip_probabilities_per_day_type: pd.DataFrame = (
        get_trip_probabilities_per_day_type(
            scenario, case_name, general_parameters
        )
    )

    mobility_quantities: list = scenario.mobility_module['mobility_quantities']

    run_mobility_matrix: pd.DataFrame = get_run_mobility_matrix(
        trips,  # type: ignore
        location_connections,
        mobility_quantities,
        run_trip_probabilities,
        scenario,
        case_name,
        general_parameters,
    )

    leg_weighted_consumptions: list[float] = []
    for leg in scenario.legs:
        if scenario.legs[leg].vehicle == scenario.vehicle.name:
            leg_distance: float = scenario.legs[leg].distance
            road_type_mix: np.ndarray = np.array(
                scenario.legs[leg].road_type_mix.mix
            )
            road_type_weights: np.ndarray = np.array(
                scenario.transport_factors.weights
            )
            road_type_factor: float = float(
                sum(road_type_mix * road_type_weights)
            )
            weighted_distance: float = road_type_factor * leg_distance
            weighted_consumption: float = (
                weighted_distance
                * scenario.vehicle.base_consumption_per_km['electricity_kWh']
            )
            leg_weighted_consumptions.append(weighted_consumption)
    leg_weighted_consumptions = sorted(list(set(leg_weighted_consumptions)))

    (
        location_split,
        maximal_delivered_power_per_location,
        maximal_delivered_power,
        connectivity_per_location,
        maximal_received_power_per_location,
        vehicle_discharge_power_per_location,
        discharge_power_to_network_per_location,
    ) = get_location_split(
        trips,  # type: ignore
        run_trip_probabilities,
        scenario,
        case_name,
        general_parameters,  # type: ignore
    )
    (
        run_next_leg_kilometers,
        run_next_leg_kilometers_cumulative,
        run_next_leg_charge_from_network,
        run_next_leg_charge_to_vehicle,
    ) = get_kilometers_for_next_leg(
        trips,  # type: ignore
        run_trip_probabilities,
        scenario,
        case_name,
        general_parameters,
    )
    run_charging_sessions: list[ChargingSession] = get_run_charging_sessions(
        trips,  # type: ignore
        trip_probabilities_per_day_type,
        scenario,
        general_parameters,
    )
    pickle_interim_files: bool = general_parameters.interim_files.pickle

    charging_sessions_headers: list[str] = (
        general_parameters.sessions_dataframe.run_dataframe_headers
    )

    run_charging_sessions_dataframe: pd.DataFrame = (
        define.get_charging_sessions_dataframe(
            run_charging_sessions,
            general_parameters,
            charging_sessions_headers,
        )
    )
    if pickle_interim_files:
        output_root: str = general_parameters.files.output_root
        output_folder: str = f'{output_root}/{case_name}'

        run_charging_sessions_dataframe.to_pickle(
            f'{output_folder}/{scenario.name}_'
            f'run_charging_sessions'
            f'.pkl'
        )

    return (
        run_mobility_matrix,
        location_split,
        maximal_delivered_power_per_location,
        maximal_delivered_power,
        connectivity_per_location,
        maximal_received_power_per_location,
        vehicle_discharge_power_per_location,
        discharge_power_to_network_per_location,
        run_next_leg_kilometers,
        run_next_leg_kilometers_cumulative,
        run_next_leg_charge_from_network,
        run_next_leg_charge_to_vehicle,
        run_charging_sessions,
        run_charging_sessions_dataframe,
    )


if __name__ == '__main__':
    start_time: datetime.datetime = datetime.datetime.now()
    case_name = 'bus_test'
    scenario_name: str = 'XX_bus'
    scenario_file_name: str = f'scenarios/{case_name}/{scenario_name}.toml'
    scenario: Box = cook.parameters_from_TOML(scenario_file_name)
    scenario.name = scenario_name
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: Box = cook.parameters_from_TOML(
        general_parameters_file_name
    )

    location_connections, legs, locations, trips = (
        define.declare_all_instances(scenario, case_name, general_parameters)
    )

    (
        run_mobility_matrix,
        location_split,
        maximal_delivered_power_per_location,
        maximal_delivered_power,
        connectivity_per_location,
        maximal_received_power_per_location,
        vehicle_discharge_power_per_location,
        discharge_power_to_network_per_location,
        run_next_leg_kilometers,
        run_next_leg_kilometers_cumulative,
        run_next_leg_charge_from_network,
        run_next_leg_charge_to_vehicle,
        run_charging_sessions,
        run_charging_sessions_dataframe,
    ) = make_mobility_data(
        location_connections,
        legs,
        locations,
        trips,
        scenario,
        case_name,
        general_parameters,
    )
    print(run_mobility_matrix)
    print(location_split)
    print(run_charging_sessions_dataframe)
    print((datetime.datetime.now() - start_time).total_seconds())
