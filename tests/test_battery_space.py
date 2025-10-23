import os

import box
import pandas as pd
from ETS_CookBook import ETS_CookBook as cook


def test_battery_space() -> None:

    case_name: str = 'Mopo'
    general_parameters_file: str = 'ChaProEV.toml'
    general_parameters: box.Box = cook.parameters_from_TOML(
        general_parameters_file
    )
    save_interim_files: bool = general_parameters.interim_files.pickle

    if save_interim_files:
        scenario_files: list[str] = os.listdir(f'scenarios/{case_name}')
        scenario_names: list[str] = []

        for scenario_file in scenario_files:
            file_extension: str = scenario_file.split('.')[1]
            if file_extension == 'toml':
                scenario_names.append(scenario_file.split('.')[0])

        for scenario_name in scenario_names:
            location_split: pd.DataFrame = pd.read_pickle(
                f'output/{case_name}/{scenario_name}_location_split.pkl'
            )
            sum_of_battery_spaces: pd.DataFrame = pd.read_pickle(
                f'output/{case_name}/{scenario_name}_sum_of_battery_spaces.pkl'
            )

            print(location_split.iloc[0:24])
            print(sum_of_battery_spaces.iloc[0:24])
            print(location_split.iloc[96:120])
            print(sum_of_battery_spaces.iloc[96:120])
            print(location_split.iloc[1102:1106])
            print(sum_of_battery_spaces.iloc[1102:1106])
            # exit()

            pd.testing.assert_frame_equal(
                location_split, sum_of_battery_spaces
            )


if __name__ == '__main__':
    test_battery_space()

    # staysa at route start?
    # cut at last day end
    # Do case without spillover?
    # weekend trips should have no spillover>\???? They do, but can be removed
    # easily
