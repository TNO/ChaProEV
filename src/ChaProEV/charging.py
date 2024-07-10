import datetime
import math
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


# do it per trip
# battery level trigger (below this, will charge)

# then max power or spread

# How to deal with shift to next day?
# Trip of prior day might correlate with next day

# def get_trip_charging_array(trip_name, temperature_correction_factors,
#    scenario):
#     ...
#     or as method/property in trip?
# Dependence on temperatures, but also on battery level at day start
# So maybe do for each day(?)
# 2
# scenario_file_name = 'scenarios/baseline.toml'
# scenario = cook.parameters_from_TOML(scenario_file_name)


def travel_space_occupation(
    battery_space: ty.Dict[str, pd.DataFrame],
    time_tag: datetime.datetime,
    time_tag_index: int,
    run_range: pd.DatetimeIndex,
    run_mobility_matrix,  # This is a DataFrame, but MyPy has issues with it
    # These issues might have to do with MultiIndex
    scenario: ty.Dict,
) -> ty.Dict[str, pd.DataFrame]:

    zero_threshold: float = scenario['numbers']['zero_threshold']
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
    ]

    vehicle_parameters: ty.Dict = scenario['vehicle']
    use_weighted_km: bool = vehicle_parameters['use_weighted']
    if use_weighted_km:
        distance_header: str = 'Weighted distance (km)'
    else:
        distance_header = 'Distance (km)'
    electricity_consumption_kWh_per_km: float = vehicle_parameters[
        'base_consumption_per_km'
    ]['electricity_kWh']

    # We look at all movements starting at a given location
    for start_location in location_names:
        if time_tag_index > 0:
            # We add the values from the previous time tag to
            # the battery space. We do so because travels can propagate to
            # future time tags. I f we just copied the value from
            # the previous time tag, we would delete these
            battery_space[start_location].iloc[time_tag_index] = (
                battery_space[start_location].iloc[time_tag_index]
                + battery_space[start_location].iloc[time_tag_index - 1]
            )

        # We look at which battery spaces there are at this location
        # and sort them. The lowest battery spaces will be first.
        # These are the ones we assume aremore likely to leave,
        # as others might want to charge first
        departing_battery_spaces: ty.List[float] = sorted(
            battery_space[start_location].columns.values
        )

        # We look at all the possible destinations
        for end_location in location_names:
            # For each leg (start/end location combination), we
            # look up the consumption

            this_leg_consumption: float = (
                run_mobility_matrix.loc[
                    start_location, end_location, time_tag
                ][distance_header]
                * electricity_consumption_kWh_per_km
            )

            # We also look up how many vehicles depart
            departures: float = run_mobility_matrix.loc[
                start_location, end_location, time_tag
            ]['Departures amount']
            if departures > zero_threshold:
                # If there are no departures, we can skip this

                # We want to know what the arriving battery spaces
                # will be and the amounts/percentages of the fleet vehicles
                # for each arriving battery space
                arriving_battery_spaces: ty.List[float] = []
                arriving_amounts: ty.List[float] = []

                # We also need the duration of the leg
                travelling_time: float = run_mobility_matrix.loc[
                    start_location, end_location, time_tag
                ]['Duration (hours)']

                # We iterate through the departing battery spaces
                # (reminder, they are ordered from lowest to highest,
                # as we assumed that the lower the battery space, the higher
                # the likelihood to leave, as vehicleswith more battery space/
                # less available battery capacity wll want to charge first).
                for departing_battery_space in departing_battery_spaces:
                    # We will be removing the departures from the lower
                    # battery spaces from the pool, until we have reached
                    # all departures. For example, if we have 0.2 departures
                    # and 0.19 vehicles with space equal to zero, 0.2 vehicles
                    # with space 1, and 0.3 vehicles with space 1.6,
                    # then we will first take all the
                    # 0.19 vehicles with space 0,
                    # 0.01 vehicles with space 1,
                    # and 0 vehicles with space 1.6,
                    # leaving us with 0 vehicles wth space 0,
                    # 0.19 vehicles with
                    # space 1, and 0.3 vehicles with space 1.6
                    if departures > zero_threshold:
                        # (the departures threshold is there
                        # to avoid issues with floating point numbers, where
                        # we could have some variable being 0.1+0.2
                        # and removing that variabl from 0.3 would not be zero

                        # We need to know in which slots the vehicles
                        # will arrive at their destination and the proprtion
                        # of these slots
                        travelling_time = float(travelling_time)
                        first_arrival_shift: int = math.floor(travelling_time)
                        first_arrival_shift_time = datetime.timedelta(
                            hours=first_arrival_shift
                        )
                        second_arrival_shift_time: datetime.timedelta = (
                            datetime.timedelta(hours=first_arrival_shift + 1)
                        )
                        first_arrival_shift_proportion: float = (
                            1 - travelling_time % 1
                        )

                        # We want to know how many dpeartures will come from
                        # the battery space we are looking at. If there are
                        # more vehicles with the current space than remaining
                        # departures, then we take the remaining departures,
                        # otherwise we take all the vehicles with the current
                        # space and move to the next one
                        this_battery_space_departures: float = min(
                            departures,
                            battery_space[start_location]
                            .loc[time_tag][departing_battery_space]
                            .values[0],
                        )

                        # We add these departures to the arriving amounts,
                        # as these will arrive to the end location
                        arriving_amounts.append(this_battery_space_departures)

                        # We also add the corresponding battery space at
                        # arrival, given by the original battery space plus
                        # the leg's consumption
                        arriving_battery_spaces.append(
                            departing_battery_space + this_leg_consumption
                        )

                        # We update the departures (i.e. how many remain
                        # for larger battery spaces)
                        departures -= this_battery_space_departures

                        # Finally, we remove the departures from the start
                        # location for the current time slot

                        battery_space[start_location].loc[
                            time_tag, departing_battery_space
                        ] = (
                            battery_space[start_location]
                            .loc[time_tag][departing_battery_space]
                            .values[0]
                            - this_battery_space_departures
                        )

                # # We only need to do this if there are actually
                # # travels between
                # # the two locations at that time slot
                # if len(arriving_battery_spaces) > 0 :

                # We now can update the battery spaces in the end location.
                for arriving_battery_space, arriving_amount in zip(
                    arriving_battery_spaces, arriving_amounts
                ):
                    if arriving_amount > zero_threshold:
                        # No need to compute if there are no arrivals

                        # If the end location does not have the incoming
                        # battery space in its columns, we add the column
                        # (with zeroes)
                        if arriving_battery_space not in (
                            battery_space[end_location].columns
                        ):
                            battery_space[end_location][
                                arriving_battery_space
                            ] = float(0)

                        if first_arrival_shift_proportion > zero_threshold:
                            # Otherwise there is no first shift arrival
                            # We check if the arrivals in the first slot
                            # are in the run range
                            # if they are not, then we don't take them into
                            # account (as the are not in the run) and add them
                            # in the end_location battery space DataFrame
                            if time_tag + first_arrival_shift_time <= (
                                run_range[-1]
                            ):

                                battery_space[end_location].loc[
                                    time_tag + first_arrival_shift_time,
                                    arriving_battery_space,
                                ] = battery_space[end_location].loc[
                                    time_tag + first_arrival_shift_time
                                ][
                                    arriving_battery_space
                                ].values[
                                    0
                                ] + (
                                    arriving_amount
                                    * first_arrival_shift_proportion
                                )

                        if (1 - first_arrival_shift_proportion) > (
                            zero_threshold
                        ):
                            # Otherwise there is no first shift arrival
                            # We check if the arrivals in the second slot
                            # are in the run range
                            # if they are not, then we don't take them into
                            # account (as the are not in the run)  and add them
                            # in the end_location battery space DataFrame
                            if time_tag + second_arrival_shift_time <= (
                                run_range[-1]
                            ):
                                battery_space[end_location].loc[
                                    time_tag + second_arrival_shift_time,
                                    arriving_battery_space,
                                ] = battery_space[end_location].loc[
                                    time_tag + second_arrival_shift_time
                                ][
                                    arriving_battery_space
                                ].values[
                                    0
                                ] + (
                                    arriving_amount
                                    * (1 - first_arrival_shift_proportion)
                                )

                # We ensure that the columns of the battery space
                # array are ordered
                battery_space[end_location] = battery_space[
                    end_location
                ].reindex(sorted(battery_space[end_location].columns), axis=1)

            # We ensure that the columns of the battery space
            # array are ordered
            battery_space[start_location] = battery_space[
                start_location
            ].reindex(sorted(battery_space[start_location].columns), axis=1)

    # Have  arrivals not connect at all if partial (until leave)
    # Or assume they move around get connected later

    return battery_space


