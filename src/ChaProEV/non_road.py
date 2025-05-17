'''
Functions for non-road transport modes
'''

import datetime
import os
import typing as ty
from itertools import repeat
from multiprocessing import Pool

import box
import pandas as pd
from ETS_CookBook import ETS_CookBook as cook
from rich import print
from tqdm.rich import tqdm


def get_profile(
    scenario: box.Box,
) -> tuple[str, pd.DataFrame]:

    run_demand: float = scenario.run_demand
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
    run_demand_profile: pd.Series = pd.Series(
        run_demand, index=run_range, name=scenario.name
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

    progress_bars_parameters: box.Box = non_road_parameters.progress_bars

    display_scenario_run: bool = progress_bars_parameters.display_scenario_run
    scenario_run_description: str = (
        progress_bars_parameters.scenario_run_description
    )
    if display_scenario_run:
        pool_inputs: ty.Iterator[tuple[box.Box, str, box.Box]] | ty.Any = tqdm(
            scenarios,
            desc=scenario_run_description,
            total=len(scenarios),
        )

    with Pool(amount_of_parallel_processes) as scenarios_pool:
        output_profiles: dict[str, pd.DataFrame] = dict(
            scenarios_pool.map(get_profile, pool_inputs)
        )

    print(output_profiles['NL_air_2050_kerosene'])
    print('First/last week inclusion issues')
