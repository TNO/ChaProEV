'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import os
import pandas as pd

import weather
import define
import writing
import cookbook as cook

if __name__ == '__main__':
    for scenario_file in os.listdir('scenarios'):
        # To avoid issues if some files are not configuration files
        if scenario_file.split('.')[1] == 'toml':
            parameters_file_name = f'scenarios/{scenario_file}'
            writing.write_scenario_parameters(parameters_file_name)
            print('Do solar panel efficiency')
            print('Multiple runs/cases in output files/DB')
            print('Avoid swap by arranging before?')
            print('And explain/improve in all hourly')
            print('Clarify what theperature efficiency of vehicles is')
            print('Test leg.electricity_use_kWh')
            print('Implement road and hour in day factors')
            print('Go through class definitions (espcially Trip')
            print('Day start hour in one place?')
            print('Fast/station charging')
            weather.setup_weather(parameters_file_name)
            legs, vehicles, legs, trips = define.declare_all_instances(
                parameters_file_name)
