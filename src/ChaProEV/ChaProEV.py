'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import datetime
import os
import typing as ty
from itertools import repeat
from multiprocessing import Pool

import numpy as np
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
    import run_time  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import run_time  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


# @cook.function_timer
def car_home_parking(case_name: str, general_parameters: Box) -> None:
    home_type_parameters: Box = general_parameters.home_type
    input_root: str = general_parameters.files.input_root
    input_folder: str = f'{input_root}/{case_name}'
    percentages_file_name: str = home_type_parameters.percentages_file
    car_drivewway_percentages: pd.DataFrame = pd.read_csv(
        f'{input_folder}/{percentages_file_name}'
    ).set_index(home_type_parameters.index_name)

    profiles_index: ty.List[str] = home_type_parameters.profiles_index
    own_driveway_name: str = home_type_parameters.own_driveway_name
    on_street_name: str = home_type_parameters.on_street_name

    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'

    consumption_parameters: Box = general_parameters.consumption
    consumption_table_name: str = consumption_parameters.consumption_table_name
    use_years_in_profiles: bool = (
        general_parameters.variants.use_years_in_profiles
    )

    variant_names: ty.List[str] = list(car_drivewway_percentages.index)
    for variant_name in variant_names:
        own_driveway_percentage: float = float(
            car_drivewway_percentages.loc[variant_name][
                f'{own_driveway_name}_percentage'
            ]
        )

        if use_years_in_profiles:
            variant_year: str = variant_name.split('_')[-1]
            variant_prefix: str = '_'.join(variant_name.split('_')[:-1])
            own_driveway_profile_prefix: str = (
                f'{variant_prefix}_{own_driveway_name}_{variant_year}'
            )
            on_street_profile_prefix: str = (
                f'{variant_prefix}_{on_street_name}_{variant_year}'
            )
        else:
            own_driveway_profile_prefix = f'{variant_name}_{own_driveway_name}'
            on_street_profile_prefix = (
                f'{output_folder}/{variant_name}_{on_street_name}'
            )
        own_driveway_values: pd.DataFrame = (
            pd.read_pickle(
                f'{output_folder}/{own_driveway_profile_prefix}_profile.pkl'
            )
            .reset_index()
            .set_index(profiles_index)
            .astype(float)
        )

        on_street_values: pd.DataFrame = (
            pd.read_pickle(
                f'{output_folder}/{on_street_profile_prefix}_profile.pkl'
            )
            .reset_index()
            .set_index(profiles_index)
        )

        combined_values: pd.DataFrame = pd.DataFrame(
            index=own_driveway_values.index,
            columns=own_driveway_values.columns,
        )
        for quantity in combined_values.columns:
            combined_values[quantity] = (
                own_driveway_percentage * own_driveway_values[quantity]
                + (1 - own_driveway_percentage) * on_street_values[quantity]
            )

        combined_values.to_pickle(
            f'{output_folder}/{variant_name}_profile.pkl'
        )

        weekly_consumption_table: pd.DataFrame = pd.read_pickle(
            f'{output_folder}/{own_driveway_profile_prefix}'
            f'_{consumption_table_name}.pkl'
        )
        weekly_consumption_table.to_pickle(
            f'{output_folder}/{variant_name}_{consumption_table_name}.pkl'
        )

        do_fleet_tables: bool = (
            general_parameters.profile_dataframe.do_fleet_tables
        )
        if do_fleet_tables:
            fleet_profiles(case_name, variant_name, general_parameters)


