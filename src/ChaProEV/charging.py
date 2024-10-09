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
    pd.Series,
    pd.Series,
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
    location_nodes: pd.DataFrame = pd.DataFrame(
        index=location_names, columns=['Connections']
    )
    possible_destinations, possible_origins = (
        mobility.get_possible_destinations_and_origins(scenario)
    )

    for location_name in location_names:
        location_nodes.loc[location_name, 'Connections'] = len(
            possible_destinations[location_name]
        ) + len(possible_origins[location_name])
    location_nodes = location_nodes.sort_values(
        by='Connections', ascending=False
    )
    location_names = list(location_nodes.index.values)

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
    battery_spaces: ty.Dict[str, pd.DataFrame] = {}
    for location_name in location_names:
        battery_spaces[location_name] = pd.DataFrame(
            run_range, columns=['Time Tag']
        )
        # battery_spaces[0] float(0)
        battery_spaces[location_name] = battery_spaces[
            location_name
        ].set_index(['Time Tag'])
        battery_spaces[location_name][float(0)] = float(0)

        battery_spaces[location_name].loc[run_range[0], 0] = (
            location_split.loc[run_range[0]][location_name]
        )

    # We read the run's mobility matrix as well as specific elements of it
    run_mobility_matrix: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_run_mobility_matrix.pkl',
    ).astype(float)
    run_arrivals_impact: pd.Series = run_mobility_matrix[
        'Arrivals impact'
    ].copy()

    run_arrivals_impact_gaps: pd.Series = pd.Series(
        np.zeros(len(run_arrivals_impact.index)),
        index=run_arrivals_impact.index,
    )

    run_departures_impact: pd.Series = run_mobility_matrix[
        'Departures impact'
    ].copy()

    run_departures_impact_gaps: pd.Series = pd.Series(
        np.zeros(len(run_departures_impact.index)),
        index=run_departures_impact.index,
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
        battery_spaces,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        run_arrivals_impact,
        run_arrivals_impact_gaps,
        run_departures_impact,
        run_departures_impact_gaps,
        travelling_battery_spaces,
    )


def impact_of_departures(
    scenario: ty.Dict,
    time_tag: datetime.datetime,
    battery_spaces: ty.Dict[str, pd.DataFrame],
    start_location: str,
    end_location: str,
    run_departures_impact: pd.Series,
    travelling_battery_spaces,  # it's a DataFarame but MyPy gives an error,
    zero_threshold: float,
    run_mobility_matrix,  # it's a DataFarame but MyPy gives an error,
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, float]:

    time_tag_departures_impact: float = run_departures_impact.loc[
        start_location, end_location, time_tag
    ]

    departures_gap: float = max(
        0,
        run_departures_impact.loc[start_location, end_location, time_tag]
        - battery_spaces[start_location].sum(axis=1).loc[time_tag],
    )

    if time_tag_departures_impact > zero_threshold:

        # We look at which battery spaces there are at this location
        # and sort them. The lowest battery spaces will be first.
        # These are the ones we assume are more likely to leave,
        # as others might want to charge first.
        departing_battery_spaces: ty.List[float] = sorted(
            battery_spaces[start_location].columns.values
        )

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
            if time_tag_departures_impact > zero_threshold:
                # We do this until there are no departures left

                # We want to know how many departures will come from
                # the battery space we are looking at. If there are
                # more vehicles with the current space than remaining
                # departures, then we take the remaining departures,
                # otherwise we take all the vehicles with the current
                # space and move to the next one
                # This needs to be done separately for the current
                # time slot and the next one
                # (because of the issue of effective impact, as
                # some vehicles stay some of the time)

                this_battery_space_departures_impact_this_time: float = min(
                    time_tag_departures_impact,
                    battery_spaces[start_location].at[
                        time_tag, departing_battery_space
                    ],
                )

                # We update the departures (i.e. how many remain
                # for larger battery spaces)
                time_tag_departures_impact -= (
                    this_battery_space_departures_impact_this_time
                )

                # We remove the departures from the start
                # location for the current time slot
                battery_spaces[start_location].loc[
                    time_tag, departing_battery_space
                ] = (
                    battery_spaces[start_location].loc[time_tag][
                        departing_battery_space
                    ]
                    - this_battery_space_departures_impact_this_time
                )

                # We also add these departures to the travelling battery spaces

                # We we also need the consumption of the leg
                leg_distance: float = run_mobility_matrix.loc[
                    start_location, end_location, time_tag
                ]['Distance (km)']
                vehicle_electricity_consumption: float = scenario['vehicle'][
                    'base_consumption_per_km'
                ]['electricity_kWh']

                this_leg_consumption: float = (
                    leg_distance * vehicle_electricity_consumption
                )
                travelling_battery_space: float = (
                    departing_battery_space + this_leg_consumption
                )

                if (
                    this_battery_space_departures_impact_this_time
                    > zero_threshold
                ):
                    if (
                        travelling_battery_space
                        not in travelling_battery_spaces.columns
                    ):
                        travelling_battery_spaces[
                            float(travelling_battery_space)
                        ] = float(0)

                    travelling_battery_spaces.loc[
                        (start_location, end_location),
                        travelling_battery_space,
                    ] = (
                        travelling_battery_spaces.loc[
                            start_location, end_location
                        ][travelling_battery_space]
                        + this_battery_space_departures_impact_this_time
                    )

    return battery_spaces, travelling_battery_spaces, departures_gap


