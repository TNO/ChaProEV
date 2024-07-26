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
    # These issues might have to do with MultiIndex,
    zero_threshold: float,
    location_names: ty.List[str],
    possible_destinations: ty.Dict[str, ty.List[str]],
    distance_header: str,
    electricity_consumption_kWh_per_km: float,
    use_day_types_in_charge_computing: bool,
    day_start_hour: int,
    location_split: pd.DataFrame,
) -> ty.Dict[str, pd.DataFrame]:
    next_time_tag: datetime.datetime = time_tag + datetime.timedelta(hours=1)

    if time_tag_index == 6:
        print('00000')
        for location_name in location_names:
            print(location_name)
            ooo = (battery_space[location_name].iloc[:time_tag_index].sum(axis=1))
            aaa = (location_split[location_name].iloc[:time_tag_index])
            print(max((ooo - aaa).values))
            # print(ooo)
            # print(aaa)
            # print(ooo-aaa)
            zii = pd.DataFrame(index=ooo.index)
            zii['batt'] = ooo.values
            zii['loc'] = aaa.values
            print(zii)
        # print(battery_space['van_customer'].iloc[0:28])
        #     print(battery_space['home'].iloc[10:15])
        exit()
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

        if use_day_types_in_charge_computing and (
            time_tag.hour == day_start_hour
        ):
            battery_space[start_location].loc[time_tag, 0] = (
                location_split.loc[time_tag][start_location]
            )

        # We look at which battery spaces there are at this location
        # and sort them. The lowest battery spaces will be first.
        # These are the ones we assume aremore likely to leave,
        # as others might want to charge first
        departing_battery_spaces: ty.List[float] = sorted(
            battery_space[start_location].columns.values
        )

        # We look at all the possible destinations
        for end_location in possible_destinations[start_location]:

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
                            battery_space[start_location].at[
                                time_tag, departing_battery_space
                            ],
                        )
                        if start_location == 'home':
                            print(time_tag, end_location)
                            print(battery_space[start_location].loc[:time_tag].sum(axis=1))
                            print(battery_space[end_location].loc[:time_tag].sum(axis=1))

                            # exit()

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
                            battery_space[start_location].loc[time_tag][
                                departing_battery_space
                            ]
                            - this_battery_space_departures 
                            / 2
                            # / 1
                        )
                        # The effects on the current time tag are halved,
                        # as the vehicles leave unifornmly
                        # The rest of the impact is in the next
                        # time tag
                        if next_time_tag in run_range:
                            battery_space[start_location].loc[
                                next_time_tag, departing_battery_space
                            ] = (
                                battery_space[start_location].loc[
                                    next_time_tag
                                ][departing_battery_space]
                                - this_battery_space_departures
                                / 2
                                # * 0
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

                        # print('Hoo?')
                        # # print(battery_space['truck_hub'].iloc[54])
                        # print(time_tag)
                        # print(first_arrival_shift_time)
                        # print(arriving_battery_space)
                        # print(arriving_amount)
                        # print(first_arrival_shift_proportion)
                        # print('YYYY')

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
                                # print('ZZZ')
                                # # print(battery_space['truck_hub'].iloc[54])

                                battery_space[end_location].loc[
                                    time_tag + first_arrival_shift_time,
                                    arriving_battery_space,
                                ] = battery_space[end_location].loc[
                                    time_tag + first_arrival_shift_time
                                ][
                                    arriving_battery_space
                                ] + (
                                    arriving_amount
                                    * first_arrival_shift_proportion
                                    / 2
                                    # / 1
                                )

                                # The effects on the current time tag are
                                # halved,
                                # as the vehicles arrive unifornmly
                                # The rest of the impact is in the next
                                # time tag
                                if (
                                    next_time_tag + first_arrival_shift_time
                                    <= (run_range[-1])
                                ):
                                    battery_space[end_location].loc[
                                        next_time_tag
                                        + first_arrival_shift_time,
                                        arriving_battery_space,
                                    ] = battery_space[end_location].loc[
                                        next_time_tag
                                        + first_arrival_shift_time
                                    ][
                                        arriving_battery_space
                                    ] + (
                                         arriving_amount
                                        * first_arrival_shift_proportion
                                        / 2
                                        # * 0
                                    )

                                # print(
                                #     arriving_amount
                                #     * first_arrival_shift_proportion
                                # )
                                # print('HSK')
                                # print(
                                #     battery_space[end_location].loc[
                                #         time_tag + first_arrival_shift_time
                                #     ][arriving_battery_space]
                                # )
                                # print('Lacrosse')
                                # print(time_tag_index)
                                # moo = time_tag_index + 2 + 6
                                # print(battery_space[end_location].columns)
                                # print(time_tag + first_arrival_shift_time)
                                # too: datetime.datetime = (
                                #     time_tag + first_arrival_shift_time
                                # )
                                # print(too)
                                # print(arriving_battery_space)
                                # print(
                                #     battery_space[end_location].loc[
                                #         time_tag + first_arrival_shift_time,
                                #         arriving_battery_space,
                                #     ]
                                # )
                                # if moo > 10:
                                #     print('Score')
                                #     print(
                                #         battery_space[end_location].loc[
                                #             (too, moo, f't00{moo}'),
                                #             arriving_battery_space
                                #         ]
                                #     )
                                # print(battery_space['truck_hub'].iloc[54])

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
                                ] + (
                                    arriving_amount
                                    * (1 - first_arrival_shift_proportion)
                                    / 2
                                    # / 1
                                )

                                # The effects on the current time tag are
                                # halved,
                                # as the vehicles arrive unifornmly
                                # The rest of the impact is in the next
                                # time tag
                                if (
                                    next_time_tag + second_arrival_shift_time
                                    <= (run_range[-1])
                                ):
                                    battery_space[end_location].loc[
                                        next_time_tag
                                        + second_arrival_shift_time,
                                        arriving_battery_space,
                                    ] = battery_space[end_location].loc[
                                        next_time_tag
                                        + second_arrival_shift_time
                                    ][
                                        arriving_battery_space
                                    ] + (
                                        arriving_amount
                                        * (1 - first_arrival_shift_proportion)
                                        / 2
                                        # * 0
                                    )

    # Have  arrivals not connect at all if partial (until leave)
    # Or assume they move around get connected

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


