'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This contains functions related to writting outputs.
It contains the following functions:
1. **write_scenario_parameters:** This function writes the scenario parameters
    to the output files (either as separate files, or as tables/sheets
    in groupfiles.)
'''

import pandas as pd

import cookbook as cook


def write_scenario_parameters(parameters):
    '''
    This function writes the scenario parameters to the output files (either
    as separate files, or as tables/sheets in groupfiles.)
    '''
    scenario_parameter_categories = parameters['scenario_parameter_categories']
    case_name = parameters['case_name']
    scenario = parameters['scenario']
    groupfile_root = parameters['files']['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    output_folder = parameters['files']['output_folder']

    for parameter_category in scenario_parameter_categories:
        parameter_values = parameters[parameter_category]
        parameter_dataframe = pd.DataFrame(parameter_values)
        # Some types (suc as lists) creat issues with some file formats,
        # and we only need to show the values anyway, so we
        # convert the DataFRame contents to strings
        parameter_dataframe = parameter_dataframe.astype('str')
        parameter_dataframe_name = f'{scenario}_{parameter_category}'
        cook.save_dataframe(
            parameter_dataframe, parameter_dataframe_name,
            groupfile_name, output_folder, parameters
        )
