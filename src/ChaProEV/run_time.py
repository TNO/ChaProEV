'''
Author: Omar Usmani (Oar.Usmani@TNO.nl)
This module defines time structures.

It contains the following functions:
1. **get_time_range:** This function returns the time range of the run, and the
    associated hour numbers, based on values found in the
    scenario file.
2. **get_time_stamped_dataframe:** This function creates a DataFrame with the
time tags of the run as index (and hour numbers as a column).
3. **get_day_type:** Tells us the date type of a given time_tag.
4. **add_day_type_to_time_stamped_dataframe:** Adds a column with the date type
to a time-stamped_dataframe
5. **from_day_to_run:** Clones dataframe for a day (with zero at day start) for
the whole run.
'''

import datetime
import math
import typing as ty

import numpy as np
import pandas as pd
from box import Box
from ETS_CookBook import ETS_CookBook as cook


def get_run_duration(
    scenario: Box, general_parameters: Box
) -> ty.Tuple[float, float]:
    '''
    Gets the run duration (in seconds and years)
    '''
    run_range: pd.DatetimeIndex = get_time_range(scenario, general_parameters)[
        0
    ]

    run_duration_seconds: float = (
        run_range[-1] - run_range[0]
    ).total_seconds()

    time_parameters: Box = general_parameters.time
    SECONDS_PER_HOUR: int = int(time_parameters.SECONDS_PER_HOUR)
    HOURS_IN_A_DAY: int = int(time_parameters.HOURS_IN_A_DAY)
    DAYS_IN_A_YEAR: float = time_parameters.DAYS_IN_A_YEAR
    SECONDS_PER_YEAR: float = (
        SECONDS_PER_HOUR * HOURS_IN_A_DAY * DAYS_IN_A_YEAR
    )
    run_duration_years: float = run_duration_seconds / SECONDS_PER_YEAR

    return run_duration_seconds, run_duration_years


