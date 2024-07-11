'''
This module computes the various functions related to mobility.
It contains the following functions:
1. **get_trip_probabilities_per_day_type:** This function computes the trip
probabilities per day type.
2. **get_run_trip_probabilities:** Gets a DataFrame containing the trip
probabilities for the whole run.
3. **get_mobility_matrix:**Makes a mobility matrix for the run
that tracks departures
from and to locations (tracks amount, kilometers, and weighted kilometers)
4. **get_day_type_start_location:** Tells us the proportion of vehicles
that start their day at a given location (per day type)
5. **get_location_split:** Produces the location split of the vehicles
for the whole run
6. **get_starting_location_split:** Gets the location split at run start
'''

import datetime
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


def get_trip_probabilities_per_day_type(
    scenario: ty.Dict, case_name: str
) -> pd.DataFrame:
    vehicle: str = scenario['vehicle']['name']
    if vehicle == 'car':
        trip_probabilities_per_day_type: pd.DataFrame = (
            get_car_trip_probabilities_per_day_type(scenario, case_name)
        )
    else:
        print(f'{vehicle} does not have a model')
        exit()

    return trip_probabilities_per_day_type


def get_car_trip_probabilities_per_day_type(
    scenario: ty.Dict, case_name: str
) -> pd.DataFrame:
    '''
    This function computes the trip probabilities per day type for cars
    '''
    day_type_start_location_split: pd.DataFrame = (
        get_day_type_start_location_split(scenario)
    )

    trip_list: ty.List[str] = list(scenario['trips'].keys())
    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict = scenario['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    groupfile_root: str = file_parameters['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'

    time_parameters: ty.Dict = scenario['time']
    DAYS_IN_A_YEAR: float = time_parameters['DAYS_IN_A_YEAR']
    DAYS_IN_A_WEEK: int = time_parameters['DAYS_IN_A_WEEK']
    weeks_in_a_year: float = DAYS_IN_A_YEAR / DAYS_IN_A_WEEK
    weekend_day_numbers: ty.List[int] = time_parameters['weekend_day_numbers']
    number_weekdays: int = DAYS_IN_A_WEEK - len(weekend_day_numbers)

    mobility_module_parameters: ty.Dict = scenario['mobility_module']
    worked_hours_per_year: float = mobility_module_parameters[
        'worked_hours_per_year'
    ]
    work_hours_in_a_work_day: float = mobility_module_parameters[
        'work_hours_in_a_work_day'
    ]
    day_types: ty.List[str] = mobility_module_parameters['day_types']
    percentage_working_on_a_work_week: float = mobility_module_parameters[
        'percentage_working_on_a_work_week'
    ]
    hours_worked_per_work_week: float = mobility_module_parameters[
        'hours_worked_per_work_week'
    ]
    hours_in_a_standard_work_week: float = mobility_module_parameters[
        'hours_in_a_standard_work_week'
    ]
    # holiday_weeks = mobility_module_parameters['holiday_weeks']
    number_of_holiday_weeks: float = mobility_module_parameters[
        'number_of_holiday_weeks'
    ]
    holiday_trips_taken: float = mobility_module_parameters[
        'holiday_trips_taken'
    ]
    # time_spent_at_holiday_destination = mobility_module_parameters[
    #     'time_spent_at_holiday_destination'
    # ]
    # days_in_holiday_weeks = (
    #     DAYS_IN_A_YEAR * number_of_holiday_weeks / weeks_in_a_year
    # )
    weekend_days_per_year: float = (
        DAYS_IN_A_YEAR * len(weekend_day_numbers) / DAYS_IN_A_WEEK
    )
    weekend_trips_per_year: float = mobility_module_parameters[
        'weekend_trips_per_year'
    ]
    leisure_trips_per_weekend: float = mobility_module_parameters[
        'leisure_trips_per_weekend'
    ]
    leisure_trips_per_week_outside_weekends: float = (
        mobility_module_parameters['leisure_trips_per_week_outside_weekends']
    )

    maximal_fill_percentage_leisure_trips_on_non_work_weekdays: float = (
        mobility_module_parameters[
            'maximal_fill_percentage_leisure_trips_on_non_work_weekdays'
        ]
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
    # weekend_days_in_holiday_weeks = (
    #     (1 - weekday_proportion) * (1 - workweek_proportion) * DAYS_IN_A_YEAR
    # )

    holiday_departures_in_weekend_week_numbers: ty.List[int] = scenario[
        'mobility_module'
    ]['holiday_departures_in_weekend_week_numbers']
    number_of_holiday_departure_weekends: int = len(
        holiday_departures_in_weekend_week_numbers
    )
    holiday_returns_in_weekend_week_numbers: ty.List[int] = scenario[
        'mobility_module'
    ]['holiday_returns_in_weekend_week_numbers']
    number_of_holiday_return_weekends: int = len(
        holiday_returns_in_weekend_week_numbers
    )

    # We build a Dataframe to store the trip probabilities per day type
    trip_probabilities_per_day_type: pd.DataFrame = pd.DataFrame(
        columns=day_types, index=trip_list
    )
    trip_probabilities_per_day_type.index.name = 'Trip'

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
        day_type_start_location_split.loc['home']['weekend_in_work_week']
    )
    trip_probabilities_per_day_type.loc[
        'weekend_trip', 'weekend_in_holiday_week'
    ] = (
        weekend_trips_per_year / weekend_days_per_year_without_holiday_trips
    ) * float(
        day_type_start_location_split.loc['home']['weekend_in_holiday_week']
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
        day_type_start_location_split.loc['home']['weekday_in_holiday_week']
    )

    if probability_of_going_to_work_in_a_holiday_week > 1:
        print('The probability of going t work is larger than one.')
        print('Check your assumptions/inputs')
        print('(e.g. too many work hours and/or holiday trips or not enough )')
        print('holiday weeks)')

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
                ]
            )
            + float(
                trip_probabilities_per_day_type.loc['holiday_back'][
                    'weekday_in_holiday_week'
                ]
            )
        )
    ) * float(
        day_type_start_location_split.loc['home']['weekday_in_holiday_week']
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
        day_type_start_location_split.loc['home']['weekday_in_work_week']
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekday_in_holiday_week'
    ] = (
        weekday_leisure_trips_on_non_work_days_in_a_holiday_week
        / number_weekdays
    ) * float(
        day_type_start_location_split.loc['home']['weekday_in_holiday_week']
    )
    # For weekends, we distribute the leisure trips across the weekemd

    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekend_in_work_week'
    ] = (leisure_trips_per_weekend / len(weekend_day_numbers)) * float(
        day_type_start_location_split.loc['home']['weekend_in_work_week']
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekend_in_holiday_week'
    ] = (leisure_trips_per_weekend / len(weekend_day_numbers)) * float(
        day_type_start_location_split.loc['home']['weekend_in_holiday_week']
    )
    # For holiday departure and return weekends, we assume
    # that only those who do not travel can have a leisure-only trip
    percentage_not_departing: float = 1 - float(
        trip_probabilities_per_day_type.loc['holiday_outward'][
            'weekend_holiday_departures'
        ]
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekend_holiday_departures'
    ] = (
        percentage_not_departing
        * leisure_trips_per_weekend
        / len(weekend_day_numbers)
    ) * float(
        day_type_start_location_split.loc['home']['weekend_holiday_departures']
    )
    percentage_not_returning: float = 1 - float(
        trip_probabilities_per_day_type.loc['holiday_back'][
            'weekend_holiday_returns'
        ]
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only', 'weekend_holiday_returns'
    ] = (
        percentage_not_returning
        * leisure_trips_per_weekend
        / len(weekend_day_numbers)
    ) * float(
        day_type_start_location_split.loc['home']['weekend_holiday_returns']
    )
    # For overlap weekends, we have:
    percentage_not_departing_or_returning: float = 1 - float(
        trip_probabilities_per_day_type.loc['holiday_outward'][
            'holiday_overlap_weekend'
        ]
        + trip_probabilities_per_day_type.loc[
            'holiday_back', 'holiday_overlap_weekend'
        ]
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only', 'holiday_overlap_weekend'
    ] = (
        percentage_not_departing_or_returning
        * leisure_trips_per_weekend
        / len(weekend_day_numbers)
    ) * float(
        day_type_start_location_split.loc['home']['holiday_overlap_weekend']
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
        day_type_start_location_split.loc['home']['weekday_in_work_week']
    )
    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekday_in_work_week'
    ] = (
        probability_of_going_to_work_in_a_work_week
        * (1 - leisure_trip_probability_on_a_work_weekday_in_a_work_week)
    ) * float(
        day_type_start_location_split.loc['home']['weekday_in_work_week']
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
        day_type_start_location_split.loc['home']['weekday_in_holiday_week']
    )
    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekday_in_holiday_week'
    ] = (
        probability_of_going_to_work_in_a_holiday_week
        * (1 - leisure_trip_probability_on_a_work_weekday_in_a_holiday_week)
    ) * float(
        day_type_start_location_split.loc['home']['weekday_in_holiday_week']
    )

    trip_probabilities_per_day_type.loc[
        'commute_to_work', 'weekend_in_holiday_week'
    ] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure', 'weekend_in_holiday_week'
    ] = 0

    # Now that we computed all travelling trips, we look at the stay_put
    # trips as remainders

    stay_put_trips: ty.List[str] = ['stay_put_home', 'stay_put_holiday']
    travelling_trip_probabilities_per_day_type: pd.DataFrame = (
        trip_probabilities_per_day_type.drop(stay_put_trips, axis=0)
    )
    # We drop the stayp put trips to have the sum of actual trips
    # We will put the stay put trips back later
    stay_put_probabilities: pd.Series = (
        1 - travelling_trip_probabilities_per_day_type.sum()
    )

    stay_put_split: ty.Dict[str, ty.Dict[str, float]] = {}

    possible_stay_locations: ty.List[str] = ['home', 'holiday']
    for location in possible_stay_locations:
        stay_put_split[f'stay_put_{location}'] = {}
        for day_type in day_types:
            stay_put_split[f'stay_put_{location}'][day_type] = float(
                day_type_start_location_split.loc[location][day_type]
            )
    # We can now put the stay put probabilities
    for day_type in day_types:
        for stay_put_trip in stay_put_trips:
            trip_probabilities_per_day_type.loc[stay_put_trip, day_type] = (
                stay_put_probabilities[day_type]
                * stay_put_split[stay_put_trip][day_type]
            )

    table_name: str = f'{scenario_name}_trip_probabilities_per_day_type'

    # For some file formats (stata, for example), we need to ensure that
    # the values are floats (or something else, but object does seem to be a
    # problem, as the original DataFrame had nan elements).
    trip_probabilities_per_day_type = trip_probabilities_per_day_type.astype(
        'float'
    )

    cook.save_dataframe(
        trip_probabilities_per_day_type,
        table_name,
        groupfile_name,
        output_folder,
        scenario,
    )
    return trip_probabilities_per_day_type


