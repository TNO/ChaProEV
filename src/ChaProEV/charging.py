import datetime
import typing as ty

import numpy as np
import pandas as pd
from ETS_CookBook import ETS_CookBook as cook

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


def get_charging_framework(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> ty.Tuple[
    ty.Dict[str, pd.DataFrame],
    pd.DatetimeIndex,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.Series,
    pd.Series,
    pd.DataFrame,
]:
    '''
    Produces the structures we want for the charging profiles
    '''

    run_range, run_hour_numbers = run_time.get_time_range(
        scenario, general_parameters
    )

    vehicle_parameters: ty.Dict = scenario['vehicle']
    vehicle_name: str = vehicle_parameters['name']
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name]['vehicle'] == vehicle_name
    ]
    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict[str, str] = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    location_split_table_name: str = f'{scenario_name}_location_split'
    location_split: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{location_split_table_name}.pkl'
    )

    # We create a dictionary of various battery spaces that are available
    # at each charging location (i.e. percent of vehicles with
    # a given battery space per location) (locations are keys and
    # battery space dataframes are dictionary entries)
    battery_space: ty.Dict[str, pd.DataFrame] = {}
    for location_name in location_names:
        battery_space[location_name] = pd.DataFrame(
            run_range, columns=['Time Tag']
        )
        # battery_space[0] float(0)
        battery_space[location_name] = battery_space[location_name].set_index(
            ['Time Tag']
        )
        battery_space[location_name][float(0)] = float(0)

        battery_space[location_name].loc[run_range[0], 0] = location_split.loc[
            run_range[0]
        ][location_name]

    # We read the run's mobility matrix as well as specific elements of it
    run_mobility_matrix: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_run_mobility_matrix.pkl',
    ).astype(float)
    run_arrivals_impact: pd.Series = run_mobility_matrix[
        'Arrivals impact'
    ].copy()
    run_departures_impact: pd.Series = run_mobility_matrix[
        'Departures impact'
    ].copy()

    battery_space_shift_arrivals_impact: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_'
        f'run_battery_space_shifts_departures_impact.pkl'
    )

    # We create the Dataframes for the charge drawn
    charge_drawn_by_vehicles: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )
    charge_drawn_by_vehicles.index.name = 'Time Tag'
    charge_drawn_from_network = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )
    charge_drawn_from_network.index.name = 'Time Tag'

    mobility_location_tuples: ty.List[ty.Tuple[str, str]] = (
        mobility.get_mobility_location_tuples(scenario)
    )
    mobility_locations_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
        mobility_location_tuples, names=['Origin', 'Destination']
    )
    travelling_battery_spaces: pd.DataFrame = pd.DataFrame(
        np.zeros([len(mobility_locations_index), 1]),
        columns=[float(0)],
        index=mobility_locations_index,
    )

    return (
        battery_space,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        battery_space_shift_arrivals_impact,
        run_arrivals_impact,
        run_departures_impact,
        travelling_battery_spaces,
    )


def impact_of_departures(
    battery_space: ty.Dict[str, pd.DataFrame],
    start_location: str,
    end_location: str,
    run_departures_impact: pd.Series,
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.Series]:

    return battery_space, run_departures_impact


def impact_of_arrivals(
    battery_space: ty.Dict[str, pd.DataFrame],
    start_location: str,
    end_location: str,
    run_arrivals_impact: pd.Series,
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.Series]:

    return battery_space, run_arrivals_impact


