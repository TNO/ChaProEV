from dataclasses import dataclass
from itertools import repeat
from multiprocessing import Pool
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print
from tqdm.rich import tqdm

from ChaProEV.stochastic.charging import compute_charging, get_hourly_values
from ChaProEV.stochastic.define import define_user
from ChaProEV.stochastic.mobility import compute_mobility_matrix
from ChaProEV.stochastic.monte_carlo import MonteCarlo, RandomGenerators
from ChaProEV.stochastic.scenarios_module import load_scenarios


@dataclass
class Charge:
    time_stamps: pl.Series
    power_to_vehicle_kW: np.ndarray
    power_from_network_kW: np.ndarray
    charge_to_vehicle_kWh: np.ndarray
    charge_from_network_kWh: np.ndarray

    @staticmethod
    def from_dataframe(charging_dataframe: pl.DataFrame) -> Charge:
        power_to_vehicle_kW: np.ndarray = charging_dataframe[
            'Power to vehicle (kW)'
        ].to_numpy()
        power_from_network_kW: np.ndarray = charging_dataframe[
            'Power drawn from network (kW)'
        ].to_numpy()
        charge_to_vehicle_kWh: np.ndarray = charging_dataframe[
            'Charge to vehicle (kWh)'
        ].to_numpy()
        charge_from_network_kWh: np.ndarray = charging_dataframe[
            'Charge from network (kWh)'
        ].to_numpy()
        time_stamps: pl.Series = charging_dataframe['Time Stamp']

        return Charge(
            time_stamps=time_stamps,
            power_to_vehicle_kW=power_to_vehicle_kW,
            power_from_network_kW=power_from_network_kW,
            charge_to_vehicle_kWh=charge_to_vehicle_kWh,
            charge_from_network_kWh=charge_from_network_kWh,
        )

    def add_iteration(self, iteration_charge: Charge) -> Charge:
        power_to_vehicle_kW: np.ndarray = (
            self.power_to_vehicle_kW + iteration_charge.power_to_vehicle_kW
        )
        power_from_network_kW: np.ndarray = (
            self.power_from_network_kW + iteration_charge.power_from_network_kW
        )
        charge_from_network_kWh: np.ndarray = (
            self.charge_from_network_kWh
            + iteration_charge.charge_from_network_kWh
        )
        charge_to_vehicle_kWh: np.ndarray = (
            self.charge_to_vehicle_kWh + iteration_charge.charge_to_vehicle_kWh
        )

        return Charge(
            time_stamps=self.time_stamps,
            power_to_vehicle_kW=power_to_vehicle_kW,
            power_from_network_kW=power_from_network_kW,
            charge_to_vehicle_kWh=charge_to_vehicle_kWh,
            charge_from_network_kWh=charge_from_network_kWh,
        )

    def average(self, iterations: int) -> Charge:
        return Charge(
            time_stamps=self.time_stamps,
            power_to_vehicle_kW=self.power_to_vehicle_kW / iterations,
            power_from_network_kW=self.power_from_network_kW / iterations,
            charge_to_vehicle_kWh=self.charge_to_vehicle_kWh / iterations,
            charge_from_network_kWh=self.charge_from_network_kWh / iterations,
        )


def get_charging_quantities(
    scenario: Box, random_generators: RandomGenerators
) -> Charge:
    (
        charging_behaviour,
        vehicle,
        time_ranges,
        run_trips,
        base_trips,
        locations,
        activity_parameters,
        time_constants,
    ) = define_user(
        scenario=scenario, random_generator=random_generators.define
    )

    mobility_matrix: pl.DataFrame = compute_mobility_matrix(
        vehicle=vehicle,
        run_trips=run_trips,
        base_trips=base_trips,
        time_ranges=time_ranges,
    )

    charging_dataframe = compute_charging(
        charging_behaviour=charging_behaviour,
        vehicle=vehicle,
        mobility_matrix=mobility_matrix,
        locations=locations,
        random_generator=random_generators.charging,
        time_ranges=time_ranges,
        time_constants=time_constants,
    )

    return Charge.from_dataframe(charging_dataframe=charging_dataframe)


def get_iterated_charging_dataframe(
    scenario: Box,
    iterations: int,
    random_generators: RandomGenerators,
) -> pl.DataFrame:
    cumulative_charge: Charge = get_charging_quantities(
        scenario=scenario, random_generators=random_generators
    )

    for _ in range(iterations - 1):
        iteration_charge: Charge = get_charging_quantities(
            scenario=scenario, random_generators=random_generators
        )
        cumulative_charge = cumulative_charge.add_iteration(
            iteration_charge=iteration_charge
        )

    average_charge: Charge = cumulative_charge.average(iterations=iterations)
    charging_dataframe: pl.DataFrame = pl.DataFrame(
        {'Time Stamp': cumulative_charge.time_stamps}
    )

    charging_dataframe = charging_dataframe.with_columns(
        pl.Series('Power to vehicle (kW)', average_charge.power_to_vehicle_kW),
        pl.Series(
            'Power drawn from network (kW)',
            average_charge.power_from_network_kW,
        ),
        pl.Series(
            'Charge to vehicle (kWh)', average_charge.charge_to_vehicle_kWh
        ),
        pl.Series(
            'Charge from network (kWh)', average_charge.charge_from_network_kWh
        ),
    )

    return charging_dataframe


