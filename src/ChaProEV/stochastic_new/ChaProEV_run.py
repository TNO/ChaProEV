import uuid
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

import numpy as np
import polars as pl
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print

from ChaProEV.stochastic_new.benchmark import benchmark
from ChaProEV.stochastic_new.charging import compute_fleet_charging
from ChaProEV.stochastic_new.define import User, get_users_pool
from ChaProEV.stochastic_new.grid import LocalGrid
from ChaProEV.stochastic_new.monte_carlo import MonteCarlo, RandomGenerators
from ChaProEV.stochastic_new.time import TimeConstants, TimeRange

# def print_memory(label: str) -> None:
#     process: psutil.Process = psutil.Process(os.getpid())
#     memory_gb: float = process.memory_info().rss / 1024**3
#     print(f'{label}: {memory_gb:.2f} GB')


def compute_EV_matching(
    local_grid: LocalGrid,
    users_by_ID: dict[uuid.UUID, User],
    time_ranges: TimeRange,
    scenario: Box,
    grid_parameters: Box,
) -> None:
    '''
    Match residential EV charging demand to power lines.

    For each power line, aggregate the power drawn from the grid by EVs
    charging at home. Add this EV demand to the line's EV-demand-matching
    DataFrame and combine it with non-EV demand to determine whether
    the line capacity is exceeded at each timestep.

    For overloaded timesteps, also calculate the additional capacity required
    to accommodate the total demand. The results are stored in each power
    line's EV-demand-matching DataFrame.
    '''

    for power_line in local_grid.power_lines:
        line_EV_demand_from_grid: pl.Series = pl.Series(
            np.zeros(len(time_ranges.run_stamps))
        )
        print(line_EV_demand_from_grid.sum())
        for user_ID in power_line.EV_users:

            home_power: pl.Series = (
                users_by_ID[user_ID]
                .charge.with_columns(
                    pl.when(
                        pl.col(scenario.charging_dataframe.location_header)
                        == grid_parameters.home_location_name
                    )
                    .then(
                        pl.col(
                            scenario.charging_dataframe.power_from_grid_header  # noqa:E501
                        )
                    )
                    .otherwise(0.0)
                    .alias('home_power')
                )
                .get_column('home_power')
            )

            line_EV_demand_from_grid += home_power
        non_EV_header: str = (
            grid_parameters.EV_demand_matching_DF.non_EV_demand_header
        )
        EV_header: str = grid_parameters.EV_demand_matching_DF.EV_demand_header
        capacity_exceeded_header: str = (
            grid_parameters.EV_demand_matching_DF.capacity_exceeded_header
        )
        extra_capacity_needed_header: str = (
            grid_parameters.EV_demand_matching_DF.extra_capacity_needed_header  # noqa:E501
        )

        # First add the EV demand because subsequent
        # alculations depend on it.
        power_line.EV_demand_matching = (
            power_line.EV_demand_matching.with_columns(
                line_EV_demand_from_grid.alias(EV_header),
            )
        )

        # Determine whether total demand exceeds the line capacity.
        power_line.EV_demand_matching = (
            power_line.EV_demand_matching.with_columns(
                (
                    pl.col(non_EV_header) + pl.col(EV_header)
                    > power_line.capacity_kW
                ).alias(capacity_exceeded_header),
                pl.when(
                    pl.col(non_EV_header) + pl.col(EV_header)
                    > power_line.capacity_kW
                )
                .then(
                    pl.col(non_EV_header)
                    + pl.col(EV_header)
                    - power_line.capacity_kW
                )
                .otherwise(0.0)
                .alias(extra_capacity_needed_header),
            )
        )


