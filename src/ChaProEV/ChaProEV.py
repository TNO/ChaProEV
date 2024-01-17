'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import os
import pandas as pd

from ETS_CookBook import ETS_CookBook as cook

try:
    import weather
except ModuleNotFoundError:
    from ChaProEV import weather
# So that it works both as a standalone (1st) and as a package (2nd)
try:
    import define
except ModuleNotFoundError:
    from ChaProEV import define
# So that it works both as a standalone (1st) and as a package (2nd)
try:
    import writing
except ModuleNotFoundError:
    from ChaProEV import writing
# So that it works both as a standalone (1st) and as a package (2nd)
try:
    import mobility
except ModuleNotFoundError:
    from ChaProEV import mobility
# So that it works both as a standalone (1st) and as a package (2nd)
try:
    import run_time
except ModuleNotFoundError:
    from ChaProEV import run_time
# So that it works both as a standalone (1st) and as a package (2nd)
try:
    import consumption
except ModuleNotFoundError:
    from ChaProEV import consumption
# So that it works both as a standalone (1st) and as a package (2nd)

if __name__ == '__main__':
    for scenario_file in os.listdir('scenarios'):
        # To avoid issues if some files are not configuration files
        if scenario_file.split('.')[1] == 'toml':
            parameters_file_name = f'scenarios/{scenario_file}'
            parameters = cook.parameters_from_TOML(parameters_file_name)

            legs, locations, trips = define.declare_all_instances(
                parameters)
            for trip in trips:
                print(trip.name)
                print(trip.run_mobility_matrix)
            exit()
            mobility.make_mobility_data(parameters)
            consumption.create_consumption_tables(parameters)

            # writing.write_scenario_parameters(parameters)
            # weather.setup_weather(parameters)
            # legs, vehicles, legs, trips = define.declare_all_instances(
            #     parameters)

            # run_trip_probabilities = (
            #     mobility.get_run_trip_probabilities(parameters)
            # )
