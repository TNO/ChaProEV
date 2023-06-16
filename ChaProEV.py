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
            writing.write_scenario_parameters(parameters_file_name)
            weather.setup_weather(parameters_file_name)
            legs, vehicles, legs, trips = define.declare_all_instances(
                parameters_file_name)

            run_trip_probabilities = (
                mobility.get_run_trip_probabilities(parameters_file_name)
            )
