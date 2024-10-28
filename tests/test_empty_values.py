import os

import pandas as pd


def test_empty_values() -> None:

    case_name: str = 'Mopo'

    folder_to_test: str = f'output/{case_name}'

    for test_file in os.listdir(f'{folder_to_test}'):
        if test_file.endswith('.pkl'):
            if not test_file.split('.')[0].endswith('connections'):
                test_dataframe: pd.DataFrame = pd.read_pickle(
                    f'{folder_to_test}/{test_file}'
                )
                print(test_dataframe)
                assert not test_dataframe.isnull().values.any()


if __name__ == '__main__':
    test_empty_values()