# @cook.function_timer
def fleet_profiles(
    case_name: str, scenario_name: str, general_parameters: Box
) -> None:
    produce_standard_profiles: bool = (
        general_parameters.standard_profiles.produce
    )
    home_type_parameters: Box = general_parameters.home_type
    consumption_parameters: Box = general_parameters.consumption
    consumption_table_name: str = consumption_parameters.consumption_table_name

    distance_header: str = consumption_parameters.distance_header
    fleet_distance_header: str = consumption_parameters.fleet_distance_header

    energy_carriers_consumption_names: ty.List[str] = (
        consumption_parameters.energy_carriers_consumption_names
    )

    fleet_energy_carriers_consumption_names: ty.List[str] = (
        consumption_parameters.fleet_energy_carriers_consumption_names
    )
    energy_carriers: ty.List[str] = consumption_parameters.energy_carriers
    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'
    profiles_index: ty.List[str] = home_type_parameters.profiles_index
    profile_headers: ty.List = general_parameters.profile_dataframe.headers
    fleet_headers: ty.List = general_parameters.profile_dataframe.fleet_headers

    input_root: str = general_parameters.files.input_root
    input_folder: str = f'{input_root}/{case_name}'
    fleet_file_name: str = general_parameters.profile_dataframe.fleet_file_name

    fleet_split: pd.DataFrame = pd.read_csv(
        f'{input_folder}/{fleet_file_name}'
    ).set_index('Variant name')

    total_fleet_thousands: float = float(
        fleet_split.loc[scenario_name]['Total Fleet (thousands)']
    )
    consumption_table: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_{consumption_table_name}.pkl'
    )
    fleet_consumption_table: pd.DataFrame = pd.DataFrame(
        index=consumption_table.index
    )

    fleet_consumption_table[fleet_distance_header] = (
        total_fleet_thousands * consumption_table[distance_header]
    )

    for (
        energy_carrier,
        consumption_name,
        fleet_consumption_name,
    ) in zip(
        energy_carriers,
        energy_carriers_consumption_names,
        fleet_energy_carriers_consumption_names,
    ):
        carrier_fleet_thousands: float = float(
            total_fleet_thousands
            * fleet_split.loc[scenario_name][f'{energy_carrier} proportion']
        )
        fleet_consumption_table[fleet_consumption_name] = (
            carrier_fleet_thousands * consumption_table[consumption_name]
        )
        if energy_carrier == 'electricity':
            if produce_standard_profiles:
                reference_profile: pd.DataFrame = (
                    pd.read_pickle(
                        f'{output_folder}/{scenario_name}_profile.pkl'
                    )
                    .reset_index()
                    .set_index(profiles_index)
                    .astype(float)
                )
                fleet_profile: pd.DataFrame = pd.DataFrame(
                    columns=fleet_headers, index=reference_profile.index
                )

                for profile_header, fleet_header in zip(
                    profile_headers, fleet_headers
                ):
                    fleet_profile[fleet_header] = (
                        carrier_fleet_thousands
                        * reference_profile[profile_header]
                    )
                fleet_profile.to_pickle(
                    f'{output_folder}/{scenario_name}_profile_fleet.pkl'
                )
            produce_sessions: bool = general_parameters.sessions.produce
            if produce_sessions:
                reference_sessions: pd.DataFrame = pd.read_pickle(
                    f'{output_folder}/{scenario_name}_charging_sessions.pkl'
                )
                sessions_dataframe_params: Box = (
                    general_parameters.sessions_dataframe
                )
                fleet_display_dataframe_headers: ty.List[str] = (
                    sessions_dataframe_params.fleet_display_dataframe_headers
                )
                fleet_sessions: pd.DataFrame = pd.DataFrame(
                    columns=fleet_display_dataframe_headers,
                    index=reference_sessions.index,
                )
                for profile_header, fleet_header in zip(
                    reference_sessions.columns, fleet_display_dataframe_headers
                ):
                    fleet_sessions[fleet_header] = (
                        carrier_fleet_thousands
                        * reference_sessions[profile_header]
                    )

    fleet_consumption_table.to_pickle(
        f'{output_folder}/{scenario_name}_{consumption_table_name}_fleet.pkl'
    )
    if produce_sessions:
        fleet_sessions.to_pickle(
            f'{output_folder}/{scenario_name}_charging_sessions_fleet.pkl'
        )


