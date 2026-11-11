from dataclasses import dataclass
from datetime import date, datetime

import polars as pl
from box import Box


@dataclass
class TimeConstants:
    SECONDS_PER_HOUR: int
    MINUTES_PER_HOUR: int
    HOURS_IN_A_DAY: int
    MONTHS_IN_A_YEAR: int
    MAX_DAYS_IN_A_MONTH: int
    DAYS_IN_A_YEAR: float
    DAYS_IN_A_WEEK: int
    WEEKS_IN_A_YEAR: float
    first_hour_number: int
    first_week_index: int
    last_week_index: int
    weekend_day_numbers: list[int]
    holiday_weeks: list[int]
    number_of_holiday_weeks: int
    # We need to provide the number of holiday weeks separately,
    # as counting the elements of the list above might not work, such as
    # when the above list contains weeks 1 and 53 (which just represent
    # the fact that years don't necessarily start and/or end at the start/end
    # of a week).

    @classmethod
    def read_parameters(cls, *, time_parameters: Box) -> TimeConstants:
        holiday_weeks: list[int] = time_parameters.holiday_weeks

        return cls(
            SECONDS_PER_HOUR=time_parameters.SECONDS_PER_HOUR,
            MINUTES_PER_HOUR=time_parameters.MINUTES_PER_HOUR,
            HOURS_IN_A_DAY=time_parameters.HOURS_IN_A_DAY,
            MONTHS_IN_A_YEAR=time_parameters.MONTHS_IN_A_YEAR,
            MAX_DAYS_IN_A_MONTH=time_parameters.MAX_DAYS_IN_A_MONTH,
            DAYS_IN_A_YEAR=time_parameters.DAYS_IN_A_YEAR,
            DAYS_IN_A_WEEK=time_parameters.DAYS_IN_A_WEEK,
            WEEKS_IN_A_YEAR=time_parameters.DAYS_IN_A_YEAR
            / time_parameters.DAYS_IN_A_WEEK,
            first_hour_number=time_parameters.first_hour_number,
            first_week_index=time_parameters.first_week_index,
            last_week_index=time_parameters.last_week_index,
            weekend_day_numbers=time_parameters.weekend_day_numbers,
            holiday_weeks=holiday_weeks,
            number_of_holiday_weeks=time_parameters.number_of_holiday_weeks,
        )


@dataclass
class TimeRange:
    '''
    The time ranges used for dates and timestamps, both for
    computation and display.

    '''

    run_dates: pl.Series
    display_dates: pl.Series
    run_stamps: pl.Series
    display_stamps: pl.Series
    day_types: pl.Series
    frequency: str
    frequency_type: str
    frequency_size: int

    @classmethod
    def set_ranges(
        cls,
        *,
        run_parameters: Box,
        time_constants: TimeConstants,
    ) -> TimeRange:
        start: Box = run_parameters.start
        end: Box = run_parameters.end

        if (
            start.hour != 0
            or start.minute != 0
            or end.hour != 0
            or end.minute != 0
        ):
            raise ValueError(
                'The run must start and end at midnight because trips are '
                'assigned per complete run day. The display period may have '
                'different start and end times, but the underlying run must '
                'be extended to start and end at midnight.'
            )

        display_start: Box = run_parameters.display_start
        display_end: Box = run_parameters.display_end
        run_frequency_settings: Box = run_parameters.frequency
        display_frequency_settings: Box = run_parameters.display_frequency

        run_frequency: str = (
            f'{run_frequency_settings.size}{run_frequency_settings.type}'
        )
        display_frequency: str = (
            f'{display_frequency_settings.size}'
            f'{display_frequency_settings.type}'
        )
        if (
            run_frequency_settings.size <= 0
            or display_frequency_settings.size <= 0
        ):
            raise ValueError(
                f'Both {run_frequency_settings.size=} and '
                f'{display_frequency_settings.size=} must be positive.'
            )

        start_date: date = date(
            year=start.year, month=start.month, day=start.day
        )
        end_date: date = date(year=end.year, month=end.month, day=end.day)

        start_datetime: datetime = datetime(
            year=start.year,
            month=start.month,
            day=start.day,
            hour=start.hour,
            minute=start.minute,
        )
        end_datetime: datetime = datetime(
            year=end.year,
            month=end.month,
            day=end.day,
            hour=end.hour,
            minute=end.minute,
        )
        display_start_datetime: datetime = datetime(
            year=display_start.year,
            month=display_start.month,
            day=display_start.day,
            hour=display_start.hour,
            minute=display_start.minute,
        )
        display_end_datetime: datetime = datetime(
            year=display_end.year,
            month=display_end.month,
            day=display_end.day,
            hour=display_end.hour,
            minute=display_end.minute,
        )
        if start_datetime >= end_datetime:
            raise ValueError(
                f'{start_datetime=} must be before {end_datetime=}'
            )
        if display_start_datetime >= display_end_datetime:
            raise ValueError(
                f'{display_start_datetime=} must be before '
                f'{display_end_datetime=}'
            )

        if display_start_datetime < start_datetime:
            raise ValueError(
                f'{display_start_datetime=} must be later or '
                f'at the same time as {start_datetime=}'
            )
        if display_end_datetime > end_datetime:
            raise ValueError(
                f'{display_end_datetime=} must be earlier or '
                f'at the same time as {end_datetime=}'
            )

        run_dates: pl.Series = pl.date_range(
            start=start_date,
            end=end_date,
            eager=True,
            closed='left',
        ).rename('date')

        run_stamps: pl.Series = pl.datetime_range(
            start=start_datetime,
            end=end_datetime,
            interval=run_frequency,
            eager=True,
            closed='left',
        ).rename('timestamp')
        display_stamps: pl.Series = pl.datetime_range(
            start=display_start_datetime,
            end=display_end_datetime,
            interval=display_frequency,
            eager=True,
            closed='left',
        ).rename('timestamp')
        display_dates: pl.Series = (
            display_stamps.dt.date().unique(maintain_order=True).rename('date')
        )
        # Derived from display_stamps because a display range with non-midnight
        # boundaries may cover more dates than an equivalent closed-left
        # date range.

        day_types: pl.Series = pl.DataFrame({'date': run_dates}).with_columns(
            pl.concat_str(
                [
                    pl.when(
                        pl.col('date')
                        .dt.weekday()
                        .is_in(time_constants.weekend_day_numbers)
                    )
                    .then(pl.lit('weekend'))
                    .otherwise(pl.lit('weekday')),
                    pl.lit('_in_'),
                    pl.when(
                        pl.col('date')
                        .dt.week()
                        .is_in(time_constants.holiday_weeks)
                    )
                    .then(pl.lit('holiday'))
                    .otherwise(pl.lit('work')),
                    pl.lit('_week'),
                ]
            ).alias('day_type')
        )['day_type']

        return cls(
            run_dates=run_dates,
            display_dates=display_dates,
            run_stamps=run_stamps,
            display_stamps=display_stamps,
            day_types=day_types,
            frequency=run_frequency,
            frequency_type=run_frequency_settings.type,
            frequency_size=run_frequency_settings.size,
        )
