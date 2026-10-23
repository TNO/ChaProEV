import os
from pathlib import Path
from box import Box
from ETS_CookBook import ETS_CookBook as cook


# @cook.function_timer
def load_scenarios(case_name: str) -> list[Box]:
    scenario_folder_files: list[str] = os.listdir(f'scenarios/{case_name}')
    scenario_file_names: list[str] = [
        scenario_folder_file
        for scenario_folder_file in scenario_folder_files
        if scenario_folder_file.split('.')[1] == 'toml'
    ]
    scenario_file_paths: list[Path] = [
        Path(f'scenarios/{case_name}/{scenario_file_name}')
        for scenario_file_name in scenario_file_names
    ]
    scenarios: list[Box] = [
        cook.parameters_from_TOML(scenario_file_path)
        for scenario_file_path in scenario_file_paths
    ]
    for scenario, scenario_file_name in zip(scenarios, scenario_file_names):
        scenario.name = scenario_file_name.split('.')[0]
    return scenarios