def get_excesses(
    local_grid: LocalGrid, grid_parameters: Box
) -> CapacityOverloads:
    """
    Calculate residential power-line congestion statistics.

    For each timestep, determine how many power lines exceed their capacity and
    whether at least one line is overloaded. Aggregate these results over the
    complete simulation and by hour of day.

    The calculated statistics distinguish between the average number of
    overloaded lines per timestep and the proportion of timesteps during which
    at least one line is overloaded.
    """

    capacity_exceeded_series: list[pl.Series] = [
        power_line.EV_demand_matching.get_column(
            grid_parameters.EV_demand_matching_DF.capacity_exceeded_header
        ).cast(pl.Int64)
        for power_line in local_grid.power_lines
    ]

    # Determine the number of overloaded power lines at each timestep.
    excess_occurrences: pl.Series = capacity_exceeded_series[0]

    for series in capacity_exceeded_series[1:]:
        excess_occurrences = excess_occurrences + series

    # Calculate statistics over the complete simulation.
    average_overloaded_lines: float = sum(excess_occurrences) / len(
        excess_occurrences
    )

    proportion_timesteps_with_overload: float = sum(
        excess_occurrences > 0
    ) / len(excess_occurrences)

    time_header = grid_parameters.EV_demand_matching_DF.time_header

    # Calculate the same congestion statistics by hour of day.
    excess_per_hour: pl.DataFrame = (
        pl.DataFrame(
            {
                'time': local_grid.power_lines[
                    0
                ].EV_demand_matching.get_column(time_header),
                'excess_occurrences': excess_occurrences,
            }
        )
        .with_columns(pl.col('time').dt.hour().alias('hour'))
        .group_by('hour')
        .agg(
            pl.col('excess_occurrences').sum().alias('excess_occurrences'),
            (pl.col('excess_occurrences').sum() / pl.len()).alias(
                'average_overloaded_lines'
            ),
            (pl.col('excess_occurrences') > 0)
            .sum()
            .alias('timesteps_with_overload'),
            ((pl.col('excess_occurrences') > 0).sum() / pl.len()).alias(
                'proportion_timesteps_with_overload'
            ),
        )
        .sort('hour')
    )

    return CapacityOverloads(
        excess_occurrences == excess_occurrences,
        average_overloaded_lines=average_overloaded_lines,
        proportion_timesteps_with_overload=proportion_timesteps_with_overload,
        excess_per_hour=excess_per_hour,
    )


@dataclass
class CapacityOverloads:
    excess_occurrences: pl.Series
    average_overloaded_lines: float
    proportion_timesteps_with_overload: float
    excess_per_hour: pl.DataFrame


