'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This contains functions related to writting outputs.
It contains the following functions:
1. **write_scenario_parameters:** This function writes the scenario parameters
    to the output files (either as separate files, or as tables/sheets
    in groupfiles.)
'''

import pandas as pd
from ETS_CookBook import ETS_CookBook as cook


def write_scenario_parameters(scenario):
    '''
    This function writes the scenario parameters to the output files (either
    as separate files, or as tables/sheets in groupfiles.)
    '''
    scenario_parameter_categories = scenario['scenario_parameter_categories']
    case_name = scenario['case_name']
    scenario_name = scenario['scenario']
    groupfile_root = scenario['files']['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    output_folder = scenario['files']['output_folder']

    for parameter_category in scenario_parameter_categories:
        parameter_values = scenario[parameter_category]
        parameter_dataframe = pd.DataFrame(parameter_values)
        # Some types (such as lists) create issues with some file formats,
        # and we only need to show the values anyway, so we
        # convert the DataFrame contents to strings
        parameter_dataframe = parameter_dataframe.astype('str')
        parameter_dataframe_name = f'{scenario_name}_{parameter_category}'
        cook.save_dataframe(
            parameter_dataframe,
            parameter_dataframe_name,
            groupfile_name,
            output_folder,
            scenario,
        )


if __name__ == '__main__':
    scenario_file_name = 'scenarios/baseline.toml'
    scenario = cook.parameters_from_TOML(scenario_file_name)
    write_scenario_parameters(scenario)
