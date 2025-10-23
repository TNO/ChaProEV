import os

import pandas as pd
import pytest
from rich import print


def test_enough_power_next_leg() -> None:

    case_name: str = 'Mopo'

    folder_to_test: str = f'output/{case_name}'

    profile_names: list[str] = [
        test_file.split('.')[0]
        for test_file in os.listdir(folder_to_test)
        if (test_file.split('.')[1] == 'pkl')
        and (test_file.split('.')[0].endswith('_profile'))
    ]

    profiles: list[pd.DataFrame] = [
        pd.read_pickle(f'{folder_to_test}/{profile_name}.pkl')
        for profile_name in profile_names
    ]

    for profile, profile_name in zip(profiles, profile_names):

        print(profile_name)

        for_next_leg_header: str = 'Demand for next leg (kWh) (from network)'
        for_next_leg: pd.Series = profile[for_next_leg_header]

        supply_power_header: str = 'Charging Power from Network (kW)'
        supply_power: pd.Series = profile[supply_power_header]

        power_gaps: pd.Series = supply_power - for_next_leg
        power_gaps[power_gaps > 0] = 0

        total_gap: float = power_gaps.sum()
        assert total_gap == pytest.approx(0)


if __name__ == '__main__':
    test_enough_power_next_leg()
