from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print

from ChaProEV.stochastic.monte_carlo import RandomGenerators
from ChaProEV.stochastic.define import (
    TimeRange,
    Trip,
    TripStep,
    Vehicle,
    define_user,
)


def create_trip_step_record(
    *,
    trip_date: date,
    trip_step: TripStep,
    run_time_resolution_hours: float,
) -> dict[str, object]:
    midnight: datetime = datetime.combine(date=trip_date, time=time.min)

    start_step: int = int(
        np.floor(trip_step.start_hour / run_time_resolution_hours + 0.5)
    )
    # Using floor + 0.5 raather than round to consistently round up instead
    # of having rounding changingon evenness of value
    end_step: int = int(
        np.floor(trip_step.end_hour / run_time_resolution_hours + 0.5)
    )
    # Using floor + 0.5 raather than round to consistently round up instead
    # of having rounding changingon evenness of value
    number_of_steps: int = max(1, end_step - start_step)

    step_start: datetime = midnight + timedelta(
        hours=start_step * run_time_resolution_hours
    )
    step_end: datetime = midnight + timedelta(
        hours=(start_step + number_of_steps) * run_time_resolution_hours
    )

    return {
        'Step start': step_start,
        'Step end': step_end,
        'Location': trip_step.location_name,
        'Kilometers driven': trip_step.length_kilometers / number_of_steps,
    }


@cook.function_timer
def compute_mobility_matrix(
    *,
    time_ranges: TimeRange,
    run_trips: pl.Series,
    base_trips: dict[str, dict[str, Trip]],
    scenario: Box,
    vehicle: Vehicle,
) -> pl.DataFrame:
    MINUTES_PER_HOUR: int = scenario.time.MINUTES_PER_HOUR

    if scenario.run.frequency.type != 'm':
        raise ValueError('You need to use minutes for the frequency!')
    run_frequency_size: int = scenario.run.frequency.size
    run_time_resolution_hours: float = run_frequency_size / MINUTES_PER_HOUR

    trip_step_records: list[dict[str, object]] = []
    base: str = 'home'

    this_base_trips: dict[str, Trip] = base_trips[base]
    # print(run_trips)
    print('Do it per base and add transitions!!!')
    exit()
    for trip_date, trip_name in zip(
        time_ranges.run_dates, run_trips, strict=True
    ):
        trip: Trip = this_base_trips[trip_name]
        for trip_step in trip.trip_steps:
            trip_step_record: dict[str, object] = create_trip_step_record(
                trip_date=trip_date,
                trip_step=trip_step,
                run_time_resolution_hours=run_time_resolution_hours,
            )
            trip_step_records.append(trip_step_record)

    mobility_matrix: pl.DataFrame = time_ranges.run_stamps.to_frame(
        'Time Stamp'
    ).with_columns(
        pl.lit(base).alias('Location'), pl.lit(0.0).alias('Kilometers driven')
    )

    if not trip_step_records:
        return mobility_matrix

    trip_steps: pl.DataFrame = pl.DataFrame(trip_step_records)

    trip_step_stamps: pl.DataFrame = (
        trip_steps.with_columns(
            pl.datetime_ranges(
                start='Step start',
                end='Step end',
                interval=f'{run_frequency_size}{scenario.run.frequency.type}',
                closed='left',
            ).alias('Time Stamp')
        )
        .explode('Time Stamp')
        .select('Time Stamp', 'Location', 'Kilometers driven')
    )
    # Polars emits a deprecation warning about empty datetime ranges.
    # This should not affect us because number_of_steps >= 1.

    duplicate_time_stamps: pl.DataFrame = (
        trip_step_stamps.group_by('Time Stamp').len().filter(pl.col('len') > 1)
    )

    if duplicate_time_stamps.height > 0:
        raise ValueError(
            'Multiple trip steps modify the same time stamp.',
            'You need to resolve overlaps explicitely',
        )

    mobility_matrix = (
        mobility_matrix.join(
            trip_step_stamps,
            on='Time Stamp',
            how='left',
            suffix='_trip',
            # maintain_order='left',
        )
        .with_columns(
            pl.coalesce('Location_trip', 'Location').alias('Location'),
            pl.coalesce('Kilometers driven_trip', 'Kilometers driven').alias(
                'Kilometers driven'
            ),
        )
        .drop('Location_trip', 'Kilometers driven_trip')  # .sort('Time Stamp')
    )
    mobility_matrix = mobility_matrix.with_columns(
        (pl.col('Kilometers driven') * vehicle.consumption_kWh_km).alias(
            'Consumption (kWh)'
        )
    )

    mobility_matrix = (
        mobility_matrix.with_columns(
            (pl.col('Location') != pl.col('Location').shift(1))
            .fill_null(True)
            .cum_sum()
            .alias('location_run_ID')
        )
        .with_columns(
            pl.len().over('location_run_ID').alias('location_run_rows')
        )
        .with_columns(
            (pl.col('location_run_rows') * run_time_resolution_hours).alias(
                'Time at location (hours)'
            )
        )
        .drop('location_run_ID', 'location_run_rows')
    )
    return mobility_matrix


if __name__ == '__main__':
    scenario_path: Path = Path('scenarios/plus/test.toml')
    scenario: Box = cook.parameters_from_TOML(scenario_path)
    run_parameters: Box = scenario.run

    random_generators: RandomGenerators = RandomGenerators.create_generators(
        scenario=scenario
    )

    (
        vehicle,
        time_ranges,
        run_trips,
        base_trips,
        locations,
    ) = define_user(
        scenario=scenario, random_generator=random_generators.define
    )

    mobility_matrix: pl.DataFrame = compute_mobility_matrix(
        vehicle=vehicle,
        time_ranges=time_ranges,
        run_trips=run_trips,
        base_trips=base_trips,
        scenario=scenario,
    )

    print(mobility_matrix['Kilometers driven'].sum())
    print(mobility_matrix['Consumption (kWh)'].sum())
