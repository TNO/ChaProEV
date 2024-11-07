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


def car_home_parking(case_name: str, general_parameters: ty.Dict) -> None:
    home_type_parameters: ty.Dict = general_parameters['home_type']
    input_root: str = general_parameters['files']['input_root']
    input_folder: str = f'{input_root}/{case_name}'
    percentages_file_name: str = home_type_parameters['percentages_file']
    car_drivewway_percentages: pd.DataFrame = pd.read_csv(
        f'{input_folder}/{percentages_file_name}'
    ).set_index(home_type_parameters['index_name'])

    profiles_index: ty.List[str] = home_type_parameters['profiles_index']
    own_driveway_name: str = home_type_parameters['own_driveway_name']
    on_street_name: str = home_type_parameters['on_street_name']

    output_root: ty.Dict = general_parameters['files']['output_root']
    output_folder: str = f'{output_root}/{case_name}'

    consumption_parameters: ty.Dict = general_parameters['consumption']
    consumption_table_name: str = consumption_parameters[
        'consumption_table_name'
    ]
    use_years_in_profiles: bool = general_parameters['variants'][
        'use_years_in_profiles'
    ]

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

        do_fleet_tables: float = general_parameters['profile_dataframe'][
            'do_fleet_tables'
        ]
        if do_fleet_tables:
            fleet_profiles(case_name, variant_name, general_parameters)


def fleet_profiles(
    case_name: str, scenario_name: str, general_parameters: ty.Dict
) -> None:
    home_type_parameters: ty.Dict = general_parameters['home_type']
    consumption_parameters: ty.Dict = general_parameters['consumption']
    consumption_table_name: str = consumption_parameters[
        'consumption_table_name'
    ]

    distance_header: str = consumption_parameters['distance_header']
    fleet_distance_header: str = consumption_parameters[
        'fleet_distance_header'
    ]
    energy_carriers_consumption_names: ty.List[str] = consumption_parameters[
        'energy_carriers_consumption_names'
    ]
    fleet_energy_carriers_consumption_names: ty.List[str] = (
        consumption_parameters['fleet_energy_carriers_consumption_names']
    )
    energy_carriers: ty.List[str] = consumption_parameters['energy_carriers']
    output_root: ty.Dict = general_parameters['files']['output_root']
    output_folder: str = f'{output_root}/{case_name}'
    profiles_index: ty.List[str] = home_type_parameters['profiles_index']
    profile_headers: ty.List = general_parameters['profile_dataframe'][
        'headers'
    ]
    fleet_headers: ty.List = general_parameters['profile_dataframe'][
        'fleet_headers'
    ]
    input_root: str = general_parameters['files']['input_root']
    input_folder: str = f'{input_root}/{case_name}'
    fleet_file_name: str = general_parameters['profile_dataframe'][
        'fleet_file_name'
    ]

    fleet_split: pd.DataFrame = pd.read_csv(
        f'{input_folder}/{fleet_file_name}'
    ).set_index('Variant name')

    total_fleet_thousands: float = float(
        fleet_split.loc[scenario_name]['Total Fleet (thousands)']
    )
    consumption_table: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_' f'{consumption_table_name}.pkl'
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
            reference_profile: pd.DataFrame = (
                pd.read_pickle(f'{output_folder}/{scenario_name}_profile.pkl')
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
                    carrier_fleet_thousands * reference_profile[profile_header]
                )
            fleet_profile.to_pickle(
                f'{output_folder}/{scenario_name}_profile_fleet.pkl'
            )

    fleet_consumption_table.to_pickle(
        f'{output_folder}/{scenario_name}_{consumption_table_name}_fleet.pkl'
    )


def run_scenario(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> None:
    scenario_name: str = scenario['scenario_name']
    print(scenario_name)
    decla_start: datetime.datetime = datetime.datetime.now()
    location_connections, legs, locations, trips = (
        define.declare_all_instances(scenario, case_name, general_parameters)
    )
    print(
        f'Declare {scenario_name}',
        (datetime.datetime.now() - decla_start).total_seconds(),
    )

    mob_start: datetime.datetime = datetime.datetime.now()
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
    ) = mobility.make_mobility_data(
        location_connections,
        legs,
        locations,
        trips,
        scenario,
        case_name,
        general_parameters,
    )
    print(
        f'Mobility {scenario_name}',
        (datetime.datetime.now() - mob_start).total_seconds(),
    )
    cons_start: datetime.datetime = datetime.datetime.now()
    consumption.get_consumption_data(
        run_mobility_matrix,
        run_next_leg_kilometers,
        run_next_leg_kilometers_cumulative,
        scenario,
        case_name,
        general_parameters,
    )
    print(
        f'Consumption {scenario_name}',
        (datetime.datetime.now() - cons_start).total_seconds(),
    )
    charge_start: datetime.datetime = datetime.datetime.now()
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
    print(
        f'Charge {scenario_name}',
        (datetime.datetime.now() - charge_start).total_seconds(),
    )

    battery_capacity: float = scenario['vehicle']['battery_capacity']
    battery_capacity_dataframe: pd.DataFrame = pd.DataFrame(
        battery_capacity
        * np.ones(len(total_battery_space_per_location.index)),
        index=total_battery_space_per_location.index,
    )

    dataframes_for_profile: ty.List[pd.DataFrame] = [
        charge_drawn_from_network,
        total_battery_space_per_location,
        battery_capacity_dataframe,
        run_next_leg_charge_from_network,
        connectivity_per_location,
        maximal_delivered_power_per_location,
        maximal_received_power_per_location,
        vehicle_discharge_power_per_location,
        discharge_power_to_network_per_location,
    ]
    profile_dataframe_headers: ty.List[str] = general_parameters[
        'profile_dataframe'
    ]['headers']
    profile_dataframe: pd.DataFrame = run_time.get_time_stamped_dataframe(
        scenario, general_parameters, locations_as_columns=False
    )
    for dataframe_for_profile, dataframe_header in zip(
        dataframes_for_profile, profile_dataframe_headers
    ):

        profile_dataframe[dataframe_header] = dataframe_for_profile.sum(axis=1)

    output_root: str = general_parameters['files']['output_root']
    output_folder: str = f'{output_root}/{case_name}'
    profile_dataframe.to_pickle(f'{output_folder}/{scenario_name}_profile.pkl')

    do_fleet_tables: float = general_parameters['profile_dataframe'][
        'do_fleet_tables'
    ]
    if do_fleet_tables:
        fleet_profiles(case_name, scenario_name, general_parameters)


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
    output_root: str = general_parameters['files']['output_root']
    cook.check_if_folder_exists(f'{output_root}/{case_name}')
    use_variants = general_parameters['variants']['use_variants']
    if use_variants:
        csv_version = general_parameters['variants']['csv_version']
        make_variants.make_variants(case_name, csv_version)

    scenarios: ty.List[ty.Dict] = load_scenarios(case_name)

    set_amount_of_processes: bool = general_parameters['parallel_processing'][
        'number_of_parallel_processes'
    ]['set_amount_of_processes']
    if set_amount_of_processes:
        number_of_parallel_processes: int | None = None
    else:
        number_of_parallel_processes = general_parameters[
            'parallel_processing'
        ]['number_of_parallel_processes']['for_scenarios']

    with Pool(number_of_parallel_processes) as scenarios_pool:
        scenarios_pool.starmap(
            run_scenario,
            zip(scenarios, repeat(case_name), repeat(general_parameters)),
        )

    do_car_home_type_split: bool = general_parameters['home_type'][
        'do_car_home_type_split'
    ]
    if do_car_home_type_split:
        car_home_parking(case_name, general_parameters)

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
