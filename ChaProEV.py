'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import os
import pandas as pd

import weather
import define
import cookbook as cook

if __name__ == '__main__':
    for scenario_file in os.listdir('scenarios'):
        # To avoid issues if some files are not configuration files
        if scenario_file.split('.')[1] == 'toml':

            print(scenario_file.split('.')[0])
            parameters_file_name = f'scenarios/{scenario_file}'
            parameters = cook.parameters_from_TOML(parameters_file_name)
            legs = parameters['legs']
            legs_dataframe = pd.DataFrame(legs)
            legs_dataframe = legs_dataframe.astype('str')
            case_name = parameters['case_name']
            scenario = parameters['scenario']
            groupfile_root = parameters['files']['groupfile_root']
            groupfile_name = f'{groupfile_root}_{case_name}'
            legs_dataframe_name = f'{scenario}_legs'
            output_folder = parameters['files']['output_folder']
            cook.save_dataframe(
                legs_dataframe,  legs_dataframe_name,
                groupfile_name, output_folder, parameters_file_name
            )
            # Put this in a function, with a list of things to save
            # Excel overwrite issue
            # exit()
            print('Do solar panel efficiency')
            print('Multiple runs/cases in output files/DB')
            print('Avoid swap by arranging before?')
            print('And explain/improve in all hourly')
            print('Clarify what theperature efficiency of vehicles is')
            print('Test leg.electricity_use_kWh')
            print('Implement road and hour in day factors')
            print('Go through class definitions (espcially Trip')
            weather.setup_weather(parameters_file_name)
            legs, vehicles, legs, trips = define.declare_all_instances(
                parameters_file_name)