def impact_of_arrivals(
    time_tag: datetime.datetime,
    battery_spaces: ty.Dict[str, pd.DataFrame],
    start_location: str,
    end_location: str,
    run_arrivals_impact: pd.Series,
    travelling_battery_spaces,  #: It's a DataFrame, but MyPy gives an error (
    # due to the MultiIndex)
    zero_threshold: float,
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, float]:

    time_tag_arrivals_impact: float = run_arrivals_impact.loc[
        start_location, end_location, time_tag
    ]

    battery_spaces_arriving_to_this_location = travelling_battery_spaces.loc[
        (start_location, end_location)
    ]

    arrivals_gap: float = max(
        0,
        time_tag_arrivals_impact
        - sum(battery_spaces_arriving_to_this_location),
    )

    if time_tag_arrivals_impact > zero_threshold:

        # We look at which battery spaces can arrive at the end
        # location. We sort them by size, as the ones with a lower
        # battery space are more likely to have left their origin first

        arriving_battery_spaces: ty.List[float] = sorted(
            travelling_battery_spaces.loc[start_location, end_location].index
        )

        # We iterate through the arriving battery spaces
        # (reminder, they are ordered from lowest to highest,
        # as we assumed that the lower the battery space, the higher
        # the likelihood to leave, as vehicles with more battery space/
        # less available battery capacity wll want to charge first).

        for arriving_battery_space in arriving_battery_spaces:

            # We will be removing the arrivals from the lower
            # battery spaces from the pool, until we have reached
            # all arrivals. For example, if we have 0.2 arrivals
            # and 0.19 vehicles with space equal to zero, 0.2 vehicles
            # with space 1, and 0.3 vehicles with space 1.6,
            # then we will first take all the
            # 0.19 vehicles with space 0,
            # 0.01 vehicles with space 1,
            # and 0 vehicles with space 1.6,
            # leaving us with 0 vehicles wth space 0,
            # 0.19 vehicles with
            # space 1, and 0.3 vehicles with space 1.6
            if time_tag_arrivals_impact > zero_threshold:
                # We do this until there are no departures left
                # We look at how much impact the travelling spaces
                # can have (it cannot be more than the arrivals impact from
                # the mobility matrix)
                this_battery_space_arrivals_impact_this_time: float = min(
                    time_tag_arrivals_impact,
                    battery_spaces_arriving_to_this_location.loc[
                        arriving_battery_space
                    ],
                )

                # We update the arrivals:
                time_tag_arrivals_impact -= (
                    this_battery_space_arrivals_impact_this_time
                )
                # We update the battery spaces:
                if (
                    arriving_battery_space
                    not in battery_spaces[end_location].columns.values
                ):
                    battery_spaces[end_location][arriving_battery_space] = (
                        float(0)
                    )

                battery_spaces[end_location].loc[
                    time_tag, arriving_battery_space
                ] = (
                    battery_spaces[end_location].loc[time_tag][
                        arriving_battery_space
                    ]
                    + this_battery_space_arrivals_impact_this_time
                )

                # We alo update the travelling battery spaces (as they have
                # arrived)
                travelling_battery_spaces.loc[
                    (start_location, end_location), arriving_battery_space
                ] = (
                    travelling_battery_spaces.loc[
                        start_location, end_location
                    ][arriving_battery_space]
                    - this_battery_space_arrivals_impact_this_time
                )

    return battery_spaces, travelling_battery_spaces, arrivals_gap


