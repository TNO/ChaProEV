'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import datetime
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
try:
    import charging
except ModuleNotFoundError:
    from ChaProEV import charging
# So that it works both as a standalone (1st) and as a package (2nd)

if __name__ == '__main__':
    start_ = datetime.datetime.now()
    print('Adde @cache')
    print('Rearrange toml (with non-specific elements in the back)')
    print('Match en required fo next and total')
    print('Make one-year run')
    print('Recap DF')
    print('Sum over locations ofenergy for next?')
    print('Other vehicles')
    print('Trips to keep memory')
    print('US module')
    print(
        'Time agnostic and option to spread evenly (or otherwise) at the end'
    )
    print('Bus percent of time in route at bus stops')
    print('Other quantities')
    print('Cahrging strategies')

    print('discharge V2X')
    print('Label min and max for btt space and energy fro next leg')
    print('Aggregates: KMs and cons per trip, day type (?) and total')
    print(
        'Aggregates: Stats (mean, min, max) of Charging power (kW), Driving%, Connected %, Batt space, batt charge level, Maximal delivered power (kW), Percentage of maximal delivered power used (%), Minimal delivered power (kW)'
    )
    print(
        'Data for Tulipa/COMPETES Connected (%)	Charging Power (kW)	Charging Profile	Energy_demand_for_next_leg (kWh)	Energy_demand_for_next_leg (as percent of total demand)	Maximal delivered power (kW)	Percentage of maximal power used(%)	Minimal deliverd power (kW) '
    )
    print(
        'Full data too? Or per location, with one table per, and have sumtable 9or sum in Table?'
    )
    print('Temperature effect')
    print('PVs from PVlib')
    print('Fast chargers')
    print('Speedup per day type (option if using mob module)')
    print('recap DF?')
    print('Check connectivity')
    print('Clarify charge and power! for drawn')
    print(
        'Minimal state of charge = energy for next leg + lowest acceptabl;e level'
    )
    print(
        'Charging Power and Charge Drawn as separate tables and the in percentage and such'
    )
    for scenario_file in os.listdir('scenarios'):
        # To avoid issues if some files are not configuration files
        if scenario_file.split('.')[1] == 'toml':
            parameters_file_name = f'scenarios/{scenario_file}'
            parameters = cook.parameters_from_TOML(parameters_file_name)
            print((datetime.datetime.now() - start_).total_seconds())
            decla_start = datetime.datetime.now()
            legs, locations, trips = define.declare_all_instances(parameters)
            print(
                'Declare',
                (datetime.datetime.now() - decla_start).total_seconds(),
            )

            mob_start = datetime.datetime.now()
            mobility.make_mobility_data(parameters)
            print(
                'Mobility',
                (datetime.datetime.now() - mob_start).total_seconds(),
            )
            cons_start = datetime.datetime.now()
            consumption.get_consumption_data(parameters)
            print(
                'Cons', (datetime.datetime.now() - cons_start).total_seconds()
            )
            charge_start = datetime.datetime.now()
            (
                battery_space,
                charge_drawn_by_vehicles,
                charge_drawn_from_network,
            ) = charging.get_charging_profile(parameters)
            print(
                'Charge',
                (datetime.datetime.now() - charge_start).total_seconds(),
            )
            # print(charge_drawn_by_vehicles)
            # print(charge_drawn_from_network)
    print('Tot', (datetime.datetime.now() - start_).total_seconds())

    # writing.write_scenario_parameters(parameters)
    # weather.setup_weather(parameters)
    # legs, vehicles, legs, trips = define.declare_all_instances(
    #     parameters)

    # run_trip_probabilities = (
    #     mobility.get_run_trip_probabilities(parameters)
    # )
    # Histograms!
