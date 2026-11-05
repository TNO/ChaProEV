from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

import polars as pl
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print

from ChaProEV.stochastic_new.charging import compute_charging
from ChaProEV.stochastic_new.define import User, get_users_pool
from ChaProEV.stochastic_new.monte_carlo import MonteCarlo, RandomGenerators


@dataclass
class UsersPoolStatistics:
    average_kilometrage: float
    average_consumption_kWh: float
    average_purchased_electricity_kWh: float
    average_charge_spending_eur: float
    average_electricity_sold_kWh: float
    average_discharge_income_eur: float
    pool_average_hourly_power_from_network_kW: pl.Series
    pool_average_electricity_costs_eur_kWh: float
    pool_average_travel_costs_eur_km: float

    @staticmethod
    def compute(*, users_pool: list[User]) -> UsersPoolStatistics:
        average_kilometrage: float = fmean(
            user.run_metrics.kilometrage for user in users_pool
        )

        average_consumption_kWh: float = fmean(
            user.run_metrics.consumption_kWh for user in users_pool
        )

        average_purchased_electricity_kWh: float = fmean(
            user.run_metrics.purchased_electricity_kWh for user in users_pool
        )
        average_charge_spending_eur: float = fmean(
            user.run_metrics.charge_spending_eur for user in users_pool
        )

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
        pool_average_hourly_power_from_network_kW: pl.Series = (
            pl.DataFrame(
                [
                    user.run_metrics.average_hourly_power_from_network_kW.rename(  # noqa: E501
                        str(user_index)
                    )
                    for user_index, user in enumerate(users_pool)
                ]
            )
            .mean_horizontal()
            .rename('Average hourly power from network (kW)')
        )

        return UsersPoolStatistics(
            average_kilometrage=average_kilometrage,
            average_consumption_kWh=average_consumption_kWh,
            average_purchased_electricity_kWh=(
                average_purchased_electricity_kWh
            ),
            average_charge_spending_eur=average_charge_spending_eur,
            average_electricity_sold_kWh=average_electricity_sold_kWh,
            average_discharge_income_eur=average_discharge_income_eur,
            pool_average_hourly_power_from_network_kW=(
                pool_average_hourly_power_from_network_kW
            ),
            pool_average_electricity_costs_eur_kWh=(
                pool_average_electricity_costs_eur_kWh
            ),
            pool_average_travel_costs_eur_km=pool_average_travel_costs_eur_km,
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


@cook.function_timer
def run_scenario(scenario: Box) -> UsersPoolStatistics:
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
        # print(user.locations)
        # input()
        # print(user.charge['Power drawn from network (kW)'].sum())
        # print(user.run_metrics)
        user.charge = compute_charging(
            charging_behaviour=user.charging_behaviour,
            charge=user.charge,
            charging_settings=scenario.charging_dataframe,
            vehicle=user.vehicle,
            scenario=scenario,
            locations=user.locations,
        )
        user.run_metrics.charge_update(
            charge_dataframe=user.charge,
            charging_settings=scenario.charging_dataframe,
            locations=user.locations
        )
        print(user.run_metrics)
        exit()
        # with pl.Config(tbl_rows=26):
        #     print(user.run_metrics)
        # exit()
        # print(user.ID)
        # print(user.run_metrics.charge_spending_eur)
        # print(
        #     user.run_metrics.charge_spending_eur
        #     / user.run_metrics.purchased_electricity_kWh
        # )

    users_pool_statistics: UsersPoolStatistics = UsersPoolStatistics.compute(
        users_pool=users_pool
    )
    with pl.Config(tbl_rows=26):
        print(users_pool_statistics)

    return users_pool_statistics


@cook.function_timer
def run_ChaProEV(case_name: str) -> None:
    raise NotImplementedError


if __name__ == '__main__':

    case_name: str = 'plus'
    run_ChaProEV(case_name=case_name)