def get_charging_framework(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> ty.Tuple[
    ty.Dict[str, pd.DataFrame],
    pd.DatetimeIndex,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    run_range, run_hour_numbers = run_time.get_time_range(
        scenario, general_parameters
    )
    # print(run_range[3573])
    # exit()

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
    
    # We look at the various battery spaces that are available
    # at this charging location (i.e. percent of vehicles with
    # a given battery space per location)
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

    run_mobility_matrix: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_run_mobility_matrix.pkl',
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
    case_name: str,
    general_parameters: ty.Dict,
) -> None:
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
        zero_threshold: float = general_parameters['numbers']['zero_threshold']

        battery_space[location_name] = battery_space[location_name][
            battery_space[location_name].columns[
                battery_space[location_name].sum() > zero_threshold
            ]
        ]
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


def get_charging_profile(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:

    (
        battery_space,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
    ) = get_charging_framework(scenario, case_name, general_parameters)
    
    loop_times: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), 1)),
        columns=['Loop duration'],
        index=run_range,
    )
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
    run_hours_from_day_start: ty.List[int] = [
        (time_tag.hour - day_start_hour) % HOURS_IN_A_DAY
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

    possible_destinations: ty.Dict[str, ty.List[str]] = (
        mobility.get_possible_destinations(scenario)
    )

    use_weighted_km: bool = vehicle_parameters['use_weighted']
    if use_weighted_km:
        distance_header: str = 'Weighted distance (km)'
    else:
        distance_header = 'Distance (km)'
    electricity_consumption_kWh_per_km: float = vehicle_parameters[
        'base_consumption_per_km'
    ]['electricity_kWh']

    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict[str, str] = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    location_split_table_name: str = f'{scenario_name}_location_split'
    location_split: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{location_split_table_name}.pkl'
    )

    # We look at how the available battery space in the vehicles moves around
    # (it increases with movements and decreases with charging)

    for time_tag_index, (time_tag, run_day_type) in enumerate(
        zip(run_range, run_day_types)
    ):
        # print(time_tag_index)
        # if time_tag_index > 5:
        #     print(time_tag)
        #     exit()
        if (
            use_day_types_in_charge_computing
            and (time_tag.hour == day_start_hour)
            and (run_day_type in day_types_to_compute)
        ):
            day_types_to_compute.remove(run_day_type)
            compute_charge = True
            time_tags_of_day_type = []

        if compute_charge:
            loop_start: datetime.datetime = datetime.datetime.now()
            if use_day_types_in_charge_computing:
                time_tags_of_day_type.append(time_tag)
            # print('Before')
            # print(battery_space['van_base'].iloc[2:6])

            battery_space = travel_space_occupation(
                battery_space,
                time_tag,
                time_tag_index,
                run_range,
                run_mobility_matrix,
                zero_threshold,
                location_names,
                possible_destinations,
                distance_header,
                electricity_consumption_kWh_per_km,
                use_day_types_in_charge_computing,
                day_start_hour,
                location_split,
            )
            # print(time_tag)
            # print('After')
            # print(battery_space['van_base'].iloc[2:6])
            # if vehicle_name == 'van':
            #     # print(time_tag_index)
            #     for location_name in location_names:
            #         # print(location_name)
            #         mii = (location_split.loc[time_tag][location_name])
            #         moo = (battery_space[location_name].loc[time_tag].sum())
            #         if abs(mii-moo) > zero_threshold:
            #             print(time_tag)
            #             print(moo)

            #         if time_tag_index == 1000000:
            #             exit()

            loop_mid: datetime.datetime = datetime.datetime.now()

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
            # print('After compute')
            # print(battery_space['van_base'].iloc[2:6])
            if use_day_types_in_charge_computing and (
                time_tag.hour == day_end_hour
            ):
                compute_charge = False
                reference_day_type_time_tags[run_day_type] = (
                    time_tags_of_day_type
                )

            loop_end: datetime.datetime = datetime.datetime.now()
            loop_time: float = (loop_end - loop_start).total_seconds()
            loop_a: float = (loop_mid - loop_start).total_seconds()
            loop_b: float = (loop_end - loop_mid).total_seconds()
            loop_times.loc[time_tag, 'Loop duration'] = loop_time
            loop_times.loc[time_tag, 'Loop duration a'] = loop_a
            loop_times.loc[time_tag, 'Loop duration b'] = loop_b

        # We start with the battery space reduction duw to moving
    # print(battery_space['van_base'].iloc[2:6])
    # exit()

    print('Keep float precision?')
    print('Check totals and such?')
    print('Other charging strategies?')

    print('Other vehicles')
    print('Local values')

    if use_day_types_in_charge_computing:
        filter_dataframe: pd.DataFrame = pd.DataFrame(
            run_day_types, columns=['Day Type'], index=run_range
        )

        filter_dataframe['Hours from day start'] = run_hours_from_day_start
        # The battery space DataFramehas another index:
        filter_for_battery_space: pd.DataFrame = pd.DataFrame(
            run_day_types,
            columns=['Day Type'],
            index=battery_space[location_names[0]].index,
        )
        filter_for_battery_space['Hours from day start'] = (
            run_hours_from_day_start
        )
        for day_type in day_types:
            for hour_index in range(HOURS_IN_A_DAY):
                charge_drawn_from_network.loc[
                    (filter_dataframe['Day Type'] == day_type)
                    & (filter_dataframe['Hours from day start'] == hour_index)
                ] = charge_drawn_from_network.loc[
                    reference_day_type_time_tags[day_type][hour_index]
                ].values
                charge_drawn_by_vehicles.loc[
                    (filter_dataframe['Day Type'] == day_type)
                    & (filter_dataframe['Hours from day start'] == hour_index)
                ] = charge_drawn_by_vehicles.loc[
                    reference_day_type_time_tags[day_type][hour_index]
                ].values
                for location_name in location_names:
                    battery_space[location_name].loc[
                        (filter_for_battery_space['Day Type'] == day_type)
                        & (
                            filter_for_battery_space['Hours from day start']
                            == hour_index
                        )
                    ] = (
                        battery_space[location_name]
                        .loc[
                            reference_day_type_time_tags[day_type][hour_index]
                        ]
                        .values
                    )
        # print(battery_space['van_base'].iloc[2:6])

        # The per day type appraoch has possible issues with cases where
        # a shift occurs over several days (such as holiday departures or
        # returns occurring over the two days of a weekend).
        # We therefore need to ensure that the sum of battery spaces is
        # equal to the location split. We do this by adjustinmg the battery
        # space with 0 kWh.
        for location_name in location_names:
            # print(location_name)
            totals_from_battery_space: pd.DataFrame | pd.Series = (
                battery_space[location_name].sum(axis=1)
            )

            target_location_split: pd.DataFrame | pd.Series = location_split[
                location_name
            ]
            # print(target_location_split)
            # exit()
            location_correction: pd.DataFrame | pd.Series = (
                target_location_split - totals_from_battery_space
            ).astype(
                float
            )  # astype to keep type
            # print(battery_space['van_base'].iloc[2:6])

            battery_space[location_name][0] = (
                battery_space[location_name][0] + location_correction
            )
            # print(battery_space['van_base'].iloc[2:6])

        # print('S')
        # print(battery_space['van_base'].iloc[2:6])

        # Some trips result in charging events spilling over int the next day

        (
            spillover_battery_space,
            run_range,
            run_mobility_matrix,
            spillover_charge_drawn_by_vehicles,
            spillover_charge_drawn_from_network,
        ) = get_charging_framework(scenario, case_name, general_parameters)
        for location_name in location_names:
            spillover_battery_space[location_name][
                battery_space[location_name].columns
            ] = float(0)

        for location_name in location_names:
            day_end_battery_space: pd.DataFrame = battery_space[
                location_name
            ].loc[run_range.hour == day_end_hour]
            non_empty_day_end_battery_space: pd.DataFrame = (
                day_end_battery_space.drop(columns=float(0))
            )
            day_ends_with_leftover_battery_space = (
                non_empty_day_end_battery_space.loc[
                    non_empty_day_end_battery_space.sum(axis=1)
                    > zero_threshold
                ].index.get_level_values('Time Tag')
            )
            print(location_name)
            print(day_ends_with_leftover_battery_space)

            for day_end_time_tag in day_ends_with_leftover_battery_space:

                spillover_battery_space[location_name].loc[
                    day_end_time_tag
                ] = (battery_space[location_name].loc[day_end_time_tag].values)

                spillover_time_tag_index: int = list(run_range).index(
                    day_end_time_tag
                )

                # print(spillover_battery_space[location_name].drop(columns=float(0)).loc[day_end_time_tag])
                # exit()
                amount_in_spillover = (
                    spillover_battery_space[location_name]
                    .drop(columns=float(0))
                    .loc[day_end_time_tag]
                    .sum()
                )
                if amount_in_spillover > zero_threshold:
                    print(amount_in_spillover)
                    print(battery_space[location_name][0:26])
                    print('Poisbjdhsjh')
                    print(
                        spillover_battery_space[location_name].loc[
                            day_end_time_tag
                        ]
                    )
                    exit()
                # print(location_name)
                # print(battery_space[location_name].iloc[72:98])
                # print(amount_in_spillover)
                # exit()

                while amount_in_spillover > zero_threshold:
                    spillover_time_tag_index += 1
                    # if spillover_time_tag_index >= len(run_range) - 1:
                    #     amount_in_spillover = 0
                    # print(spillover_time_tag_index)
                    # print(len(run_range))
                    spillover_time_tag: ty.Any = run_range[
                        spillover_time_tag_index
                    ]
                    # used Any (and less hints above because MyPy seems
                    # to get wrong type matches)
                    spillover_battery_space = travel_space_occupation(
                        spillover_battery_space,
                        spillover_time_tag,
                        spillover_time_tag_index,
                        run_range,
                        run_mobility_matrix,
                        zero_threshold,
                        location_names,
                        possible_destinations,
                        distance_header,
                        electricity_consumption_kWh_per_km,
                        use_day_types_in_charge_computing,
                        day_start_hour,
                        location_split,
                    )

                    (
                        spillover_battery_space,
                        spillover_charge_drawn_by_vehicles,
                        spillover_charge_drawn_from_network,
                    ) = compute_charging_events(
                        spillover_battery_space,
                        spillover_charge_drawn_by_vehicles,
                        spillover_charge_drawn_from_network,
                        spillover_time_tag,
                        scenario,
                        general_parameters,
                    )

                    #             # update baat space and charge drawn

                    amount_in_spillover = (
                        spillover_battery_space[location_name]
                        .drop(columns=float(0))
                        .loc[spillover_time_tag]
                        .sum()
                    )
                    # print(amount_in_spillover)
                    # exit()
                    # print(battery_space[location_name].dtypes)
                    # print(spillover_battery_space[location_name].dtypes)
                    # exit()

                    # print(battery_space[location_name].loc[spillover_time_tag])
                    battery_space[location_name].loc[
                        spillover_time_tag, float(0)
                    ] = (
                        battery_space[location_name].loc[spillover_time_tag][
                            float(0)
                        ]
                        - amount_in_spillover
                    )
                    # print(battery_space[location_name].loc[spillover_time_tag])
                    # exit()
                    non_zero_battery_spaces = battery_space[
                        location_name
                    ].columns[1:]
                    # print(non_zero_battery_spaces)
                    battery_space[location_name].loc[
                        spillover_time_tag, non_zero_battery_spaces
                    ] = (
                        battery_space[location_name].loc[spillover_time_tag][
                            non_zero_battery_spaces
                        ]
                        + spillover_battery_space[location_name].loc[
                            spillover_time_tag
                        ][non_zero_battery_spaces]
                    )
                    charge_drawn_by_vehicles.loc[
                        spillover_time_tag, location_name
                    ] = (
                        # charge_drawn_by_vehicles.loc[spillover_time_tag][
                        #     location_name
                        # ]
                        # +
                        spillover_charge_drawn_by_vehicles.loc[
                            spillover_time_tag
                        ][location_name]
                    )

                    charge_drawn_from_network.loc[
                        spillover_time_tag, location_name
                    ] = (
                        # charge_drawn_by_vehicles.loc[spillover_time_tag][
                        #     location_name
                        # ]
                        # +
                        spillover_charge_drawn_from_network.loc[
                            spillover_time_tag
                        ][location_name]
                    )
                    # print(battery_space[location_name].loc[spillover_time_tag])
                    # print(
                    #     charge_drawn_by_vehicles.loc[
                    #         spillover_time_tag, location_name
                    #     ]
                    # )

                    # exit()

        #         # remove spillover from zero and addspillover elements until
        #         # they are zero
        #     for location_name in location_names:
        #         print(location_name)
        #         print(
        #             spillover_battery_space[location_name].iloc[
        #                 89:105
        #             ]  # 95:97
        #             # .sum(axis=1)
        #         )
        #         print(
        #             battery_space[location_name].iloc[89:105]  # 95:97
        #             # .sum(axis=1)
        #         )
        #     #     # print(run_range.get_loc(day_end_time_tag))

        # if vehicle_name == 'car':
        #     # for location_name in location_names:
        #     #     zouki = battery_space[location_name].sum(axis=1).values
        #     #     zaki = pd.DataFrame(
        #     #         zouki, columns=['Baa'], index=run_range
        #     #     )
        #     #     zaki['LOc split'] = location_split[location_name].values
        #     #     zaki['Corr'] = zaki['LOc split'] - zaki['Baa']
        #     #     print(zaki.iloc[89:120])
        #     exit()

        # print(day_ends_with_leftover_battery_space)
        #     filter_day_ends_with_leftover_battery_space: pd.DataFrame = (
        #         filter_for_battery_space.loc[
        #             day_ends_with_leftover_battery_space
        #         ]
        #     )
        #     day_types_with_leftover_battery_space: ty.List[str] = list(
        #         set(
        #             filter_for_battery_space.loc[
        #                 day_ends_with_leftover_battery_space
        #             ]['Day Type']
        #         )
        #     )
        #     print(day_types_with_leftover_battery_space)
        #     time_tags_for_leftover: pd.Dict[
        #         str, ty.List[datetime.datetime]
        #     ] = {}
        #     for (
        #         day_type_with_leftover_battery_space
        #     ) in day_types_with_leftover_battery_space:
        #         time_tags_for_leftover[
        #             day_type_with_leftover_battery_space
        #         ] = filter_day_ends_with_leftover_battery_space.loc[
        #             filter_day_ends_with_leftover_battery_space['Day Type']
        #             == day_type_with_leftover_battery_space
        #         ].index.get_level_values(
        #             'Time Tag'
        #         )

        # if vehicle_name == 'car':
        #     # print(time_tags_for_leftover)
        #     exit()
    # print(battery_space['van_base'].iloc[0:20])
    # print(charge_drawn_by_vehicles.iloc[0:20])
    # exit()
    write_output(
        battery_space,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        scenario,
        case_name,
        general_parameters,
    )
    loop_times.to_csv('Lopi.csv')
    # print('Write', (datetime.datetime.now()-write_out_start).total_seconds())

    return battery_space, charge_drawn_by_vehicles, charge_drawn_from_network