def get_time_range(
    scenario: Box, general_parameters: Box
) -> ty.Tuple[pd.DatetimeIndex, ty.List[int], pd.DatetimeIndex]:
    '''
    This function returns the time range of the run, and the
    associated hour numbers, based on values found in the
    scenario file.
    '''
    run_parameters: Box = scenario.run
    run_start_parameters: Box = run_parameters.start
    run_start_year: int = int(run_start_parameters.year)
    run_start_month: int = int(run_start_parameters.month)
    run_start_day: int = int(run_start_parameters.day)
    run_start_hour: int = int(run_start_parameters.hour)
    run_start_minute: int = int(run_start_parameters.minute)

    run_start: datetime.datetime = datetime.datetime(
        run_start_year,
        run_start_month,
        run_start_day,
        run_start_hour,
        run_start_minute,
    )

    display_run_start_parameters: Box = run_parameters.display_start
    display_run_start_year: int = int(display_run_start_parameters.year)
    display_run_start_month: int = int(display_run_start_parameters.month)
    display_run_start_day: int = int(display_run_start_parameters.day)
    display_run_start_hour: int = int(display_run_start_parameters.hour)
    display_run_start_minute: int = int(display_run_start_parameters.minute)

    display_run_start: datetime.datetime = datetime.datetime(
        display_run_start_year,
        display_run_start_month,
        display_run_start_day,
        display_run_start_hour,
        display_run_start_minute,
    )

    mobility_module_parameters: Box = scenario.mobility_module

    day_start_hour: int = int(mobility_module_parameters.day_start_hour)
    compute_start_location_split: bool = (
        mobility_module_parameters.compute_start_location_split
    )

    # If we want the model to compute the starting values, we
    # expand the run to the prior day start so that we can use the
    # location split at day start per day type
    if compute_start_location_split:
        # If the start hour is before the day start hour,
        # we need to go one day backward
        if run_start_hour < day_start_hour:
            run_start -= datetime.timedelta(days=1)
            run_start_year = run_start.year
            run_start_month = run_start.month
            run_start_day = run_start.day
        run_start_hour = day_start_hour
        run_start = datetime.datetime(
            run_start_year,
            run_start_month,
            run_start_day,
            run_start_hour,
            run_start_minute,
        )

    run_end_parameters: Box = run_parameters.end
    run_end_year: int = int(run_end_parameters.year)
    run_end_month: int = int(run_end_parameters.month)
    run_end_day: int = int(run_end_parameters.day)
    run_end_hour: int = int(run_end_parameters.hour)
    run_end_minute: int = int(run_end_parameters.minute)

    run_end: datetime.datetime = datetime.datetime(
        run_end_year, run_end_month, run_end_day, run_end_hour, run_end_minute
    )

    display_run_end_parameters: Box = run_parameters.display_end
    display_run_end_year: int = int(display_run_end_parameters.year)
    display_run_end_month: int = int(display_run_end_parameters.month)
    display_run_end_day: int = int(display_run_end_parameters.day)
    display_run_end_hour: int = int(display_run_end_parameters.hour)
    display_run_end_minute: int = int(display_run_end_parameters.minute)

    display_run_end: datetime.datetime = datetime.datetime(
        display_run_end_year,
        display_run_end_month,
        display_run_end_day,
        display_run_end_hour,
        display_run_end_minute,
    )

    run_frequency_parameters: Box = run_parameters.frequency
    run_frequency_size: int = run_frequency_parameters.size
    run_frequency_type: str = run_frequency_parameters.type
    run_frequency: str = f'{run_frequency_size}{run_frequency_type}'

    display_run_frequency_parameters: Box = run_parameters.display_frequency
    display_run_frequency_size: int = display_run_frequency_parameters.size
    display_run_frequency_type: str = display_run_frequency_parameters.type
    display_run_frequency: str = (
        f'{display_run_frequency_size}{display_run_frequency_type}'
    )

    run_range: pd.DatetimeIndex = pd.date_range(
        start=run_start,
        end=run_end,
        freq=run_frequency,
        inclusive='left',
        # We want the start timestamp, but not the end one, so we need
        # to say it is closed left
    )

    display_range: pd.DatetimeIndex = pd.date_range(
        start=display_run_start,
        end=display_run_end,
        freq=display_run_frequency,
        inclusive='left',
        # We want the start timestamp, but not the end one, so we need
        # to say it is closed left
    )

    time_parameters: Box = general_parameters.time
    SECONDS_PER_HOUR: int = time_parameters.SECONDS_PER_HOUR
    first_hour_number: int = time_parameters.first_hour_number

    run_hour_numbers: ty.List[int] = [
        first_hour_number
        + int(
            (
                time_stamp - datetime.datetime(time_stamp.year, 1, 1, 0, 0)
            ).total_seconds()
            / SECONDS_PER_HOUR
        )
        for time_stamp in run_range
    ]

    return run_range, run_hour_numbers, display_range


def get_time_stamped_dataframe(
    scenario: Box,
    general_parameters: Box,
    locations_as_columns: bool = True,
) -> pd.DataFrame:
    '''
    This function creates a DataFrame with the timestamps of the
    run as index (and hour numbers, SPINE hour numbers as a column).
    '''

    run_range, run_hour_numbers, display_range = get_time_range(
        scenario, general_parameters
    )
    time_stamped_dataframe: pd.DataFrame = pd.DataFrame(
        run_hour_numbers, columns=['Hour Number'], index=run_range
    )
    time_stamped_dataframe.index.name = 'Time Tag'

    time_stamped_dataframe['SPINE_hour_number'] = [
        f't{hour_number:04}' for hour_number in run_hour_numbers
    ]
    time_stamped_dataframe = add_day_type_to_time_stamped_dataframe(
        time_stamped_dataframe, scenario, general_parameters
    )

    day_start_hour: int = int(scenario.mobility_module.day_start_hour)
    HOURS_IN_A_DAY = general_parameters.time.HOURS_IN_A_DAY
    hour_in_day: ty.List[int] = [
        (
            timestamp.hour - day_start_hour
            if timestamp.hour >= day_start_hour
            else HOURS_IN_A_DAY + timestamp.hour - day_start_hour
        )
        for timestamp in run_range
    ]

    time_stamped_dataframe['Hour index from day start'] = hour_in_day

    if locations_as_columns:
        vehicle: str = scenario.vehicle.name
        location_parameters: Box = scenario.locations
        locations: ty.List[str] = [
            location_name
            for location_name in location_parameters.keys()
            if location_parameters[location_name].vehicle == vehicle
        ]
        time_stamped_dataframe[locations] = np.empty(
            (len(run_range), len(locations))
        )
        time_stamped_dataframe[locations] = np.nan

    return time_stamped_dataframe


