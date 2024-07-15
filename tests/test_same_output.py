import os
import typing as ty

import pandas as pd


def test_all_files() -> None:
    test_all_outputs: bool = True
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
        if 'matrix' not in test_quantity:# and 'connections' not in test_quantity:
            if f'{test_quantity}.pkl' in os.listdir(reference_folder):
                print(test_quantity)
                test_file: str = f'{folder_to_test}/{test_quantity}.pkl'
                reference_file: str = f'{reference_folder}/{test_quantity}.pkl'
                test_table: pd.DataFrame = pd.read_pickle(test_file)
                reference_table: pd.DataFrame = pd.read_pickle(reference_file)

                if '_battery_space' in test_quantity:
                    reference_table.columns = reference_table.columns.astype(
                        float
                    )
                    test_table.columns = test_table.columns.astype(float)

                    print(reference_table)
                if (
                    test_quantity
                    == 'baseline_percentage_of_maximal_delivered_power_used_per_location'
                ):
                    reference_table = reference_table.fillna(0)

                if test_quantity.startswith('baseline_energy_for_next_leg'):
                    reference_table.index = test_table.index
                print(test_table)
                print(reference_table)
                if 'connections'  in test_quantity:
                    exit()
                # print(test_table.index)
                # print(reference_table.index)
                pd.testing.assert_frame_equal(test_table, reference_table)


if __name__ == '__main__':
    test_all_files()