def travel_space_occupation(
    battery_space: ty.Dict[str, pd.DataFrame],
    time_tag: datetime.datetime,
    time_tag_index: int,
    run_mobility_matrix,  # This is a DataFrame, but MyPy has issues with it
    # These issues might have to do with MultiIndex,
    zero_threshold: float,
    location_names: ty.List[str],
    possible_destinations: ty.Dict[str, ty.List[str]],
    possible_origins: ty.Dict[str, ty.List[str]],
    use_day_types_in_charge_computing: bool,
    day_start_hour: int,
    location_split: pd.DataFrame,
    run_arrivals_impact: pd.Series,
    run_departuere_impact: pd.Series,
    run_range: pd.DatetimeIndex,
) -> ty.Dict[str, pd.DataFrame]:

    for location_to_compute in location_names:

        if time_tag_index > 0:
            # We add the values from the previous time tag to
            # the battery space. We do so because travels can propagate to
            # future time tags. I f we just copied the value from
            # the previous time tag, we would delete these
            battery_space[location_to_compute].iloc[time_tag_index] = (
                battery_space[location_to_compute].iloc[time_tag_index]
                + battery_space[location_to_compute].iloc[time_tag_index - 1]
            )

        if use_day_types_in_charge_computing and (
            time_tag.hour == day_start_hour
        ):
            battery_space[location_to_compute].loc[time_tag, 0] = (
                location_split.loc[time_tag][location_to_compute]
            )

        for end_location in possible_destinations[location_to_compute]:
            battery_space, run_departures_impact = impact_of_departures(
                battery_space,
                location_to_compute,
                end_location,
                run_arrivals_impact,
            )
        for start_location in possible_origins[location_to_compute]:
            battery_space, run_arrivals_impact = impact_of_arrivals(
                battery_space,
                start_location,
                location_to_compute,
                run_departures_impact,
            )

    return battery_space


def compute_charging_events(
    battery_space: ty.Dict[str, pd.DataFrame],
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    time_tag: datetime.datetime,
    scenario: ty.Dict,
    general_parameters: ty.Dict,
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:

    zero_threshold: float = general_parameters['numbers']['zero_threshold']
    vehicle_parameters: ty.Dict = scenario['vehicle']
    vehicle_name: str = vehicle_parameters['name']
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name]['vehicle'] == vehicle_name
    ]

    for charging_location in location_names:
        charging_location_parameters: ty.Dict[str, float] = (
            location_parameters[charging_location]
        )
        charger_efficiency: float = charging_location_parameters[
            'charger_efficiency'
        ]
        percent_charging: float = charging_location_parameters['connectivity']
        max_charge: float = charging_location_parameters['charging_power']

        # This variable is useful if new battery spaces
        # are added within this charging procedure
        original_battery_spaces: np.ndarray = battery_space[
            charging_location
        ].columns.values
        charge_drawn_per_charging_vehicle: np.ndarray = np.array(
            [
                min(this_battery_space, max_charge)
                for this_battery_space in original_battery_spaces
            ]
        )
        network_charge_drawn_per_charging_vehicle: np.ndarray = (
            charge_drawn_per_charging_vehicle / charger_efficiency
        )

        vehicles_charging: ty.Any = (
            percent_charging * battery_space[charging_location].loc[time_tag]
        )  # It is a flaot, but MyPy does not get it

        charge_drawn_by_vehicles_this_time_tag_per_battery_space: (
            pd.Series[float] | pd.DataFrame
        ) = (vehicles_charging * charge_drawn_per_charging_vehicle)
        charge_drawn_by_vehicles_this_time_tag: float | pd.Series[float] = (
            charge_drawn_by_vehicles_this_time_tag_per_battery_space
        ).sum()

        network_charge_drawn_by_vehicles_this_time_tag_per_battery_space: (
            pd.Series[float] | pd.DataFrame
        ) = (vehicles_charging * network_charge_drawn_per_charging_vehicle)
        network_charge_drawn_by_vehicles_this_time_tag: (
            float | pd.Series[float]
        ) = (
            network_charge_drawn_by_vehicles_this_time_tag_per_battery_space
        ).sum()

        # We only do the charge computations if there is a charge to be drawn
        if charge_drawn_by_vehicles_this_time_tag > zero_threshold:
            charge_drawn_by_vehicles.loc[time_tag, charging_location] = (
                charge_drawn_by_vehicles.loc[time_tag][charging_location]
                + charge_drawn_by_vehicles_this_time_tag
            )

            charge_drawn_from_network.loc[time_tag, charging_location] = (
                charge_drawn_from_network.loc[time_tag][charging_location]
                + network_charge_drawn_by_vehicles_this_time_tag
            )

            battery_spaces_after_charging: np.ndarray = (
                battery_space[charging_location].columns.values
                - charge_drawn_per_charging_vehicle
            )

            for (
                battery_space_after_charging,
                original_battery_space,
                vehicles_that_get_to_this_space,
            ) in zip(
                battery_spaces_after_charging,
                original_battery_spaces,
                vehicles_charging,
            ):
                # To avoid unnecessary calculations
                if vehicles_that_get_to_this_space > zero_threshold:
                    if original_battery_space > zero_threshold:
                        if battery_space_after_charging not in (
                            battery_space[charging_location].columns.values
                        ):
                            battery_space[charging_location][
                                battery_space_after_charging
                            ] = float(0)

                        battery_space[charging_location].loc[
                            time_tag, battery_space_after_charging
                        ] = (
                            battery_space[charging_location].loc[time_tag][
                                battery_space_after_charging
                            ]
                            + vehicles_that_get_to_this_space
                        )

                        battery_space[charging_location].loc[
                            time_tag, original_battery_space
                        ] = (
                            battery_space[charging_location].loc[time_tag][
                                original_battery_space
                            ]
                            - vehicles_that_get_to_this_space
                        )

            battery_space[charging_location] = battery_space[
                charging_location
            ].reindex(sorted(battery_space[charging_location].columns), axis=1)

    return battery_space, charge_drawn_by_vehicles, charge_drawn_from_network


