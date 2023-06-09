'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import os

import weather
import define

if __name__ == '__main__':
    for scenario_file in os.listdir('scenarios'):
        # To avoid issues if some files are not configuration files
        if scenario_file.split('.')[1] == 'toml':
            print(scenario_file.split('.')[0] )
            parameters_file_name = f'scenarios/{scenario_file}'
            print('Do solar panel efficiency')
            print('Multiple runs/cases in output files/DB')
            print('Avoid swap by arranging before?')
            print('And explain/improve in all hourly')
            print('Clarify what theperature efficiency of vehicles is')
            print('Test leg.electricity_use_kWh')
            print('Implement road and hour in day factors')
            print('Go through class definitions (espcially Trip')
            weather.setup_weather(parameters_file_name)
            legs, vehicles, locations, trips = define.declare_all_instances(
                parameters_file_name)
