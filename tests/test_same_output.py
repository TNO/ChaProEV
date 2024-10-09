import os
import typing as ty

import pandas as pd


def test_all_files() -> None:

    case_name: str = 'Mopo'

    folder_to_test: str = f'output/{case_name}'
    reference_folder: str = 'reference_run'

    test_quantities: ty.List[str] = [
        test_file.split('.')[0]
        for test_file in os.listdir(folder_to_test)
        if test_file.split('.')[1] == 'pkl'
    ]

    for test_quantity in test_quantities:

        if f'{test_quantity}.pkl' in os.listdir(reference_folder):
            print(test_quantity)

            test_file: str = f'{folder_to_test}/{test_quantity}.pkl'
            reference_file: str = f'{reference_folder}/{test_quantity}.pkl'
            test_table: pd.DataFrame = pd.read_pickle(test_file)
            reference_table: pd.DataFrame = pd.read_pickle(reference_file)
            print(test_table)
            print(reference_table)

            pd.testing.assert_frame_equal(test_table, reference_table)


if __name__ == '__main__':
    test_all_files()