def copy_day_type_profiles_to_whole_run(
    scenario: ty.Dict,
    run_range: pd.DatetimeIndex,
    reference_day_type_time_tags: ty.Dict[str, ty.List[datetime.datetime]],
    location_split: pd.DataFrame,
    battery_space: ty.Dict[str, pd.DataFrame],
) -> None:
    '''
    This copies the day type runs to whe whole run
    '''

    # day_start_hour: int = scenario['mobility_module']['day_start_hour']
    # HOURS_IN_A_DAY: int = general_parameters['time']['HOURS_IN_A_DAY']
    # run_hours_from_day_start: ty.List[int] = [
    #     (time_tag.hour - day_start_hour) % HOURS_IN_A_DAY
    #     for time_tag in run_range
    # ]

    # run_day_types: ty.List[str] = [
    #     run_time.get_day_type(
    #         time_tag - datetime.timedelta(hours=day_start_hour),
    #         scenario,
    #         general_parameters,
    #     )
    #     for time_tag in run_range
    # ]

    # vehicle_parameters: ty.Dict = scenario['vehicle']
    # vehicle_name: str = vehicle_parameters['name']

    # location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
    #     'locations'
    # ]
    # location_names: ty.List[str] = [
    #     location_name
    #     for location_name in location_parameters
    #     if location_parameters[location_name]['vehicle'] == vehicle_name
    # ]

    # filter_dataframe: pd.DataFrame = pd.DataFrame(
    #     run_day_types, columns=['Day Type'], index=run_range
    # )

    # filter_dataframe['Hours from day start'] = run_hours_from_day_start
    # # The battery space DataFrame has another index:
    # filter_for_battery_space: pd.DataFrame = pd.DataFrame(
    #     run_day_types,
    #     columns=['Day Type'],
    #     index=battery_space[location_names[0]].index,
    # )
    # filter_for_battery_space['Hours from day start'] = run_hours_from_day_start
    # day_types: ty.List[str] = scenario['mobility_module']['day_types']

    # for day_type in day_types:
    #     for hour_index in range(HOURS_IN_A_DAY):
    #         charge_drawn_from_network.loc[
    #             (filter_dataframe['Day Type'] == day_type)
    #             & (filter_dataframe['Hours from day start'] == hour_index)
    #         ] = charge_drawn_from_network.loc[
    #             reference_day_type_time_tags[day_type][hour_index]
    #         ].values
    #         charge_drawn_by_vehicles.loc[
    #             (filter_dataframe['Day Type'] == day_type)
    #             & (filter_dataframe['Hours from day start'] == hour_index)
    #         ] = charge_drawn_by_vehicles.loc[
    #             reference_day_type_time_tags[day_type][hour_index]
    #         ].values
    #         for location_name in location_names:
    #             battery_space[location_name].loc[
    #                 (filter_for_battery_space['Day Type'] == day_type)
    #                 & (
    #                     filter_for_battery_space['Hours from day start']
    #                     == hour_index
    #                 )
    #             ] = (
    #                 battery_space[location_name]
    #                 .loc[reference_day_type_time_tags[day_type][hour_index]]
    #                 .values
    #             )

    # # The per day type appraoch has possible issues with cases where
    # # a shift occurs over several days (such as holiday departures or
    # # returns occurring over the two days of a weekend).
    # # We therefore need to ensure that the sum of battery spaces is
    # # equal to the location split. We do this by adjustinmg the battery
    # # space with 0 kWh.

    # for location_name in location_names:

    #     totals_from_battery_space: pd.DataFrame | pd.Series = battery_space[
    #         location_name
    #     ].sum(axis=1)

    #     target_location_split: pd.DataFrame | pd.Series = location_split[
    #         location_name
    #     ]

    #     location_correction: pd.DataFrame | pd.Series = (
    #         target_location_split - totals_from_battery_space
    #     ).astype(
    #         float
    #     )  # astype to keep type

    #     battery_space[location_name][0] = (
    #         battery_space[location_name][0] + location_correction
    #     )

    # # Some trips result in charging events spilling over int the next day

    # (
    #     spillover_battery_space,
    #     run_range,
    #     run_mobility_matrix,
    #     spillover_charge_drawn_by_vehicles,
    #     spillover_charge_drawn_from_network,
    #     battery_space_shift_arrivals_impact,
    #     run_arrivals_impact, run _departures_impact,
    #     travelling_battery_spaces
    # ) = get_charging_framework(scenario, case_name, general_parameters)


