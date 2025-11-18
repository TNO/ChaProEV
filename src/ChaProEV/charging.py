import datetime
import typing as ty

import numpy as np
import pandas as pd
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print

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


def get_time_modulation(
    run_range: pd.DatetimeIndex, scenario: Box, general_parameters: Box
) -> pd.DataFrame:
    time_modulation: pd.DataFrame = pd.DataFrame(
        np.ones((len(run_range), len(scenario.locations))),
        columns=scenario.locations,
        index=run_range,
    )
    for location in scenario.locations:
        time_modulation_factors: list[float] = scenario.locations[
            location
        ].time_modulation_factors
        for hour_index, time_modulation_factor in enumerate(
            time_modulation_factors
        ):
            time_modulation.loc[
                pd.to_datetime(time_modulation.index).hour == hour_index,
                location,
            ] = time_modulation_factor

    return time_modulation


def get_charging_modulation(
    run_range: pd.DatetimeIndex,
    scenario: Box,
    general_parameters: Box,
) -> pd.DataFrame:
    charging_modulation: pd.DataFrame = get_time_modulation(
        run_range, scenario, general_parameters
    )

    location_prices: list[float] = [
        scenario.locations[location_tested].charging_price
        for location_tested in scenario.locations
    ]

    if scenario.charging.price_reaction_exponent > 0:
        location_price_factor: pd.Series = pd.Series(
            [
                (
                    (min(location_prices) / (location_price))
                    ** scenario.charging.price_reaction_exponent
                    if location_price > 0
                    else 1
                )
                for location_price in location_prices
            ],
            index=scenario.locations,
        )
    else:
        location_price_factor = pd.Series(
            np.ones(len(scenario.locations)), index=scenario.locations
        )

    location_desirabilities: list[float] = [
        scenario.locations[location_tested].charging_desirability
        for location_tested in scenario.locations
    ]

    if scenario.charging.desirability_reaction_exponent > 0:
        location_desirability_factor: pd.Series = pd.Series(
            [
                (
                    (location_desirability / max(location_desirabilities))
                    ** scenario.charging.desirability_reaction_exponent
                )
                for location_desirability in location_desirabilities
            ],
            index=scenario.locations,
        )
    else:
        location_desirability_factor = pd.Series(
            np.ones(len(scenario.locations)), index=scenario.locations
        )

    for location in scenario.locations:
        charging_modulation[location] *= (
            location_price_factor[location]
            * location_desirability_factor[location]
        )

    return charging_modulation


