'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This contains functions related to writting outputs.
It contains the following functions:
1. **write_scenario_parameters:** This function writes the scenario parameters
    to the output files (either as separate files, or as tables/sheets
    in groupfiles.)
'''

import os
import typing as ty

import pandas as pd
from ETS_CookBook import ETS_CookBook as cook


def extra_end_outputs(case_name: str, general_parameters: ty.Dict) -> None:
    '''
    Saves the pickle files to other formats
    '''
    output_root: str = general_parameters['files']['output_root']
    output_folder: str = f'{output_root}/{case_name}'
    groupfile_root: str = general_parameters['files']['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'
    for output_file in os.listdir(output_folder):
        if output_file.split('.')[1] == 'pkl':
            table_name: str = output_file.split('.')[0]
            table_to_save = pd.DataFrame(
                pd.read_pickle(f'{output_root}/{case_name}/{output_file}')
            )

            cook.save_dataframe(
                table_to_save,
                table_name,
                groupfile_name,
                output_folder,
                general_parameters,
            )


def write_scenario_parameters(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> None:
    '''
    This function writes the scenario parameters to the output files (either
    as separate files, or as tables/sheets in groupfiles.)
    '''
    scenario_parameter_categories: ty.List[str] = scenario[
        'scenario_parameter_categories'
    ]
    scenario_name: str = scenario['scenario_name']
    # groupfile_root: str = scenario['files']['groupfile_root']
    # groupfile_name: str = f'{groupfile_root}_{case_name}'
    output_root: str = general_parameters['files']['output_root']
    output_folder: str = f'{output_root}/{case_name}'

    for parameter_category in scenario_parameter_categories:
        parameter_values = scenario[parameter_category]
        parameter_dataframe = pd.DataFrame(parameter_values)
        # Some types (such as lists) create issues with some file formats,
        # and we only need to show the values anyway, so we
        # convert the DataFrame contents to strings
        parameter_dataframe = parameter_dataframe.astype('str')
        parameter_dataframe_name: str = f'{scenario_name}_{parameter_category}'
        parameter_dataframe.to_pickle(
            f'{output_folder}/{parameter_dataframe_name}.pkl'
        )


if __name__ == '__main__':
    case_name = 'Mopo'
    # test_scenario_name: str = 'baseline'
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: ty.Dict = cook.parameters_from_TOML(
        general_parameters_file_name
    )

    extra_end_outputs(case_name, general_parameters)