def travel_space_occupation(
    scenario: ty.Dict,
    battery_spaces: ty.Dict[str, pd.DataFrame],
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
    run_arrivals_impact_gaps: pd.Series,
    run_departures_impact: pd.Series,
    run_departures_impact_gaps: pd.Series,
    run_range: pd.DatetimeIndex,
    travelling_battery_spaces: pd.DataFrame,
    use_spillover: bool = False,
) -> ty.Dict[str, pd.DataFrame]:

    for location_to_compute in location_names:

        if time_tag_index > 0:
            # We add the values from the previous time tag to
            # the battery space. We do so because travels can propagate to
            # future time tags. I f we just copied the value from
            # the previous time tag, we would delete these
            battery_spaces[location_to_compute].iloc[time_tag_index] = (
                battery_spaces[location_to_compute].iloc[time_tag_index]
                + battery_spaces[location_to_compute].iloc[time_tag_index - 1]
            )

        if (
            use_day_types_in_charge_computing
            and (time_tag.hour == day_start_hour)
            and not use_spillover
        ):
            battery_spaces[location_to_compute].loc[time_tag, 0] = (
                location_split.loc[time_tag][location_to_compute]
            )

        # We need to look at the impact of arrivals first
        # because if we look at departures first, we might go wrong,
        # as some departures will be deemd not happening because
        # the battery space occupation would drop below zero (and
        # because we do the computations for occupations above zero)
        for start_location in possible_origins[location_to_compute]:
            battery_spaces, travelling_battery_spaces, arrivals_gap = (
                impact_of_arrivals(
                    time_tag,
                    battery_spaces,
                    start_location,
                    location_to_compute,
                    run_arrivals_impact,
                    travelling_battery_spaces,
                    zero_threshold,
                )
            )

            run_arrivals_impact_gaps.loc[
                start_location, location_to_compute, time_tag
            ] += arrivals_gap

        for end_location in possible_destinations[location_to_compute]:
            battery_spaces, travelling_battery_spaces, departures_gap = (
                impact_of_departures(
                    scenario,
                    time_tag,
                    battery_spaces,
                    location_to_compute,
                    end_location,
                    run_departures_impact,
                    travelling_battery_spaces,
                    zero_threshold,
                    run_mobility_matrix,
                )
            )

            run_departures_impact_gaps.loc[
                location_to_compute, end_location, time_tag
            ] += departures_gap

    for location_to_compute in location_names:
        this_time_tag_departures_gap: float = (
            run_departures_impact_gaps.groupby(['From', 'Time Tag'])
            .sum()
            .loc[location_to_compute, time_tag]
        )
        this_time_tag_arrivals_gap: float = (
            run_arrivals_impact_gaps.groupby(['To', 'Time Tag'])
            .sum()
            .loc[location_to_compute, time_tag]
        )

        if (
            max(this_time_tag_arrivals_gap, this_time_tag_departures_gap)
            > zero_threshold
        ):

            # If the departures gap is larger than the arrivals gap, we add
            # extra arrivals (from within the same hour) first. Otherwise,
            # we start wit the extra departures.

            for start_location in possible_origins[location_to_compute]:

                battery_spaces, travelling_battery_spaces, arrivals_gap = (
                    impact_of_arrivals(
                        time_tag,
                        battery_spaces,
                        start_location,
                        location_to_compute,
                        run_arrivals_impact_gaps,
                        travelling_battery_spaces,
                        zero_threshold,
                    )
                )

            for end_location in possible_destinations[location_to_compute]:

                battery_spaces, travelling_battery_spaces, departures_gap = (
                    impact_of_departures(
                        scenario,
                        time_tag,
                        battery_spaces,
                        location_to_compute,
                        end_location,
                        run_departures_impact_gaps,
                        travelling_battery_spaces,
                        zero_threshold,
                        run_mobility_matrix,
                    )
                )

    return battery_spaces