def get_charging_framework(
    location_split: pd.DataFrame,
    run_mobility_matrix: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> tuple[
    dict[str, pd.DataFrame],
    pd.DatetimeIndex,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.Series,
    pd.Series,
    pd.Series,
    pd.Series,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    '''
    Produces the structures we want for the charging profiles
    '''

    run_range: pd.DatetimeIndex = run_time.get_time_range(
        scenario, general_parameters
    )[0]

    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name
    location_parameters: Box = scenario.locations
    location_names: list[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name].vehicle == vehicle_name
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

    # We create a dictionary of various battery spaces that are available
    # at each charging location (i.e. percent of vehicles with
    # a given battery space per location) (locations are keys and
    # battery space dataframes are dictionary entries)
    battery_spaces: dict[str, pd.DataFrame] = {}
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
    total_battery_space_per_location: pd.DataFrame = pd.DataFrame(
        index=run_range, columns=location_names
    )
    total_battery_space_per_location.index.name = 'Time Tag'

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

    mobility_location_tuples: list[tuple[str, str]] = (
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
    charging_modulation: pd.DataFrame = get_charging_modulation(
        run_range, scenario, general_parameters
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
        total_battery_space_per_location,
        charging_modulation,
    )


def impact_of_departures(
    scenario: Box,
    time_tag: datetime.datetime,
    battery_spaces: dict[str, pd.DataFrame],
    start_location: str,
    end_location: str,
    run_departures_impact: pd.Series,
    travelling_battery_spaces,  # it's a DataFarame but MyPy gives an error,
    zero_threshold: float,
    run_mobility_matrix,  # it's a DataFarame but MyPy gives an error,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, float]:

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
        departing_battery_spaces: list[float] = sorted(
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
                    ],  # type: ignore
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
                vehicle_electricity_consumption: float = scenario.vehicle[
                    'base_consumption_per_km'
                ].electricity_kWh

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
    battery_spaces: dict[str, pd.DataFrame],
    start_location: str,
    end_location: str,
    run_arrivals_impact: pd.Series,
    travelling_battery_spaces,  #: It's a DataFrame, but MyPy gives an error (
    # due to the MultiIndex)
    zero_threshold: float,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, float]:

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

        arriving_battery_spaces: list[float] = sorted(
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
    scenario: Box,
    battery_spaces: dict[str, pd.DataFrame],
    time_tag: datetime.datetime,
    time_tag_index: int,
    run_mobility_matrix,  # This is a DataFrame, but MyPy has issues with it
    # These issues might have to do with MultiIndex,
    zero_threshold: float,
    location_names: list[str],
    possible_destinations: dict[str, list[str]],
    possible_origins: dict[str, list[str]],
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
) -> dict[str, pd.DataFrame]:

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
    battery_spaces: dict[str, pd.DataFrame],
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    time_tag: datetime.datetime,
    scenario: Box,
    general_parameters: Box,
    location_names: list[str],
    charging_modulation: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:

    zero_threshold: float = general_parameters.numbers.zero_threshold
    location_parameters: Box = scenario.locations

    for charging_location in location_names:
        charging_location_parameters: Box = location_parameters[
            charging_location
        ]

        charger_efficiency: float = (
            charging_location_parameters.charger_efficiency
        )

        percent_charging: float = charging_location_parameters.connectivity
        location_charging_power: float = float(
            charging_location_parameters.charging_power
        )
        location_modulated_charging_power: float = (
            location_charging_power
            * float(
                charging_modulation.loc[time_tag][
                    charging_location
                ]  # type: ignore
            )  # type: ignore
        )

        # This variable is useful if new battery spaces
        # are added within this charging procedure
        original_battery_spaces: np.ndarray = battery_spaces[
            charging_location
        ].columns.values
        charge_drawn_per_charging_vehicle: np.ndarray = np.array(
            [
                min(this_battery_space, location_modulated_charging_power)
                for this_battery_space in original_battery_spaces
            ]
        )
        network_charge_drawn_per_charging_vehicle: np.ndarray = (
            charge_drawn_per_charging_vehicle / charger_efficiency
        )

        vehicles_charging: ty.Any = (
            percent_charging * battery_spaces[charging_location].loc[time_tag]
        )  # It is a float, but MyPy does not get it

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
        if (
            charge_drawn_by_vehicles_this_time_tag > zero_threshold
        ):  # type: ignore

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
    scenario: Box,
    case_name: str,
    run_range: pd.DatetimeIndex,
    reference_day_type_time_tags: dict[str, list[datetime.datetime]],
    location_split: pd.DataFrame,
    run_mobility_matrix: pd.DataFrame,
    battery_spaces: dict[str, pd.DataFrame],
    day_end_hour: int,
    zero_threshold: float,
    possible_destinations: dict[str, list[str]],
    possible_origins: dict[str, list[str]],
    use_day_types_in_charge_computing: bool,
    general_parameters: Box,
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
) -> None:
    '''
    This copies the day type runs to whe whole run
    '''

    day_start_hour: int = scenario.mobility_module.day_start_hour
    HOURS_IN_A_DAY: int = general_parameters.time.HOURS_IN_A_DAY
    run_hours_from_day_start: list[int] = [
        (time_tag.hour - day_start_hour) % HOURS_IN_A_DAY
        for time_tag in run_range
    ]

    run_day_types: list[str] = [
        run_time.get_day_type(
            time_tag - datetime.timedelta(hours=day_start_hour),
            scenario,
            general_parameters,
        )
        for time_tag in run_range
    ]

    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name

    location_parameters: Box = scenario.locations
    location_names: list[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name].vehicle == vehicle_name
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
    day_types: list[str] = scenario.mobility_module.day_types

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
    # equal to the location split. We do this by adjusting the battery
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

    # Some trips result in charging events spilling over into the next day

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
        total_battery_space_per_location,
        charging_modulation,
    ) = get_charging_framework(
        location_split,
        run_mobility_matrix,
        scenario,
        case_name,
        general_parameters,
    )

    # We first get all the days (day end time tags) that end with a spillover
    # at each of the locations
    day_ends_with_spillover_battery_spaces: dict = {}
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
                occupied_spillover_battery_spaces: list[float] = []
                for (
                    test_battery_space
                ) in spillover_amounts_per_battery_space.index:
                    if (
                        spillover_amounts_per_battery_space[test_battery_space]
                        > zero_threshold
                    ):  # type: ignore
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
                    print('Do a procedure for this')
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
                    charging_modulation,
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
                        if (
                            modified_battery_space
                            not in battery_spaces[spillover_location].columns
                        ):
                            battery_spaces[spillover_location][
                                modified_battery_space
                            ] = float(0)
                            # We sort the battery spaces for consistency
                            battery_spaces[
                                spillover_location
                            ] = battery_spaces[spillover_location].reindex(
                                sorted(
                                    battery_spaces[spillover_location].columns
                                ),
                                axis=1,
                            )
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

                if (
                    float(0)
                    in spillover_battery_spaces[spillover_location].columns
                ):
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
    battery_spaces: dict[str, pd.DataFrame],
    total_battery_space_per_location: pd.DataFrame,
    charge_drawn_by_vehicles: pd.DataFrame,
    charge_drawn_from_network: pd.DataFrame,
    charging_costs: pd.DataFrame,
    scenario: Box,
    case_name: str,
    maximal_delivered_power_per_location: pd.DataFrame,
    maximal_delivered_power: pd.DataFrame,
    general_parameters: Box,
) -> None:
    '''
    Writes the outputs to files
    '''

    run_range, run_hour_numbers, display_range = run_time.get_time_range(
        scenario, general_parameters
    )
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    SPINE_hour_numbers: list[str] = [
        f't{hour_number:04}' for hour_number in run_hour_numbers
    ]
    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name
    location_parameters: Box = scenario.locations
    location_names: list[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name].vehicle == vehicle_name
    ]
    scenario.name

    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'

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
        if pickle_interim_files:
            battery_spaces[location_name].to_pickle(
                f'{output_folder}/{scenario.name}_'
                f'{location_name}_battery_spaces.pkl'
            )
    charge_drawn_from_network = charge_drawn_from_network.reset_index()
    charge_drawn_from_network['Hour number'] = run_hour_numbers
    charge_drawn_from_network['SPINE hour number'] = SPINE_hour_numbers
    charge_drawn_from_network = charge_drawn_from_network.set_index(
        ['Time Tag', 'Hour number', 'SPINE hour number']
    )
    if pickle_interim_files:
        charge_drawn_from_network.to_pickle(
            f'{output_folder}/{scenario.name}_charge_drawn_from_network.pkl'
        )
        charging_costs.to_pickle(
            f'{output_folder}/{scenario.name}_charging_costs.pkl'
        )

    charge_drawn_from_network_total: pd.DataFrame = pd.DataFrame(
        index=charge_drawn_from_network.index
    )
    charge_drawn_from_network_total['Total Charge Drawn (kWh)'] = (
        charge_drawn_from_network.sum(axis=1)
    )

    charging_costs_total: pd.Series = charging_costs.sum(axis=1)
    percentage_of_maximal_delivered_power_used_per_location: pd.DataFrame = (
        pd.DataFrame(index=charge_drawn_from_network.index)
    )
    if pickle_interim_files:
        charge_drawn_from_network_total.to_pickle(
            f'{output_folder}/{scenario.name}_'
            'charge_drawn_from_network_total.pkl'
        )
        charging_costs_total.to_pickle(
            f'{output_folder}/{scenario.name}_total_charging_costs.pkl'
        )

    if pickle_interim_files:
        total_battery_space_per_location.to_pickle(
            f'{output_folder}/{scenario.name}_'
            'total_battery_space_per_location.pkl'
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
    if pickle_interim_files:
        percentage_of_maximal_delivered_power_used_per_location.to_pickle(
            f'{output_folder}/{scenario.name}_'
            f'percentage_of_maximal_delivered_power_used_per_location.pkl'
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
    if pickle_interim_files:
        percentage_of_maximal_delivered_power_used.to_pickle(
            f'{output_folder}/{scenario.name}'
            f'_percentage_of_maximal_delivered_power_used.pkl'
        )

    charge_drawn_by_vehicles = charge_drawn_by_vehicles.reset_index()
    charge_drawn_by_vehicles['Hour number'] = run_hour_numbers
    charge_drawn_by_vehicles['SPINE hour number'] = SPINE_hour_numbers
    charge_drawn_by_vehicles = charge_drawn_by_vehicles.set_index(
        ['Time Tag', 'Hour number', 'SPINE hour number']
    )
    if pickle_interim_files:
        charge_drawn_by_vehicles.to_pickle(
            f'{output_folder}/{scenario.name}_charge_drawn_by_vehicles.pkl'
        )

    charge_drawn_by_vehicles_total: pd.DataFrame = pd.DataFrame(
        index=charge_drawn_by_vehicles.index
    )
    charge_drawn_by_vehicles_total['Total Charge Drawn (kWh)'] = (
        charge_drawn_by_vehicles.sum(axis=1)
    )
    percentage_of_maximal_delivered_power_used_per_location = pd.DataFrame(
        index=charge_drawn_by_vehicles.index
    )
    if pickle_interim_files:
        charge_drawn_by_vehicles_total.to_pickle(
            f'{output_folder}/{scenario.name}'
            '_charge_drawn_by_vehicles_total.pkl'
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
    if pickle_interim_files:
        sum_of_battery_spaces.to_pickle(
            f'{output_folder}/{scenario.name}_sum_of_battery_spaces.pkl'
        )


# @cook.function_timer
def get_charging_profile(
    location_split: pd.DataFrame,
    run_mobility_matrix: pd.DataFrame,
    maximal_delivered_power_per_location: pd.DataFrame,
    maximal_delivered_power: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> tuple[
    dict[str, pd.DataFrame],
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
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
        total_battery_space_per_location,
        charging_modulation,
    ) = get_charging_framework(
        location_split,
        run_mobility_matrix,
        scenario,
        case_name,
        general_parameters,
    )

    # We want to either compute charging for the whole run, or only
    # do it per day type (to compute faster by avoiding repeats)
    compute_charge: bool = True
    day_types: list[str] = scenario.mobility_module.day_types
    use_day_types_in_charge_computing: bool = scenario.run[
        'use_day_types_in_charge_computing'
    ]

    if use_day_types_in_charge_computing:
        compute_charge = False
        day_types_to_compute: list[str] = day_types.copy()
        reference_day_type_time_tags: dict[str, list[datetime.datetime]] = {}
        time_tags_of_day_type: list[datetime.datetime] = []

    day_start_hour: int = scenario.mobility_module.day_start_hour
    HOURS_IN_A_DAY: int = general_parameters.time.HOURS_IN_A_DAY
    day_end_hour: int = (day_start_hour - 1) % HOURS_IN_A_DAY
    run_day_types: list[str] = [
        run_time.get_day_type(
            time_tag - datetime.timedelta(hours=day_start_hour),
            scenario,
            general_parameters,
        )
        for time_tag in run_range
    ]

    zero_threshold: float = general_parameters.numbers.zero_threshold
    vehicle_parameters: Box = scenario.vehicle
    vehicle_name: str = vehicle_parameters.name

    location_parameters: Box = scenario.locations
    location_names: list[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name].vehicle == vehicle_name
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

    for time_tag_index, (time_tag, run_day_type) in enumerate(
        zip(run_range, run_day_types)
    ):

        if (
            use_day_types_in_charge_computing
            and (time_tag.hour == day_start_hour)
            and (run_day_type in day_types_to_compute)  # type: ignore
        ):
            # For the da to be representative, it cannot have
            # charging from the prior day (this spillover issue
            # will be dealt with later)
            weighted_residual_battery_spaces: float = 0
            for charging_location_to_test in location_names:
                location_residual_battery_spaces: pd.Series = battery_spaces[
                    charging_location_to_test
                ].iloc[time_tag_index - 1]
                location_weighted_residual_battery_spaces: float = (
                    location_residual_battery_spaces.index.values
                    * location_residual_battery_spaces
                ).sum()
                weighted_residual_battery_spaces += (
                    location_weighted_residual_battery_spaces
                )
            does_charge_demand_spillover: bool = (
                weighted_residual_battery_spaces > zero_threshold
            )

            if not does_charge_demand_spillover:
                day_types_to_compute.remove(run_day_type)  # type: ignore
                compute_charge = True
                time_tags_of_day_type = []

        if compute_charge:

            if use_day_types_in_charge_computing:
                time_tags_of_day_type.append(time_tag)  # type: ignore

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
                charging_modulation,
            )

            if use_day_types_in_charge_computing and (
                time_tag.hour == day_end_hour
            ):
                compute_charge = False
                reference_day_type_time_tags[run_day_type] = (  # type: ignore
                    time_tags_of_day_type
                )  # type: ignore

    if use_day_types_in_charge_computing:

        copy_day_type_profiles_to_whole_run(
            scenario,
            case_name,
            run_range,
            reference_day_type_time_tags,  # type: ignore
            location_split,
            run_mobility_matrix,
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

    for location_name in location_names:
        location_total_battery_space: pd.Series = pd.Series(
            np.zeros(len(run_range)), index=run_range
        )

        for battery_space in battery_spaces[location_name].columns:

            location_total_battery_space += (
                pd.Series(battery_spaces[location_name][battery_space].values)
                * float(battery_space)
            ).values

        total_battery_space_per_location[location_name] = (
            location_total_battery_space
        )
    charging_costs: pd.DataFrame = charge_drawn_from_network.copy()
    for location in scenario.locations:
        charging_costs[location] *= scenario.locations[location].charging_price
    write_output(
        battery_spaces,
        total_battery_space_per_location,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        charging_costs,
        scenario,
        case_name,
        maximal_delivered_power_per_location,
        maximal_delivered_power,
        general_parameters,
    )

    return (
        battery_spaces,
        total_battery_space_per_location,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        charging_costs,
    )


def session_modulation(
    run_charging_sessions_dataframe: pd.DataFrame,
) -> pd.Series:

    modulation_factor: pd.Series = pd.Series(
        np.ones(len(run_charging_sessions_dataframe.index))
    )
    return modulation_factor


# @cook.function_timer
def charging_amounts_in_charging_sessions(
    run_charging_sessions_dataframe: pd.DataFrame,
    scenario: Box,
    general_parameters: Box,
    case_name: str,
) -> pd.DataFrame:
    charging_sessions_with_charged_amounts: pd.DataFrame = (
        run_charging_sessions_dataframe.copy()
    )
    charging_sessions_with_charged_amounts['Duration (hours)'] = (
        charging_sessions_with_charged_amounts['End time']
        - charging_sessions_with_charged_amounts['Start time']
    ).astype('timedelta64[s]').astype(
        int
    ) / general_parameters.time.SECONDS_PER_HOUR

    charging_sessions_with_charged_amounts['Target charge (kWh)'] = (
        charging_sessions_with_charged_amounts[
            'Demand for incoming leg (kWh) (to vehicle)'
        ]
    )
    charging_sessions_with_charged_amounts[
        'Maximal Possible Charge to Vehicles (kWh)'
    ] = (
        charging_sessions_with_charged_amounts['Duration (hours)']
        * charging_sessions_with_charged_amounts[
            'Charging Power to Vehicles (kW)'
        ]
    )
    charging_sessions_with_charged_amounts['Modulation factor'] = (
        session_modulation(charging_sessions_with_charged_amounts).values
    )
    charging_sessions_with_charged_amounts[
        'Available Charge to Vehicles (kWh)'
    ] = charging_sessions_with_charged_amounts['Modulation factor'].multiply(
        charging_sessions_with_charged_amounts[
            'Maximal Possible Charge to Vehicles (kWh)'
        ]
    )
    charging_sessions_with_charged_amounts['Charge to Vehicles (kWh)'] = (
        charging_sessions_with_charged_amounts[
            [
                'Available Charge to Vehicles (kWh)',
                'Target charge (kWh)',
            ]
        ].min(axis=1)
    )
    charging_sessions_with_charged_amounts['Charge deficit (kWh)'] = (
        charging_sessions_with_charged_amounts['Target charge (kWh)']
        - charging_sessions_with_charged_amounts[
            'Available Charge to Vehicles (kWh)'
        ]
    )
    charging_sessions_with_charged_amounts['Charge deficit (kWh)'] = [
        0 if deficit < 0 else deficit
        for deficit in charging_sessions_with_charged_amounts[
            'Charge deficit (kWh)'
        ].values
    ]
    total_charge_deficit: float = charging_sessions_with_charged_amounts[
        'Charge deficit (kWh)'
    ].sum()

    while total_charge_deficit > 0:
        rolled_deficit: np.ndarray = np.roll(
            charging_sessions_with_charged_amounts['Charge deficit (kWh)'], 1
        )

        charging_sessions_with_charged_amounts['Target charge (kWh)'] = (
            charging_sessions_with_charged_amounts['Target charge (kWh)']
            - charging_sessions_with_charged_amounts['Charge deficit (kWh)']
        )
        charging_sessions_with_charged_amounts['Target charge (kWh)'] = (
            charging_sessions_with_charged_amounts[
                'Target charge (kWh)'
            ].values
            + rolled_deficit
        )

        charging_sessions_with_charged_amounts['Charge to Vehicles (kWh)'] = (
            charging_sessions_with_charged_amounts[
                [
                    'Available Charge to Vehicles (kWh)',
                    'Target charge (kWh)',
                ]
            ].min(axis=1)
        )
        charging_sessions_with_charged_amounts['Charge deficit (kWh)'] = (
            charging_sessions_with_charged_amounts['Target charge (kWh)']
            - charging_sessions_with_charged_amounts[
                'Available Charge to Vehicles (kWh)'
            ]
        )
        charging_sessions_with_charged_amounts['Charge deficit (kWh)'] = [
            0 if deficit < 0 else deficit
            for deficit in charging_sessions_with_charged_amounts[
                'Charge deficit (kWh)'
            ].values
        ]
        total_charge_deficit = charging_sessions_with_charged_amounts[
            'Charge deficit (kWh)'
        ].sum()

    charging_sessions_locations: list[str] = list(
        set(charging_sessions_with_charged_amounts['Location'])
    )
    location_charger_loss_factors: list[float] = [
        1 / scenario.locations[session_location].charger_efficiency
        for session_location in charging_sessions_locations
    ]
    location_loss_factors_dict: dict[str, float] = dict(
        zip(charging_sessions_locations, location_charger_loss_factors)
    )

    charging_sessions_with_charged_amounts[
        'Charge from Network (kWh)'
    ] = charging_sessions_with_charged_amounts[
        'Charge to Vehicles (kWh)'
    ] * charging_sessions_with_charged_amounts[
        'Location'
    ].map(
        location_loss_factors_dict
    )
    charging_sessions_with_charged_amounts[
        'Duration at constant charge (hours)'
    ] = charging_sessions_with_charged_amounts['Charge to Vehicles (kWh)'] / (
        charging_sessions_with_charged_amounts['Modulation factor']
        * charging_sessions_with_charged_amounts[
            'Charging Power to Vehicles (kW)'
        ]
    )
    constant_charge_time_shifts: pd.Series = pd.Series(
        [
            datetime.timedelta(hours=constant_charge_time)
            for constant_charge_time in charging_sessions_with_charged_amounts[
                'Duration at constant charge (hours)'
            ]
        ]
    )
    charging_sessions_with_charged_amounts[
        'End time if constant charge from start'
    ] = (
        charging_sessions_with_charged_amounts['Start time']
        + constant_charge_time_shifts
    )
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    output_root: str = general_parameters.files.output_root
    if pickle_interim_files:
        charging_sessions_with_charged_amounts.to_pickle(
            f'{output_root}/{case_name}/{scenario.name}_'
            f'charging_sessions_with_charged_amounts.pkl'
        )

    return charging_sessions_with_charged_amounts


# @cook.function_timer
def get_profile_from_sessions(
    sessions: pd.DataFrame,
    scenario: Box,
    general_parameters: Box,
    case_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    charging_profile_from_sessions: pd.DataFrame = (
        run_time.get_time_stamped_dataframe(scenario, general_parameters)
    ).fillna(0)
    charging_profile_to_vehicle_from_sessions: pd.DataFrame = (
        run_time.get_time_stamped_dataframe(scenario, general_parameters)
    ).fillna(0)
    charging_profile_from_network_from_sessions: pd.DataFrame = (
        run_time.get_time_stamped_dataframe(scenario, general_parameters)
    ).fillna(0)

    sessions_charging_slots: list = [
        pd.date_range(
            start=session_start.replace(second=0, microsecond=0, minute=0),
            end=session_end.replace(second=0, microsecond=0, minute=0),
            inclusive='both',
            freq='1h',
        )
        for session_start, session_end in zip(
            sessions['Start time'],
            sessions['End time if constant charge from start'],
        )
    ]
    used_powers_to_vehicle: pd.Series = (
        sessions['Charging Power to Vehicles (kW)']
        * sessions['Modulation factor']
    )
    used_powers_from_network: pd.Series = (
        sessions['Charging Power from Network (kW)']
        * sessions['Modulation factor']
    )
    sessions_charging_slots_charge_factors_to_vehicle: list[np.ndarray] = [
        used_power * np.ones(len(session_charging_slots))
        for session_charging_slots, used_power in zip(
            sessions_charging_slots, used_powers_to_vehicle
        )
    ]
    sessions_charging_slots_charge_factors_from_network: list[np.ndarray] = [
        used_power * np.ones(len(session_charging_slots))
        for session_charging_slots, used_power in zip(
            sessions_charging_slots, used_powers_from_network
        )
    ]

    for (
        session_charging_slots_charge_factors_to_vehicle,
        session_charging_slots_charge_factors_from_network,
        start_time,
        end_time,
        session_charging_slots,
    ) in zip(
        sessions_charging_slots_charge_factors_to_vehicle,
        sessions_charging_slots_charge_factors_from_network,
        sessions['Start time'],
        sessions['End time if constant charge from start'],
        sessions_charging_slots,
    ):

        first_slot_non_charging_portion: float = (
            start_time - session_charging_slots[0]
        ).total_seconds() / general_parameters.time.SECONDS_PER_HOUR
        last_slot_charging_portion: float = (
            end_time - session_charging_slots[-1]
        ).total_seconds() / general_parameters.time.SECONDS_PER_HOUR

        session_charging_slots_charge_factors_to_vehicle[0] *= (
            1 - first_slot_non_charging_portion
        )
        session_charging_slots_charge_factors_from_network[0] *= (
            1 - first_slot_non_charging_portion
        )
        session_charging_slots_charge_factors_to_vehicle[
            -1
        ] *= last_slot_charging_portion
        session_charging_slots_charge_factors_from_network[
            -1
        ] *= last_slot_charging_portion

    for (
        location,
        session_charging_slots,
        session_charging_slots_charge_factors_to_vehicle,
        session_charging_slots_charge_factors_from_network,
    ) in zip(
        sessions['Location'],
        sessions_charging_slots,
        sessions_charging_slots_charge_factors_to_vehicle,
        sessions_charging_slots_charge_factors_from_network,
    ):
        for time_slot, charge_to_vehicle, charge_from_network in zip(
            session_charging_slots,
            session_charging_slots_charge_factors_to_vehicle,
            session_charging_slots_charge_factors_from_network,
        ):
            if time_slot in charging_profile_from_sessions.index:
                charging_profile_to_vehicle_from_sessions.loc[
                    time_slot, location
                ] += charge_to_vehicle
                charging_profile_from_network_from_sessions.loc[
                    time_slot, location
                ] += charge_from_network

    output_root: str = general_parameters.files.output_root

    charging_profile_to_vehicle_from_sessions.to_pickle(
        f'{output_root}/{case_name}/{scenario.name}'
        f'_charging_profile_to_vehicle_from_sessions.pkl'
    )
    charging_profile_from_network_from_sessions.to_pickle(
        f'{output_root}/{case_name}/{scenario.name}'
        f'_charging_profile_from_network_from_sessions.pkl'
    )

    return (
        charging_profile_to_vehicle_from_sessions,
        charging_profile_from_network_from_sessions,
    )


# def shift_excess_demand_to_next_session

# def shift to next session (do this wile not setisfied?)
if __name__ == '__main__':
    case_name = 'Mopo'
    # scenario_name = 'XX_car'
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: Box = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    # scenario_file_name: str = f'scenarios/{case_name}/{scenario_name}.toml'
    # scenario = Box(cook.parameters_from_TOML(scenario_file_name))
    # scenario.name = scenario_name

    # run_charging_sessions_dataframe: pd.DataFrame = pd.read_pickle(
    #     'output/Mopo/XX_car_run_charging_sessions.pkl'
    # )

    # charging_sessions_with_charged_amounts = (
    #     charging_amounts_in_charging_sessions(
    #         run_charging_sessions_dataframe,
    #         scenario,
    #         general_parameters,
    #         case_name,
    #     )
    # )
    # (
    #     charging_profile_to_vehicle_from_sessions,
    #     charging_profile_from_network_from_sessions,
    # ) = get_profile_from_sessions(
    #     charging_sessions_with_charged_amounts,
    #     scenario,
    #     general_parameters,
    #     case_name,
    # )

    # charging_sessions_with_charged_amounts['Start time'] = (
    #     charging_sessions_with_charged_amounts['Start time'].astype(
    #         'datetime64[ns]'
    #     )
    # )

    # case_name = 'Mopo'
    scenario_name = 'Latvia_car_own_driveway_2050'
    scenario_file_name: str = f'scenarios/{case_name}/{scenario_name}.toml'
    # # scenario: Box = Box(cook.parameters_from_TOML(scenario_file_name))
    # scenario.name = scenario_name
    general_parameters_file_name = 'ChaProEV.toml'

    scenario = cook.parameters_from_TOML(scenario_file_name)
    scenario.name = scenario_name
    general_parameters = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'
    location_split_table_name: str = f'{scenario_name}_location_split'
    location_split: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{location_split_table_name}.pkl'
    )
    run_mobility_matrix: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_run_mobility_matrix.pkl',
    ).astype(float)
    maximal_delivered_power_per_location: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}'
        f'_maximal_delivered_power_per_location.pkl',
    )
    maximal_delivered_power: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_maximal_delivered_power.pkl',
    ).astype(float)

    start_: datetime.datetime = datetime.datetime.now()
    (
        battery_spaces,
        total_battery_space_per_location,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        charging_costs,
    ) = get_charging_profile(
        location_split,
        run_mobility_matrix,
        maximal_delivered_power_per_location,
        maximal_delivered_power,
        scenario,
        case_name,
        general_parameters,
    )

    print((datetime.datetime.now() - start_).total_seconds())