def compute_charging_events(
    battery_space: ty.Dict[str, pd.DataFrame],
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    time_tag: datetime.datetime,
    scenario: ty.Dict,
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    zero_threshold: float = scenario['numbers']['zero_threshold']
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
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

        vehicles_charging: ty.List[float] = (
            percent_charging * battery_space[charging_location].loc[time_tag]
        ).values[0]

        charge_drawn_by_vehicles_this_time_tag_per_battery_space: ty.List[
            float
        ] = (vehicles_charging * charge_drawn_per_charging_vehicle)
        charge_drawn_by_vehicles_this_time_tag: float = sum(
            charge_drawn_by_vehicles_this_time_tag_per_battery_space
        )
        network_charge_drawn_by_vehicles_this_time_tag_per_battery_space: (
            ty.List[float]
        ) = (
            vehicles_charging * network_charge_drawn_per_charging_vehicle
        )
        network_charge_drawn_by_vehicles_this_time_tag: float = sum(
            network_charge_drawn_by_vehicles_this_time_tag_per_battery_space
        )

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
                # USE Thresh?
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
                            battery_space[charging_location]
                            .loc[time_tag][battery_space_after_charging]
                            .values[0]
                            + vehicles_that_get_to_this_space
                        )

                        battery_space[charging_location].loc[
                            time_tag, original_battery_space
                        ] = (
                            battery_space[charging_location]
                            .loc[time_tag][original_battery_space]
                            .values[0]
                            - vehicles_that_get_to_this_space
                        )

            battery_space[charging_location] = battery_space[
                charging_location
            ].reindex(sorted(battery_space[charging_location].columns), axis=1)

    return battery_space, charge_drawn_by_vehicles, charge_drawn_from_network