def get_day_type(
    time_tag: datetime.datetime, scenario: Box, general_parameters: Box
) -> str:
    '''
    Tells us the date type of a given time_tag.
    '''

    weekend_day_numbers: ty.List[int] = general_parameters.time[
        'weekend_day_numbers'
    ]
    holiday_weeks: ty.List[int] = scenario.mobility_module.holiday_weeks
    if time_tag.isoweekday() in weekend_day_numbers:
        day_type: str = 'weekend'
    else:
        day_type = 'weekday'

    if time_tag.isocalendar().week in holiday_weeks:
        week_type: str = 'holiday'
    else:
        week_type = 'work'

    day_name: str = f'{day_type}_in_{week_type}_week'

    holiday_departures_in_weekend_week_numbers: ty.List[int] = (
        scenario.mobility_module.holiday_departures_in_weekend_week_numbers
    )
    holiday_returns_in_weekend_week_numbers: ty.List[int] = (
        scenario.mobility_module.holiday_returns_in_weekend_week_numbers
    )
    holiday_overlap_weekend_week_numbers: ty.List[int] = list(
        set(holiday_departures_in_weekend_week_numbers).intersection(
            holiday_returns_in_weekend_week_numbers
        )
    )

    if day_type == 'weekend':
        if time_tag.isocalendar().week in (
            holiday_overlap_weekend_week_numbers
        ):
            day_name = 'holiday_overlap_weekend'
        elif time_tag.isocalendar().week in (
            holiday_departures_in_weekend_week_numbers
        ):
            day_name = 'weekend_holiday_departures'
        elif time_tag.isocalendar().week in (
            holiday_returns_in_weekend_week_numbers
        ):
            day_name = 'weekend_holiday_returns'

    return day_name


def add_day_type_to_time_stamped_dataframe(
    dataframe: pd.DataFrame, scenario: Box, general_parameters: Box
) -> pd.DataFrame:
    '''
    Adds a column with the date type
    to a time-stamped_dataframe
    '''
    day_start_hour: int = int(scenario.mobility_module.day_start_hour)
    day_types: ty.List[str] = [
        get_day_type(
            time_tag - datetime.timedelta(hours=day_start_hour),
            scenario,
            general_parameters,
        )
        for time_tag in dataframe.index
    ]

    dataframe['Day Type'] = day_types
    return dataframe


def get_day_start_time_tags_and_types(
    scenario: Box, general_parameters: Box
) -> ty.List[ty.Tuple[datetime.datetime, str]]:
    time_tags_and_types: ty.List[ty.Tuple[datetime.datetime, str]] = []

    run_start_year: int = int(scenario.run.start.year)
    run_start_month: int = int(scenario.run.start.month)
    run_start_day: int = int(scenario.run.start.day)
    run_end_year: int = int(scenario.run.end.year)
    run_end_month: int = int(scenario.run.end.month)
    run_end_day: int = int(scenario.run.end.day)
    day_start_hour: int = int(scenario.mobility_module.day_start_hour)
    tags_start: datetime.datetime = datetime.datetime(
        year=run_start_year,
        month=run_start_month,
        day=run_start_day,
        hour=day_start_hour,
    )
    tags_end: datetime.datetime = datetime.datetime(
        year=run_end_year,
        month=run_end_month,
        day=run_end_day,
        hour=day_start_hour,
    )

    tags_range: pd.DatetimeIndex = pd.date_range(
        start=tags_start, end=tags_end, freq='D', inclusive='both'
    )
    for time_tag in tags_range:
        time_tags_and_types.append(
            (time_tag, get_day_type(time_tag, scenario, general_parameters))
        )

    return time_tags_and_types


