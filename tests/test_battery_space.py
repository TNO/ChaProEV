import os
import typing as ty

import pandas as pd


def test_battery_space() -> None:

    case_name: str = 'Mopo'

    scenario_files: ty.List[str] = os.listdir(f'scenarios/{case_name}')
    scenario_names: ty.List[str] = []

    for scenario_file in scenario_files:
        file_extension: str = scenario_file.split('.')[1]
        if file_extension == 'toml':
            scenario_names.append(scenario_file.split('.')[0])
    scenario_names = ['XX_truck']  #['XX_car',  'XX_truck']
    for scenario_name in scenario_names:
        location_split: pd.DataFrame = pd.read_pickle(
            f'output/{case_name}/{scenario_name}_location_split.pkl'
        )
        sum_of_battery_spaces: pd.DataFrame = pd.read_pickle(
            f'output/{case_name}/{scenario_name}_sum_of_battery_spaces.pkl'
        )
        print(location_split)
        print(sum_of_battery_spaces)

        pd.testing.assert_frame_equal(location_split, sum_of_battery_spaces)


if __name__ == '__main__':
    test_battery_space()
