'''
Author: Omar Usmani (Oar.Usmani@TNO.nl)
This module defines time structures.

It contains the following functions:
1. **get_time_range:** This function returns the time range of the run, and the
    associated hour numbers, based on values found in the
    parameters file.
2. **get_time_stamped_dataframe:** This function creates a DataFrame with the
timestamps of the run as index (and hour numbers as a column).
3. **get_day_type:** Tells us the date type of a given time_tag.
4. **add_day_type_to_time_stamped_dataframe:** Adds a column with the date type
to a time-stamped_dataframe
5. **from_day_to_run:** Clones dataframefor a day (with zero at day start) for
the whole run.
'''


import datetime

import pandas as pd
import numpy as np
import math

from ETS_CookBook import ETS_CookBook as cook


def get_time_range(parameters):
    '''
    This function returns the time range of the run, and the
    associated hour numbers, based on values found in the
    parameters file.
    '''

    run_start_parameters = parameters['run']['start']
    run_start_year = run_start_parameters['year']
    run_start_month = run_start_parameters['month']
    run_start_day = run_start_parameters['day']
    run_start_hour = run_start_parameters['hour']
    run_start_minute = run_start_parameters['minute']

    run_start = datetime.datetime(
        run_start_year, run_start_month, run_start_day,
        run_start_hour, run_start_minute
    )

    run_end_parameters = parameters['run']['end']
    run_end_year = run_end_parameters['year']
    run_end_month = run_end_parameters['month']
    run_end_day = run_end_parameters['day']
    run_end_hour = run_end_parameters['hour']
    run_end_minute = run_end_parameters['minute']

    run_end = datetime.datetime(
        run_end_year, run_end_month, run_end_day,
        run_end_hour, run_end_minute
    )

    run_parameters = parameters['run']
    run_frequency_parameters = run_parameters['frequency']
    run_frequency_size = run_frequency_parameters['size']
    run_frequency_type = run_frequency_parameters['type']
    run_frequency = f'{run_frequency_size}{run_frequency_type}'

    run_range = pd.date_range(
        start=run_start, end=run_end, freq=run_frequency, inclusive='left'
        # We want the start timestamp, but not the end one, so we need
        # to say it is closed left
    )

    time_parameters = parameters['time']
    SECONDS_PER_HOUR = time_parameters['SECONDS_PER_HOUR']
    first_hour_number = time_parameters['first_hour_number']

    run_hour_numbers = [
        first_hour_number
        + int(
            (
                time_stamp-datetime.datetime(time_stamp.year, 1, 1, 0, 0)
            ).total_seconds()/SECONDS_PER_HOUR
        )
        for time_stamp in run_range
    ]

    return run_range, run_hour_numbers


def get_time_stamped_dataframe(parameters):
    '''
    This function creates a DataFrame with the timestamps of the
    run as index (and hour numbers as a column).
    '''

    run_range, run_hour_numbers = get_time_range(parameters)
    time_stamped_dataframe = pd.DataFrame(
        run_hour_numbers, columns=['Hour Number'], index=run_range
    )
    time_stamped_dataframe.index.name = 'Timestamp'

    time_stamped_dataframe['SPINE_hour_number'] = (
        [f't{hour_number:04}' for hour_number in run_hour_numbers]
    )
    time_stamped_dataframe = (
        add_day_type_to_time_stamped_dataframe(
            time_stamped_dataframe, parameters
        )
    )

    location_parameters = parameters['locations']
    locations = list(location_parameters.keys())
    time_stamped_dataframe[locations] = np.empty(
        (len(run_range), len(locations)))
    time_stamped_dataframe[locations] = np.nan

    return time_stamped_dataframe


def get_day_type(time_tag, parameters):
    '''
    Tells us the date type of a given time_tag.
    '''

    weekend_day_numbers = parameters['time']['weekend_day_numbers']
    holiday_weeks = parameters['mobility_module']['holiday_weeks']
    if time_tag.isoweekday() in weekend_day_numbers:
        day_type = 'weekend'
    else:
        day_type = 'weekday'

    if time_tag.isocalendar().week in holiday_weeks:
        week_type = 'holiday'
    else:
        week_type = 'work'

    return f'{day_type}_in_{week_type}_week'


def add_day_type_to_time_stamped_dataframe(dataframe, parameters):
    '''
    Adds a column with the date type
    to a time-stamped_dataframe
    '''
    day_types = [
        get_day_type(time_tag, parameters)
        for time_tag in dataframe.index
    ]

    dataframe['Day Type'] = day_types
    return dataframe


def from_day_to_run(dataframe_to_clone, run_range, day_start_hour, parameters):
    '''
    Clones dataframe for a day (with zero at day start) for
    the whole run.
    '''

    # We need to roll the values so that they start at midnight
    rolled_values = [
        np.roll(dataframe_to_clone[column], day_start_hour)
        for column in dataframe_to_clone.columns
    ]

    rolled_dataframe_to_clone = pd.DataFrame()
    for column, column_values in zip(
            dataframe_to_clone.columns, rolled_values):
        rolled_dataframe_to_clone[column] = column_values

    SECONDS_PER_HOUR = parameters['time']['SECONDS_PER_HOUR']
    HOURS_IN_A_DAY = parameters['time']['HOURS_IN_A_DAY']
    run_number_of_seconds = (run_range[-1] - run_range[0]).total_seconds()
    run_days = (
        math.ceil(run_number_of_seconds/(SECONDS_PER_HOUR*HOURS_IN_A_DAY))
    )
    run_dataframe = pd.DataFrame()
    for _ in range(run_days):
        run_dataframe = pd.concat(
            (rolled_dataframe_to_clone, run_dataframe), ignore_index=True
        )

    # We create an extended run range, which includes all hours in the days
    # of the range (i.e. hours before the run starts and after it ends)
    extended_run_start = datetime.datetime(
        year=run_range[0].year, month=run_range[0].month,
        day=run_range[0].day, hour=0)
    day_after_end_run = run_range[-1] + datetime.timedelta(days=1)
    extended_run_end = datetime.datetime(
        year=day_after_end_run.year, month=day_after_end_run.month,
        day=day_after_end_run.day, hour=0)
    run_parameters = parameters['run']
    run_frequency_parameters = run_parameters['frequency']
    run_frequency_size = run_frequency_parameters['size']
    run_frequency_type = run_frequency_parameters['type']
    run_frequency = f'{run_frequency_size}{run_frequency_type}'
    extended_run_range = pd.date_range(
        start=extended_run_start, end=extended_run_end,
        freq=run_frequency,
        inclusive='left'
    )
    run_dataframe['Time tag'] = extended_run_range

    # We then cut the parts that arenot in the run
    run_dataframe = run_dataframe[run_dataframe['Time tag'] <= run_range[-1]]
    run_dataframe = run_dataframe[run_dataframe['Time tag'] >= run_range[0]]
    run_dataframe = run_dataframe.set_index('Time tag')

    return run_dataframe


if __name__ == '__main__':

    parameters_file_name = 'scenarios/baseline.toml'
    parameters = cook.parameters_from_TOML(parameters_file_name)
    run_range, run_hour_numbers = get_time_range(parameters)
    time_stamped_dataframe = get_time_stamped_dataframe(parameters)
    print(run_range)
    print(run_hour_numbers)
    print(time_stamped_dataframe)