def get_run_trip_probabilities(scenario: ty.Dict, case_name) -> pd.DataFrame:
    '''
    Gets a DataFrame containing the trip probabilities for the whole run.
    '''

    trip_list: ty.List[str] = list(scenario['trips'].keys())
    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict = scenario['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    groupfile_root: str = file_parameters['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'

    run_range, run_hour_numbers = run_time.get_time_range(scenario)
    run_trip_probabilities: pd.DataFrame = pd.DataFrame(index=run_range)
    run_trip_probabilities.index.name = 'Time Tag'

    run_trip_probabilities = run_time.add_day_type_to_time_stamped_dataframe(
        run_trip_probabilities, scenario
    )

    trip_probabilities_per_day_type: pd.DataFrame = (
        get_trip_probabilities_per_day_type(scenario, case_name)
    )

    for trip in trip_list:
        trip_probabilities: ty.List[float] = [
            trip_probabilities_per_day_type.loc[trip, day_type]
            for day_type in run_trip_probabilities['Day Type']
        ]

        run_trip_probabilities[trip] = trip_probabilities

    table_name: str = f'{scenario_name}_run_trip_probabilities'
    cook.save_dataframe(
        run_trip_probabilities,
        table_name,
        groupfile_name,
        output_folder,
        scenario,
    )
    return run_trip_probabilities


def get_mobility_matrix(scenario: ty.Dict, case_name: str) -> None:
    '''
    Makes a mobility matrix for the run that tracks departures
    from and to locations (tracks amount, kilometers, and weighted kilometers)
    '''

    run_trip_probabilities: pd.DataFrame = get_run_trip_probabilities(
        scenario, case_name
    )

    location_parameters: ty.Dict = scenario['locations']
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
    ]
    trip_parameters: ty.Dict = scenario['trips']
    trip_names: ty.List[str] = [trip_name for trip_name in trip_parameters]

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
    mobility_quantities: ty.List[str] = scenario['mobility_module'][
        'mobility_quantities'
    ]
    run_mobility_matrix: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_mobility_index), len(mobility_quantities))),
        columns=mobility_quantities,
        index=run_mobility_index,
    )
    run_mobility_matrix = run_mobility_matrix.sort_index()

    scenario_name: str = scenario['scenario_name']
    file_parameters: ty.Dict = scenario['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    groupfile_root: str = file_parameters['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'
    for trip_name in trip_names:
        this_trip_run_probabilities: pd.DataFrame = pd.DataFrame(
            run_trip_probabilities[trip_name]
        )
        # We need a version for each start/end location combination
        this_trip_run_probabilities_extended: pd.DataFrame = pd.DataFrame()
        for _ in range(len(location_names) * len(location_names)):
            this_trip_run_probabilities_extended = pd.concat(
                (
                    this_trip_run_probabilities,
                    this_trip_run_probabilities_extended,
                ),
                ignore_index=True,
            )
        trip_run_mobility_matrix_name: str = (
            f'{scenario_name}_{trip_name}_run_mobility_matrix'
        )

        trip_run_mobility_matrix: pd.DataFrame = cook.read_table_from_database(
            trip_run_mobility_matrix_name,
            f'{output_folder}/{groupfile_name}.sqlite3',
        )

        location_connections_headers: ty.List[str] = scenario[
            'mobility_module'
        ]['location_connections_headers']

        trip_run_mobility_matrix = trip_run_mobility_matrix.set_index(
            mobility_index_names
        )

        probability_values_to_use = this_trip_run_probabilities_extended[
            trip_name
        ].values
        # print(probability_values_to_use)
        # print(trip_run_mobility_matrix.loc['home', 'work'])
        # exit()

        for mobility_quantity in mobility_quantities:
            if mobility_quantity not in location_connections_headers:

                weighted_mobility_quantity_to_use = (
                    trip_run_mobility_matrix[mobility_quantity]
                    * probability_values_to_use
                )
                # print(mobility_quantity)
                # print(
                #     trip_run_mobility_matrix[mobility_quantity].loc[
                #         'home', 'work'
                #     ]
                # )
                # print(weighted_mobility_quantity_to_use.loc['home', 'work'])
                # exit()

                run_mobility_matrix[
                    mobility_quantity
                ] += weighted_mobility_quantity_to_use.values
    # print(run_mobility_matrix.loc['home', 'work'].iloc[26:89])
    # exit()
    location_connections: pd.DataFrame = (
        cook.read_table_from_database(
            f'{scenario_name}_location_connections',
            f'{output_folder}/{groupfile_name}.sqlite3',
        )
        .set_index(['From', 'To'])
        .astype(float)
    )
    # print(location_connections)
    # exit()
    run_range: pd.Index = run_mobility_index.get_level_values('Time Tag')

    for start_location in location_names:
        for end_location in location_names:
            these_locations_connections: pd.Series = pd.Series(
                location_connections.loc[start_location, end_location]
            )
            these_locations_tuples: ty.List[
                ty.Tuple[str, str, datetime.datetime]
            ] = [
                (start_location, end_location, time_tag)
                for time_tag in run_range
            ]
            these_loations_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
                these_locations_tuples
            )

            run_mobility_matrix.loc[
                these_loations_index,
                location_connections_headers,
            ] = these_locations_connections.values

            # run_mobility_matrix.loc[
            #     (start_location, end_location), location_connections_headers
            # ] = location_connections.loc[
            # (start_location, end_location)].values
    # print(run_mobility_matrix.loc['home', 'work'])
    # exit()
    cook.save_dataframe(
        run_mobility_matrix,
        f'{scenario_name}_run_mobility_matrix',
        groupfile_name,
        output_folder,
        scenario,
    )


