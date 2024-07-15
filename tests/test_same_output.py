import os
import typing as ty

import pandas as pd


def test_all_files() -> None:
    test_all_outputs: bool = False
    case_name: str = 'local_impact_BEVs'
    scenario_name: str = 'baseline'
    folder_to_test: str = f'output/{case_name}'
    reference_folder: str = 'reference_run'
    # changed_quantities: ty.List[str] = []
    if test_all_outputs:
        test_quantities: ty.List[str] = [
            test_file.split('.')[0]
            for test_file in os.listdir(folder_to_test)
            if test_file.split('.')[1] == 'pkl'
        ]
    else:
        test_quantities = list(
            pd.read_csv('tests/test_quantities.csv')[
                'Quantities to test'
            ].values
        )

    for test_quantity in test_quantities:
        print(test_quantity)
        test_file: str = (
            f'{folder_to_test}/{scenario_name}_{test_quantity}.pkl'
        )
        reference_file: str = (
            f'{reference_folder}/{scenario_name}_{test_quantity}.pkl'
        )
        test_table: pd.DataFrame = pd.read_pickle(test_file)
        reference_table: pd.DataFrame = pd.read_pickle(reference_file)

        if test_quantity == 'weekend_battery_space':
            reference_table.columns = reference_table.columns.astype(float)
            test_table.columns = test_table.columns.astype(float)

            print(reference_table)
        if (
            test_quantity
            == 'percentage_of_maximal_delivered_power_used_per_location'
        ):
            reference_table = reference_table.fillna(0)
        print(test_table)
        print(reference_table)
        pd.testing.assert_frame_equal(test_table, reference_table)


if __name__ == '__main__':
    test_all_files()