def compute_charging_events(
    battery_spaces: ty.Dict[str, pd.DataFrame],
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    time_tag: datetime.datetime,
    scenario: ty.Dict,
    general_parameters: ty.Dict,
    location_names: ty.List[str],
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:

    zero_threshold: float = general_parameters['numbers']['zero_threshold']
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
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
        original_battery_spaces: np.ndarray = battery_spaces[
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
            percent_charging * battery_spaces[charging_location].loc[time_tag]
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
                battery_spaces[charging_location].columns.values
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
                            battery_spaces[charging_location].columns.values
                        ):
                            battery_spaces[charging_location][
                                battery_space_after_charging
                            ] = float(0)

                        battery_spaces[charging_location].loc[
                            time_tag, battery_space_after_charging
                        ] = (
                            battery_spaces[charging_location].loc[time_tag][
                                battery_space_after_charging
                            ]
                            + vehicles_that_get_to_this_space
                        )

                        battery_spaces[charging_location].loc[
                            time_tag, original_battery_space
                        ] = (
                            battery_spaces[charging_location].loc[time_tag][
                                original_battery_space
                            ]
                            - vehicles_that_get_to_this_space
                        )

            battery_spaces[charging_location] = battery_spaces[
                charging_location
            ].reindex(
                sorted(battery_spaces[charging_location].columns), axis=1
            )

    return battery_spaces, charge_drawn_by_vehicles, charge_drawn_from_network


def copy_day_type_profiles_to_whole_run(
    scenario: ty.Dict,
    case_name: str,
    run_range: pd.DatetimeIndex,
    reference_day_type_time_tags: ty.Dict[str, ty.List[datetime.datetime]],
    location_split: pd.DataFrame,
    battery_spaces: ty.Dict[str, pd.DataFrame],
    day_end_hour: int,
    zero_threshold: float,
    possible_destinations: ty.Dict[str, ty.List[str]],
    possible_origins: ty.Dict[str, ty.List[str]],
    use_day_types_in_charge_computing: bool,
    general_parameters: ty.Dict,
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
) -> None:
    '''
    This copies the day type runs to whe whole run
    '''

    day_start_hour: int = scenario['mobility_module']['day_start_hour']
    HOURS_IN_A_DAY: int = general_parameters['time']['HOURS_IN_A_DAY']
    run_hours_from_day_start: ty.List[int] = [
        (time_tag.hour - day_start_hour) % HOURS_IN_A_DAY
        for time_tag in run_range
    ]

    run_day_types: ty.List[str] = [
        run_time.get_day_type(
            time_tag - datetime.timedelta(hours=day_start_hour),
            scenario,
            general_parameters,
        )
        for time_tag in run_range
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
    location_nodes: pd.DataFrame = pd.DataFrame(
        index=location_names, columns=['Connections']
    )
    possible_destinations, possible_origins = (
        mobility.get_possible_destinations_and_origins(scenario)
    )

    for location_name in location_names:
        location_nodes.loc[location_name, 'Connections'] = len(
            possible_destinations[location_name]
        ) + len(possible_origins[location_name])
    location_nodes = location_nodes.sort_values(
        by='Connections', ascending=False
    )
    location_names = list(location_nodes.index.values)

    filter_dataframe: pd.DataFrame = pd.DataFrame(
        run_day_types, columns=['Day Type'], index=run_range
    )

    filter_dataframe['Hours from day start'] = run_hours_from_day_start
    # The battery space DataFrame has another index:
    filter_for_battery_spaces: pd.DataFrame = pd.DataFrame(
        run_day_types,
        columns=['Day Type'],
        index=battery_spaces[location_names[0]].index,
    )
    filter_for_battery_spaces['Hours from day start'] = (
        run_hours_from_day_start
    )
    day_types: ty.List[str] = scenario['mobility_module']['day_types']

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
                battery_spaces[location_name].loc[
                    (filter_for_battery_spaces['Day Type'] == day_type)
                    & (
                        filter_for_battery_spaces['Hours from day start']
                        == hour_index
                    )
                ] = (
                    battery_spaces[location_name]
                    .loc[reference_day_type_time_tags[day_type][hour_index]]
                    .values
                )

    # The per day type approach has possible issues with cases where
    # a shift occurs over several days (such as holiday departures or
    # returns occurring over the two days of a weekend).
    # We therefore need to ensure that the sum of battery spaces is
    # equal to the location split. We do this by adjustinmg the battery
    # space with 0 kWh.

    for location_name in location_names:

        totals_from_battery_space: pd.DataFrame | pd.Series = battery_spaces[
            location_name
        ].sum(axis=1)

        target_location_split: pd.DataFrame | pd.Series = location_split[
            location_name
        ]

        location_correction: pd.DataFrame | pd.Series = (
            target_location_split - totals_from_battery_space
        ).astype(
            float
        )  # astype to keep type

        battery_spaces[location_name][0] = (
            battery_spaces[location_name][0] + location_correction
        )

    # Some trips result in charging events spilling over int the next day

    (
        spillover_battery_spaces,
        run_range,
        run_mobility_matrix,
        spillover_charge_drawn_by_vehicles,
        spillover_charge_drawn_from_network,
        run_arrivals_impact,
        run_arrivals_impact_gaps,
        run_departures_impact,
        run_departures_impact_gaps,
        spillover_travelling_battery_spaces,
    ) = get_charging_framework(scenario, case_name, general_parameters)

    # We first get all the days (day end time tags) that end with a spillover
    # at each of the locations
    day_ends_with_spillover_battery_spaces: ty.Dict = {}
    for location_name in location_names:

        day_end_battery_spaces: pd.DataFrame = battery_spaces[
            location_name
        ].loc[run_range.hour == day_end_hour]
        non_empty_day_end_battery_spaces: pd.DataFrame = (
            day_end_battery_spaces.drop(columns=float(0))
        )
        day_ends_with_spillover_battery_spaces[location_name] = (
            non_empty_day_end_battery_spaces.loc[
                non_empty_day_end_battery_spaces.sum(axis=1) > zero_threshold
            ].index.get_level_values('Time Tag')
        )

    # We look at the battery spillover spaces
    for spillover_location in location_names:
        # The get charging framework created a spillover Dataframe
        # with battery spaces starting aat the inital location split.
        # We don't need it for spillover (as it is zero)
        spillover_battery_spaces[spillover_location] = (
            spillover_battery_spaces[spillover_location].drop(float(0), axis=1)
        )

        for day_end_time_tag in day_ends_with_spillover_battery_spaces[
            spillover_location
        ]:

            spillover_time_tag_index: int = list(run_range).index(
                day_end_time_tag
            )
            spillover_amounts_per_battery_space: pd.Series = (
                battery_spaces[spillover_location]
                .drop(columns=float(0))
                .loc[day_end_time_tag]
            )

            amount_in_spillover: float = (
                spillover_amounts_per_battery_space.sum()
            )

            while amount_in_spillover > zero_threshold:
                spillover_time_tag_index += 1

                if spillover_time_tag_index >= len(run_range) - 1:
                    amount_in_spillover = 0
                    # Does not matter, as the run is then over

                spillover_time_tag: ty.Any = run_range[
                    spillover_time_tag_index
                ]

                battery_spaces[spillover_location].loc[
                    spillover_time_tag, float(0)
                ] = (
                    battery_spaces[spillover_location].loc[spillover_time_tag][
                        float(0)
                    ]
                    - amount_in_spillover
                )
                occupied_spillover_battery_spaces: ty.List[float] = []
                for (
                    test_battery_space
                ) in spillover_amounts_per_battery_space.index:
                    if (
                        spillover_amounts_per_battery_space[test_battery_space]
                        > zero_threshold
                    ):
                        occupied_spillover_battery_spaces.append(
                            test_battery_space
                        )

                for (
                    occupied_spillover_battery_space
                ) in occupied_spillover_battery_spaces:

                    battery_spaces[spillover_location].loc[
                        spillover_time_tag,
                        occupied_spillover_battery_space,
                    ] = (
                        battery_spaces[spillover_location].loc[
                            spillover_time_tag
                        ][occupied_spillover_battery_space]
                        + spillover_amounts_per_battery_space[
                            occupied_spillover_battery_space
                        ]
                    )
                    if (
                        occupied_spillover_battery_space
                        not in spillover_battery_spaces[
                            spillover_location
                        ].columns
                    ):
                        spillover_battery_spaces[spillover_location][
                            occupied_spillover_battery_space
                        ] = float(0)
                    spillover_battery_spaces[spillover_location].loc[
                        spillover_time_tag,
                        float(occupied_spillover_battery_space),
                    ] = (
                        spillover_battery_spaces[spillover_location].loc[
                            spillover_time_tag
                        ][occupied_spillover_battery_space]
                        + spillover_amounts_per_battery_space[
                            occupied_spillover_battery_space
                        ]
                    )

                fully_charged_vehicles: float = battery_spaces[
                    spillover_location
                ].iloc[spillover_time_tag_index - 1][float(0)]

                time_tag_departures_impact: float = run_departures_impact.loc[
                    spillover_location,
                    possible_destinations[spillover_location],
                    spillover_time_tag,
                ].sum()

                if (
                    time_tag_departures_impact - fully_charged_vehicles
                    > zero_threshold
                ):
                    print(spillover_time_tag)
                    print(spillover_location)
                    print(
                        battery_spaces[spillover_location]
                        .loc[spillover_time_tag]
                        .sum()
                    )
                    print(time_tag_departures_impact)
                    print(fully_charged_vehicles)
                    print('Do a proecedure for this')
                    exit()

                spillover_battery_spaces_before_charging: pd.Series = (
                    spillover_battery_spaces[spillover_location]
                    .loc[spillover_time_tag]
                    .copy()
                    # The copy is needed because
                    # the spillover battery spaces can change, which
                    # affects spillover_battery_spaces_before_charging
                    # (but apparently only if there is only one value)
                )

                (
                    spillover_battery_spaces,
                    spillover_charge_drawn_by_vehicles,
                    spillover_charge_drawn_from_network,
                ) = compute_charging_events(
                    spillover_battery_spaces,
                    spillover_charge_drawn_by_vehicles,
                    spillover_charge_drawn_from_network,
                    spillover_time_tag,
                    scenario,
                    general_parameters,
                    location_names,
                )

                spillover_battery_spaces_after_charging: pd.Series = (
                    spillover_battery_spaces[spillover_location].loc[
                        spillover_time_tag
                    ]
                )

                spillover_battery_spaces_change: pd.Series = (
                    spillover_battery_spaces_after_charging.add(
                        -spillover_battery_spaces_before_charging, fill_value=0
                    )
                )

                # We put the fully charged spillover vehicles
                # into the battery spaces and remove them from
                # the spillover battery spaces

                if spillover_time_tag_index < len(run_range) - 1:

                    for (
                        modified_battery_space
                    ) in spillover_battery_spaces_change.index:
                        battery_spaces[spillover_location].loc[
                            spillover_time_tag, modified_battery_space
                        ] = (
                            battery_spaces[spillover_location].loc[
                                spillover_time_tag
                            ][modified_battery_space]
                            + spillover_battery_spaces_change[
                                modified_battery_space
                            ]
                        )

                spillover_battery_spaces[spillover_location] = (
                    spillover_battery_spaces[spillover_location].drop(
                        float(0), axis=1
                    )
                )

                charge_drawn_by_vehicles.loc[
                    spillover_time_tag, spillover_location
                ] = (
                    charge_drawn_by_vehicles.loc[spillover_time_tag][
                        spillover_location
                    ]
                    + spillover_charge_drawn_by_vehicles.loc[
                        spillover_time_tag
                    ][spillover_location]
                )

                charge_drawn_from_network.loc[
                    spillover_time_tag, spillover_location
                ] = (
                    charge_drawn_from_network.loc[spillover_time_tag][
                        spillover_location
                    ]
                    + spillover_charge_drawn_from_network.loc[
                        spillover_time_tag
                    ][spillover_location]
                )

                spillover_amounts_per_battery_space = spillover_battery_spaces[
                    spillover_location
                ].loc[spillover_time_tag]

                amount_in_spillover = spillover_amounts_per_battery_space.sum()


def write_output(
    battery_spaces: ty.Dict[str, pd.DataFrame],
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
        battery_spaces[location_name].columns = battery_spaces[
            location_name
        ].columns.astype(str)
        battery_spaces[location_name] = battery_spaces[
            location_name
        ].reset_index()
        battery_spaces[location_name]['Hour Number'] = run_hour_numbers
        battery_spaces[location_name]['SPINE_Hour_Number'] = SPINE_hour_numbers
        battery_spaces[location_name] = battery_spaces[
            location_name
        ].set_index(['Time Tag', 'Hour Number', 'SPINE_Hour_Number'])
        battery_spaces[location_name].to_pickle(
            f'{output_folder}/{scenario_name}_'
            f'{location_name}_battery_spaces.pkl'
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
        sum_of_battery_spaces_this_location: pd.Series[float] = battery_spaces[
            location_name
        ].sum(axis=1)
        sum_of_battery_spaces[location_name] = (
            sum_of_battery_spaces_this_location.values
        )

    sum_of_battery_spaces.to_pickle(
        f'{output_folder}/{scenario_name}_sum_of_battery_spaces.pkl'
    )


def get_charging_profile(
    scenario: ty.Dict,
    case_name: str,
    general_parameters: ty.Dict,
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    '''
    This is the main function of the charging module.
    It produces the charging profile
    '''

    (
        battery_spaces,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        run_arrivals_impact,
        run_arrivals_impact_gaps,
        run_departures_impact,
        run_departures_impact_gaps,
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
    location_nodes: pd.DataFrame = pd.DataFrame(
        index=location_names, columns=['Connections']
    )
    possible_destinations, possible_origins = (
        mobility.get_possible_destinations_and_origins(scenario)
    )

    for location_name in location_names:
        location_nodes.loc[location_name, 'Connections'] = len(
            possible_destinations[location_name]
        ) + len(possible_origins[location_name])
    location_nodes = location_nodes.sort_values(
        by='Connections', ascending=False
    )
    location_names = list(location_nodes.index.values)

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
        # if time_tag.hour == 0 and time_tag.day == 1:
        #     print(time_tag.day, time_tag.month)
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
            battery_spaces = travel_space_occupation(
                scenario,
                battery_spaces,
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
                run_arrivals_impact_gaps,
                run_departures_impact,
                run_departures_impact_gaps,
                run_range,
                travelling_battery_spaces,
            )

            # We then look at which charging happens
            (
                battery_spaces,
                charge_drawn_by_vehicles,
                charge_drawn_from_network,
            ) = compute_charging_events(
                battery_spaces,
                charge_drawn_by_vehicles,
                charge_drawn_from_network,
                time_tag,
                scenario,
                general_parameters,
                location_names,
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
            case_name,
            run_range,
            reference_day_type_time_tags,
            location_split,
            battery_spaces,
            day_end_hour,
            zero_threshold,
            possible_destinations,
            possible_origins,
            use_day_types_in_charge_computing,
            general_parameters,
            charge_drawn_by_vehicles,
            charge_drawn_from_network,
        )

    write_output(
        battery_spaces,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        scenario,
        case_name,
        general_parameters,
    )

    return battery_spaces, charge_drawn_by_vehicles, charge_drawn_from_network


if __name__ == '__main__':
    case_name = 'local_impact_BEVs'
    test_scenario_name: str = 'baseline'
    case_name = 'Mopo'
    test_scenario_name = 'XX_car'
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
        battery_spaces,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
    ) = get_charging_profile(scenario, case_name, general_parameters)

    print((datetime.datetime.now() - start_).total_seconds())