def write_output(
    battery_space: ty.Dict[str, pd.DataFrame],
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    scenario: ty.Dict,
    case_name: str,
    general_parameters: ty.Dict,
) -> None:
    '''
    Writes the outputs to files
    '''

    run_range, run_hour_numbers = run_time.get_time_range(
        scenario, general_parameters
    )

    SPINE_hour_numbers: ty.List[str] = [
        f't{hour_number:04}' for hour_number in run_hour_numbers
    ]
    vehicle_parameters: ty.Dict = scenario['vehicle']
    vehicle_name: str = vehicle_parameters['name']
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name]['vehicle'] == vehicle_name
    ]
    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict[str, str] = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'

    for location_name in location_names:
        battery_space[location_name].columns = battery_space[
            location_name
        ].columns.astype(str)
        battery_space[location_name] = battery_space[
            location_name
        ].reset_index()
        battery_space[location_name]['Hour Number'] = run_hour_numbers
        battery_space[location_name]['SPINE_Hour_Number'] = SPINE_hour_numbers
        battery_space[location_name] = battery_space[location_name].set_index(
            ['Time Tag', 'Hour Number', 'SPINE_Hour_Number']
        )
        battery_space[location_name].to_pickle(
            f'{output_folder}/{scenario_name}_'
            f'{location_name}_battery_space.pkl'
        )
    charge_drawn_from_network = charge_drawn_from_network.reset_index()
    charge_drawn_from_network['Hour number'] = run_hour_numbers
    charge_drawn_from_network['SPINE hour number'] = SPINE_hour_numbers
    charge_drawn_from_network = charge_drawn_from_network.set_index(
        ['Time Tag', 'Hour number', 'SPINE hour number']
    )
    charge_drawn_from_network.to_pickle(
        f'{output_folder}/{scenario_name}_charge_drawn_from_network.pkl'
    )

    charge_drawn_from_network_total: pd.DataFrame = pd.DataFrame(
        index=charge_drawn_from_network.index
    )
    charge_drawn_from_network_total['Total Charge Drawn (kWh)'] = (
        charge_drawn_from_network.sum(axis=1)
    )
    percentage_of_maximal_delivered_power_used_per_location: pd.DataFrame = (
        pd.DataFrame(index=charge_drawn_from_network.index)
    )
    charge_drawn_from_network_total.to_pickle(
        f'{output_folder}/{scenario_name}_charge_drawn_from_network_total.pkl'
    )

    maximal_delivered_power_per_location: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}'
        f'_maximal_delivered_power_per_location.pkl',
    )

    for location_name in location_names:
        percentage_of_maximal_delivered_power_used_per_location[
            location_name
        ] = [
            (
                charge_drawn / maximal_delivered_power
                if maximal_delivered_power != 0
                else 0
            )
            for charge_drawn, maximal_delivered_power in zip(
                charge_drawn_from_network[location_name].values,
                maximal_delivered_power_per_location[location_name].values,
            )
        ]

    percentage_of_maximal_delivered_power_used_per_location.to_pickle(
        f'{output_folder}/{scenario_name}_'
        f'percentage_of_maximal_delivered_power_used_per_location.pkl'
    )

    maximal_delivered_power: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_maximal_delivered_power.pkl',
    ).astype(float)
    # )
    percentage_of_maximal_delivered_power_used: pd.DataFrame = pd.DataFrame(
        index=percentage_of_maximal_delivered_power_used_per_location.index
    )

    percentage_of_maximal_delivered_power_used[
        'Percentage of maximal delivered power used'
    ] = [
        (
            total_charge_drawn_kWh / maximal_delivered_power_kW
            if maximal_delivered_power_kW != 0
            else 0
        )
        for (total_charge_drawn_kWh, maximal_delivered_power_kW) in zip(
            charge_drawn_from_network_total['Total Charge Drawn (kWh)'].values,
            maximal_delivered_power['Maximal Delivered Power (kW)'].values,
        )
    ]

    percentage_of_maximal_delivered_power_used.to_pickle(
        f'{output_folder}/{scenario_name}'
        f'_percentage_of_maximal_delivered_power_used.pkl'
    )

    charge_drawn_by_vehicles = charge_drawn_by_vehicles.reset_index()
    charge_drawn_by_vehicles['Hour number'] = run_hour_numbers
    charge_drawn_by_vehicles['SPINE hour number'] = SPINE_hour_numbers
    charge_drawn_by_vehicles = charge_drawn_by_vehicles.set_index(
        ['Time Tag', 'Hour number', 'SPINE hour number']
    )
    charge_drawn_by_vehicles.to_pickle(
        f'{output_folder}/{scenario_name}_charge_drawn_by_vehicles.pkl'
    )

    charge_drawn_by_vehicles_total: pd.DataFrame = pd.DataFrame(
        index=charge_drawn_by_vehicles.index
    )
    charge_drawn_by_vehicles_total['Total Charge Drawn (kW)'] = (
        charge_drawn_by_vehicles.sum(axis=1)
    )
    percentage_of_maximal_delivered_power_used_per_location = pd.DataFrame(
        index=charge_drawn_by_vehicles.index
    )
    charge_drawn_by_vehicles_total.to_pickle(
        f'{output_folder}/{scenario_name}_charge_drawn_by_vehicles_total.pkl'
    )

    sum_of_battery_spaces: pd.DataFrame = pd.DataFrame(
        columns=location_names,
        index=run_range,
    )
    sum_of_battery_spaces.index.name = 'Time Tag'

    for location_name in location_names:
        sum_of_battery_spaces_this_location: pd.Series[float] = battery_space[
            location_name
        ].sum(axis=1)
        sum_of_battery_spaces[location_name] = (
            sum_of_battery_spaces_this_location.values
        )

    sum_of_battery_spaces.to_pickle(
        f'{output_folder}/{scenario_name}_sum_of_battery_spaces.pkl'
    )