@dataclass
class UsersPoolStatistics:
    average_kilometrage: float
    average_consumption_kWh: float
    average_purchased_electricity_kWh: float
    average_purchased_electricity_kWh_per_location_type: dict[str, float]
    average_charge_spending_eur: float
    average_charge_spending_eur_per_location_type: dict[str, float]
    average_electricity_sold_kWh: float
    average_discharge_income_eur: float
    pool_average_hourly_power_from_grid_kW: pl.Series
    pool_average_hourly_power_from_grid_kW_per_location_type: dict[
        str, pl.Series
    ]
    pool_average_electricity_costs_eur_kWh: float
    pool_average_travel_costs_eur_km: float
    capacity_overloads: CapacityOverloads | None = None

    @classmethod
    def compute(
        cls,
        *,
        users_pool: list[User],
        location_types: list[str],
    ) -> UsersPoolStatistics:
        average_kilometrage: float = fmean(
            user.run_metrics.kilometrage for user in users_pool
        )

        average_consumption_kWh: float = fmean(
            user.run_metrics.consumption_kWh for user in users_pool
        )

        actual_location_types = {
            location_type
            for user in users_pool
            for location_type in user.run_metrics.purchased_electricity_kWh_per_location_type  # noqa:E501
        }
        assert actual_location_types <= set(
            location_types
        ), f'Missing location types: {actual_location_types - set(location_types)}'  # noqa:E501

        average_purchased_electricity_kWh: float = fmean(
            user.run_metrics.purchased_electricity_kWh for user in users_pool
        )
        average_purchased_electricity_kWh_per_location_type: dict[
            str, float
        ] = {
            location_type: fmean(
                user.run_metrics.purchased_electricity_kWh_per_location_type.get(  # noqa:E501
                    location_type, 0.0
                )
                for user in users_pool
            )
            for location_type in location_types
        }
        average_charge_spending_eur: float = fmean(
            user.run_metrics.charge_spending_eur for user in users_pool
        )
        average_charge_spending_eur_per_location_type: dict[str, float] = {
            location_type: fmean(
                user.run_metrics.charge_spending_eur_per_location_type.get(
                    location_type, 0.0
                )
                for user in users_pool
            )
            for location_type in location_types
        }

        average_electricity_sold_kWh: float = fmean(
            user.run_metrics.electricity_sold_kWh for user in users_pool
        )

        average_discharge_income_eur: float = fmean(
            user.run_metrics.discharge_income_eur for user in users_pool
        )
        pool_average_electricity_costs_eur_kWh: float = fmean(
            user.run_metrics.average_electricity_costs_eur_kWh
            for user in users_pool
        )
        pool_average_travel_costs_eur_km: float = fmean(
            user.run_metrics.average_travel_costs_eur_km for user in users_pool
        )
        pool_average_hourly_power_from_grid_kW: pl.Series = (
            pl.DataFrame(
                [
                    user.run_metrics.average_hourly_power_from_grid_kW.rename(  # noqa: E501
                        str(user_index)
                    )
                    for user_index, user in enumerate(users_pool)
                ]
            )
            .mean_horizontal()
            .rename('Average hourly power from grid (kW)')
        )
        pool_average_hourly_power_from_grid_kW_per_location_type: dict[
            str, pl.Series
        ] = {
            location_type: (
                pl.DataFrame(
                    [
                        user.run_metrics.average_hourly_power_from_grid_kW_per_location_type.get(  # noqa:E501
                            location_type, pl.Series(values=[0.0] * 24)
                        ).rename(  # noqa: E501
                            str(user_index)
                        )
                        for user_index, user in enumerate(users_pool)
                    ]
                )
                .mean_horizontal()
                .rename('Average hourly power from grid (kW)')
            )
            for location_type in location_types
        }

        return cls(
            average_kilometrage=average_kilometrage,
            average_consumption_kWh=average_consumption_kWh,
            average_purchased_electricity_kWh=(
                average_purchased_electricity_kWh
            ),
            average_purchased_electricity_kWh_per_location_type=(
                average_purchased_electricity_kWh_per_location_type
            ),
            average_charge_spending_eur=average_charge_spending_eur,
            average_charge_spending_eur_per_location_type=(
                average_charge_spending_eur_per_location_type
            ),
            average_electricity_sold_kWh=average_electricity_sold_kWh,
            average_discharge_income_eur=average_discharge_income_eur,
            pool_average_hourly_power_from_grid_kW=(
                pool_average_hourly_power_from_grid_kW
            ),
            pool_average_electricity_costs_eur_kWh=(
                pool_average_electricity_costs_eur_kWh
            ),
            pool_average_travel_costs_eur_km=pool_average_travel_costs_eur_km,
            pool_average_hourly_power_from_grid_kW_per_location_type=pool_average_hourly_power_from_grid_kW_per_location_type,  # noqa:E501
        )


def test_run() -> None:

    scenario_name: str = 'cars'
    case_name: str = 'plus'
    scenario_path: Path = (
        Path('scenarios') / case_name / f'{scenario_name}.toml'
    )

    scenario: Box = cook.parameters_from_TOML(scenario_path)
    scenario.name = scenario_name
    scenario.case_name = case_name
    run_scenario(scenario)
    print('[magenta] Document pickling as a cache of sorts with warnings')
    print('Check and document batt and grid')
    print('Then add conflict counting')
    print('STeps towards sessions')
    print('session demand and counter-proposals')
    print('Maybe queues and alts')
    print('New metrics')
    print('AMount of users sliders (and display EV users per HH)')


