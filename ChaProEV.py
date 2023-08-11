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
import mobility
import run_time

if __name__ == '__main__':
    for scenario_file in os.listdir('scenarios'):
        # To avoid issues if some files are not configuration files
        if scenario_file.split('.')[1] == 'toml':
            parameters_file_name = f'scenarios/{scenario_file}'
            parameters = cook.parameters_from_TOML(parameters_file_name)

            writing.write_scenario_parameters(parameters)
            weather.setup_weather(parameters)
            legs, vehicles, legs, trips = define.declare_all_instances(
                parameters)

            run_trip_probabilities = (
                mobility.get_run_trip_probabilities(parameters)
            )