def from_day_to_run(
    dataframe_to_clone: pd.DataFrame,
    run_range: pd.DatetimeIndex,
    day_start_hour: int,
    scenario: Box,
    general_parameters: Box,
) -> pd.DataFrame:
    '''
    Clones dataframe for a day (with zero at day start) for
    the whole run.
    '''

    # We need to roll the values so that they start at midnight
    rolled_values: ty.List[np.ndarray] = [
        np.roll(dataframe_to_clone[column], day_start_hour)
        for column in dataframe_to_clone.columns
    ]

    rolled_dataframe_to_clone: pd.DataFrame = pd.DataFrame()
    for column, column_values in zip(
        dataframe_to_clone.columns, rolled_values
    ):
        rolled_dataframe_to_clone[column] = column_values

    SECONDS_PER_HOUR: int = int(general_parameters.time.SECONDS_PER_HOUR)
    HOURS_IN_A_DAY: int = int(general_parameters.time.HOURS_IN_A_DAY)
    run_number_of_seconds: float = (
        run_range[-1] - run_range[0]
    ).total_seconds()
    run_days: int = math.ceil(
        run_number_of_seconds / (SECONDS_PER_HOUR * HOURS_IN_A_DAY)
    )
    run_dataframe: pd.DataFrame = pd.DataFrame()
    run_dataframe = pd.concat(
        [rolled_dataframe_to_clone] * run_days, ignore_index=True
    )

    # We create an extended run range, which includes all hours in the days
    # of the range (i.e. hours before the run starts and after it ends)
    extended_run_start: datetime.datetime = datetime.datetime(
        year=run_range[0].year,
        month=run_range[0].month,
        day=run_range[0].day,
        hour=0,
    )
    day_after_end_run: datetime.datetime = run_range[-1] + datetime.timedelta(
        days=1
    )
    extended_run_end: datetime.datetime = datetime.datetime(
        year=day_after_end_run.year,
        month=day_after_end_run.month,
        day=day_after_end_run.day,
        hour=0,
    )
    run_parameters: Box = scenario.run
    run_frequency_parameters: Box = run_parameters.frequency
    run_frequency_size: int = run_frequency_parameters.size
    run_frequency_type: str = run_frequency_parameters.type
    run_frequency: str = f'{run_frequency_size}{run_frequency_type}'
    extended_run_range: pd.DatetimeIndex = pd.date_range(
        start=extended_run_start,
        end=extended_run_end,
        freq=run_frequency,
        inclusive='left',
    )
    run_dataframe['Time Tag'] = extended_run_range

    # We then cut the parts that are ot in the run
    run_dataframe = run_dataframe[run_dataframe['Time Tag'] <= run_range[-1]]
    run_dataframe = run_dataframe[run_dataframe['Time Tag'] >= run_range[0]]
    run_dataframe = run_dataframe.set_index('Time Tag')

    return run_dataframe


if __name__ == '__main__':
    case_name = 'Mopo'
    test_scenario_name: str = 'XX_car'
    scenario_file_name: str = (
        f'scenarios/{case_name}/{test_scenario_name}.toml'
    )
    scenario: Box = Box(cook.parameters_from_TOML(scenario_file_name))
    scenario.name = test_scenario_name
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: Box = Box(
        cook.parameters_from_TOML(general_parameters_file_name)
    )
    run_range, run_hour_numbers, display_range = get_time_range(
        scenario, general_parameters
    )
    time_stamped_dataframe: pd.DataFrame = get_time_stamped_dataframe(
        scenario, general_parameters
    )
    print(run_range)
    print(run_hour_numbers)
    print(time_stamped_dataframe.iloc[68:77])
