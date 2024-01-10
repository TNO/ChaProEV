'''
This module computes the various functions related to mobility.
It contains the following functions:
1. **get_trip_probabilities_per_day_type:** This function computes the trip
probabilities per day type.
2. **get_run_trip_probabilities:** Gets a DataFrame containing the trip
probabilities for the whole run.
3. **get_mobility_matrix(parameters):**Makes a mobility matrix for the run
that tracks departures and arrivals
from and to locations (tracks amount, kilometers, and weighted kilometers)
'''
import pandas as pd
import numpy as np
import datetime

from ETS_CookBook import ETS_CookBook as cook

try:
    import run_time
except ModuleNotFoundError:
    from ChaProEV import run_time
# So that it works both as a standalone (1st) and as a package (2nd)


def get_trip_probabilities_per_day_type(parameters):
    '''
    This function computes the trip probabilities per day type.
    '''

    trip_list = list(parameters['trips'].keys())
    scenario = parameters['scenario']
    case_name = parameters['case_name']

    file_parameters = parameters['files']
    output_folder = file_parameters['output_folder']
    groupfile_root = file_parameters['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'

    time_parameters = parameters['time']
    DAYS_IN_A_YEAR = time_parameters['DAYS_IN_A_YEAR']
    DAYS_IN_A_WEEK = time_parameters['DAYS_IN_A_WEEK']
    weeks_in_a_year = DAYS_IN_A_YEAR / DAYS_IN_A_WEEK
    weekend_day_numbers = time_parameters['weekend_day_numbers']
    number_weekdays = DAYS_IN_A_WEEK - len(weekend_day_numbers)

    mobility_module_parameters = parameters['mobility_module']
    worked_hours_per_year = mobility_module_parameters['worked_hours_per_year']
    work_hours_in_a_work_day = (
        mobility_module_parameters['work_hours_in_a_work_day']
    )
    day_types = mobility_module_parameters['day_types']
    percentage_working_on_a_work_week = (
        mobility_module_parameters['percentage_working_on_a_work_week']
    )
    hours_worked_per_work_week = (
        mobility_module_parameters['hours_worked_per_work_week']
    )
    hours_in_a_standard_work_week = (
        mobility_module_parameters['hours_in_a_standard_work_week']
    )
    holiday_weeks = mobility_module_parameters['holiday_weeks']
    number_of_holiday_weeks = (
        mobility_module_parameters['number_of_holiday_weeks']
    )
    holiday_trips_taken = mobility_module_parameters['holiday_trips_taken']
    time_spent_at_holiday_destination = (
        mobility_module_parameters['time_spent_at_holiday_destination']
    )
    days_in_holiday_weeks = (
        DAYS_IN_A_YEAR * number_of_holiday_weeks / weeks_in_a_year
    )
    weekend_days_per_year = (
        DAYS_IN_A_YEAR * len(weekend_day_numbers) / DAYS_IN_A_WEEK
    )
    weekend_trips_per_year = (
        mobility_module_parameters['weekend_trips_per_year']
    )
    percentage_of_outward_holiday_trips_on_weekends = (
        mobility_module_parameters[
            'percentage_of_outward_holiday_trips_on_weekends']
    )
    percentage_of_back_holiday_trips_on_weekends = (
        mobility_module_parameters[
            'percentage_of_back_holiday_trips_on_weekends']
    )
    leisure_trips_per_weekend = (
        mobility_module_parameters['leisure_trips_per_weekend']
    )
    leisure_trips_per_week_outside_weekends = (
        mobility_module_parameters['leisure_trips_per_week_outside_weekends']
    )

    maximal_fill_percentage_leisure_trips_on_non_work_weekdays = (
        mobility_module_parameters[
            'maximal_fill_percentage_leisure_trips_on_non_work_weekdays']
    )

    # Some useful quantities telling us how many of which day type there are
    # per year
    weekday_proportion = (
        number_weekdays / DAYS_IN_A_WEEK
    )
    workweek_proportion = number_of_holiday_weeks / weeks_in_a_year
    weekdays_in_work_weeks = (
        weekday_proportion * workweek_proportion * DAYS_IN_A_YEAR
    )
    weekdays_in_holiday_weeks = (
        weekday_proportion * (1-workweek_proportion) * DAYS_IN_A_YEAR
    )
    weekend_days_in_holiday_weeks = (
        (1-weekday_proportion) * (1-workweek_proportion) * DAYS_IN_A_YEAR
    )

    # We build a Dataframe to store the trip probabilities per day type
    trip_probabilities_per_day_type = pd.DataFrame(
        columns=day_types, index=trip_list
    )
    trip_probabilities_per_day_type.index.name = 'Trip'

    # We start with trips that are independent of others, such as weekend
    # and holiday trips
    # Weekend trips occur on the weekend and their probability is the amount
    # of such trips divided by the amount of weekend days (both per year)
    trip_probabilities_per_day_type.loc[
        'weekend_trip']['weekday_in_work_week'] = 0
    trip_probabilities_per_day_type.loc[
        'weekend_trip']['weekday_in_holiday_week'] = 0
    trip_probabilities_per_day_type.loc[
        'weekend_trip']['weekend_in_work_week'] = (
        weekend_trips_per_year / weekend_days_per_year
    )
    trip_probabilities_per_day_type.loc[
        'weekend_trip']['weekend_in_holiday_week'] = (
        weekend_trips_per_year / weekend_days_per_year
    )

    # We assume that holiday trips only occur in holiday weeks
    trip_probabilities_per_day_type.loc[
        'holiday_outward']['weekday_in_work_week'] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_outward']['weekend_in_work_week'] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_back']['weekday_in_work_week'] = 0
    trip_probabilities_per_day_type.loc[
        'holiday_back']['weekend_in_work_week'] = 0

    outward_holiday_trips_on_weekdays = (
        holiday_trips_taken
        * (1 - percentage_of_outward_holiday_trips_on_weekends)
    )
    outward_holiday_trips_on_weekends = (
        holiday_trips_taken
        * percentage_of_outward_holiday_trips_on_weekends
    )
    back_holiday_trips_on_weekdays = (
        holiday_trips_taken
        * (1 - percentage_of_back_holiday_trips_on_weekends)
    )
    back_holiday_trips_on_weekends = (
        holiday_trips_taken
        * percentage_of_back_holiday_trips_on_weekends
    )

    trip_probabilities_per_day_type.loc[
        'holiday_outward']['weekday_in_holiday_week'] = (
        outward_holiday_trips_on_weekdays / weekdays_in_holiday_weeks
    )
    trip_probabilities_per_day_type.loc[
        'holiday_outward']['weekend_in_holiday_week'] = (
        outward_holiday_trips_on_weekends / weekend_days_in_holiday_weeks
    )
    trip_probabilities_per_day_type.loc[
        'holiday_back']['weekday_in_holiday_week'] = (
        back_holiday_trips_on_weekdays / weekdays_in_holiday_weeks
    )
    trip_probabilities_per_day_type.loc[
        'holiday_back']['weekend_in_holiday_week'] = (
        back_holiday_trips_on_weekends / weekend_days_in_holiday_weeks
    )

    trip_probabilities_per_day_type.loc[
        'leisure_only']['weekend_in_work_week'] = (
            leisure_trips_per_weekend / len(weekend_day_numbers)
    )
    trip_probabilities_per_day_type.loc[
        'leisure_only']['weekend_in_holiday_week'] = (
            leisure_trips_per_weekend / len(weekend_day_numbers)
    )

    # We compute the probability to go to work on a given day in a work week.
    # It is given by the probability that peple work in that week times
    # the number of hours worked in that week divided by
    # the length of a standard work week.
    probability_of_going_to_work_in_a_work_week = (
        percentage_working_on_a_work_week
        * hours_worked_per_work_week / hours_in_a_standard_work_week
    )
    if probability_of_going_to_work_in_a_work_week > 1:
        probability_of_going_to_work_in_a_work_week = 1
        # This  is there if some scenarios have more hours per week
        # than in a standard week.

    # To compute the probability to go to work in a holiday week,
    # we need a few steps.
    # We first look at how many weekdays there are in both week types

    worked_days_in_work_weeks = (
        probability_of_going_to_work_in_a_work_week * weekdays_in_work_weeks
    )
    # We also need the total amount of worked days per year.
    worked_days_per_year = worked_hours_per_year / work_hours_in_a_work_day
    # The number of worked days in holiday weeks
    # is the difference between the above two.
    worked_days_in_holiday_weeks = (
        worked_days_per_year-worked_days_in_work_weeks
    )

    # The probability to go to work on a holiday week day is
    # the ratio bewtween the number of worked days (on holiday weekdays)
    # and the total amount of holiday weekdays.
    probability_of_going_to_work_in_a_holiday_week = (
        worked_days_in_holiday_weeks / weekdays_in_holiday_weeks
    )

    worked_days_in_a_work_week = (
         number_weekdays * probability_of_going_to_work_in_a_work_week
    )

    weekdays_with_no_work_trip_per_work_week = (
        number_weekdays - worked_days_in_a_work_week
    )

    worked_days_in_a_holiday_week = (
        number_weekdays * probability_of_going_to_work_in_a_holiday_week
    )

    weekdays_with_no_work_trip_per_holiday_week = (
        number_weekdays - worked_days_in_a_holiday_week
    )

    # For work weeks, it's the same as the amount of days
    # where there is no work trip.
    non_work_weekdays_per_work_week_where_a_leisure_trip_can_occur = (
        weekdays_with_no_work_trip_per_work_week
    )

    # For holiday weeks, we need to substract weekdays where

    non_work_weekdays_per_holiday_week_where_a_leisure_trip_can_occur = (
        weekdays_with_no_work_trip_per_holiday_week
        - number_weekdays * (
            trip_probabilities_per_day_type.loc[
                'holiday_outward']['weekday_in_holiday_week']
            + trip_probabilities_per_day_type.loc[
                'holiday_back']['weekday_in_holiday_week']
        )
    )

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
        fill_level_non_work_weekdays_with_leisure_trips_in_a_work_week = 0
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
        fill_level_non_work_weekdays_with_leisure_trips_in_a_holiday_week = 0
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
    weekday_leisure_trips_on_non_work_days_in_a_work_week = (
        fill_level_non_work_weekdays_with_leisure_trips_in_a_work_week
        * non_work_weekdays_per_work_week_where_a_leisure_trip_can_occur
    )
    weekday_leisure_trips_on_non_work_days_in_a_holiday_week = (
        fill_level_non_work_weekdays_with_leisure_trips_in_a_holiday_week
        * non_work_weekdays_per_holiday_week_where_a_leisure_trip_can_occur
    )

    # This allows us to set the leisure only trips on weekdays

    trip_probabilities_per_day_type.loc[
        'leisure_only']['weekday_in_work_week'] = (
            weekday_leisure_trips_on_non_work_days_in_a_work_week
            / number_weekdays
        )
    trip_probabilities_per_day_type.loc[
        'leisure_only']['weekday_in_holiday_week'] = (
            weekday_leisure_trips_on_non_work_days_in_a_holiday_week
            / number_weekdays
        )
    # The amount of weekday leisure trips taking place on work weekdays is
    # then the difference between the total amount of weekday leisure trips and
    # the amount we just calculated.
    weekday_leisure_trips_on_work_days_in_a_work_week = (
        leisure_trips_per_week_outside_weekends
        - weekday_leisure_trips_on_non_work_days_in_a_work_week
    )
    weekday_leisure_trips_on_work_days_in_a_holiday_week = (
        leisure_trips_per_week_outside_weekends
        - weekday_leisure_trips_on_non_work_days_in_a_holiday_week
    )

    # We can also compute the probability to have a leisure trip on a
    # working weekday (we do not use the fill parameter).
    leisure_trip_probability_on_a_work_weekday_in_a_work_week = (
        weekday_leisure_trips_on_work_days_in_a_work_week
        / worked_days_in_a_work_week
    )

    leisure_trip_probability_on_a_work_weekday_in_a_holiday_week = (
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
        'commute_to_work_and_leisure']['weekday_in_work_week'] = (
            probability_of_going_to_work_in_a_work_week
            * leisure_trip_probability_on_a_work_weekday_in_a_work_week
        )
    trip_probabilities_per_day_type.loc[
        'commute_to_work']['weekday_in_work_week'] = (
            probability_of_going_to_work_in_a_work_week
            * (1-leisure_trip_probability_on_a_work_weekday_in_a_work_week)
        )

    trip_probabilities_per_day_type.loc[
        'commute_to_work']['weekend_in_work_week'] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure']['weekend_in_work_week'] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure']['weekday_in_holiday_week'] = (
            probability_of_going_to_work_in_a_holiday_week
            * leisure_trip_probability_on_a_work_weekday_in_a_holiday_week
        )
    trip_probabilities_per_day_type.loc[
        'commute_to_work']['weekday_in_holiday_week'] = (
            probability_of_going_to_work_in_a_holiday_week
            * (1-leisure_trip_probability_on_a_work_weekday_in_a_holiday_week)
        )

    trip_probabilities_per_day_type.loc[
        'commute_to_work']['weekend_in_holiday_week'] = 0

    trip_probabilities_per_day_type.loc[
        'commute_to_work_and_leisure']['weekend_in_holiday_week'] = 0

    # Now that we computed all travelling trips, we look at the stay_put
    # trips as remainders

    stay_put_trips = ['stay_put_home', 'stay_put_holiday']
    travelling_trip_probabilities_per_day_type = (
        trip_probabilities_per_day_type.drop(stay_put_trips, axis=0)
    )
    stay_put_probabilities = (
        1 - travelling_trip_probabilities_per_day_type.sum()
    )
    stay_put_split = {}
    stay_put_split['stay_put_home'] = {}
    stay_put_split['stay_put_holiday'] = {}
    stay_put_split['stay_put_home']['weekday_in_work_week'] = 1
    stay_put_split['stay_put_holiday']['weekday_in_work_week'] = 0
    stay_put_split['stay_put_home']['weekend_in_work_week'] = 1
    stay_put_split['stay_put_holiday']['weekend_in_work_week'] = 0
    percent_days_in_holiday_weeks_at_holiday_destination = (
        holiday_trips_taken
        * time_spent_at_holiday_destination / days_in_holiday_weeks
    )
    stay_put_split['stay_put_home']['weekday_in_holiday_week'] = (
        1 - percent_days_in_holiday_weeks_at_holiday_destination
    )
    stay_put_split['stay_put_holiday']['weekday_in_holiday_week'] = (
        percent_days_in_holiday_weeks_at_holiday_destination
    )
    stay_put_split['stay_put_home']['weekend_in_holiday_week'] = (
        1 - percent_days_in_holiday_weeks_at_holiday_destination
    )
    stay_put_split['stay_put_holiday']['weekend_in_holiday_week'] = (
        percent_days_in_holiday_weeks_at_holiday_destination
    )
    for day_type in day_types:
        for stay_put_trip in stay_put_trips:
            trip_probabilities_per_day_type.loc[stay_put_trip][day_type] = (
                stay_put_probabilities[day_type]
                * stay_put_split[stay_put_trip][day_type]
            )
    table_name = f'{scenario}_trip_probabilities_per_day_type'

    # For some file formats (stata, for example), we need to ensure that
    # the values are floats (or something else, but object does seem to be a
    # problem, as the original DataFrame had nan elements).
    trip_probabilities_per_day_type = (
        trip_probabilities_per_day_type.astype('float')
    )

    cook.save_dataframe(
        trip_probabilities_per_day_type, table_name, groupfile_name,
        output_folder, parameters
    )

    return trip_probabilities_per_day_type