@cook.function_timer
def run_ChaProEV_scenario(scenario: Box) -> tuple[pl.DataFrame, pl.DataFrame]:
    monte_carlo_definitions: Box = scenario.monte_carlo
    monte_carlo: MonteCarlo = MonteCarlo(
        use_seed=monte_carlo_definitions.use_seed,
        seed=monte_carlo_definitions.seed,
        iterations=monte_carlo_definitions.iterations,
    )
    random_generators: RandomGenerators = RandomGenerators.create_generators(
        monte_carlo=monte_carlo
    )
    iterations: int = monte_carlo.iterations
    if iterations < 1:
        raise ValueError('You need at least one iteration')
    charging_dataframe: pl.DataFrame = get_iterated_charging_dataframe(
        scenario=scenario,
        iterations=iterations,
        random_generators=random_generators,
    )
    hourly_values: pl.DataFrame = get_hourly_values(charging_dataframe)

    return charging_dataframe, hourly_values


@cook.function_timer
def run_ChaProEV(case_name: str) -> None:

    general_parameters_file_name: Path = Path('ChaProEV.toml')
    general_parameters: Box = cook.parameters_from_TOML(
        general_parameters_file_name
    )

    set_amount_of_processes: bool = (
        general_parameters.parallel_processing.set_amount_of_processes
    )
    if set_amount_of_processes:
        amount_of_parallel_processes: int | None = (
            general_parameters.parallel_processing.amount_for_scenarios
        )
    else:
        amount_of_parallel_processes = None

    scenarios: list[Box] = load_scenarios(case_name=case_name)

    pool_inputs: zip[tuple[Box, str, Box]] | tqdm[tuple[Box, str, Box]] = zip(
        scenarios, repeat(case_name), repeat(general_parameters)
    )

    progress_bars_parameters: Box = general_parameters.progress_bars
    display_scenario_run: bool = progress_bars_parameters.display_scenario_run
    scenario_run_description: str = (
        progress_bars_parameters.scenario_run_description
    )

    if display_scenario_run:
        pool_inputs = tqdm(
            pool_inputs,
            desc=scenario_run_description,
            total=len(scenarios),
        )

    with Pool(amount_of_parallel_processes) as scenarios_pool:
        scenarios_pool.starmap(run_ChaProEV_scenario, pool_inputs)


def test_run() -> None:

    scenario_path: Path = Path('scenarios/plus/test.toml')
    scenario: Box = cook.parameters_from_TOML(scenario_path)
    plt.style.use('fivethirtyeight')
    network_power_figure, network_power_plot = plt.subplots(1, 1)

    charging_dataframe, hourly_values = run_ChaProEV_scenario(
        scenario=scenario
    )
    network_power_plot.bar(
        x=hourly_values['Hour number'],
        height=hourly_values['Average power drawn from network (kW)'],
    )
    network_power_figure.savefig('noot.png')

    scenario.adaptive = True
    charging_dataframe, hourly_values = run_ChaProEV_scenario(
        scenario=scenario
    )
    network_power_plot.bar(
        x=hourly_values['Hour number'],
        height=hourly_values['Average power drawn from network (kW)'],
    )
    network_power_figure.savefig('moot.png')


if __name__ == '__main__':

    case_name: str = 'plus'
    run_ChaProEV(case_name=case_name)

    # plot1, plot2 = st.columns(2)
    # with plot1:
    #     st.pyplot(network_power_figure)
    #     plt.close(network_power_figure)
    # hourly_figure, hourly_plots = plt.subplots(2, 2)
    # hourly_plots[0, 0].bar(
    #     x=hourly_values['Hour number'],
    #     height=hourly_values['Average power to vehicle (kW)'],
    # )
    # hourly_plots[0, 1].bar(
    #     x=hourly_values['Hour number'],
    #     height=hourly_values['Average power drawn from network (kW)'],
    # )
    # hourly_plots[1, 0].bar(
    #     x=hourly_values['Hour number'],
    #     height=hourly_values['Cumulative charge to vehicle (kWh)'],
    # )
    # hourly_plots[1, 1].bar(
    #     x=hourly_values['Hour number'],
    #     height=hourly_values['Cumulative charge from network (kWh)'],
    # )
    # plt.show()
    print('[magenta] Implemnt probailities')
    print('Dashboard')
    print('Variance')
    print('Test with tighter proba dist')
    print('Still some overlap issues')
    # network_power_plot.bar(
    #     x=hourly_values['Hour number'],
    #     height=hourly_values['Average power drawn from network (kW)'],
    # )
    # st.set_page_config(layout='wide')
    # sidebar = st.sidebar
    # with sidebar:
    #     charge_desire_proportion_trigger: float = st.slider(
    #         label='Charge proportion trigger percent',
    #         min_value=0.0,
    #         max_value=1.0,
    #         value=scenario.vehicle.charge_desire_proportion_trigger,
    #         step=0.01,
    #         format='percent',
    #         key='charge_desire_proportion_trigger',
    #     )
    #     adaptive: bool = st.selectbox(
    #         label='Use adaptve charging',
    #         options=[True, False],
    #         key='adaptive'
    #     )
    # scenario.adaptive = adaptive
    # scenario.vehicle.charge_desire_proportion_trigger
    # = charge_desire_proportion_trigger
