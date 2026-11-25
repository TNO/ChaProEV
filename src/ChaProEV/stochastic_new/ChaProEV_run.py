import uuid
from pathlib import Path

from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print

from ChaProEV.stochastic_new.benchmark import benchmark
from ChaProEV.stochastic_new.charging import compute_fleet_charging
from ChaProEV.stochastic_new.define import User, get_users_pool
from ChaProEV.stochastic_new.grid import LocalGrid, compute_EV_matching
from ChaProEV.stochastic_new.metrics import (
    CapacityOverloads,
    UsersPoolStatistics,
)
from ChaProEV.stochastic_new.monte_carlo import MonteCarlo, RandomGenerators
from ChaProEV.stochastic_new.time import TimeConstants, TimeRange


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
    print('Price sliders with high/low price')
    print('Steps towards discharge')
    print('Price elasticity for charging (needs cost of session)')
    print('Do something with desirabiliy too?')
    print('Slide grid elements?')
    print('Invert color for delta for overload? Fro all?')
    print('RUn ChaProEV thing')


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

    # Residential-grid creation may have changed home connectivity for users
    # with street parking. Therefore, the charging DataFrame can only be
    # created after the local grid has been initialised.
    for user in users_pool:
        user.create_charging_dataframe(
            charging_settings=scenario.charging_dataframe,
            random_generator=random_generators.charging,
        )

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

        users_pool_statistics.capacity_overloads = (
            CapacityOverloads.get_excesses(
                local_grid=local_grid, grid_parameters=grid_parameters
            )
        )

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