def get_run_trip_probabilities(parameters):
    '''
    Gets a DataFrame containing the trip probabilities for the whole run.
    '''

    trip_list = list(parameters['trips'].keys())
    scenario = parameters['scenario']
    case_name = parameters['case_name']

    file_parameters = parameters['files']
    output_folder = file_parameters['output_folder']
    groupfile_root = file_parameters['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'

    run_range, run_hour_numbers = run_time.get_time_range(parameters)
    run_trip_probabilities = pd.DataFrame(index=run_range)
    run_trip_probabilities.index.name = 'Time Tag'

    run_trip_probabilities = (
        run_time.add_day_type_to_time_stamped_dataframe(
            run_trip_probabilities, parameters
        )
    )

    trip_probabilities_per_day_type = (
                get_trip_probabilities_per_day_type(parameters)
    )

    for trip in trip_list:
        trip_probabilities = (
            [
                trip_probabilities_per_day_type[day_type][trip]
                for day_type in run_trip_probabilities['Day Type']
            ]
        )
        day_start_hour = parameters['trips'][trip]['day_start_hour']
        # The trips might not start at midnight
        trip_probabilities = np.roll(trip_probabilities, day_start_hour)
        run_trip_probabilities[trip] = trip_probabilities

    table_name = f'{scenario}_run_trip_probabilities'
    cook.save_dataframe(
        run_trip_probabilities,
        table_name, groupfile_name, output_folder, parameters
    )

    return run_trip_probabilities


def get_mobility_matrix(parameters):
    '''
    Makes a mobility matrix for the run that tracks departures and arrivals
    from and to locations (tracks amount, kilometers, and weighted kilometers)
    '''

    run_trip_probabilities = get_run_trip_probabilities(parameters)

    location_parameters = parameters['locations']
    location_names = [
            location_name for location_name in location_parameters
    ]
    trip_parameters = parameters['trips']
    trip_names = [
        trip_name for trip_name in trip_parameters
    ]

    run_time_tags = run_time.get_time_range(parameters)[0]
    run_mobility_index_tuples = [
        (start_location, end_location, time_tag)
        for start_location in location_names
        for end_location in location_names
        for time_tag in run_time_tags
    ]
    mobility_index_names = (
        parameters['mobility_module']['mobility_index_names']
    )
    run_mobility_index = pd.MultiIndex.from_tuples(
        run_mobility_index_tuples,
        names=mobility_index_names)
    mobility_quantities = (
        parameters['mobility_module']['mobility_quantities']
    )
    run_mobility_matrix = pd.DataFrame(
        np.zeros((len(run_mobility_index), len(mobility_quantities))),
        columns=mobility_quantities,
        index=run_mobility_index
    )
    run_mobility_matrix = run_mobility_matrix.sort_index()

    case_name = parameters['case_name']
    scenario = parameters['scenario']
    file_parameters = parameters['files']
    output_folder = file_parameters['output_folder']
    groupfile_root = file_parameters['groupfile_root']
    for trip_name in trip_names:
        this_trip_run_probabilities = pd.DataFrame(
            run_trip_probabilities[trip_name]
        )
        # We need a version for each start/end location combination
        this_trip_run_probabilities_extended = pd.DataFrame()
        for _ in range(len(location_names)*len(location_names)):
            this_trip_run_probabilities_extended = pd.concat(
                (this_trip_run_probabilities,
                 this_trip_run_probabilities_extended),
                ignore_index=True

            )
        trip_run_mobility_matrix_name = (
            f'{case_name}_{scenario}_{trip_name}_run_mobility_matrix'
        )
        trip_run_mobility_matrix = cook.read_table_from_database(
            trip_run_mobility_matrix_name,
            f'{output_folder}/{groupfile_root}.sqlite3'
        )
        trip_run_mobility_matrix = (
            trip_run_mobility_matrix.set_index(mobility_index_names)
        )
        probability_values_to_use = (
            this_trip_run_probabilities_extended[trip_name].values
        )

        for mobility_quantity in mobility_quantities:

            run_mobility_matrix[mobility_quantity] += (
                trip_run_mobility_matrix[mobility_quantity].values
                *
                probability_values_to_use
            )
    cook.save_dataframe(
        run_mobility_matrix, f'{case_name}_{scenario}_run_mobility_matrix',
        groupfile_root, output_folder, parameters
    )
    return run_mobility_matrix


if __name__ == '__main__':
    parameters_file_name = 'scenarios/baseline.toml'
    parameters = cook.parameters_from_TOML(parameters_file_name)
    trip_probabilities_per_day_type = get_trip_probabilities_per_day_type(
        parameters
    )
    print(trip_probabilities_per_day_type)
    # for day_type in trip_probabilities_per_day_type.columns:
    #     print(
    #         trip_probabilities_per_day_type[day_type],
    #         sum(trip_probabilities_per_day_type[day_type])
    #     )

    start_time = datetime.datetime.now()

    run_mobility_matrix = get_mobility_matrix(parameters)
    print(run_mobility_matrix)
    print((datetime.datetime.now()-start_time).total_seconds())

    print('Assume evenly distributed and shift proportionally')
    print('Then consumptions (in other module) for both')
    print('One gives demand for next leg, other cosumed energy')