def get_charging_framework(
    scenario: ty.Dict,
) -> ty.Tuple[
    ty.Dict[str, pd.DataFrame],
    pd.DatetimeIndex,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    run_range, run_hour_numbers = run_time.get_time_range(scenario)
    # print(run_range[3573])
    # exit()
    SPINE_hour_numbers: ty.List[str] = [
        f't{hour_number:04}' for hour_number in run_hour_numbers
    ]
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
    ]
    scenario_name: str = scenario['scenario']
    case_name: str = scenario['case_name']

    file_parameters: ty.Dict[str, str] = scenario['files']
    output_folder: str = file_parameters['output_folder']
    groupfile_root: str = file_parameters['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'
    location_split_table_name: str = f'{scenario_name}_location_split'
    location_split: pd.DataFrame = cook.read_table_from_database(
        location_split_table_name, f'{output_folder}/{groupfile_name}.sqlite3'
    )
    location_split['Time Tag'] = pd.to_datetime(location_split['Time Tag'])

    location_split = location_split.set_index('Time Tag')

    # We look at the various battery spaces that are available
    # at this charging location (i.e. percent of vehicles with
    # a given battery space per location)
    battery_space: ty.Dict[str, pd.DataFrame] = {}
    for location_name in location_names:
        battery_space[location_name] = pd.DataFrame(
            run_range, columns=['Time Tag']
        )
        battery_space[location_name]['Hour Number'] = run_hour_numbers
        battery_space[location_name]['SPINE_Hour_Number'] = SPINE_hour_numbers
        # battery_space[0] float(0)
        battery_space[location_name] = battery_space[location_name].set_index(
            ['Time Tag', 'Hour Number', 'SPINE_Hour_Number']
        )
        battery_space[location_name][float(0)] = float(0)

        battery_space[location_name].loc[run_range[0], 0] = location_split.loc[
            run_range[0]
        ][location_name]

    # all_charge_levels = get_all_charge_levels()
    # for location_name in location_names:
    #     for charge_level in all_charge_levels[location_name]:
    #         battery_space[location_name][charge_level] float(0)

    run_mobility_matrix: pd.DataFrame = cook.read_table_from_database(
        f'{scenario_name}_run_mobility_matrix',
        f'{output_folder}/{groupfile_name}.sqlite3',
    )
    run_mobility_matrix['Time Tag'] = pd.to_datetime(
        run_mobility_matrix['Time Tag']
    )
    run_mobility_matrix = run_mobility_matrix.set_index(
        ['From', 'To', 'Time Tag']
    ).astype(float)

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

    return (
        battery_space,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
    )


def write_output(
    battery_space: ty.Dict[str, pd.DataFrame],
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    scenario: ty.Dict,
) -> None:
    run_range, run_hour_numbers = run_time.get_time_range(scenario)
    # print(run_range[3573])
    # exit()
    SPINE_hour_numbers: ty.List[str] = [
        f't{hour_number:04}' for hour_number in run_hour_numbers
    ]
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name for location_name in location_parameters
    ]
    scenario_name: str = scenario['scenario']
    case_name: str = scenario['case_name']

    file_parameters: ty.Dict[str, str] = scenario['files']
    output_folder: str = file_parameters['output_folder']
    groupfile_root: str = file_parameters['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'

    for location_name in location_names:
        battery_space[location_name].columns = battery_space[
            location_name
        ].columns.astype(str)

        cook.save_dataframe(
            battery_space[location_name],
            f'{scenario_name}_{location_name}_battery_space',
            groupfile_name,
            output_folder,
            scenario,
        )

    charge_drawn_from_network = charge_drawn_from_network.reset_index()
    charge_drawn_from_network['Hour number'] = run_hour_numbers
    charge_drawn_from_network['SPINE hour number'] = SPINE_hour_numbers
    charge_drawn_from_network = charge_drawn_from_network.set_index(
        ['Time Tag', 'Hour number', 'SPINE hour number']
    )
    cook.save_dataframe(
        charge_drawn_from_network,
        f'{scenario_name}_charge_drawn_from_network',
        groupfile_name,
        output_folder,
        scenario,
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
    cook.save_dataframe(
        charge_drawn_from_network_total,
        f'{scenario_name}_charge_drawn_from_network_total',
        groupfile_name,
        output_folder,
        scenario,
    )
    maximal_delivered_power_per_location: pd.DataFrame = (
        cook.read_table_from_database(
            f'{scenario_name}_maximal_delivered_power_per_location',
            f'{output_folder}/{groupfile_name}.sqlite3',
        )
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

    cook.save_dataframe(
        percentage_of_maximal_delivered_power_used_per_location,
        f'{scenario_name}_'
        f'percentage_of_maximal_delivered_power_used_per_location',
        groupfile_name,
        output_folder,
        scenario,
    )

    maximal_delivered_power: pd.DataFrame = (
        cook.read_table_from_database(
            f'{scenario_name}_maximal_delivered_power',
            f'{output_folder}/{groupfile_name}.sqlite3',
        )
        .set_index('Time Tag')
        .astype(float)
    )
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
    # print(percentage_of_maximal_delivered_power_used)
    # percentage_of_maximal_delivered_power_used[
    #     'Percentage of maximal delivered power used'
    # ] = (
    #     charge_drawn_from_network_total['Total Charge Drawn (kWh)'].values
    #     / maximal_delivered_power['Maximal Delivered Power (kW)'].values
    # )
    cook.save_dataframe(
        percentage_of_maximal_delivered_power_used,
        f'{scenario_name}_percentage_of_maximal_delivered_power_used',
        groupfile_name,
        output_folder,
        scenario,
    )

    charge_drawn_by_vehicles = charge_drawn_by_vehicles.reset_index()
    charge_drawn_by_vehicles['Hour number'] = run_hour_numbers
    charge_drawn_by_vehicles['SPINE hour number'] = SPINE_hour_numbers
    charge_drawn_by_vehicles = charge_drawn_by_vehicles.set_index(
        ['Time Tag', 'Hour number', 'SPINE hour number']
    )
    cook.save_dataframe(
        charge_drawn_by_vehicles,
        f'{scenario_name}_charge_drawn_by_vehicles',
        groupfile_name,
        output_folder,
        scenario,
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
    cook.save_dataframe(
        charge_drawn_by_vehicles_total,
        f'{scenario_name}_charge_drawn_by_vehicles_total',
        groupfile_name,
        output_folder,
        scenario,
    )


def get_charging_profile(
    scenario: ty.Dict,
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    (
        battery_space,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
    ) = get_charging_framework(scenario)

    # start_time = datetime.datetime.now()
    # loop_start = start_time

    loop_times: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), 1)),
        columns=['Loop duration'],
        index=run_range,
    )

    # We look at how the available battery space in the vehicles moves around
    # (it increases with movements and decreases with charging)
    for time_tag_index, time_tag in enumerate(run_range):
        # loop_end = datetime.datetime.now()

        loop_start: datetime.datetime = datetime.datetime.now()

        # if time_tag_index > 10:
        #     exit()

        # if time_tag_index > 0:
        #     if loop_time > 0.1:
        #         print(run_range[time_tag_index - 1])
        #         print(time_tag_index - 1)

        battery_space = travel_space_occupation(
            battery_space,
            time_tag,
            time_tag_index,
            run_range,
            run_mobility_matrix,
            scenario,
        )

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
        )

        loop_end: datetime.datetime = datetime.datetime.now()
        loop_time: float = (loop_end - loop_start).total_seconds()
        loop_times.loc[time_tag, 'Loop duration'] = loop_time
        # print(time_tag, loop_time)

        # We start with the battery space reduction duw to moving

    print('Keep float precision?')
    print('Check totals and such?')
    print('Other charging strategies?')

    print('Other vehicles')
    print('Local values')
    # print((datetime.datetime.now()-start_time).total_seconds())
    # write_out_start = datetime.datetime.now()
    write_output(
        battery_space,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        scenario,
    )
    loop_times.to_csv('Lopi.csv')
    # print('Write', (datetime.datetime.now()-write_out_start).total_seconds())

    return battery_space, charge_drawn_by_vehicles, charge_drawn_from_network


