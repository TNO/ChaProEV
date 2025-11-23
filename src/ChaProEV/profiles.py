'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
Functions for profiles and car splits
'''

import numpy as np
import pandas as pd
from box import Box

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

    profiles_index: list[str] = home_type_parameters.profiles_index
    sessions_index: list[str] = home_type_parameters.sessions_index
    own_driveway_name: str = home_type_parameters.own_driveway_name
    on_street_name: str = home_type_parameters.on_street_name

    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'

    consumption_parameters: Box = general_parameters.consumption
    consumption_table_name: str = consumption_parameters.consumption_table_name
    use_years_in_profiles: bool = (
        general_parameters.variants.use_years_in_profiles
    )

    variant_names: list[str] = list(car_drivewway_percentages.index)
    for variant_name in variant_names:
        own_driveway_percentage: float = float(
            car_drivewway_percentages.loc[variant_name][
                f'{own_driveway_name}_percentage'
            ]  # type: ignore
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
        own_driveway_values_to_vehicles_from_sessions: pd.DataFrame = (
            pd.read_pickle(
                f'{output_folder}/{own_driveway_profile_prefix}'
                f'_charging_profile_to_vehicle_from_sessions.pkl'
            )
            .reset_index()
            .set_index(profiles_index)
            .astype(float)
        )
        own_driveway_values_from_network_from_sessions: pd.DataFrame = (
            pd.read_pickle(
                f'{output_folder}/{own_driveway_profile_prefix}'
                f'_charging_profile_from_network_from_sessions.pkl'
            )
            .reset_index()
            .set_index(profiles_index)
            .astype(float)
        )
        charging_sessions_own_driveway_values: pd.DataFrame = pd.DataFrame(
            pd.read_pickle(
                f'{output_folder}/{own_driveway_profile_prefix}'
                f'_charging_sessions.pkl'
            )
            .reset_index()
            .set_index(sessions_index)
            # .astype(float)
        )

        on_street_values: pd.DataFrame = (
            pd.read_pickle(
                f'{output_folder}/{on_street_profile_prefix}_profile.pkl'
            )
            .reset_index()
            .set_index(profiles_index)
            # .astype(float)
        )

        on_street_values_to_vehicles_from_sessions: pd.DataFrame = (
            pd.read_pickle(
                f'{output_folder}/{on_street_profile_prefix}'
                f'_charging_profile_to_vehicle_from_sessions.pkl'
            )
            .reset_index()
            .set_index(profiles_index)
            # .astype(float)
        )
        on_street_values_from_network_from_sessions: pd.DataFrame = (
            pd.read_pickle(
                f'{output_folder}/{on_street_profile_prefix}'
                f'_charging_profile_from_network_from_sessions.pkl'
            )
            .reset_index()
            .set_index(profiles_index)
            # .astype(float)
        )
        charging_sessions_on_street_values: pd.DataFrame = pd.DataFrame(
            pd.read_pickle(
                f'{output_folder}/{on_street_profile_prefix}'
                f'_charging_sessions.pkl'
            )
            .reset_index()
            .set_index(sessions_index)
            # .astype(float)
        )

        combined_values: pd.DataFrame = pd.DataFrame(
            index=own_driveway_values.index,
            columns=own_driveway_values.columns,
        )
        combined_values_to_vehicles_from_sessions: pd.DataFrame = pd.DataFrame(
            index=own_driveway_values_to_vehicles_from_sessions.index,
            columns=own_driveway_values_to_vehicles_from_sessions.columns,
        )
        combined_values_from_network_from_sessions: pd.DataFrame = (
            pd.DataFrame(
                index=own_driveway_values_from_network_from_sessions.index,
                columns=own_driveway_values_from_network_from_sessions.columns,
            )
        )
        for quantity in combined_values.columns:
            combined_values[quantity] = (
                own_driveway_percentage * own_driveway_values[quantity]
                + (1 - own_driveway_percentage) * on_street_values[quantity]
            )
        for quantity in combined_values_to_vehicles_from_sessions.columns:
            combined_values_to_vehicles_from_sessions[quantity] = (
                own_driveway_percentage
                * own_driveway_values_to_vehicles_from_sessions[quantity]
                + (1 - own_driveway_percentage)
                * on_street_values_to_vehicles_from_sessions[quantity]
            )
            combined_values_from_network_from_sessions[quantity] = (
                own_driveway_percentage
                * own_driveway_values_from_network_from_sessions[quantity]
                + (1 - own_driveway_percentage)
                * on_street_values_from_network_from_sessions[quantity]
            )
        sessions_values_columns: list[
            str
        ] = home_type_parameters.sessions_values_columns
        for quantity in sessions_values_columns:
            charging_sessions_own_driveway_values[
                quantity
            ] *= own_driveway_percentage
            charging_sessions_on_street_values[quantity] *= (
                1 - own_driveway_percentage
            )

        combined_sessions: pd.DataFrame = pd.concat(
            [
                charging_sessions_own_driveway_values,
                charging_sessions_on_street_values,
            ]
        )

        combined_values.to_pickle(
            f'{output_folder}/{variant_name}_profile.pkl'
        )

        combined_values_to_vehicles_from_sessions.to_pickle(
            f'{output_folder}/{variant_name}'
            f'_charging_profile_to_vehicle_from_sessions.pkl'
        )
        combined_values_from_network_from_sessions.to_pickle(
            f'{output_folder}/{variant_name}'
            f'_charging_profile_from_network_from_sessions.pkl'
        )

        combined_sessions.to_pickle(
            f'{output_folder}/{variant_name}_charging_sessions.pkl'
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

    energy_carriers_consumption_names: list[
        str
    ] = consumption_parameters.energy_carriers_consumption_names

    fleet_energy_carriers_consumption_names: list[
        str
    ] = consumption_parameters.fleet_energy_carriers_consumption_names
    energy_carriers: list[str] = consumption_parameters.energy_carriers
    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'
    profiles_index: list[str] = home_type_parameters.profiles_index
    profile_headers: list = general_parameters.profile_dataframe.headers
    fleet_headers: list = general_parameters.profile_dataframe.fleet_headers

    input_root: str = general_parameters.files.input_root
    input_folder: str = f'{input_root}/{case_name}'
    fleet_file_name: str = general_parameters.profile_dataframe.fleet_file_name

    fleet_split: pd.DataFrame = pd.read_csv(
        f'{input_folder}/{fleet_file_name}'
    ).set_index('Scenario')

    total_fleet_thousands: float = float(
        fleet_split.loc[scenario_name][
            'Total Fleet (thousands)'
        ]  # type: ignore
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
            * fleet_split.loc[scenario_name][
                f'{energy_carrier} proportion'
            ]  # type: ignore
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
                    # .astype(float)
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
                fleet_profile['Effective charging efficiency'] = (
                    fleet_profile['Charging Power to Vehicles (MW)']
                    / fleet_profile['Charging Power from Network (MW)']
                )
                fleet_profile['Effective discharge efficiency'] = (
                    fleet_profile['Discharge Power to Network (MW)']
                    / fleet_profile['Vehicle Discharge Power (MW)']
                )
                fleet_profile[
                    'Effective discharge efficiency'
                ] = fleet_profile['Effective discharge efficiency'].fillna(
                    general_parameters.discharge.no_discharge_efficiency_output
                )
                fleet_profile['Effective charging efficiency'] = fleet_profile[
                    'Effective charging efficiency'
                ].fillna(
                    general_parameters.discharge.no_charge_efficiency_output
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
                fleet_display_dataframe_headers: list[
                    str
                ] = sessions_dataframe_params.fleet_display_dataframe_headers
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
                fleet_sessions['Effective charging efficiency'] = (
                    fleet_sessions['Charging Power to Vehicles (MW)']
                    / fleet_sessions['Charging Power from Network (MW)']
                )
                fleet_sessions['Effective discharge efficiency'] = (
                    fleet_sessions['Discharge Power to Network (MW)']
                    / fleet_sessions['Vehicle Discharge Power (MW)']
                )
                fleet_sessions[
                    'Effective discharge efficiency'
                ] = fleet_sessions['Effective discharge efficiency'].fillna(
                    general_parameters.discharge.no_discharge_efficiency_output
                )
                fleet_sessions[
                    'Effective charging efficiency'
                ] = fleet_sessions['Effective charging efficiency'].fillna(
                    general_parameters.discharge.no_charge_efficiency_output
                )

    fleet_consumption_table.to_pickle(
        f'{output_folder}/{scenario_name}_{consumption_table_name}_fleet.pkl'
    )
    if produce_sessions:  # type: ignore
        fleet_sessions.to_pickle(  # type: ignore
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

    dataframes_for_profile: list[pd.DataFrame] = [
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

    profile_dataframe_headers: list[
        str
    ] = general_parameters.profile_dataframe.headers
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
        profile_dataframe['Charging Power to Vehicles (kW)']
        / profile_dataframe['Charging Power from Network (kW)']
    )
    profile_dataframe['Effective discharge efficiency'] = (
        profile_dataframe['Discharge Power to Network (kW)']
        / profile_dataframe['Vehicle Discharge Power (kW)']
    )
    profile_dataframe['Effective discharge efficiency'] = profile_dataframe[
        'Effective discharge efficiency'
    ].fillna(general_parameters.discharge.no_discharge_efficiency_output)
    profile_dataframe['Effective charging efficiency'] = profile_dataframe[
        'Effective charging efficiency'
    ].fillna(general_parameters.discharge.no_charge_efficiency_output)
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
    display_session_headers: list[
        str
    ] = general_parameters.sessions_dataframe.display_dataframe_headers
    display_session_index: list[
        str
    ] = general_parameters.sessions_dataframe.display_dataframe_index

    display_charging_sessions: pd.DataFrame = (
        charging_sessions_with_charged_amounts[
            display_session_headers
        ].set_index(display_session_index)
    )
    display_charging_sessions['Effective charging efficiency'] = (
        display_charging_sessions['Charging Power to Vehicles (kW)']
        / display_charging_sessions['Charging Power from Network (kW)']
    )
    display_charging_sessions['Effective discharge efficiency'] = (
        display_charging_sessions['Discharge Power to Network (kW)']
        / display_charging_sessions['Vehicle Discharge Power (kW)']
    )

    display_charging_sessions[
        'Effective discharge efficiency'
    ] = display_charging_sessions['Effective discharge efficiency'].fillna(
        general_parameters.discharge.no_discharge_efficiency_output
    )
    display_charging_sessions[
        'Effective charging efficiency'
    ] = display_charging_sessions['Effective charging efficiency'].fillna(
        general_parameters.discharge.no_charge_efficiency_output
    )

    display_charging_sessions.to_pickle(
        f'{output_folder}/{scenario.name}_charging_sessions.pkl'
    )


def make_display_totals(
    charging_costs: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    charge_drawn_by_vehicles: pd.DataFrame,
    consumption_table: pd.DataFrame,
    scenario: Box,
    general_parameters: Box,
    case_name: str,
) -> tuple[pd.Series, pd.Series]:
    display_range: pd.DatetimeIndex = run_time.get_time_range(
        scenario, general_parameters
    )[2]
    display_run_charging_costs: float = (
        charging_costs.loc[display_range].sum().sum()
    )
    display_run_charge_from_network: float = (
        charge_drawn_from_network.loc[display_range].sum().sum()
    )
    display_run_charge_drwan_by_vehicles: float = (
        charge_drawn_by_vehicles.loc[display_range].sum().sum()
    )
    display_run_kilometrage: float = consumption_table.loc[display_range][
        'Kilometers'
    ].sum()
    display_run_totals: pd.Series = pd.Series()
    display_run_totals['Kilometers'] = display_run_kilometrage
    display_run_totals[
        'Charge drawn by vehicles (kWh)'
    ] = display_run_charge_drwan_by_vehicles
    display_run_totals[
        'Charge drawn from network (kWh)'
    ] = display_run_charge_from_network
    display_run_totals['Charging costs (€)'] = display_run_charging_costs
    input_root: str = general_parameters.files.input_root
    input_folder: str = f'{input_root}/{case_name}'
    fleet_file_name: str = general_parameters.profile_dataframe.fleet_file_name
    fleet_split: pd.DataFrame = pd.read_csv(
        f'{input_folder}/{fleet_file_name}'
    ).set_index('Scenario')

    total_electric_fleet_thousands: float = float(
        fleet_split.loc[scenario.name]['Total Fleet (thousands)']
        * fleet_split.loc[scenario.name]['electricity proportion']
    )
    display_fleet_run_totals: pd.Series = pd.Series()
    display_fleet_run_totals['Thousand Kilometers'] = (
        display_run_kilometrage * total_electric_fleet_thousands
    )
    display_fleet_run_totals['Charge drawn by vehicles (MWh)'] = (
        display_run_charge_drwan_by_vehicles * total_electric_fleet_thousands
    )
    display_fleet_run_totals['Charge drawn from network (MWh)'] = (
        display_run_charge_from_network * total_electric_fleet_thousands
    )
    display_fleet_run_totals['Charging costs (thousand €)'] = (
        display_run_charging_costs * total_electric_fleet_thousands
    )
    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'
    display_run_totals.to_pickle(
        f'{output_folder}/{scenario.name}_display_run_totals.pkl'
    )
    display_fleet_run_totals.to_pickle(
        f'{output_folder}/{scenario.name}'
        f'_display_electric_fleet_run_totals.pkl'
    )

    return display_run_totals, display_fleet_run_totals
