'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import datetime
import os
import typing as ty

from ETS_CookBook import ETS_CookBook as cook

try:
    import define  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import define  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again

try:
    import mobility  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import mobility  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again

try:
    import consumption  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import consumption  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again
try:
    import charging  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import charging  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again

try:
    import writing  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import writing  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


def run_ChaProEV(case_name: str) -> None:
    start_: datetime.datetime = datetime.datetime.now()
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: ty.Dict = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    cook.check_if_folder_exists(f'output/{case_name}')
    for scenario_file in os.listdir(f'scenarios/{case_name}'):
        # To avoid issues if some files are not configuration files
        if scenario_file.split('.')[1] == 'toml':
            scenario_file_name: str = f'scenarios/{case_name}/{scenario_file}'
            scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
            scenario['scenario_name'] = scenario_file.split('.')[0]
            print(scenario['scenario_name'])
            print((datetime.datetime.now() - start_).total_seconds())
            decla_start: datetime.datetime = datetime.datetime.now()
            legs, locations, trips = define.declare_all_instances(
                scenario, case_name, general_parameters
            )
            print(
                'Declare',
                (datetime.datetime.now() - decla_start).total_seconds(),
            )

            mob_start: datetime.datetime = datetime.datetime.now()
            mobility.make_mobility_data(
                scenario, case_name, general_parameters
            )
            print(
                'Mobility',
                (datetime.datetime.now() - mob_start).total_seconds(),
            )
            cons_start: datetime.datetime = datetime.datetime.now()
            consumption.get_consumption_data(
                scenario, case_name, general_parameters
            )
            print(
                'Cons', (datetime.datetime.now() - cons_start).total_seconds()
            )
            charge_start: datetime.datetime = datetime.datetime.now()
            (
                battery_space,
                charge_drawn_by_vehicles,
                charge_drawn_from_network,
            ) = charging.get_charging_profile(
                scenario, case_name, general_parameters
            )
            print(
                'Charge',
                (datetime.datetime.now() - charge_start).total_seconds(),
            )
            # print(charge_drawn_by_vehicles)
            # print(charge_drawn_from_network)
            write_start: datetime.datetime = datetime.datetime.now()

    writing.extra_end_outputs(case_name, general_parameters)
    print(
        'Writing other outputs',
        (datetime.datetime.now() - write_start).total_seconds(),
    )
    print('Tot', (datetime.datetime.now() - start_).total_seconds())


if __name__ == '__main__':
    start_: datetime.datetime = datetime.datetime.now()
    print('Match en required fo next and total')
    print('Recap DF')
    print('Sum over locations ofenergy for next?')
    print('Other vehicles')
    print('Trips to keep memory')
    print('Bus percent of time in route at bus stops')
    print('Other quantities')
    # print('Label min and max for btt space and energy fro next leg')
    # print('Aggregates: KMs and cons per trip, day type (?) and total')
    # print(
    #     'Aggregates: Stats (mean, min, max) of Charging power (kW),
    # Driving%, Connected %, Batt space, batt charge level,
    # Maximal delivered power (kW),
    # Percentage of maximal delivered power used (%),
    # Minimal delivered power (kW)'
    # )
    # print(
    #     'Data for Tulipa/COMPETES Connected (%)	Charging Power (kW)
    # Charging Profile	Energy_demand_for_next_leg (kWh)
    # Energy_demand_for_next_leg (as percent of total demand)
    # \Maximal delivered power (kW)
    # Percentage of maximal power used(%)	Minimal deliverd power (kW) '
    # )
    # print(
    #     'Full data too? Or per location, with one table per,
    # and have sumtable 9or sum in Table?'
    # )
    print('Temperature effect')
    print('PVs from PVlib')
    print('Fast chargers')
    print('Speedup per day type (option if using mob module)')
    print('recap DF?')
    print('Check connectivity')
    print('Clarify charge and power! for drawn')
    # print(
    #     'Minimal state of charge = energy for next leg
    # + lowest acceptabl;e level'
    # )
    # print(
    #     'Charging Power and Charge Drawn as separate tables
    # and the in percentage and such'
    # )
    # print(
    #     'Split home an-home and home-street (or have it as
    # separate runs with different powers?)'
    # )
    # print('Other vehicles')
    print('Speed up by using day types only calc as option')
    print('Chargin strategis (basic, adaptive, price (?))')
    print('Every x days')
    # This is a case name, which is the grouping of all your scenarios.
    # This is principally used to label your output files.
    case_name = 'Mopo'

    run_ChaProEV(case_name)
    print('Iterate over cases? At least as a separate fucntion')
    # writing.write_scenario_parameters(scenario)
    # weather.setup_weather( scenario)
    # legs, vehicles, legs, trips = define.declare_all_instances(
    #     scenario)

    # run_trip_probabilities = (
    #     mobility.get_run_trip_probabilities(scenario)
    # )
    # Histograms!

    # Spillover at vans too Or maybe the spillover is also for mobility
