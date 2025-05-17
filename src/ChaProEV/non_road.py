'''
Functions for non-road transport modes
'''

import datetime
import os
from itertools import repeat
from multiprocessing import Pool

import box
import pandas as pd
import tqdm
from ETS_CookBook import ETS_CookBook as cook
from rich import print


def get_profile(
    scenario: box.Box,
) -> pd.Series:

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
    run_demand_profile: pd.Series = pd.Series(run_demand, index=run_range)

    return run_demand_profile


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

    scenarios: list[box.Box] = load_scenarios(
        non_road_parameters.source_folder, case_name
    )

    for scenario in scenarios:
        run_demand_profile: pd.Series = get_profile(scenario)

    print(run_demand_profile)
    print('First/last week inclusion issues')