def get_charging_profile(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    '''
    This is the main function of the charging module.
    It produces the charging profile
    '''

    (
        battery_space,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        battery_space_shift_arrivals_impact,
        run_arrivals_impact,
        run_departures_impact,
        travelling_battery_spaces,
    ) = get_charging_framework(scenario, case_name, general_parameters)

    # We want to either compute charging for the whole run, or only
    # do it per day type (to compute faster by avoiding repeats)
    compute_charge: bool = True
    day_types: ty.List[str] = scenario['mobility_module']['day_types']
    use_day_types_in_charge_computing: bool = scenario['run'][
        'use_day_types_in_charge_computing'
    ]

    if use_day_types_in_charge_computing:
        compute_charge = False
        day_types_to_compute: ty.List[str] = day_types.copy()
        reference_day_type_time_tags: ty.Dict[
            str, ty.List[datetime.datetime]
        ] = {}
        time_tags_of_day_type: ty.List[datetime.datetime] = []

    day_start_hour: int = scenario['mobility_module']['day_start_hour']
    HOURS_IN_A_DAY: int = general_parameters['time']['HOURS_IN_A_DAY']
    day_end_hour: int = (day_start_hour - 1) % HOURS_IN_A_DAY
    run_day_types: ty.List[str] = [
        run_time.get_day_type(
            time_tag - datetime.timedelta(hours=day_start_hour),
            scenario,
            general_parameters,
        )
        for time_tag in run_range
    ]

    zero_threshold: float = general_parameters['numbers']['zero_threshold']
    vehicle_parameters: ty.Dict = scenario['vehicle']
    vehicle_name: str = vehicle_parameters['name']

    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name]['vehicle'] == vehicle_name
    ]

    possible_destinations, possible_origins = (
        mobility.get_possible_destinations_and_origins(scenario)
    )
    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict[str, str] = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    location_split_table_name: str = f'{scenario_name}_location_split'
    location_split: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{location_split_table_name}.pkl'
    )

    for time_tag_index, (time_tag, run_day_type) in enumerate(
        zip(run_range, run_day_types)
    ):

        if (
            use_day_types_in_charge_computing
            and (time_tag.hour == day_start_hour)
            and (run_day_type in day_types_to_compute)
        ):
            day_types_to_compute.remove(run_day_type)
            compute_charge = True
            time_tags_of_day_type = []

        if compute_charge:

            if use_day_types_in_charge_computing:
                time_tags_of_day_type.append(time_tag)

            # We start by looking at how travel changes the
            # available battery spaces at each location
            battery_space = travel_space_occupation(
                battery_space,
                time_tag,
                time_tag_index,
                run_mobility_matrix,
                zero_threshold,
                location_names,
                possible_destinations,
                possible_origins,
                use_day_types_in_charge_computing,
                day_start_hour,
                location_split,
                run_arrivals_impact,
                run_departures_impact,
                run_range,
            )

            # We then look at which charging happens
            (
                battery_space,
                charge_drawn_by_vehicles,
                charge_drawn_from_network,
            ) = compute_charging_events(
                battery_space,
                charge_drawn_by_vehicles,
                charge_drawn_from_network,
                time_tag,
                scenario,
                general_parameters,
            )

            if use_day_types_in_charge_computing and (
                time_tag.hour == day_end_hour
            ):
                compute_charge = False
                reference_day_type_time_tags[run_day_type] = (
                    time_tags_of_day_type
                )

    if use_day_types_in_charge_computing:
        copy_day_type_profiles_to_whole_run(
            scenario,
            run_range,
            reference_day_type_time_tags,
            location_split,
            battery_space,
        )

    write_output(
        battery_space,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        scenario,
        case_name,
        general_parameters,
    )

    return battery_space, charge_drawn_by_vehicles, charge_drawn_from_network


if __name__ == '__main__':
    case_name = 'local_impact_BEVs'
    test_scenario_name: str = 'baseline'
    case_name = 'Mopo'
    test_scenario_name = 'XX_truck'
    scenario_file_name: str = (
        f'scenarios/{case_name}/{test_scenario_name}.toml'
    )
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
    scenario['scenario_name'] = test_scenario_name
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: ty.Dict = cook.parameters_from_TOML(
        general_parameters_file_name
    )

    start_: datetime.datetime = datetime.datetime.now()
    (
        battery_space,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
    ) = get_charging_profile(scenario, case_name, general_parameters)
    print((datetime.datetime.now() - start_).total_seconds())
    print('Add after care of turbo boost')