def get_day_type_start_location_split(scenario: ty.Dict) -> pd.DataFrame:
    '''
    Tells us the proportion of vehicles
    that start their day at a given location (per day type)
    '''
    mobility_module_parameters: ty.Dict = scenario['mobility_module']
    holiday_trips_taken: float = mobility_module_parameters[
        'holiday_trips_taken'
    ]
    holiday_departures_in_weekend_week_numbers: ty.List[int] = (
        mobility_module_parameters[
            'holiday_departures_in_weekend_week_numbers'
        ]
    )
    number_of_holiday_departure_weekends: int = len(
        holiday_departures_in_weekend_week_numbers
    )
    day_types: ty.List[str] = mobility_module_parameters['day_types']
    location_parameters: ty.Dict = scenario['locations']
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
    ]

    day_type_start_location_split: pd.DataFrame = pd.DataFrame(
        np.zeros((len(location_names), len(day_types))),
        columns=day_types,
        index=location_names,
    )
    day_type_start_location_split.index.name = 'Location'

    # Outside holidays, the vehicles start at home
    day_types_outside_holidays: ty.List[str] = [
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

    non_travelling_holiday_day_types: ty.List[str] = [
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

    # For departure and retrun weekends, this is split across
    # the weekend days (note that this is an approximation, as
    # we ideally should split the weekend in two, but that would make
    # the model complexer)
    weekend_day_numbers: ty.List[int] = scenario['time']['weekend_day_numbers']
    travelling_weekend_day_types: ty.List[str] = [
        'weekend_holiday_departures',
        'weekend_holiday_returns',
        'holiday_overlap_weekend',
    ]
    for day_type in travelling_weekend_day_types:
        day_type_start_location_split.loc['home', day_type] = 1 - (
            percentage_on_holiday_in_holiday_week / len(weekend_day_numbers)
        )
        day_type_start_location_split.loc['holiday', day_type] = (
            percentage_on_holiday_in_holiday_week / len(weekend_day_numbers)
        )

    return day_type_start_location_split


def get_location_split(scenario: ty.Dict, case_name: str) -> None:
    '''
    Produces the location split of the vehicles for the whole run
    '''
    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict = scenario['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    groupfile_root: str = file_parameters['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'
    location_parameters: ty.Dict = scenario['locations']
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
    ]
    run_range: pd.DatetimeIndex = run_time.get_time_range(scenario)[0]
    location_split: pd.DataFrame = pd.DataFrame(
        columns=location_names, index=run_range
    )

    location_split.index.name = 'Time Tag'

    location_split = get_starting_location_split(location_split, scenario)

    run_mobility_matrix_name: str = f'{scenario_name}_run_mobility_matrix'
    database_file: str = f'{output_folder}/{groupfile_name}.sqlite3'

    run_mobility_matrix: pd.DataFrame = cook.read_table_from_database(
        run_mobility_matrix_name, database_file
    )
    mobility_index_names: ty.List[str] = scenario['mobility_module'][
        'mobility_index_names'
    ]

    run_mobility_matrix['Time Tag'] = pd.to_datetime(
        run_mobility_matrix['Time Tag']
    )
    run_mobility_matrix = run_mobility_matrix.set_index(
        mobility_index_names
    ).astype(float)

    previous_time_tag: datetime.datetime = run_range[0]
    for time_tag in run_range:
        if time_tag > run_range[0]:
            for location in location_names:

                departures: float = sum(
                    run_mobility_matrix.loc[
                        (location, location_names, time_tag),
                        'Departures amount',
                    ]
                    # *
                    # location_split.loc[previous_time_tag,location]
                )

                # We need to reduce the arrivals by the driving time
                # in the current hour, but add the one from the previous
                # hour (and departures correspond to arrivals later)
                arrivals: float = (
                    sum(
                        run_mobility_matrix.loc[
                            (location_names, location, time_tag),
                            'Arrivals amount',
                        ]
                    )
                    # -
                    # sum(
                    #     run_mobility_matrix.loc[
                    #         :, location, time_tag,
                    #             'Departures driving time']
                    # )
                    # +
                    # sum(
                    #     run_mobility_matrix.loc[
                    #         :, location, previous_time_tag,
                    #             'Departures driving time']
                    # )
                )

                location_split.loc[time_tag, location] = (
                    location_split.loc[previous_time_tag][location]
                    + arrivals
                    - departures
                )
            previous_time_tag = time_tag

    driving: pd.DataFrame = pd.DataFrame(index=location_split.index)
    driving['Driving percent'] = 1 - sum(location_split.sum(axis=1))
    connectivity_per_location: pd.DataFrame = location_split.copy()
    for location_name in location_names:
        connectivity_per_location[location_name] = (
            connectivity_per_location[location_name]
            * location_parameters[location_name]['connectivity']
        )
    maximal_delivered_power_location: pd.DataFrame = (
        connectivity_per_location.copy()
    )
    for location_name in location_names:
        maximal_delivered_power_location[location_name] = (
            maximal_delivered_power_location[location_name]
            * location_parameters[location_name]['charging_power']
            / location_parameters[location_name]['charger_efficiency']
            # Weare looking at the power delivered by the network
        )
    connectivity: pd.DataFrame = pd.DataFrame(
        index=connectivity_per_location.index
    )
    connectivity['Connectivity'] = connectivity_per_location.sum(axis=1)
    maximal_deivered_power: pd.DataFrame = pd.DataFrame(
        index=maximal_delivered_power_location.index
    )
    maximal_deivered_power['Maximal Delivered Power (kW)'] = (
        maximal_delivered_power_location.sum(axis=1)
    )
    cook.save_dataframe(
        location_split,
        f'{scenario_name}_location_split',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        driving,
        f'{scenario_name}_percentage_driving',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        connectivity_per_location,
        f'{scenario_name}_connectivity_per_location',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        connectivity,
        f'{scenario_name}_connectivity',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        maximal_delivered_power_location,
        f'{scenario_name}_maximal_delivered_power_per_location',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        maximal_deivered_power,
        f'{scenario_name}_maximal_delivered_power',
        groupfile_name,
        output_folder,
        scenario,
    )


def get_starting_location_split(
    location_split: pd.DataFrame, scenario: ty.Dict
) -> pd.DataFrame:
    '''
    Gets the location split at run start
    '''
    location_parameters: ty.Dict = scenario['locations']
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
    ]
    mobility_module_parameters: ty.Dict = scenario['mobility_module']
    compute_start_location_split: bool = mobility_module_parameters[
        'compute_start_location_split'
    ]
    if compute_start_location_split:
        run_start_time_tag: datetime.datetime = run_time.get_time_range(
            scenario
        )[0][0]
        run_start_day_type: str = run_time.get_day_type(
            run_start_time_tag, scenario
        )
        day_type_start_location_split: pd.DataFrame = (
            get_day_type_start_location_split(scenario)
        )

        for location_name in location_names:

            location_split.loc[run_start_time_tag, location_name] = (
                day_type_start_location_split[run_start_day_type][
                    location_name
                ]
            )

    else:
        for location_name in location_names:
            location_split.loc[run_start_time_tag, location_name] = (
                location_parameters[location_name][
                    'percentage_in_location_at_run_start'
                ]
            )

    return location_split


def get_kilometers_for_next_leg(scenario: ty.Dict, case_name: str) -> None:
    run_trip_probabilities: pd.DataFrame = get_run_trip_probabilities(
        scenario, case_name
    )

    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict = scenario['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    groupfile_root: str = file_parameters['groupfile_root']

    location_parameters: ty.Dict = scenario['locations']
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
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

    trip_parameters: ty.Dict = scenario['trips']
    trip_names: ty.List[str] = [trip_name for trip_name in trip_parameters]
    for trip_name in trip_names:
        trip_run_next_leg_kilometers: pd.DataFrame = (
            cook.read_table_from_database(
                f'{scenario_name}_{trip_name}_run_next_leg_kilometers',
                f'{output_folder}/{groupfile_root}_{case_name}.sqlite3',
            )
        )
        trip_run_next_leg_kilometers['Time Tag'] = pd.to_datetime(
            trip_run_next_leg_kilometers['Time Tag']
        )
        trip_run_next_leg_kilometers = trip_run_next_leg_kilometers.set_index(
            'Time Tag'
        )
        trip_run_next_leg_kilometers_cumulative: pd.DataFrame = (
            cook.read_table_from_database(
                f'{scenario_name}_{trip_name}_'
                f'run_next_leg_kilometers_cumulative',
                f'{output_folder}/{groupfile_root}_{case_name}.sqlite3',
            )
        )
        trip_run_next_leg_kilometers_cumulative['Time Tag'] = pd.to_datetime(
            trip_run_next_leg_kilometers_cumulative['Time Tag']
        )
        trip_run_next_leg_kilometers_cumulative = (
            trip_run_next_leg_kilometers_cumulative.set_index('Time Tag')
        )
        this_trip_probabilities: pd.Series[float] = pd.Series(
            run_trip_probabilities[trip_name]
        )

        run_next_leg_kilometers += trip_run_next_leg_kilometers.mul(
            this_trip_probabilities, axis=0
        )
        run_next_leg_kilometers_cumulative += (
            trip_run_next_leg_kilometers_cumulative.mul(
                this_trip_probabilities, axis=0
            )
        )

    cook.save_dataframe(
        run_next_leg_kilometers,
        f'{scenario_name}_next_leg_kilometers',
        f'{groupfile_root}_{case_name}',
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        run_next_leg_kilometers_cumulative,
        f'{scenario_name}_next_leg_kilometers_cumulative',
        f'{groupfile_root}_{case_name}',
        output_folder,
        scenario,
    )


def make_mobility_data(scenario: ty.Dict, case_name: str) -> None:
    get_trip_probabilities_per_day_type(scenario, case_name)
    get_mobility_matrix(scenario, case_name)
    get_location_split(scenario, case_name)
    get_kilometers_for_next_leg(scenario, case_name)


if __name__ == '__main__':
    case_name: str = 'local_impact_BEVs'
    scenario_file_name: str = f'scenarios/{case_name}/baseline.toml'
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)

    make_mobility_data(scenario, case_name)

    print('Add spillover?')
    print('Use departures from and arrivals to for location split')
    print('Difference with zero is % driving')
    print('Station users might be an issue')
    print('Assume evenly distributed and shift proportionally')
    print('Then consumptions (in other module) for both')
    print('One gives demand for next leg, other cosumed energy')
    # NEED percentage driving too! Do it in trip mobility matrix
    # and propagate into future hours if > 1 hour
    # (and maybe use the opportunity to do that too for trips<1 hour
    #  that propagate (but add after check))
    # e.g. 0.25 will be 0.25 for 0.75 and 0.75-x for last 0.25
    # with x going into next hour
    # in mobility: value at
    # [-1] + arrivals(1-travelling) - departures (1-travelling)
    # but then need to add spillover0
