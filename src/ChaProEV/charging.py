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


def sort_locations(
    location_names: ty.List[str],
    time_tag: datetime.datetime,
    run_arrivals_impact,  # Dataframe with multiindex, having issues with MyPy
    possible_origins: ty.Dict[str, ty.List[str]],
    travelling_battery_spaces: pd.DataFrame,
) -> ty.List[str]:
    travel_reserve: pd.DataFrame = pd.DataFrame(
        index=location_names, columns=['Travel reserve']
    )
    for location_name in location_names:
        arrivals_impact: float = sum(
            run_arrivals_impact.loc[
                possible_origins[location_name],
                location_name,
                time_tag,
            ].values
        )
        travelling_battery_spaces_before_current_time_tag: float = sum(
            travelling_battery_spaces.loc[
                travelling_battery_spaces.index.get_level_values('Destination')
                == location_name
            ]
            .sum(axis=1)
            .values
        )
        this_location_travel_reserve: float = float(
            travelling_battery_spaces_before_current_time_tag - arrivals_impact
        )
        travel_reserve.loc[location_name, 'Travel reserve'] = (
            this_location_travel_reserve
        )
    travel_reserve = travel_reserve.sort_values(by=['Travel reserve'])

    sorted_locations: ty.List[str] = list(travel_reserve.index.values)
    # if time_tag.hour == 13:
    #     sorted_locations = ['bus_route_start', 'bus_route_end', 'bus_depot']
    # elif time_tag.hour == 14:
    #     sorted_locations = ['bus_route_start', 'bus_route_end', 'bus_depot']
    # elif time_tag.hour == 22:
    #     sorted_locations = ['bus_route_start', 'bus_route_end', 'bus_depot']
    # else:
    #     sorted_locations = location_names

    # sorted_locations = ['bus_route_start', 'bus_route_end', 'bus_depot']
    return sorted_locations


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
        battery_space,
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
    battery_space: ty.Dict[str, pd.DataFrame],
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
        - battery_space[start_location].sum(axis=1).loc[time_tag],
    )

    # h=8 van Base
    # do travles update?
    # should get travelling from base to cust?

    # if departures_gap > 0:
    #     print('Departures gap')
    #     print(time_tag)
    #     print(start_location, end_location)
    #     print(departures_gap)
    #     input()

    if time_tag_departures_impact > zero_threshold:

        # We look at which battery spaces there are at this location
        # and sort them. The lowest battery spaces will be first.
        # These are the ones we assume are more likely to leave,
        # as others might want to charge first.
        departing_battery_spaces: ty.List[float] = sorted(
            battery_space[start_location].columns.values
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
                    battery_space[start_location].at[
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
                battery_space[start_location].loc[
                    time_tag, departing_battery_space
                ] = (
                    battery_space[start_location].loc[time_tag][
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
                # this_battery_space_departures_impact_this_time = round(
                #     this_battery_space_departures_impact_this_time, 5
                # )
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
                        # travelling_battery_spaces = (
                        #     travelling_battery_spaces.reindex(
                        #         sorted(travelling_battery_spaces.columns),
                        #         axis=1,
                        #     )
                        # )
                    # print('Bef')
                    # if time_tag.hour == 8:
                    #     print(start_location)
                    #     input()
                    # print(travelling_battery_spaces)
                    # print(this_battery_space_departures_impact_this_time)
                    travelling_battery_spaces.loc[
                        (start_location, end_location),
                        travelling_battery_space,
                    ] = (
                        travelling_battery_spaces.loc[
                            start_location, end_location
                        ][travelling_battery_space]
                        + this_battery_space_departures_impact_this_time
                    )
                    # print('Up')
                    # print(travelling_battery_spaces)
                    # input()
    # if time_tag.hour == 8 and start_location == 'van_base':
    #     print(666)
    #     input()

    return battery_space, travelling_battery_spaces, departures_gap


def impact_of_arrivals(
    time_tag: datetime.datetime,
    battery_space: ty.Dict[str, pd.DataFrame],
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
    # if time_tag.hour == 8:
    #     print('Haha')
    #     print(time_tag_arrivals_impact)
    #     print(battery_spaces_arriving_to_this_location)
    #     print(travelling_battery_spaces)
    #     # update to TBS goes to the wrong place?
    #     # Or removal is not at te right spot?>
    #     # track travelling battery spaces!!!!
    #     # Before/after each update (input after update)
    #     # input()
    #     print(start_location)
    #     if start_location == 'van_base':
    #         print('vee')
    #         input()
    # print(time_tag)
    # print(time_tag_arrivals_impact)
    # print(
    #     sum(battery_spaces_arriving_to_this_location)
    # )  # <--- Issue? Need deps in same hour too! Do deps first (or go negative?)
    # print('Jiii')
    # print(battery_spaces_arriving_to_this_location)
    # exit()
    arrivals_gap: float = max(
        0,
        time_tag_arrivals_impact
        - sum(battery_spaces_arriving_to_this_location),
    )
    # if time_tag.hour == 6:
    #     if time_tag_arrivals_impact >0:
    #         print(time_tag_arrivals_impact)
    #         print(travelling_battery_spaces)

    #         exit()

    # if arrivals_gap > 0:
    #     print('Arrivals gap')
    #     print(time_tag)
    #     print(start_location, end_location)
    #     print(arrivals_gap)
    #     input()
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
                # print(arriving_battery_space)
                # print(battery_spaces_arriving_to_this_location)

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
                # print('Sort index!')
                # We update the arrivals:
                time_tag_arrivals_impact -= (
                    this_battery_space_arrivals_impact_this_time
                )
                # We update the battery spaces:
                if (
                    arriving_battery_space
                    not in battery_space[end_location].columns.values
                ):
                    battery_space[end_location][arriving_battery_space] = (
                        float(0)
                    )

                # print(battery_space[end_location])
                battery_space[end_location].loc[
                    time_tag, arriving_battery_space
                ] = (
                    battery_space[end_location].loc[time_tag][
                        arriving_battery_space
                    ]
                    + this_battery_space_arrivals_impact_this_time
                )

                # We alo update the travelling battery spaces (as they have
                # arrived)
                # print('Befoooo')
                # print(travelling_battery_spaces)
                travelling_battery_spaces.loc[
                    (start_location, end_location), arriving_battery_space
                ] = (
                    travelling_battery_spaces.loc[
                        start_location, end_location
                    ][arriving_battery_space]
                    - this_battery_space_arrivals_impact_this_time
                )
                # print('Upiiii')
                # print(travelling_battery_spaces)
    #             Mazinger += this_battery_space_arrivals_impact_this_time
    # print(Mazinger)
    # input()
    # if time_tag.hour == 8 and start_location == 'van_base':
    #     print(666)
    #     exit()
    return battery_space, travelling_battery_spaces, arrivals_gap


def travel_space_occupation(
    scenario: ty.Dict,
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
    run_arrivals_impact_gaps: pd.Series,
    run_departures_impact: pd.Series,
    run_departures_impact_gaps: pd.Series,
    run_range: pd.DatetimeIndex,
    travelling_battery_spaces: pd.DataFrame,
) -> ty.Dict[str, pd.DataFrame]:

    # sorted_locations: ty.List[str] = sort_locations(
    #     location_names,
    #     time_tag,
    #     run_arrivals_impact,
    #     possible_origins,
    #     travelling_battery_spaces,
    # )
    time_tag_arrival_gaps: ty.Dict[str, float] = {}

    # if time_tag_index == 24:
    #     zazoo = pd.DataFrame()
    #     for location_name in location_names:
    #         print(location_name)
    #         print(location_split[location_name].iloc[0:24])
    #         print(battery_space[location_name].sum(axis=1).iloc[0:24])
    #         zazoo[location_name] = (
    #             location_split[location_name].iloc[0:24]
    #             - battery_space[location_name].sum(axis=1).iloc[0:24]
    #         )
    #     zazoo[abs(zazoo) < zero_threshold] = 0
    #     print(zazoo)
    #     exit()

    # Get travllling batt spaces first! (should that only have one location index?)

    # battery space updates after
    # first arrivals then departures

    # We get all the arrival and departure impacts that we need
    # to achieve for this time slot, as well as the pools we can draw
    # from coming from prior time slots (the latter split into battery spaces
    # and a total value)

    # run_arrivals_impact_flat: pd.DataFrame = (
    #     run_arrivals_impact.copy().reset_index()
    # )
    # this_time_slot_arrival_impacts: pd.DataFrame = (
    #     run_arrivals_impact_flat.loc[
    #         run_arrivals_impact_flat['Time Tag'] == time_tag
    #     ]
    #     .set_index(['From', 'To'])
    #     .drop(columns=['Time Tag'])
    #     .groupby(level='To')
    #     .sum()
    # )
    # this_time_slot_arrival_impacts.index.name = 'Destination'

    # print('HSK')
    # arrivals_pool_from_previous_slots: pd.DataFrame = (
    #     travelling_battery_spaces.groupby(level='Destination').sum()
    # )

    # total_arrivals_pool_from_previous_slots: pd.DataFrame = pd.DataFrame(
    #     arrivals_pool_from_previous_slots.sum(axis=1),
    #     columns=['Arrivals impact'],
    # )

    # # print(this_time_slot_arrival_impacts)
    # print('zpzp')
    # # print(total_arrivals_pool_from_previous_slots)

    # this_time_tag_arrivals_gap: pd.DataFrame = (
    #     this_time_slot_arrival_impacts
    #     - total_arrivals_pool_from_previous_slots
    # ).rename(columns={'Arrivals impact': 'Arrivals gap'})
    # # print(this_time_slot_arrival_impacts)
    # # print(this_time_slot_arrival_impacts.columns)
    # # exit()
    # # this_time_tag_arrivals_gap[this_time_tag_arrivals_gap < 0] = 0

    # print(this_time_tag_arrivals_gap)

    # this_time_slot_departures_impacts: pd.DataFrame = pd.DataFrame(
    #     index=travel_index, columns=['Needed departures impact']
    # )
    # departures_pool_from_previous_slots: pd.DataFrame = pd.DataFrame(
    #     index=travel_index
    # )
    # total_departures_pool_from_previous_slots: pd.DataFrame = pd.DataFrame(
    #     index=travel_index
    # )

    # for location_to_compute in location_names:
    #     for leg_origin in possible_origins[location_to_compute]:
    #         this_time_slot_arrival_impacts.loc[
    #             (leg_origin, location_to_compute), 'Needed arrivals impact'
    #         ] = run_arrivals_impact.loc[
    #             leg_origin, location_to_compute, time_tag
    #         ]
    #     for leg_destination in possible_destinations[location_to_compute]:
    #         this_time_slot_departures_impacts.loc[
    #             (location_to_compute, leg_destination),
    #             'Needed departures impact',
    #         ] = run_departures_impact.loc[
    #             location_to_compute, leg_destination, time_tag
    #         ]

    # print(this_time_slot_arrival_impacts)
    # print(arrivals_pool_from_previous_slots)
    # print(total_arrivals_pool_from_previous_slots)
    # print(time_tag)
    # print(arrivals_pool_from_previous_slots)
    # print(this_time_slot_arrival_impacts)
    # print(travelling_battery_spaces)
    # input()
    # if time_tag.hour == 13:
    #     print(travelling_battery_spaces.sum(axis=1))
    #     exit()
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

        # print(location_to_compute)
        # print(time_tag)
        # print(sum(battery_space[location_to_compute].iloc[time_tag_index]))
        # total_arrivals_impact: float = sum(
        #     run_arrivals_impact.loc[
        #         possible_origins[location_to_compute],
        #         location_to_compute,
        #         time_tag,
        #     ].values
        # )
        # travelling_from_previous_times: float = (
        #     travelling_battery_spaces.loc[
        #         travelling_battery_spaces.index.get_level_values('Destination')
        #         == location_to_compute
        #     ]
        #     .sum(axis=1)

        # )
        # print(travelling_from_previous_times)
        # exit()

        # arrivals_gap: float = max(
        #     0, total_arrivals_impact - travelling_from_previous_times
        # )
        # time_tag_arrival_gaps[location_to_compute] = arrivals_gap
        # print('Too', time_tag, arrivals_gap)
        # input()

        # We need to look at the impact of arrivals first
        # because if we look at departures first, we might go wrong,
        # as some departures will be deemd not happening because
        # the battery space occupation would drop below zero (and
        # because we do the computations for occupations above zero)
        for start_location in possible_origins[location_to_compute]:
            battery_space, travelling_battery_spaces, arrivals_gap = (
                impact_of_arrivals(
                    time_tag,
                    battery_space,
                    start_location,
                    location_to_compute,
                    run_arrivals_impact,
                    travelling_battery_spaces,
                    zero_threshold,
                )
            )
            # print(run_arrivals_impact_gaps)

            run_arrivals_impact_gaps.loc[
                start_location, location_to_compute, time_tag
            ] += arrivals_gap
            # if arrivals_gap > 0:
            #     print(time_tag)
            #     print(run_arrivals_impact_gaps.loc['van_customer'])
            #     exit()
        # for location_to_compute in location_names:
        #     # Mango

        for end_location in possible_destinations[location_to_compute]:
            battery_space, travelling_battery_spaces, departures_gap = (
                impact_of_departures(
                    scenario,
                    time_tag,
                    battery_space,
                    location_to_compute,
                    end_location,
                    run_departures_impact,
                    travelling_battery_spaces,
                    zero_threshold,
                    run_mobility_matrix,
                )
            )
            # if departures_gap > 0:
            #     print('Departures gap')
            #     print(time_tag)
            #     print(start_location, end_location)
            #     print(departures_gap)
            #     input()
            # print(time_tag)
            # print(run_departures_impact_gaps)
            # exit()
            run_departures_impact_gaps.loc[
                location_to_compute, end_location, time_tag
            ] += departures_gap
            # Issue was here (wrong terms in loc)
            # See if can switch departures/arrivals order (in both or just one?)
            # Test with more parameters
            # clean code
            # No gap speed up?
            # Extra speed up of charging
            # Boost mode  plus tests
            # See if mango faster
            # Make actualbase scenarios
            # PLuis country versions
            # and send around profiles
            # if departures_gap > 0:
            #     print('Departures gap')
            #     print(time_tag)
            #     print(start_location, location_to_compute)
            #     print(departures_gap)
            #     print(run_departures_impact_gaps[start_location].iloc[0:12])
            #     print(run_departures_impact_gaps[location_to_compute].iloc[0:12])

            #     input()

        # if location_to_compute == 'van_base':
        #     if time_tag.hour == 7:
        #         print(location_split.iloc[0:6])
        #         print(battery_space['van_base'].sum(axis=1).iloc[0:6])
        # exit()
        # print(battery_space['van_customer'].iloc[0:6])
        # exit()
        # for start_location in possible_origins[location_to_compute]:
        #     print(time_tag)
        #     print(travelling_battery_spaces.loc[start_location, location_to_compute])
        #     if time_tag.hour == 7 :
        #         print(start_location)
        #         # print(battery_space['van_customer'].iloc[0:12].sum(axis=1))
        #         print(travelling_battery_spaces)
        #         input()
        #     # For some reason, the below does not update things
        #     battery_space, travelling_battery_spaces, arrivals_gap = (
        #         impact_of_arrivals(
        #             time_tag,
        #             battery_space,
        #             start_location,
        #             location_to_compute,
        #             run_arrivals_impact_gaps,
        #             travelling_battery_spaces,
        #             zero_threshold,
        #         )
        # #     )
        # if time_tag.hour == 7:
        #     print(travelling_battery_spaces)
        #     input()

        #     print(start_location)
        #     print(battery_space['van_customer'].iloc[0:12].sum(axis=1))
        #     #     input()
        # if location_to_compute == 'van_base':
        #     if time_tag.hour == 7:
        #         print(location_split.iloc[0:6])
        #         print(battery_space['van_base'].sum(axis=1).iloc[0:6])
        #         print(run_arrivals_impact_gaps.loc['van_customer'].iloc[0:6])
        #         exit()
        # if time_tag.hour == 14:
        #     print(battery_space['van_base'].iloc[0:12].sum(axis=1))
        #     print(location_split['van_base'].iloc[0:12])
        #     print(battery_space['van_customer'].iloc[0:12].sum(axis=1))
        #     print(location_split['van_customer'].iloc[0:12])
        #     exit()
        # if arrivals_gap > 0:
        #     print(time_tag)
        #     print('Gap', arrivals_gap)
        #     print(location_to_compute)
    #     #     input()
    # print(travelling_battery_spaces)
    # print('Fooooooooo')
    # print(time_tag)
    # print(run_arrivals_impact_gaps.loc['van_base'].iloc[0:12])
    # print(run_arrivals_impact_gaps.loc['van_customer'].iloc[0:12])
    # print(travelling_battery_spaces)
    # print(battery_space['van_base'].sum(axis=1).iloc[0:12])
    # print(battery_space['van_customer'].sum(axis=1).iloc[0:12])
    # print(location_split.iloc[0:12])
    # print(run_arrivals_impact_gaps.loc['van_base'].iloc[time_tag_index])
    # print(run_arrivals_impact_gaps.loc['van_customer'].iloc[time_tag_index])
    # print('Ooooooof')
    # input()
    # if time_tag.hour == 8:
    #     print('Woo')
    #     print(travelling_battery_spaces)
    #     input()

    # if time_tag.hour == 8:
    #     print(time_tag)
    #     print(sum(battery_space['van_base'].iloc[time_tag_index]))
    #     print(sum(battery_space['van_customer'].iloc[time_tag_index]))
    #     input()

    #  battery space too low? at cust?
    #     exit()
    # location_names = ['van_customer', 'van_base']
    sorted_locations: ty.List[str] = sort_locations(
        location_names,
        time_tag,
        run_arrivals_impact,
        possible_origins,
        travelling_battery_spaces,
    )

    for location_to_compute in sorted_locations:
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
        # if time_tag_index == 8:
        #     if location_to_compute == 'bus_depot':
        #         print(travelling_battery_spaces.sum(axis=1))
        #         # exit()
        #     print(location_to_compute)
        #     print(this_time_tag_arrivals_gap)
        #     print(this_time_tag_departures_gap)
        #     print(run_arrivals_impact_gaps.loc['bus_route_end'].iloc[time_tag_index])
        #     exit()

        # if time_tag_index == 3:
        #         print(location_to_compute)

        #         print(location_to_compute)
        #         # if location_to_compute == 'bus_depot':
        #         print(this_time_tag_arrivals_gap)
        #         print(this_time_tag_departures_gap)
        #         input()

        # if time_tag_index == 9:
        #     print(battery_space['bus_depot'].sum(axis=1).iloc[8])
        #     # exit()
        if (
            max(this_time_tag_arrivals_gap, this_time_tag_departures_gap)
            > zero_threshold
        ):

            # If the departures gap is larger than the arrivals gap, we add
            # extra arrivals (from within the same hour) first. Otherwise,
            # we start wit the extra departures.

            # if this_time_tag_departures_gap < this_time_tag_arrivals_gap:
            # print(time_tag)
            # input()
            for start_location in possible_origins[location_to_compute]:
                # if time_tag_index == 8:
                #     print('ty')
                #     print(start_location)
                #     # not enough travelling should be 0.42 or so
                #     print(
                #         run_departures_impact_gaps.loc['bus_route_start'].iloc[
                #             time_tag_index
                #         ]
                #     )
                #     print(travelling_battery_spaces.sum(axis=1))
                #     # exit()

                battery_space, travelling_battery_spaces, arrivals_gap = (
                    impact_of_arrivals(
                        time_tag,
                        battery_space,
                        start_location,
                        location_to_compute,
                        run_arrivals_impact_gaps,
                        travelling_battery_spaces,
                        zero_threshold,
                    )
                )
                # if time_tag_index == 8:
                #     # if arrivals_gap >0:
                #     #     print(arrivals_gap)
                #     print(location_to_compute)
                #     print(travelling_battery_spaces.sum(axis=1))
                #     print(
                #         run_arrivals_impact_gaps.loc[
                #             'bus_route_start', 'bus_depot'
                #         ].iloc[time_tag_index]
                #     )

                # exit()
            for end_location in possible_destinations[location_to_compute]:

                battery_space, travelling_battery_spaces, departures_gap = (
                    impact_of_departures(
                        scenario,
                        time_tag,
                        battery_space,
                        location_to_compute,
                        end_location,
                        run_departures_impact_gaps,
                        travelling_battery_spaces,
                        zero_threshold,
                        run_mobility_matrix,
                    )
                )

            # else:
            #     print(time_tag)
            #     print('print')
            #     input()
            #     for end_location in possible_destinations[location_to_compute]:
            #         (
            #             battery_space,
            #             travelling_battery_spaces,
            #             departures_gap,
            #         ) = impact_of_departures(
            #             scenario,
            #             time_tag,
            #             battery_space,
            #             location_to_compute,
            #             end_location,
            #             run_departures_impact_gaps,
            #             travelling_battery_spaces,
            #             zero_threshold,
            #             run_mobility_matrix,
            #         )
            #     for start_location in possible_origins[location_to_compute]:
            #         battery_space, travelling_battery_spaces, arrivals_gap = (
            #             impact_of_arrivals(
            #                 time_tag,
            #                 battery_space,
            #                 start_location,
            #                 location_to_compute,
            #                 run_arrivals_impact_gaps,
            #                 travelling_battery_spaces,
            #                 zero_threshold,
            #             )
            #         )

        # if time_tag.hour == 12:

        #     if location_to_compute == 'bus_route_start':
        #         print(this_time_tag_departures_gap)
        #         print(this_time_tag_arrivals_gap)

        #         exit()
        # this_time_tag_departures_gap: float = departures_gap
        # print('Coco')
        # print((time_tag, location_to_compute))
        # input()
        # if time_tag.hour == 8:
        #     print('GSHC')
        #     print(location_names)
        #     print(location_to_compute)
        #     print(time_tag)
        #     print(sum(battery_space['van_base'].iloc[time_tag_index]))
        #     print(sum(battery_space['van_customer'].iloc[time_tag_index]))
        #     print(travelling_battery_spaces)
        #     input()

        # for end_location in possible_destinations[location_to_compute]:
        # if (
        #     run_departures_impact_gaps.loc[
        #         location_to_compute, end_location, time_tag
        #     ]
        #     > 0
        # ):
        #     # print('pppgfnjfbgjfgnbh')
        #     # print(time_tag)
        #     # print(departures_gap)
        #     # print(
        #     #     run_departures_impact_gaps.loc[
        #     #         location_to_compute, end_location, time_tag
        #     #     ]
        #     # )
        #     # print(
        #     #     sum(
        #     #         battery_space[location_to_compute].iloc[time_tag_index]
        #     #     )
        #     #     # )
        #     #     # input()
        #     battery_space, travelling_battery_spaces, departures_gap = (
        #         impact_of_departures(
        #             scenario,
        #             time_tag,
        #             battery_space,
        #             location_to_compute,
        #             end_location,
        #             run_departures_impact_gaps,
        #             travelling_battery_spaces,
        #             zero_threshold,
        #             run_mobility_matrix,
        #         )
        #     )

        # for start_location in possible_origins[location_to_compute]:
        #     # print(time_tag)
        # print(
        #     travelling_battery_spaces.loc[
        #         start_location, location_to_compute
        #     ]
        # )
        # if time_tag.hour == 7:
        #     print(start_location)
        #     # print(battery_space['van_customer'].iloc[0:12].sum(axis=1))
        #     print(travelling_battery_spaces)
        #     input()
        # # For some reason, the below does not update things
        # print(time_tag)
        # print('travel')
        # print('Tavellig batt sp not updated???? Or gaps should be zero')

        # departuesx gap compensated by departures ??? Should be in travl bat spaces
        # # It actually is there
        # print(
        #     travelling_battery_spaces.sum(axis=1)
        #     .loc[start_location]
        #     .values[0]
        # )
        # print(
        #     run_arrivals_impact_gaps.loc[
        #         start_location, location_to_compute, time_tag
        #     ]
        # )
        # print('run gaps first is used?')
        # print(
        #     run_arrivals_impact_gaps.loc[start_location].iloc[
        #         time_tag_index
        #     ]
        # )
        # print(
        #     run_arrivals_impact_gaps.loc[location_to_compute].iloc[
        #         time_tag_index
        #     ]
        # )
        # # Location to compute?
        # print('arrivals gap')
        # print(start_location)
        # print(arrivals_gap)
        # print(travelling_battery_spaces)
        # exit()
        # input()
        # time tag, start, end, gap in arr and in deps with input stop

        #     battery_space, travelling_battery_spaces, arrivals_gap = (
        #         impact_of_arrivals(
        #             time_tag,
        #             battery_space,
        #             start_location,
        #             location_to_compute,
        #             run_arrivals_impact_gaps,
        #             travelling_battery_spaces,
        #             zero_threshold,
        #         )
        #     )
        # # if time_tag.hour == 8:
        #     print(1602)
        #     print(time_tag)
        #     print(location_to_compute)
        #     print(sum(battery_space['van_base'].iloc[time_tag_index]))
        #     print(sum(battery_space['van_customer'].iloc[time_tag_index]))
        #     input()
        # Looks liks arrivals gap customer does not play?
    # for location_to_compute in location_names:
    #     # Mango

    # if (
    #     run_departures_impact_gaps.loc[
    #         location_to_compute, end_location, time_tag
    #     ]
    #     > 0
    # ):
    #     print(departures_gap)
    # exit()
    # print(arrivals_gap)
    # print(travelling_battery_spaces)
    # if arrivals_gap > 0:
    #     print(time_tag)
    #     print(start_location, location_to_compute)
    #     print(
    #         'Do the extra only if gap >0 (tough need to compute again?)'
    #     )
    # Run arrivals gap should be zero for VB to VC

    # exit()
    # does thge gap occur for wrong loc (or travel go to wrong?)
    # input()
    # print('oooo', time_tag, arrivals_gap) <-- Still some gap!!!! Use amounts for travelling?
    # if time_tag.hour == 4:
    #     print(battery_space['van_base'].iloc[0:24].sum(axis=1))
    #     print(location_split['van_base'].iloc[0:24])
    #     print(battery_space['van_customer'].iloc[0:24].sum(axis=1))
    #     print(location_split['van_customer'].iloc[0:24])
    #     exit()
    #     # print(run_arrivals_impact_gaps.loc['van_base'].iloc[0:15])
    #     # print(run_arrivals_impact_gaps.loc['van_customer'].iloc[0:15])
    #     print('extra arrivals/missing departures at vase at 08.00????')
    #     print(run_departures_impact_gaps[start_location].iloc[0:12])
    #     print(run_departures_impact_gaps[location_to_compute].iloc[0:12])
    #     exit()

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
    day_end_hour: int,
    zero_threshold: float,
    possible_destinations: ty.Dict[str, ty.List[str]],
    possible_origins: ty.Dict[str, ty.List[str]],
    use_day_types_in_charge_computing: bool,
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

    filter_dataframe: pd.DataFrame = pd.DataFrame(
        run_day_types, columns=['Day Type'], index=run_range
    )

    filter_dataframe['Hours from day start'] = run_hours_from_day_start
    # The battery space DataFrame has another index:
    filter_for_battery_space: pd.DataFrame = pd.DataFrame(
        run_day_types,
        columns=['Day Type'],
        index=battery_space[location_names[0]].index,
    )
    filter_for_battery_space['Hours from day start'] = run_hours_from_day_start
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
                battery_space[location_name].loc[
                    (filter_for_battery_space['Day Type'] == day_type)
                    & (
                        filter_for_battery_space['Hours from day start']
                        == hour_index
                    )
                ] = (
                    battery_space[location_name]
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

        totals_from_battery_space: pd.DataFrame | pd.Series = battery_space[
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

        battery_space[location_name][0] = (
            battery_space[location_name][0] + location_correction
        )

    # Some trips result in charging events spilling over int the next day

    (
        spillover_battery_space,
        run_range,
        run_mobility_matrix,
        spillover_charge_drawn_by_vehicles,
        spillover_charge_drawn_from_network,
        run_arrivals_impact,
        run_arrivals_impact_gaps,
        run_departures_impact,
        run_departures_impact_gaps,
        travelling_battery_spaces,
    ) = get_charging_framework(scenario, case_name, general_parameters)

    for location_name in location_names:
        spillover_battery_space[location_name][
            battery_space[location_name].columns
        ] = float(0)

    for location_name in location_names:
        day_end_battery_space: pd.DataFrame = battery_space[location_name].loc[
            run_range.hour == day_end_hour
        ]
        non_empty_day_end_battery_space: pd.DataFrame = (
            day_end_battery_space.drop(columns=float(0))
        )
        day_ends_with_leftover_battery_space = (
            non_empty_day_end_battery_space.loc[
                non_empty_day_end_battery_space.sum(axis=1) > zero_threshold
            ].index.get_level_values('Time Tag')
        )

        for day_end_time_tag in day_ends_with_leftover_battery_space:

            spillover_battery_space[location_name].loc[day_end_time_tag] = (
                battery_space[location_name].loc[day_end_time_tag].values
            )

            spillover_time_tag_index: int = list(run_range).index(
                day_end_time_tag
            )

            amount_in_spillover = (
                spillover_battery_space[location_name]
                .drop(columns=float(0))
                .loc[day_end_time_tag]
                .sum()
            )

            while amount_in_spillover > zero_threshold:
                spillover_time_tag_index += 1
                if spillover_time_tag_index >= len(run_range) - 1:
                    amount_in_spillover = 0

                spillover_time_tag: ty.Any = run_range[
                    spillover_time_tag_index
                ]
                # used Any (and less hints above because MyPy seems
                # to get wrong type matches)
                (spillover_battery_space) = travel_space_occupation(
                    scenario,
                    spillover_battery_space,
                    spillover_time_tag,
                    spillover_time_tag_index,
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

                amount_in_spillover = (
                    spillover_battery_space[location_name]
                    .drop(columns=float(0))
                    .loc[spillover_time_tag]
                    .sum()
                )

                battery_space[location_name].loc[
                    spillover_time_tag, float(0)
                ] = (
                    battery_space[location_name].loc[spillover_time_tag][
                        float(0)
                    ]
                    - amount_in_spillover
                )

                non_zero_battery_spaces = battery_space[location_name].columns[
                    1:
                ]
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
                ] = spillover_charge_drawn_by_vehicles.loc[spillover_time_tag][
                    location_name
                ]

                charge_drawn_from_network.loc[
                    spillover_time_tag, location_name
                ] = spillover_charge_drawn_from_network.loc[
                    spillover_time_tag
                ][
                    location_name
                ]


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

    # if a-->b-->c within one hour, then directly a-->c?
    #     Actually no, because isses would happen eralier
    #     But maybe too many arrivals in procedure?

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
        if time_tag.hour == 0:
            print(time_tag.day, time_tag.month)
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
                scenario,
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
                run_arrivals_impact_gaps,
                run_departures_impact,
                run_departures_impact_gaps,
                run_range,
                travelling_battery_spaces,
            )
            # if time_tag.hour == 13:
            #     print(battery_space['bus_depot'].iloc[7:10].sum(axis=1))
            #     print(run_arrivals_impact.loc['bus_route_start', 'bus_depot', time_tag])
            #     print(run_arrivals_impact_gaps.loc['bus_route_start', 'bus_depot', time_tag])
            #     exit()
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

    run_arrivals_impact_gaps.to_csv('arr_g.csv')
    run_departures_impact_gaps.to_csv('dep_g.csv')

    if use_day_types_in_charge_computing:
        copy_day_type_profiles_to_whole_run(
            scenario,
            run_range,
            reference_day_type_time_tags,
            location_split,
            battery_space,
            day_end_hour,
            zero_threshold,
            possible_destinations,
            possible_origins,
            use_day_types_in_charge_computing,
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
    test_scenario_name = 'XX_bus'
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