@cook.function_timer
def run_scenario(scenario: Box) -> UsersPoolStatistics:

    time_constants: TimeConstants = TimeConstants.read_parameters(
        time_parameters=scenario.time
    )
    run_parameters: Box = scenario.run
    time_ranges: TimeRange = TimeRange.set_ranges(
        run_parameters=run_parameters,
        time_constants=time_constants,
    )
    monte_carlo_definitions: Box = scenario.monte_carlo

    monte_carlo: MonteCarlo = MonteCarlo(
        use_seed=monte_carlo_definitions.use_seed,
        seed=monte_carlo_definitions.seed,
    )
    random_generators: RandomGenerators = RandomGenerators.create_generators(
        monte_carlo=monte_carlo
    )

    users_pool = get_users_pool(
        scenario=scenario,
        random_generators=random_generators,
        time_ranges=time_ranges,
        time_constants=time_constants,
    )
    users_by_ID: dict[uuid.UUID, User] = {user.ID: user for user in users_pool}

    # We check if we include the residential grid congestion
    local_grid: LocalGrid | None = None
    grid_parameters: Box = scenario.grid
    if grid_parameters.include_residential_grid_congestion:
        local_grid = LocalGrid.initialise(
            users_pool=users_pool,
            grid_parameters=grid_parameters,
            scenario=scenario,
            time_ranges=time_ranges,
            time_constants=time_constants,
            random_generator=random_generators.local_grid,
        )
        # for line_index in range(len(local_grid.power_lines)):
        #     print(line_index)
        #     min_demand = min(
        #         local_grid.power_lines[line_index].non_EV_demand_profile
        #     )
        #     mean_demand = sum(
        #         local_grid.power_lines[line_index].non_EV_demand_profile
        #     ) / (8760 * 60)
        #     max_demand = max(
        #         local_grid.power_lines[line_index].non_EV_demand_profile
        #     )
        #     capacity = local_grid.power_lines[line_index].capacity_kW
        #     print(min_demand, mean_demand, max_demand)
        #     print(
        #         capacity - min_demand,
        #         capacity - mean_demand,
        #         capacity - max_demand,
        #     )

    # Residential-grid creation may have changed home connectivity for users
    # with street parking. Therefore, the charging DataFrame can only be
    # created after the local grid has been initialised.
    for user in users_pool:
        user.create_charging_dataframe(
            charging_settings=scenario.charging_dataframe,
            random_generator=random_generators.charging,
        )

    # line_non_EV_power_kW: npt.NDArray[np.float64] = (
    #     get_non_EV_power_demand_per_line_kW(
    #         lines=lines, amount_of_time_stamps=len(time_ranges.run_stamps)
    #     )
    # )

    # grid: Grid = Grid.create(
    #     transformers_pool=transformers_pool,
    #     line_non_EV_power_kW=line_non_EV_power_kW,
    #     amount_of_time_steps=len(time_ranges.run_stamps),
    # )

    HOURS_IN_A_DAY: int = time_constants.HOURS_IN_A_DAY

    MINUTES_PER_HOUR: int = time_constants.MINUTES_PER_HOUR

    if time_ranges.frequency_type != 'm':
        raise ValueError('You need to use minutes for the frequency!')
    run_frequency_size: int = time_ranges.frequency_size
    run_time_resolution_hours: float = run_frequency_size / MINUTES_PER_HOUR

    users_pool = compute_fleet_charging(
        users_pool=users_pool,
        scenario=scenario,
        run_time_resolution_hours=run_time_resolution_hours,
        HOURS_IN_A_DAY=HOURS_IN_A_DAY,
        run_time_stamps=time_ranges.run_stamps.to_list(),
    )

    if local_grid is not None:
        compute_EV_matching(
            local_grid=local_grid,
            users_by_ID=users_by_ID,
            time_ranges=time_ranges,
            scenario=scenario,
            grid_parameters=grid_parameters,
        )

    users_pool_statistics: UsersPoolStatistics = UsersPoolStatistics.compute(
        users_pool=users_pool, location_types=scenario.metrics.location_types
    )

    if local_grid is not None:

        users_pool_statistics.capacity_overloads = get_excesses(
            local_grid=local_grid, grid_parameters=grid_parameters
        )

        with pl.Config(tbl_rows=26):
            print(users_pool_statistics.capacity_overloads)

    # with pl.Config(tbl_rows=26):
    #     print(users_pool_statistics)

    return users_pool_statistics


def run_benchmark() -> None:
    benchmark(test_run)


@cook.function_timer
def run_ChaProEV(case_name: str) -> None:
    raise NotImplementedError


if __name__ == '__main__':

    case_name: str = 'plus'
    run_ChaProEV(case_name=case_name)
    # MOdel maintenance
    # iterate on time stamps too if we need time
