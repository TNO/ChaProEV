'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import datetime
import os
import typing as ty
from itertools import repeat
from multiprocessing import Pool

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


def run_scenario(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> None:
    scenario_name: str = scenario['scenario_name']
    print(scenario_name)
    decla_start: datetime.datetime = datetime.datetime.now()
    legs, locations, trips = define.declare_all_instances(
        scenario, case_name, general_parameters
    )
    print(
        f'Declare {scenario_name}',
        (datetime.datetime.now() - decla_start).total_seconds(),
    )

    mob_start: datetime.datetime = datetime.datetime.now()
    mobility.make_mobility_data(scenario, case_name, general_parameters)
    print(
        f'Mobility {scenario_name}',
        (datetime.datetime.now() - mob_start).total_seconds(),
    )
    cons_start: datetime.datetime = datetime.datetime.now()
    consumption.get_consumption_data(scenario, case_name, general_parameters)
    print(
        f'Consumption {scenario_name}',
        (datetime.datetime.now() - cons_start).total_seconds(),
    )
    charge_start: datetime.datetime = datetime.datetime.now()
    (
        battery_space,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
    ) = charging.get_charging_profile(scenario, case_name, general_parameters)
    print(
        f'Charge {scenario_name}',
        (datetime.datetime.now() - charge_start).total_seconds(),
    )


def load_scenarios(case_name: str) -> ty.List[ty.Dict]:
    scenario_folder_files: ty.List[str] = os.listdir(f'scenarios/{case_name}')
    scenario_files: ty.List[str] = [
        scenario_folder_file
        for scenario_folder_file in scenario_folder_files
        if scenario_folder_file.split('.')[1] == 'toml'
    ]
    scenario_file_paths: ty.List[str] = [
        f'scenarios/{case_name}/{scenario_file}'
        for scenario_file in scenario_files
    ]
    scenarios: ty.List[ty.Dict] = [
        cook.parameters_from_TOML(scenario_file_path)
        for scenario_file_path in scenario_file_paths
    ]
    for scenario, scenario_file in zip(scenarios, scenario_files):
        scenario['scenario_name'] = scenario_file.split('.')[0]
    return scenarios


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

    scenarios: ty.List[ty.Dict] = load_scenarios(case_name)

    number_of_parallel_processes: int = general_parameters[
        'parallel_processing'
    ]['number_of_parallel_processes']['for_scenarios']
    with Pool(number_of_parallel_processes) as scenarios_pool:
        scenarios_pool.starmap(
            run_scenario,
            zip(scenarios, repeat(case_name), repeat(general_parameters)),
        )

    write_start: datetime.datetime = datetime.datetime.now()
    writing.extra_end_outputs(case_name, general_parameters)
    print(
        'Writing other outputs',
        (datetime.datetime.now() - write_start).total_seconds(),
    )
    print('Total time', (datetime.datetime.now() - start_).total_seconds())


if __name__ == '__main__':
    start_: datetime.datetime = datetime.datetime.now()

    # This is a case name, which is the grouping of all your scenarios.
    # This is principally used to label your output files.
    case_name = 'Mopo'

    run_ChaProEV(case_name)