def make_profile_display_dataframe(
    location_split: pd.DataFrame,
    total_battery_space_per_location: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    run_next_leg_charge_from_network: pd.DataFrame,
    run_next_leg_charge_to_vehicle: pd.DataFrame,
    connectivity_per_location: pd.DataFrame,
    maximal_delivered_power_per_location: pd.DataFrame,
    maximal_received_power_per_location: pd.DataFrame,
    vehicle_discharge_power_per_location: pd.DataFrame,
    discharge_power_to_network_per_location: pd.DataFrame,
    scenario: Box,
    general_parameters: Box,
    case_name: str,
) -> None:

    battery_capacity: float = scenario.vehicle.battery_capacity
    battery_capacity_dataframe: pd.DataFrame = (
        battery_capacity * location_split
    )

    state_of_charge_dataframe: pd.DataFrame = (
        battery_capacity_dataframe - total_battery_space_per_location
    )

    connectivities: np.ndarray = np.array(
        [
            scenario.locations[dataframe_location].connectivity
            for dataframe_location in battery_capacity_dataframe.columns
        ]
    )
    connected_total_battery_space_per_location: pd.DataFrame = (
        total_battery_space_per_location * connectivities
    )
    connected_battery_capacity_dataframe: pd.DataFrame = (
        battery_capacity_dataframe * connectivities
    )
    connected_state_of_charge_dataframe: pd.DataFrame = (
        state_of_charge_dataframe * connectivities
    )

    dataframes_for_profile: ty.List[pd.DataFrame] = [
        charge_drawn_from_network,
        connected_total_battery_space_per_location,
        connected_state_of_charge_dataframe,
        connected_battery_capacity_dataframe,
        run_next_leg_charge_from_network,
        run_next_leg_charge_to_vehicle,
        connectivity_per_location,
        maximal_delivered_power_per_location,
        maximal_received_power_per_location,
        vehicle_discharge_power_per_location,
        discharge_power_to_network_per_location,
    ]

    display_range: pd.DatetimeIndex = run_time.get_time_range(
        scenario, general_parameters
    )[2]
    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'

    profile_dataframe_headers: ty.List[str] = (
        general_parameters.profile_dataframe.headers
    )
    profile_dataframe: pd.DataFrame = run_time.get_time_stamped_dataframe(
        scenario, general_parameters, locations_as_columns=False
    )
    for dataframe_for_profile, dataframe_header in zip(
        dataframes_for_profile, profile_dataframe_headers
    ):

        profile_dataframe[dataframe_header] = dataframe_for_profile.sum(axis=1)

    profile_dataframe = profile_dataframe.loc[display_range]
    profile_dataframe.index.name = 'Time Tag'
    profile_dataframe['Effective charging efficiency'] = (
        profile_dataframe['Connected Power to Vehicles (kW)']
        / profile_dataframe['Connected Power from Network (kW)']
    )
    profile_dataframe['Effective discharge efficiency'] = (
        profile_dataframe['Discharge Power to Network (kW)']
        / profile_dataframe['Vehicle Discharge Power (kW)']
    )
    profile_dataframe.to_pickle(f'{output_folder}/{scenario.name}_profile.pkl')


def make_sessions_display_dataframes(
    charging_sessions_with_charged_amounts: pd.DataFrame,
    scenario: Box,
    general_parameters: Box,
    case_name: str,
) -> None:
    display_range: pd.DatetimeIndex = run_time.get_time_range(
        scenario, general_parameters
    )[2]
    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'

    charging_sessions_with_charged_amounts = (
        charging_sessions_with_charged_amounts.loc[
            charging_sessions_with_charged_amounts['Start time']
            .apply(pd.to_datetime)
            .between(display_range[0], display_range[-1])
        ]
    )
    display_session_headers: ty.List[str] = (
        scenario.charging_sessions.display_dataframe_headers
    )
    display_session_index: ty.List[str] = (
        scenario.charging_sessions.display_dataframe_index
    )

    display_charging_sessions: pd.DataFrame = (
        charging_sessions_with_charged_amounts[
            display_session_headers
        ].set_index(display_session_index)
    )

    display_charging_sessions.to_pickle(
        f'{output_folder}/{scenario.name}_charging_sessions.pkl'
    )


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

    consumption.get_consumption_data(
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
        make_profile_display_dataframe(
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
        make_sessions_display_dataframes(
            charging_sessions_with_charged_amounts,
            scenario,
            general_parameters,
            case_name,
        )

    do_fleet_tables: bool = (
        general_parameters.profile_dataframe.do_fleet_tables
    )

    if do_fleet_tables:
        fleet_profiles(case_name, scenario_name, general_parameters)


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
        car_home_parking(case_name, general_parameters)

    writing.extra_end_outputs(case_name, general_parameters)


if __name__ == '__main__':
    start_: datetime.datetime = datetime.datetime.now()

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
