from pathlib import Path

from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print

from ChaProEV.stochastic_new.define import User, get_users_pool
from ChaProEV.stochastic_new.monte_carlo import MonteCarlo, RandomGenerators


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


@cook.function_timer
def run_scenario(scenario: Box) -> None:
    monte_carlo_definitions: Box = scenario.monte_carlo

    monte_carlo: MonteCarlo = MonteCarlo(
        use_seed=monte_carlo_definitions.use_seed,
        seed=monte_carlo_definitions.seed,
    )
    random_generators: RandomGenerators = RandomGenerators.create_generators(
        monte_carlo=monte_carlo
    )

    users_pool: list[User] = get_users_pool(
        scenario=scenario, random_generator=random_generators.define
    )
    for user in users_pool:
        print(user.ID)
        print(user.activities.commuting_weekday_numbers)
        print(user.activities.leisure_trip_weekday_numbers)
        print(user.activities.holiday_trip_week_numbers)
        print(user.activities.weekday_occurrences_holiday_trips_outward)
        print(user.activities.weekday_occurrences_holiday_trips_back)
        print(user.activities.weekend_trip_week_numbers)
        print(user.activities.weekday_occurrences_weekend_trips)


@cook.function_timer
def run_ChaProEV(case_name: str) -> None:
    raise NotImplementedError


if __name__ == '__main__':

    case_name: str = 'plus'
    run_ChaProEV(case_name=case_name)
