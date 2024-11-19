'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import os
import typing as ty
from itertools import repeat
from multiprocessing import Pool

import pandas as pd
import tqdm
from box import Box
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


try:
    import profiles  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import profiles  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


@cook.function_timer
def run_scenario(
    scenario: Box, case_name: str, general_parameters: Box
) -> None:
    scenario_name: str = scenario.name
    print(scenario_name)
    location_connections, legs, locations, trips = (
        define.declare_all_instances(scenario, case_name, general_parameters)
    )

    (
        run_mobility_matrix,
        location_split,
        maximal_delivered_power_per_location,
        maximal_delivered_power,
        connectivity_per_location,
        maximal_received_power_per_location,
        vehicle_discharge_power_per_location,
        discharge_power_to_network_per_location,
        run_next_leg_kilometers,
        run_next_leg_kilometers_cumulative,
        run_next_leg_charge_from_network,
        run_next_leg_charge_to_vehicle,
        run_charging_sessions,
        run_charging_sessions_dataframe,
    ) = mobility.make_mobility_data(
        location_connections,
        legs,
        locations,
        trips,
        scenario,
        case_name,
        general_parameters,
    )

    consumption_table: pd.DataFrame = consumption.get_consumption_data(
        run_mobility_matrix,
        run_next_leg_kilometers,
        run_next_leg_kilometers_cumulative,
        scenario,
        case_name,
        general_parameters,
    )

    produce_sessions: bool = general_parameters.sessions.produce
    if produce_sessions:
        charging_sessions_with_charged_amounts = (
            charging.charging_amounts_in_charging_sessions(
                run_charging_sessions_dataframe,
                scenario,
                general_parameters,
                case_name,
            )
        )

    produce_standard_profiles: bool = (
        general_parameters.standard_profiles.produce
    )
    if produce_standard_profiles:
        (
            battery_spaces,
            total_battery_space_per_location,
            charge_drawn_by_vehicles,
            charge_drawn_from_network,
            charging_costs,
        ) = charging.get_charging_profile(
            location_split,
            run_mobility_matrix,
            maximal_delivered_power_per_location,
            maximal_delivered_power,
            scenario,
            case_name,
            general_parameters,
        )

    profiles_from_sessions: bool = (
        general_parameters.sessions.generate_profiles
    )
    if produce_sessions and profiles_from_sessions:
        (
            charging_profile_to_vehicle_from_sessions,
            charging_profile_from_network_from_sessions,
        ) = charging.get_profile_from_sessions(
            charging_sessions_with_charged_amounts,
            scenario,
            general_parameters,
            case_name,
        )
    if produce_standard_profiles:
        profiles.make_profile_display_dataframe(
            location_split,
            total_battery_space_per_location,
            charge_drawn_from_network,
            run_next_leg_charge_from_network,
            run_next_leg_charge_to_vehicle,
            connectivity_per_location,
            maximal_delivered_power_per_location,
            maximal_received_power_per_location,
            vehicle_discharge_power_per_location,
            discharge_power_to_network_per_location,
            scenario,
            general_parameters,
            case_name,
        )
    if produce_sessions:
        profiles.make_sessions_display_dataframes(
            charging_sessions_with_charged_amounts,
            scenario,
            general_parameters,
            case_name,
        )

    do_fleet_tables: bool = (
        general_parameters.profile_dataframe.do_fleet_tables
    )

    if do_fleet_tables:
        profiles.fleet_profiles(case_name, scenario_name, general_parameters)

    display_run_totals, display_fleet_run_totals = (
        profiles.make_display_totals(
            charging_costs,
            charge_drawn_from_network,
            charge_drawn_by_vehicles,
            consumption_table,
            scenario,
            general_parameters,
            case_name,
        )
    )
    # print(scenario.name)
    # print(display_run_totals)
    # print(display_fleet_run_totals)


# @cook.function_timer
def load_scenarios(case_name: str) -> ty.List[Box]:
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
    scenarios: ty.List[Box] = [
        Box(cook.parameters_from_TOML(scenario_file_path))
        for scenario_file_path in scenario_file_paths
    ]
    for scenario, scenario_file in zip(scenarios, scenario_files):
        scenario.name = scenario_file.split('.')[0]
    return scenarios


@cook.function_timer
def run_ChaProEV(case_name: str) -> None:
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: Box = Box(
        cook.parameters_from_TOML(general_parameters_file_name)
    )
    output_root: str = general_parameters.files.output_root
    cook.check_if_folder_exists(f'{output_root}/{case_name}')
    variant_parameters: Box = general_parameters.variants
    use_variants: bool = variant_parameters.use_variants
    if use_variants:
        csv_version: bool = variant_parameters.csv_version
        make_variants.make_variants(case_name, csv_version)

    scenarios: ty.List[Box] = load_scenarios(case_name)

    set_amount_of_processes: bool = (
        general_parameters.parallel_processing.set_amount_of_processes
    )
    if set_amount_of_processes:
        amount_of_parallel_processes: int | None = None
    else:
        amount_of_parallel_processes = (
            general_parameters.parallel_processing.amount_for_scenarios
        )

    pool_inputs: ty.Iterator[ty.Tuple[Box, str, Box]] | ty.Any = zip(
        scenarios, repeat(case_name), repeat(general_parameters)
    )
    # the ty.Any alternative is there because transforming it with the
    # progress bar makes mypy think it change is type
    progress_bars_parameters: Box = general_parameters.progress_bars
    display_scenario_run: bool = progress_bars_parameters.display_scenario_run
    scenario_run_description: str = (
        progress_bars_parameters.scenario_run_description
    )
    if display_scenario_run:
        pool_inputs = tqdm.tqdm(
            pool_inputs,
            desc=scenario_run_description,
            total=len(scenarios),
        )

    with Pool(amount_of_parallel_processes) as scenarios_pool:
        scenarios_pool.starmap(run_scenario, pool_inputs)

    do_car_home_type_split: bool = (
        general_parameters.home_type.do_car_home_type_split
    )
    if do_car_home_type_split:
        profiles.car_home_parking(case_name, general_parameters)

    writing.extra_end_outputs(case_name, general_parameters)


if __name__ == '__main__':
    # This is a case name, which is the grouping of all your scenarios.
    # This is principally used to label your output files.
    case_name = 'Mopo'

    run_ChaProEV(case_name)

    # print('Add sessions into next day')
    # print('Iterate through sessions and send remainder to next session')
    # print('Compute session first pass')
    # print('Do a second compute with passthrough')
    # print('Convert session-basec charge to profile')
    # print('Have parameter that shifts within a session?')
    # print('Do kilometers/consumption split for sessions?')
    # print('Do effetive session end andthen a match between the approaches')
    # print('Make profile DF (with all) from sessions version')
    # print('Make fleet version')
    # print('Compare profiles')
    # Add actual stop time (if using full power)
    # Then infer profiles
    # DO this in a sperate DF that will be used to compare
    # COnnectivity: does the groupneed to be smaller?
    # Also somehow include legs from before that did not charge because
    # of connectivity
    # Base profile is spread according to partial arrivals.
