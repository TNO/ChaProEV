import os
import typing as ty

import pandas as pd


def test_charge() -> None:

    case_name: str = 'Mopo'

    scenario_files: ty.List[str] = os.listdir(f'scenarios/{case_name}')
    scenario_names: ty.List[str] = []

    for scenario_file in scenario_files:
        file_extension: str = scenario_file.split('.')[1]
        if file_extension == 'toml':
            scenario_names.append(scenario_file.split('.')[0])
    scenario_names = [
        # 'XX_truck',
        # 'XX_van',
        # 'XX_bus',
        'XX_car'
    ]
    for scenario_name in scenario_names:
        charge_drawn_table: pd.DataFrame = pd.read_pickle(
            f'output/{case_name}/{scenario_name}'
            f'_charge_drawn_by_vehicles_total.pkl'
        )
        charge_drawn: float = charge_drawn_table[
            'Total Charge Drawn (kW)'
        ].sum()

        consumption_table: pd.DataFrame = pd.read_pickle(
            f'output/{case_name}/{scenario_name}_consumption_table.pkl'
        )
        consumption: float = consumption_table[
            'electricity consumption kWh'
        ].sum()
        print(scenario_name)
        print(charge_drawn)
        print(consumption)

        assert charge_drawn == consumption


if __name__ == '__main__':
    test_charge()