def get_all_charge_levels() -> ty.Dict[str, ty.List[float]]:
    leg_distances: ty.Dict[str, ty.List[float]] = {}
    leg_distances['home'] = [400, 200, 100, 44, 22, 12, 6]
    leg_distances['work'] = [22]
    leg_distances['leisure'] = [6]
    leg_distances['weekend'] = [100]
    leg_distances['holiday'] = [400]
    draws: ty.Dict[str, float] = {}
    draws['home'] = 8.9
    draws['work'] = 22
    draws['leisure'] = 22
    draws['weekend'] = 22
    draws['holiday'] = 22
    kWh_per_km: float = 0.2
    locations: ty.List[str] = ['home', 'work', 'leisure', 'weekend', 'holiday']
    all_charge_levels: ty.Dict[str, ty.List[float]] = {}
    for location in locations:
        start_levels: ty.List[float] = [
            leg_distance * kWh_per_km
            for leg_distance in leg_distances[location]
        ]

        all_charge_levels[location] = []
        draw: float = draws[location]
        charge_levels: ty.List[float] = start_levels
        while max(charge_levels) > 0:
            new_levels: ty.List[float] = []
            for charge_level in charge_levels:
                if charge_level > 0:
                    all_charge_levels[location].append(charge_level)
                new_charge_level: float = charge_level - draw
                if new_charge_level > 0:
                    new_levels.append(new_charge_level)
            charge_levels = new_levels
            all_charge_levels[location] = sorted(all_charge_levels[location])
            if len(charge_levels) == 0:
                charge_levels = [0]

    return all_charge_levels


if __name__ == '__main__':
    scenario_file_name: str = 'scenarios/baseline.toml'
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)

    start_: datetime.datetime = datetime.datetime.now()
    (
        battery_space,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
    ) = get_charging_profile(scenario)
    print((datetime.datetime.now() - start_).total_seconds())
