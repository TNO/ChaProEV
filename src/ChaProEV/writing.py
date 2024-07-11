'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This contains functions related to writting outputs.
It contains the following functions:
1. **write_scenario_parameters:** This function writes the scenario parameters
    to the output files (either as separate files, or as tables/sheets
    in groupfiles.)
'''

import typing as ty

import pandas as pd
from ETS_CookBook import ETS_CookBook as cook


def write_scenario_parameters(scenario: ty.Dict, case_name: str) -> None:
    '''
    This function writes the scenario parameters to the output files (either
    as separate files, or as tables/sheets in groupfiles.)
    '''
    scenario_parameter_categories: ty.List[str] = scenario[
        'scenario_parameter_categories'
    ]
    scenario_name: str = scenario['scenario_name']
    groupfile_root: str = scenario['files']['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'
    output_folder: str = scenario['files']['output_folder']

    for parameter_category in scenario_parameter_categories:
        parameter_values = scenario[parameter_category]
        parameter_dataframe = pd.DataFrame(parameter_values)
        # Some types (such as lists) create issues with some file formats,
        # and we only need to show the values anyway, so we
        # convert the DataFrame contents to strings
        parameter_dataframe = parameter_dataframe.astype('str')
        parameter_dataframe_name: str = f'{scenario_name}_{parameter_category}'
        cook.save_dataframe(
            parameter_dataframe,
            parameter_dataframe_name,
            groupfile_name,
            output_folder,
            scenario,
        )


if __name__ == '__main__':
    case_name: str = 'local_impact_BEVs'
    scenario_file_name: str = f'scenarios/{case_name}/baseline.toml'
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
    write_scenario_parameters(scenario, case_name)
