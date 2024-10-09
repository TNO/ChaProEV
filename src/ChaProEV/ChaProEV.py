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


try:
    import make_variants  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import make_variants  # type: ignore
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
    use_variants = general_parameters['variants']['use_variants']
    if use_variants:
        csv_version = general_parameters['variants']['csv_version']
        make_variants.make_variants(case_name, csv_version)
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

            write_start: datetime.datetime = datetime.datetime.now()

    writing.extra_end_outputs(case_name, general_parameters)
    print(
        'Writing other outputs',
        (datetime.datetime.now() - write_start).total_seconds(),
    )
    print('Tot', (datetime.datetime.now() - start_).total_seconds())


if __name__ == '__main__':
    start_: datetime.datetime = datetime.datetime.now()

    # This is a case name, which is the grouping of all your scenarios.
    # This is principally used to label your output files.
    case_name = 'Mopo'

    run_ChaProEV(case_name)
