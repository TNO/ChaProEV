'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import os

import pandas as pd
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print

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
    print(f'Running scenario {scenario_name}')
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
            charging_sessions_with_charged_amounts,  # type: ignore
            scenario,
            general_parameters,
            case_name,
        )
    if produce_standard_profiles:
        profiles.make_profile_display_dataframe(
            location_split,
            total_battery_space_per_location,  # type: ignore
            charge_drawn_from_network,  # type: ignore
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
            charging_sessions_with_charged_amounts,  # type: ignore
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
            charging_costs,  # type: ignore
            charge_drawn_from_network,  # type: ignore
            charge_drawn_by_vehicles,  # type: ignore
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
def load_scenarios(case_name: str) -> list[Box]:
    scenario_folder_files: list[str] = os.listdir(f'scenarios/{case_name}')
    scenario_files: list[str] = [
        scenario_folder_file
        for scenario_folder_file in scenario_folder_files
        if scenario_folder_file.split('.')[1] == 'toml'
    ]
    scenario_file_paths: list[str] = [
        f'scenarios/{case_name}/{scenario_file}'
        for scenario_file in scenario_files
    ]
    scenarios: list[Box] = [
        cook.parameters_from_TOML(scenario_file_path)
        for scenario_file_path in scenario_file_paths
    ]
    for scenario, scenario_file in zip(scenarios, scenario_files):
        scenario.name = scenario_file.split('.')[0]
    return scenarios


if __name__ == '__main__':
    case_name = 'Mopo'
