'''
Functions for non-road transport modes
'''

import datetime
import os
import typing as ty
from itertools import repeat
from multiprocessing import Pool

import box
import numpy as np
import pandas as pd
from ETS_CookBook import ETS_CookBook as cook
from rich import print
from tqdm.rich import tqdm


def get_run_demand(
    scenario_name: str, case_name: str, general_parameters: box.Box
) -> float:

    scenario_elements_list: list[str] = scenario_name.split('_')

    country_code: str = scenario_elements_list[0]
    mode: str = scenario_elements_list[1]
    year: int = int(scenario_elements_list[2])
    carrier: str = scenario_elements_list[3]

    source_folder: str = general_parameters.source_folder
    demand_file: str = general_parameters.demand_file
    demand_index: str = general_parameters.demand_index
    demand_header: str = general_parameters.demand_header

    scenario_demand_elements: pd.DataFrame = pd.read_csv(
        f'{source_folder}/{case_name}/{demand_file}'
    ).set_index(demand_index)

    run_demand: float = scenario_demand_elements.loc[
        country_code, mode, year, carrier
    ][demand_header][0]

    return run_demand


def get_profile_weights(
    scenario: box.Box, run_range=pd.DatetimeIndex
) -> pd.Series:

    uniform_split: bool = scenario.uniform_split
    if uniform_split:
        weight_factors: np.ndarray = np.ones(len(run_range)) / len(run_range)
    else:
        weight_factors = np.ones(len(run_range))
        print('Create a procedure!')

    run_profile_weights: pd.Series = pd.Series(
        weight_factors, index=run_range, name=scenario.name
    )
    return run_profile_weights


def get_profile(
    scenario: box.Box, case_name: str, general_parameters: box.Box
) -> tuple[str, pd.DataFrame]:

    run_demand: float = get_run_demand(
        scenario.name, case_name, general_parameters
    )
    run_start_parameters: box.Box = scenario.run_start
    run_start: datetime.datetime = datetime.datetime(
        run_start_parameters.year,
        run_start_parameters.month,
        run_start_parameters.day,
        run_start_parameters.hour,
    )
    run_end_parameters: box.Box = scenario.run_end
    run_end: datetime.datetime = datetime.datetime(
        run_end_parameters.year,
        run_end_parameters.month,
        run_end_parameters.day,
        run_end_parameters.hour,
    )
    frequency: str = scenario.frequency

    run_range: pd.DatetimeIndex = pd.date_range(
        start=run_start, end=run_end, freq=frequency, inclusive='left'
    )

    run_profile_weights: pd.Series = get_profile_weights(scenario, run_range)
    run_demand_profile: pd.Series = pd.Series(
        run_demand * run_profile_weights, index=run_range, name=scenario.name
    )
    run_demand_dataframe: pd.DataFrame = pd.DataFrame(run_demand_profile)
    return scenario.name, run_demand_dataframe


def load_scenarios(non_road_folder: str, case_name: str) -> list[box.Box]:
    scenario_folder_files: list[str] = os.listdir(
        f'{non_road_folder}/{case_name}'
    )
    scenario_files: list[str] = [
        scenario_folder_file
        for scenario_folder_file in scenario_folder_files
        if scenario_folder_file.split('.')[1] == 'toml'
    ]
    scenario_file_paths: list[str] = [
        f'{non_road_folder}/{case_name}/{scenario_file}'
        for scenario_file in scenario_files
    ]
    scenarios: list[box.Box] = [
        box.Box(cook.parameters_from_TOML(scenario_file_path))
        for scenario_file_path in scenario_file_paths
    ]
    for scenario, scenario_file in zip(scenarios, scenario_files):
        scenario.name = scenario_file.split('.')[0]
    return scenarios


if __name__ == '__main__':

    case_name: str = 'Mopo'
    non_road_parameters_general_file: str = 'non-road.toml'

    non_road_parametrs_file: str = 'non-road.toml'
    non_road_parameters: box.Box = box.Box(
        cook.parameters_from_TOML(non_road_parametrs_file)
    )

    set_amount_of_processes: bool = (
        non_road_parameters.parallel_processing.set_amount_of_processes
    )
    if set_amount_of_processes:
        amount_of_parallel_processes: int | None = None
    else:
        amount_of_parallel_processes = (
            non_road_parameters.parallel_processing.amount_of_processes
        )

    scenarios: list[box.Box] = load_scenarios(
        non_road_parameters.source_folder, case_name
    )

    pool_inputs: ty.Iterator[tuple[box.Box, str, box.Box]] | ty.Any = zip(
        scenarios, repeat(case_name), repeat(non_road_parameters)
    )
    # the ty.Any alternative is there because transforming it with the
    # progress bar makes mypy think it change is type

    progress_bars_parameters: box.Box = non_road_parameters.progress_bars

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
        output_profiles: dict[str, pd.DataFrame] = dict(
            scenarios_pool.starmap(get_profile, pool_inputs)
        )

    print(output_profiles['NL_air_2050_kerosene'])
    print('First/last week inclusion issues')