# def get_all_charge_levels() -> ty.Dict[str, ty.List[float]]:
#     leg_distances: ty.Dict[str, ty.List[float]] = {}
#     leg_distances['home'] = [400, 200, 100, 44, 22, 12, 6]
#     leg_distances['work'] = [22]
#     leg_distances['leisure'] = [6]
#     leg_distances['weekend'] = [100]
#     leg_distances['holiday'] = [400]
#     draws: ty.Dict[str, float] = {}
#     draws['home'] = 8.9
#     draws['work'] = 22
#     draws['leisure'] = 22
#     draws['weekend'] = 22
#     draws['holiday'] = 22
#     kWh_per_km: float = 0.2
#     locations: ty.List[str] = [
#       'home', 'work', 'leisure', 'weekend', 'holiday'
# ]
#     all_charge_levels: ty.Dict[str, ty.List[float]] = {}
#     for location in locations:
#         start_levels: ty.List[float] = [
#             leg_distance * kWh_per_km
#             for leg_distance in leg_distances[location]
#         ]

#         all_charge_levels[location] = []
#         draw: float = draws[location]
#         charge_levels: ty.List[float] = start_levels
#         while max(charge_levels) > 0:
#             new_levels: ty.List[float] = []
#             for charge_level in charge_levels:
#                 if charge_level > 0:
#                     all_charge_levels[location].append(charge_level)
#                 new_charge_level: float = charge_level - draw
#                 if new_charge_level > 0:
#                     new_levels.append(new_charge_level)
#             charge_levels = new_levels
#             all_charge_levels[location] = sorted(all_charge_levels[location])
#             if len(charge_levels) == 0:
#                 charge_levels = [0]

#     return all_charge_levels


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
