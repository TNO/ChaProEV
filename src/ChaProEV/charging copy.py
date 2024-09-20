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


def impact_of_departures(
    battery_space: ty.Dict,
    start_location: str,
    end_location: str,
    time_slot_departures: float,
    time_slot_departures_impact: float,
    time_tag: datetime.datetime,
    next_time_tag: datetime.datetime,
    run_range: pd.DatetimeIndex,
    run_mobility_matrix,  # It is a DataFrame, but MyPy gives an error
    run_arrivals_impact,  # It is a DataFrame, but MyPy gives an error
    zero_threshold: float,
) -> ty.Tuple[ty.Dict, pd.Series]:
    '''
    THis function looks at the impact of a set of departures on the battery
    spaces. It has to be called separately for departures in the
    current time slot and for those in the next time slot.
    The latter needs to be computed on the basis of the battery spaces
    after the former has taken place and after the charging in the current
    time slot has taken place. In other words, it has to occur at the top
    of the next time slot.
    '''
    print('Check description!')

    # print(battery_space[start_location])

    if time_tag.hour == 11:
        print(battery_space[start_location].iloc[0:5])
        print(battery_space[end_location].iloc[0:5])
        print(run_mobility_matrix.loc['truck_hub'].iloc[0:12])
        print(run_mobility_matrix.loc['truck_customer'].iloc[0:12])

        print(battery_space['truck_customer'].iloc[0:12].sum(axis=1))
        print(battery_space['truck_hub'].iloc[0:12].sum(axis=1))
        print(111)
        exit()
    # if time_tag.hour == 7:
    #     print(time_slot_departures_impact)
    #     print(time_slot_departures)
    #     exit()

    
    # We first look at what happens to the arriving battery spaces
    # (i.e. the battery spaces at the end location.) We need to do this first
    # because we might not have the right battery spaces if we do not
    time_slot_departures_store: float = time_slot_departures
    if time_slot_departures_store > zero_threshold:
        departing_battery_spaces: ty.List[float] = sorted(
            battery_space[start_location].columns.values
        )
        # If there are no departures, there are no arrivals either
        # We get the consumption of the leg
        leg_distance: float = run_mobility_matrix.loc[
            start_location, end_location, time_tag
        ]['Distance (km)']
        vehicle_electricity_consumption: float = scenario['vehicle'][
            'base_consumption_per_km'
        ]['electricity_kWh']
        this_leg_consumption: float = (
            leg_distance * vehicle_electricity_consumption
        )

        # We also need the duration of the leg
        travelling_time: float = float(
            run_mobility_matrix.loc[
                start_location, end_location, time_tag
            ]['Duration (hours)']
        )

        # We want to know what the arriving battery spaces
        # will be and the amounts/percentages of the fleet vehicles
        # for each arriving battery space
        arriving_battery_spaces: ty.List[float] = []
        arriving_amounts: ty.List[float] = []

        # We iterate through the departing battery spaces
        # (reminder, they are ordered from lowest to highest,
        # as we assumed that the lower the battery space, the higher
        # the likelihood to leave, as vehicleswith more battery space/
        # less available battery capacity wll want to charge first).

        # This time, we will be looking at the actual departures
        # (not their impact)
        

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
            if time_slot_departures > zero_threshold:
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

                

                this_battery_space_departures_this_time: float = min(
                    time_slot_departures,
                    battery_space[start_location].at[
                        time_tag, departing_battery_space
                    ],
                )
                #     HERE?  We need to add 0.5, not 0.25
                # so maybe use previous battery spaces? Or do this before deps
                if time_tag.hour == 7:
                    print(1602)
                    print(time_slot_departures)
                    print('Is this 0.5?')
                    print(this_battery_space_departures_this_time)
                    print(battery_space[start_location].iloc[0:10])
                    # exit()
                print(time_tag)
                print('Battt Spa')
                print(battery_space[start_location].iloc[0:5])
                print(battery_space[end_location].iloc[0:5])
                # print(
                #     'Zaaa',
                #     this_battery_space_departures_impact_this_time,
                #     time_slot_departures,
                # )
                if time_tag.hour == 12:
                    exit()
                # We add these departures to the arriving amounts,
                # as these will arrive to the end location
                if (
                    this_battery_space_departures_this_time
                    > zero_threshold
                ):
                    arriving_amounts.append(
                        this_battery_space_departures_this_time
                    )

                    # We also add the corresponding battery space at
                    # arrival, given by the original battery space plus
                    # the leg's consumption
                    arriving_battery_spaces.append(
                        departing_battery_space + this_leg_consumption
                    )

                    # We update the departures (i.e. how many remain
                    # for larger battery spaces)
                    time_slot_departures -= (
                        this_battery_space_departures_this_time
                    )

                # # Now, we remove the departures from the start
                # # location for the current time slot
                # battery_space[start_location].loc[
                #     time_tag, departing_battery_space
                # ] = (
                #     battery_space[start_location].loc[time_tag][
                #         departing_battery_space
                #     ]
                #     - this_battery_space_departures_impact_this_time
                # )
        # print(arriving_battery_spaces)
        print('Zobi')
        print(arriving_amounts)
        print(arriving_battery_spaces)
        # print(arriving_amounts)
        # exit()

        first_arrival_time_tag: datetime.datetime = (
            time_tag
            + datetime.timedelta(hours=math.floor(travelling_time))
        )
        second_arrival_time_tag: datetime.datetime = (
            first_arrival_time_tag + datetime.timedelta(hours=1)
        )
        third_arrival_time_tag: datetime.datetime = (
            first_arrival_time_tag + datetime.timedelta(hours=2)
        )

        arrival_time_tags: ty.List[datetime.datetime] = [
            first_arrival_time_tag,
            second_arrival_time_tag,
            third_arrival_time_tag,
        ]

        first_arrival_impact: float = run_arrivals_impact.loc[
            start_location, end_location, first_arrival_time_tag
        ]

        percent_in_first_slot: float = math.sqrt(
            (first_arrival_impact / time_slot_departures_store) * 2
        )

        slot_impacts: ty.Tuple[float, float, float] = (
            define.get_slot_split(
                percent_in_first_slot, time_slot_departures_store
            )
        )
        # print(time_tag)
        # print(slot_impacts)
        # issue is below

        # print(
        #     run_arrivals_impact.loc[
        #         start_location, end_location, arrival_time_tags
        #     ]
        # )
        # if arrival_time_tags[0].hour == 11:
        print(arrival_time_tags)
        print(slot_impacts)
        print(
            run_arrivals_impact.loc[start_location, end_location][
                arrival_time_tags
            ]
        )
        print(battery_space['truck_hub'].loc[arrival_time_tags])
        print('ttt')
        print(arriving_battery_spaces)
        # exit()
        # We update the arrivals impact (so that the next arrivals have
        # the right basis)
        for arrival_time_tag, arrival_slot_impact in zip(
            arrival_time_tags, slot_impacts
        ):
            run_arrivals_impact.loc[
                start_location, end_location, arrival_time_tag
            ] = (
                run_arrivals_impact.loc[start_location, end_location][
                    arrival_time_tag
                ]
                - arrival_slot_impact
            )

        # print(
        #     run_arrivals_impact.loc[
        #         start_location, end_location, arrival_time_tags
        #     ]
        # )
        # exit()
        # print(battery_space[end_location].loc[arrival_time_tags])
        # We now look at the impact of the arrivals, starting with the first
        # time slot
        print(arriving_amounts)
        for time_slot_index in range(3):
            time_slot_arrivals_impact: float = slot_impacts[
                time_slot_index
            ]

            for space_index, (
                arriving_battery_space,
                arriving_amount,
            ) in enumerate(zip(arriving_battery_spaces, arriving_amounts)):

                if (
                    arriving_battery_space
                    not in battery_space[end_location].columns
                ):
                    battery_space[end_location][arriving_battery_space] = (
                        float(0)
                    )
                if arriving_amount > zero_threshold:
                    this_battery_space_impact_this_time: float = min(
                        time_slot_arrivals_impact,
                        arriving_amount,
                    )
                    # print(this_battery_space_impact_this_time)
                    # exit()

                    arriving_amounts[
                        space_index
                    ] -= this_battery_space_impact_this_time



                    if time_tag.hour == 6 and start_location == 'truck_hub':
                        print(999)
                        print(time_slot_index)
                        print(this_battery_space_impact_this_time)
                        print(time_slot_arrivals_impact)
                        print(battery_space[end_location].loc[arrival_time_tags])
                        # if time_slot_index == 2:
                        #     exit()
                    if time_slot_index == 0:
                        go_back_index: int = 0
                    else:
                        go_back_index = time_slot_index
                    battery_space[end_location].loc[
                        arrival_time_tags[time_slot_index],
                        arriving_battery_space,
                    ] = (
                        battery_space[end_location].loc[
                            arrival_time_tags[
                                time_slot_index  # - go_back_index
                            ]
                        ][arriving_battery_space]
                        + this_battery_space_impact_this_time
                    )
                    if time_tag.hour == 7 and start_location == 'truck_hub':
                        print(999)
                        print(time_slot_index)
                        print(this_battery_space_impact_this_time)
                        print(time_slot_arrivals_impact)
                        print(battery_space[end_location].loc[arrival_time_tags])
                        # if time_slot_index == 2:
                        #     exit()

        print('ABS')
        print(arriving_battery_spaces)
        print(arriving_amounts)
        print(arrival_time_tags)
        print(slot_impacts)
        print(
            run_arrivals_impact.loc[start_location, end_location][
                arrival_time_tags
            ]
        )
        print(battery_space['truck_hub'].loc[arrival_time_tags])
        if arrival_time_tags[0].hour == 17:

            print('Should be .16 and .33 at 30')
            exit()









    if time_slot_departures_impact > zero_threshold:
        
        # time_slot_departures_store: float = time_slot_departures
        # print(
        #     time_tag, time_slot_departures_store, time_slot_departures_impact
        # )
        # If there are no departures, we can skip this

        # We do the impact on the start location

        # We look at which battery spaces there are at this location
        # and sort them. The lowest battery spaces will be first.
        # These are the ones we assume aremore likely to leave,
        # as others might want to charge first
        departing_battery_spaces = sorted(
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
            if time_slot_departures_impact > zero_threshold:
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
                    time_slot_departures_impact,
                    battery_space[start_location].at[
                        time_tag, departing_battery_space
                    ],
                )

                # We update the departures (i.e. how many remain
                # for larger battery spaces)
                time_slot_departures_impact -= (
                    this_battery_space_departures_impact_this_time
                )
                if time_tag.hour == 10 and start_location == 'truck_customer':
                    print(this_battery_space_departures_impact_this_time)
                    print(time_slot_departures_impact)
                    print(battery_space[start_location].loc[time_tag])
                    # exit()
                # Now, we remove the departures from the start
                # location for the current time slot
                battery_space[start_location].loc[
                    time_tag, departing_battery_space
                ] = (
                    battery_space[start_location].loc[time_tag][
                        departing_battery_space
                    ]
                    - this_battery_space_departures_impact_this_time
                )
        
        # # We now look at what happens to the arriving battery spaces
        # # (i.e. the battery spaces at the end location.)
        # if time_slot_departures_store > zero_threshold:
        #     # If there are no departures, there are no arrivals either
        #     # We get the consumption of the leg
        #     leg_distance: float = run_mobility_matrix.loc[
        #         start_location, end_location, time_tag
        #     ]['Distance (km)']
        #     vehicle_electricity_consumption: float = scenario['vehicle'][
        #         'base_consumption_per_km'
        #     ]['electricity_kWh']
        #     this_leg_consumption: float = (
        #         leg_distance * vehicle_electricity_consumption
        #     )

        #     # We also need the duration of the leg
        #     travelling_time: float = float(
        #         run_mobility_matrix.loc[
        #             start_location, end_location, time_tag
        #         ]['Duration (hours)']
        #     )

        #     # We want to know what the arriving battery spaces
        #     # will be and the amounts/percentages of the fleet vehicles
        #     # for each arriving battery space
        #     arriving_battery_spaces: ty.List[float] = []
        #     arriving_amounts: ty.List[float] = []

        #     # We iterate through the departing battery spaces
        #     # (reminder, they are ordered from lowest to highest,
        #     # as we assumed that the lower the battery space, the higher
        #     # the likelihood to leave, as vehicleswith more battery space/
        #     # less available battery capacity wll want to charge first).

        #     # This time, we will be looking at the actual departures
        #     # (not their impact)
            

        #     for departing_battery_space in departing_battery_spaces:
        #         # We will be removing the departures from the lower
        #         # battery spaces from the pool, until we have reached
        #         # all departures. For example, if we have 0.2 departures
        #         # and 0.19 vehicles with space equal to zero, 0.2 vehicles
        #         # with space 1, and 0.3 vehicles with space 1.6,
        #         # then we will first take all the
        #         # 0.19 vehicles with space 0,
        #         # 0.01 vehicles with space 1,
        #         # and 0 vehicles with space 1.6,
        #         # leaving us with 0 vehicles wth space 0,
        #         # 0.19 vehicles with
        #         # space 1, and 0.3 vehicles with space 1.6
        #         if time_slot_departures > zero_threshold:
        #             # We do this until there are no departures left

        #             # We want to know how many departures will come from
        #             # the battery space we are looking at. If there are
        #             # more vehicles with the current space than remaining
        #             # departures, then we take the remaining departures,
        #             # otherwise we take all the vehicles with the current
        #             # space and move to the next one
        #             # This needs to be done separately for the current
        #             # time slot and the next one
        #             # (because of the issue of effective impact, as
        #             # some vehicles stay some of the time)

                    

        #             this_battery_space_departures_this_time: float = min(
        #                 time_slot_departures,
        #                 battery_space[start_location].at[
        #                     time_tag, departing_battery_space
        #                 ],
        #             )
        #             #     HERE?  We need to add 0.5, not 0.25
        #             # so maybe use previous battery spaces? Or do this before deps
        #             if time_tag.hour == 7:
        #                 print(1602)
        #                 print(time_slot_departures)
        #                 print('Is this 0.5?')
        #                 print(this_battery_space_departures_this_time)
        #                 print(battery_space[start_location].iloc[0:10])
        #                 exit()
        #             print(time_tag)
        #             print('Battt Spa')
        #             print(battery_space[start_location].iloc[0:5])
        #             print(battery_space[end_location].iloc[0:5])
        #             print(
        #                 'Zaaa',
        #                 this_battery_space_departures_impact_this_time,
        #                 time_slot_departures,
        #             )
        #             if time_tag.hour == 12:
        #                 exit()
        #             # We add these departures to the arriving amounts,
        #             # as these will arrive to the end location
        #             if (
        #                 this_battery_space_departures_impact_this_time
        #                 > zero_threshold
        #             ):
        #                 arriving_amounts.append(
        #                     this_battery_space_departures_this_time
        #                 )

        #                 # We also add the corresponding battery space at
        #                 # arrival, given by the original battery space plus
        #                 # the leg's consumption
        #                 arriving_battery_spaces.append(
        #                     departing_battery_space + this_leg_consumption
        #                 )

        #                 # We update the departures (i.e. how many remain
        #                 # for larger battery spaces)
        #                 time_slot_departures -= (
        #                     this_battery_space_departures_this_time
        #                 )

        #             # # Now, we remove the departures from the start
        #             # # location for the current time slot
        #             # battery_space[start_location].loc[
        #             #     time_tag, departing_battery_space
        #             # ] = (
        #             #     battery_space[start_location].loc[time_tag][
        #             #         departing_battery_space
        #             #     ]
        #             #     - this_battery_space_departures_impact_this_time
        #             # )
        #     # print(arriving_battery_spaces)
        #     print('Zobi')
        #     print(arriving_amounts)
        #     print(arriving_battery_spaces)
        #     # print(arriving_amounts)
        #     # exit()

        #     first_arrival_time_tag: datetime.datetime = (
        #         time_tag
        #         + datetime.timedelta(hours=math.floor(travelling_time))
        #     )
        #     second_arrival_time_tag: datetime.datetime = (
        #         first_arrival_time_tag + datetime.timedelta(hours=1)
        #     )
        #     third_arrival_time_tag: datetime.datetime = (
        #         first_arrival_time_tag + datetime.timedelta(hours=2)
        #     )

        #     arrival_time_tags: ty.List[datetime.datetime] = [
        #         first_arrival_time_tag,
        #         second_arrival_time_tag,
        #         third_arrival_time_tag,
        #     ]

        #     first_arrival_impact: float = run_arrivals_impact.loc[
        #         start_location, end_location, first_arrival_time_tag
        #     ]

        #     percent_in_first_slot: float = math.sqrt(
        #         (first_arrival_impact / time_slot_departures_store) * 2
        #     )

        #     slot_impacts: ty.Tuple[float, float, float] = (
        #         define.get_slot_split(
        #             percent_in_first_slot, time_slot_departures_store
        #         )
        #     )
        #     # print(time_tag)
        #     # print(slot_impacts)
        #     # issue is below

        #     # print(
        #     #     run_arrivals_impact.loc[
        #     #         start_location, end_location, arrival_time_tags
        #     #     ]
        #     # )
        #     # if arrival_time_tags[0].hour == 11:
        #     print(arrival_time_tags)
        #     print(slot_impacts)
        #     print(
        #         run_arrivals_impact.loc[start_location, end_location][
        #             arrival_time_tags
        #         ]
        #     )
        #     print(battery_space['truck_hub'].loc[arrival_time_tags])
        #     print('ttt')
        #     print(arriving_battery_spaces)
        #     # exit()
        #     # We update the arrivals impact (so that the next arrivals have
        #     # the right basis)
        #     for arrival_time_tag, arrival_slot_impact in zip(
        #         arrival_time_tags, slot_impacts
        #     ):
        #         run_arrivals_impact.loc[
        #             start_location, end_location, arrival_time_tag
        #         ] = (
        #             run_arrivals_impact.loc[start_location, end_location][
        #                 arrival_time_tag
        #             ]
        #             - arrival_slot_impact
        #         )

        #     # print(
        #     #     run_arrivals_impact.loc[
        #     #         start_location, end_location, arrival_time_tags
        #     #     ]
        #     # )
        #     # exit()
        #     # print(battery_space[end_location].loc[arrival_time_tags])
        #     # We now look at the impact of the arrivals, starting with the first
        #     # time slot
        #     print(arriving_amounts)
        #     for time_slot_index in range(3):
        #         time_slot_arrivals_impact: float = slot_impacts[
        #             time_slot_index
        #         ]

        #         for space_index, (
        #             arriving_battery_space,
        #             arriving_amount,
        #         ) in enumerate(zip(arriving_battery_spaces, arriving_amounts)):

        #             if (
        #                 arriving_battery_space
        #                 not in battery_space[end_location].columns
        #             ):
        #                 battery_space[end_location][arriving_battery_space] = (
        #                     float(0)
        #                 )
        #             if arriving_amount > zero_threshold:
        #                 this_battery_space_impact_this_time: float = min(
        #                     time_slot_arrivals_impact,
        #                     arriving_amount,
        #                 )
        #                 # print(this_battery_space_impact_this_time)
        #                 # exit()

        #                 arriving_amounts[
        #                     space_index
        #                 ] -= this_battery_space_impact_this_time



        #                 if time_tag.hour == 6 and start_location == 'truck_hub':
        #                     print(999)
        #                     print(time_slot_index)
        #                     print(this_battery_space_impact_this_time)
        #                     print(time_slot_arrivals_impact)
        #                     print(battery_space[end_location].loc[arrival_time_tags])
        #                     # if time_slot_index == 2:
        #                     #     exit()
        #                 if time_slot_index == 0:
        #                     go_back_index: int = 0
        #                 else:
        #                     go_back_index = time_slot_index
        #                 battery_space[end_location].loc[
        #                     arrival_time_tags[time_slot_index],
        #                     arriving_battery_space,
        #                 ] = (
        #                     battery_space[end_location].loc[
        #                         arrival_time_tags[
        #                             time_slot_index  # - go_back_index
        #                         ]
        #                     ][arriving_battery_space]
        #                     + this_battery_space_impact_this_time
        #                 )
        #                 if time_tag.hour == 7 and start_location == 'truck_hub':
        #                     print(999)
        #                     print(time_slot_index)
        #                     print(this_battery_space_impact_this_time)
        #                     print(time_slot_arrivals_impact)
        #                     print(battery_space[end_location].loc[arrival_time_tags])
        #                     if time_slot_index == 2:
        #                         exit()

        #     print('ABS')
        #     print(arriving_battery_spaces)
        #     print(arriving_amounts)
        #     print(arrival_time_tags)
        #     print(slot_impacts)
        #     print(
        #         run_arrivals_impact.loc[start_location, end_location][
        #             arrival_time_tags
        #         ]
        #     )
        #     print(battery_space['truck_hub'].loc[arrival_time_tags])
        #     if arrival_time_tags[0].hour == 17:

        #         print('Should be .16 and .33 at 30')
        #         exit()
        # print(battery_space[end_location].loc[arrival_time_tags])
        # exit()

        # print('Problem might be here (if start is non-uniformly spread)')
        # # print(battery_space)
        # print(
        #     run_mobility_matrix.loc[start_location, end_location].loc[
        #         arrival_time_tags
        #     ]
        # )
        # print(run_mobility_matrix.loc[start_location, end_location].
        # iloc[0:24])
        # exit()
        # add space shifts to arrivals

        # # We now can update the battery spaces in the end location.
        # for arriving_battery_space, arriving_amount in zip(
        #     arriving_battery_spaces, arriving_amounts
        # ):
        #     if arriving_amount > zero_threshold:
        #         # No need to cmpute if there are no

        #         # If the end location does not have the incoming
        #         # battery space in its columns, we add the column
        #         # (with zeroes)
        #         if arriving_battery_space not in (
        #             battery_space[end_location].columns
        #         ):
        #             battery_space[end_location][arriving_battery_space] = (
        #                 float(0)
        #             )

        #         if first_arrival_shift_proportion > zero_threshold:
        #             # Otherwise there is no first shift arrival
        #             # We check if the arrivals in the first slot
        #             # are in the run range
        #             # if they are not, then we don't take them into
        #             # account (as the are not in the run) and add them
        #             # in the end_location battery space DataFrame
        #             if time_tag + first_arrival_shift_time <=
        #  (run_range[-1]):
        #                 battery_space[end_location].loc[
        #                     time_tag + first_arrival_shift_time,
        #                     arriving_battery_space,
        #                 ] = battery_space[end_location].loc[
        #                     time_tag + first_arrival_shift_time
        #                 ][
        #                     arriving_battery_space
        #                 ] + (
        #                     arriving_amount
        #                     * first_arrival_shift_proportion
        #                     / 2
        #                     # / 1
        #                 )

        #                 # The effects on the current time tag are
        #                 # halved,
        #                 # as the vehicles arrive unifornmly
        #                 # The rest of the impact is in the next
        #                 # time tag
        #                 if next_time_tag + first_arrival_shift_time <= (
        #                     run_range[-1]
        #                 ):
        #                     battery_space[end_location].loc[
        #                         next_time_tag + first_arrival_shift_time,
        #                         arriving_battery_space,
        #                     ] = battery_space[end_location].loc[
        #                         next_time_tag + first_arrival_shift_time
        #                     ][
        #                         arriving_battery_space
        #                     ] + (
        #                         arriving_amount
        #                         * first_arrival_shift_proportion
        #                         / 2
        #                         # * 0
        #                     )
        #         if (1 - first_arrival_shift_proportion) > zero_threshold:

        #             # Otherwise there is no first shift arrival
        #             # We check if the arrivals in the second slot
        #             # are in the run range
        #             # if they are not, then we don't take them into
        #             # account (as the are not in the run)  and add them
        #             # in the end_location battery space DataFrame
        #             if time_tag + second_arrival_shift_time <=
        #  (run_range[-1]):
        #                 battery_space[end_location].loc[
        #                     time_tag + second_arrival_shift_time,
        #                     arriving_battery_space,
        #                 ] = battery_space[end_location].loc[
        #                     time_tag + second_arrival_shift_time
        #                 ][
        #                     arriving_battery_space
        #                 ] + (
        #                     arriving_amount
        #                     * (1 - first_arrival_shift_proportion)
        #                     / 2
        #                     # / 1
        #                 )

        #                 # The effects on the current time tag are
        #                 # halved,
        #                 # as the vehicles arrive unifornmly
        #                 # The rest of the impact is in the next
        #                 # time tag
        #                 if next_time_tag + second_arrival_shift_time <= (
        #                     run_range[-1]
        #                 ):
        #                     battery_space[end_location].loc[
        #                         next_time_tag + second_arrival_shift_time,
        #                         arriving_battery_space,
        #                     ] = battery_space[end_location].loc[
        #                         next_time_tag + second_arrival_shift_time
        #                     ][
        #                         arriving_battery_space
        #                     ] + (
        #                         arriving_amount
        #                         * (1 - first_arrival_shift_proportion)
        #                         / 2
        #                         # * 0
        #                     )
    # else:
    #     # If there are no impactful movements, we copy the battery spaces down
    #     battery_space[end_location].loc[next_time_tag] = battery_space[
    #         end_location
    #     ].loc[time_tag]
    #     # print('Foooo')
    #     # print(battery_space[end_location])
    #     # if end_location == 'truck_hub':
    #     #     exit()

    return battery_space, run_arrivals_impact


# def impact_of_departures(
#     battery_space: ty.Dict,
#     start_location: str,
#     end_location: str,
#     time_slot_departures: float,
#     time_tag: datetime.datetime,
#     next_time_tag: datetime.datetime,
#     run_range: pd.DatetimeIndex,
#     run_mobility_matrix,  # It is a DataFrame, but MyPy gives an error
#     distance_header: str,
#     electricity_consumption_kWh_per_km: float,
#     zero_threshold: float,
#     first_wave: bool,
# ) -> ty.Dict:
#     '''
#     THis function looks at the impact of a set of departures on the battery
#     spaces. It has to be called separately for departures in the
#     current time slot and for those in the next time slot.
#     The latter needs to be computed on the basis of the battery spaces
#     after the former has taken place and after the charging in the current
#     time slot has taken place. In other words, it has to occur at the top
#     of the next time slot.
#     '''

#     if time_slot_departures > zero_threshold:
#         # If there are no departures, we can skip this

#         # We want to know what the arriving battery spaces
#         # will be and the amounts/percentages of the fleet vehicles
#         # for each arriving battery space
#         arriving_battery_spaces: ty.List[float] = []
#         arriving_amounts: ty.List[float] = []

#         # We also need the duration of the leg
#         travelling_time: float = float(
#             run_mobility_matrix.loc[start_location, end_location, time_tag][
#                 'Duration (hours)'
#             ]
#         )

#         # We iterate through the departing battery spaces
#         # (reminder, they are ordered from lowest to highest,
#         # as we assumed that the lower the battery space, the higher
#         # the likelihood to leave, as vehicleswith more battery space/
#         # less available battery capacity wll want to charge first).

#         # We look at which battery spaces there are at this location
#         # and sort them. The lowest battery spaces will be first.
#         # These are the ones we assume aremore likely to leave,
#         # as others might want to charge first
#         departing_battery_spaces: ty.List[float] = sorted(
#             battery_space[start_location].columns.values
#         )

#         for departing_battery_space in departing_battery_spaces:
#             # We will be removing the departures from the lower
#             # battery spaces from the pool, until we have reached
#             # all departures. For example, if we have 0.2 departures
#             # and 0.19 vehicles with space equal to zero, 0.2 vehicles
#             # with space 1, and 0.3 vehicles with space 1.6,
#             # then we will first take all the
#             # 0.19 vehicles with space 0,
#             # 0.01 vehicles with space 1,
#             # and 0 vehicles with space 1.6,
#             # leaving us with 0 vehicles wth space 0,
#             # 0.19 vehicles with
#             # space 1, and 0.3 vehicles with space 1.6
#             if time_slot_departures > zero_threshold:
#                 # We do this until there are no departures left

#                 # We need to know in which slots the vehicles
#                 # will arrive at their destination and the proprtion
#                 # of these slots
#                 first_arrival_shift: int = math.floor(travelling_time)
#                 if first_wave:
#                     # This isfor departures in the original time slot
#                     first_arrival_shift_time: datetime.timedelta = (
#                         datetime.timedelta(hours=first_arrival_shift)
#                     )
#                     second_arrival_shift_time: datetime.timedelta = (
#                         datetime.timedelta(hours=first_arrival_shift + 1)
#                     )
#                 else:
#                     # This is for departures in the next time slot
#                     first_arrival_shift_time = datetime.timedelta(
#                         hours=first_arrival_shift - 1
#                     )
#                     second_arrival_shift_time = datetime.timedelta(
#                         hours=first_arrival_shift
#                     )
#                 first_arrival_shift_proportion: float =
#  1 - travelling_time % 1

#                 # We want to know how many departures will come from
#                 # the battery space we are looking at. If there are
#                 # more vehicles with the current space than remaining
#                 # departures, then we take the remaining departures,
#                 # otherwise we take all the vehicles with the current
#                 # space and move to the next one
#                 # This needs to be done separately for the current
#                 # time slot and the next one
#                 # (because of the issue of effective impact, as
#                 # some vehicles stay some of the time)

#                 this_battery_space_departures_impact_this_time: float = min(
#                     time_slot_departures,
#                     battery_space[start_location].at[
#                         time_tag, departing_battery_space
#                     ],
#                 )

#                 # We add these departures to the arriving amounts,
#                 # as these will arrive to the end location

#                 arriving_amounts.append(
#                     this_battery_space_departures_impact_this_time
#                 )
#                 # print(time_tag)
#                 # print(first_wave)
#                 # print(start_location)
#                 # print(end_location)
#                 # print(sum(arriving_amounts))

#                 # We
#                 # look up the consumption
#                 this_leg_consumption: float = float(
#                     run_mobility_matrix.loc[
#                         start_location, end_location, time_tag
#                     ][distance_header]
#                     * electricity_consumption_kWh_per_km
#                 )

#                 # We also add the corresponding battery space at
#                 # arrival, given by the original battery space plus
#                 # the leg's consumption
#                 arriving_battery_spaces.append(
#                     departing_battery_space + this_leg_consumption
#                 )
#                 # We update the departures (i.e. how many remain
#                 # for larger battery spaces)
#                 time_slot_departures -= (
#                     this_battery_space_departures_impact_this_time
#                 )

#                 # Now, we remove the departures from the start
#                 # location for the current time slot
#                 battery_space[start_location].loc[
#                     time_tag, departing_battery_space
#                 ] = (
#                     battery_space[start_location].loc[time_tag][
#                         departing_battery_space
#                     ]
#                     - this_battery_space_departures_impact_this_time
#                 )

#         # We now can update the battery spaces in the end location.
#         for arriving_battery_space, arriving_amount in zip(
#             arriving_battery_spaces, arriving_amounts
#         ):
#             if arriving_amount > zero_threshold:
#                 # No need to cmpute if there are no

#                 # If the end location does not have the incoming
#                 # battery space in its columns, we add the column
#                 # (with zeroes)
#                 if arriving_battery_space not in (
#                     battery_space[end_location].columns
#                 ):
#                     battery_space[end_location][arriving_battery_space] = (
#                         float(0)
#                     )

#                 if first_arrival_shift_proportion > zero_threshold:
#                     # Otherwise there is no first shift arrival
#                     # We check if the arrivals in the first slot
#                     # are in the run range
#                     # if they are not, then we don't take them into
#                     # account (as the are not in the run) and add them
#                     # in the end_location battery space DataFrame
#                     if time_tag + first_arrival_shift_time <= (
# run_range[-1]):
#                         battery_space[end_location].loc[
#                             time_tag + first_arrival_shift_time,
#                             arriving_battery_space,
#                         ] = battery_space[end_location].loc[
#                             time_tag + first_arrival_shift_time
#                         ][
#                             arriving_battery_space
#                         ] + (
#                             arriving_amount
#                             * first_arrival_shift_proportion
#                             / 2
#                             # / 1
#                         )

#                         # The effects on the current time tag are
#                         # halved,
#                         # as the vehicles arrive unifornmly
#                         # The rest of the impact is in the next
#                         # time tag
#                         if next_time_tag + first_arrival_shift_time <= (
#                             run_range[-1]
#                         ):
#                             battery_space[end_location].loc[
#                                 next_time_tag + first_arrival_shift_time,
#                                 arriving_battery_space,
#                             ] = battery_space[end_location].loc[
#                                 next_time_tag + first_arrival_shift_time
#                             ][
#                                 arriving_battery_space
#                             ] + (
#                                 arriving_amount
#                                 * first_arrival_shift_proportion
#                                 / 2
#                                 # * 0
#                             )
#                 if (1 - first_arrival_shift_proportion) > zero_threshold:

#                     # Otherwise there is no first shift arrival
#                     # We check if the arrivals in the second slot
#                     # are in the run range
#                     # if they are not, then we don't take them into
#                     # account (as the are not in the run)  and add them
#                     # in the end_location battery space DataFrame
#                     if time_tag + second_arrival_shift_time <= (
# run_range[-1]):
#                         battery_space[end_location].loc[
#                             time_tag + second_arrival_shift_time,
#                             arriving_battery_space,
#                         ] = battery_space[end_location].loc[
#                             time_tag + second_arrival_shift_time
#                         ][
#                             arriving_battery_space
#                         ] + (
#                             arriving_amount
#                             * (1 - first_arrival_shift_proportion)
#                             / 2
#                             # / 1
#                         )

#                         # The effects on the current time tag are
#                         # halved,
#                         # as the vehicles arrive unifornmly
#                         # The rest of the impact is in the next
#                         # time tag
#                         if next_time_tag + second_arrival_shift_time <= (
#                             run_range[-1]
#                         ):
#                             battery_space[end_location].loc[
#                                 next_time_tag + second_arrival_shift_time,
#                                 arriving_battery_space,
#                             ] = battery_space[end_location].loc[
#                                 next_time_tag + second_arrival_shift_time
#                             ][
#                                 arriving_battery_space
#                             ] + (
#                                 arriving_amount
#                                 * (1 - first_arrival_shift_proportion)
#                                 / 2
#                                 # * 0
#                             )
#     return battery_space


def travel_space_occupation(
    battery_space: ty.Dict[str, pd.DataFrame],
    time_tag: datetime.datetime,
    time_tag_index: int,
    run_mobility_matrix,  # This is a DataFrame, but MyPy has issues with it
    # These issues might have to do with MultiIndex,
    zero_threshold: float,
    location_names: ty.List[str],
    possible_destinations: ty.Dict[str, ty.List[str]],
    use_day_types_in_charge_computing: bool,
    day_start_hour: int,
    location_split: pd.DataFrame,
    run_arrivals_impact: pd.Series,
    run_range: pd.DatetimeIndex,
) -> ty.Dict[str, pd.DataFrame]:
    next_time_tag: datetime.datetime = time_tag + datetime.timedelta(hours=1)

    # if time_tag_index == 6:
    #     print('00000')
    #     for location_name in location_names:
    #         print(location_name)
    #         ooo = (
    #             battery_space[location_name].iloc[:time_tag_index].sum(axis=1)
    #         )
    #         aaa = location_split[location_name].iloc[:time_tag_index]
    #         print(max((ooo - aaa).values))
    #         # print(ooo)
    #         # print(aaa)
    #         # print(ooo-aaa)
    #         zii = pd.DataFrame(index=ooo.index)
    #         zii['batt'] = ooo.values
    #         zii['loc'] = aaa.values
    #         print(zii)
    #     # print(battery_space['van_customer'].iloc[0:28])
    #     #     print(battery_space['home'].iloc[10:15])
    #     exit()
    # We look at all movements starting at a given location
    for start_location in location_names:
        # battery_space[start_location].iloc[time_tag_index+1] = (
        #         battery_space[start_location].iloc[time_tag_index+1]
        #         + battery_space[start_location].iloc[time_tag_index]
        #     )

        if time_tag_index > 0:
        #     # We add the values from the previous time tag to
        #     # the battery space. We do so because travels can propagate to
        #     # future time tags. I f we just copied the value from
        #     # the previous time tag, we would delete these
        #     # print(time_tag_index, start_location)
        #     # print(battery_space['truck_hub'].iloc[8])
        #     # nori = partial_time_stay_corrections.il
        #     # print('Poooooo')
        #     # print(time_tag_index)
        #     # if time_tag_index == 12:
        #     #     print(battery_space['truck_hub'].iloc[0:24].sum(axis=1))
        #     #     print(battery_space['truck_customer'].iloc[0:24].sum(axis=1))
        #     # print(battery_space['truck_customer'].iloc[11])
        #     # print(battery_space['truck_customer'].iloc[10])

        #     # exit()
        #     # print(battery_space[start_location].iloc[0:24])

            # ...
            battery_space[start_location].iloc[time_tag_index] = (
                battery_space[start_location].iloc[time_tag_index]
                + battery_space[start_location].iloc[time_tag_index - 1]
            )
        # # We can now look at the impact of departures in the next time
        # slot
        # # for the previous iteration, which are deprtures in the current
        # # time
        # # We look at all the possible destinations
        # for end_location in possible_destinations[start_location]:
        #     departures_impact_next_time_slot: float = float(
        #         departures_impact_next_time_slot_store.loc[start_location][
        #             end_location
        #         ]
        #     )

        #     battery_space = impact_of_departures(
        #         battery_space,
        #         start_location,
        #         end_location,
        #         departures_impact_next_time_slot,
        #         time_tag,
        #         next_time_tag,
        #         run_range,
        #         run_mobility_matrix,
        #         distance_header,
        #         electricity_consumption_kWh_per_km,
        #         zero_threshold,
        #         first_wave=False,
        #     )

        # print(battery_space[start_location].iloc[0:10])
        # print(battery_space[end_location].iloc[0:10])
        # # print(battery_space[start_location].iloc[0:3])
        # if time_tag_index == 2 and start_location == 'truck_hub':
        #     #     print(departures_impact_next_time_slot)
        #     #     print(departures_impact_next_time_slot_store)
        #     exit()

        # DO DEPARTURES NEXT TIME HERE, (on current time index, as it has
        #  been incremented)
        # have the var set to 0 at top and
        # updated at the lin where departures_impact_next_time_slot is
        # now set
        # Then do the departing stuff here for these intaed of here
        # Maybe refactor

        # print(battery_space[start_location].iloc[0:24])

        # print(time_tag, 'ryuryrury')
        # print(battery_space['truck_hub'].iloc[8])

        if use_day_types_in_charge_computing and (
            time_tag.hour == day_start_hour
        ):
            battery_space[start_location].loc[time_tag, 0] = (
                location_split.loc[time_tag][start_location]
            )

        # # We look at which battery spaces there are at this location
        # # and sort them. The lowest battery spaces will be first.
        # # These are the ones we assume aremore likely to leave,
        # # as others might want to charge first
        # departing_battery_spaces: ty.List[float] = sorted(
        #     battery_space[start_location].columns.values
        # )

        # We look at all the possible destinations
        for end_location in possible_destinations[start_location]:
            departures_impact_this_time_slot = run_mobility_matrix.loc[
                start_location, end_location, time_tag
            ]['Departures impact']
            departures_this_time_slot = run_mobility_matrix.loc[
                start_location, end_location, time_tag
            ]['Departures amount']

            battery_space, run_arrivals_impact = impact_of_departures(
                battery_space,
                start_location,
                end_location,
                departures_this_time_slot,
                departures_impact_this_time_slot,
                time_tag,
                next_time_tag,
                run_range,
                run_mobility_matrix,
                run_arrivals_impact,
                zero_threshold,
            )

            #     # )
            #     departures_impact: float = run_mobility_matrix.loc[
            #         start_location, end_location, time_tag
            #     ]['Departures impact']

            #     if departures_impact > zero_threshold:
            #         # If there are no departures, we can skip this

            #         # We want to know what the arriving battery spaces
            #         # will be and the amounts/percentages of the fleet
            #  vehicles
            #         # for each arriving battery space
            #         arriving_battery_spaces: ty.List[float] = []
            #         arriving_amounts: ty.List[float] = []

            #         # We iterate through the departing battery spaces
            #         # (reminder, they are ordered from lowest to highest,
            #         # as we assumed that the lower the battery space, the
            # higher
            #         # the likelihood to leave, as vehicleswith more battery
            #  space/
            #         # less available battery capacity wll want to charge
            # first).

            #         # We look at which battery spaces there are at this
            # location
            #         # and sort them. The lowest battery spaces will be first.
            #         # These are the ones we assume aremore likely to leave,
            #         # as others might want to charge first
            #         departing_battery_spaces: ty.List[float] = sorted(
            #             battery_space[start_location].columns.values
            #         )

            #         for departing_battery_space in departing_battery_spaces:
            #             # We will be removing the departures from the lower
            #             # battery spaces from the pool, until we have reached
            #             # all departures. For example, if we have 0.2
            # departures
            #             # and 0.19 vehicles with space equal to zero, 0.2
            # vehicles
            #             # with space 1, and 0.3 vehicles with space 1.6,
            #             # then we will first take all the
            #             # 0.19 vehicles with space 0,
            #             # 0.01 vehicles with space 1,
            #             # and 0 vehicles with space 1.6,
            #             # leaving us with 0 vehicles wth space 0,
            #             # 0.19 vehicles with
            #             # space 1, and 0.3 vehicles with space 1.6
            #             if departures_impact > zero_threshold:
            #                 # We do this until there are no departures left

            #                 # We want to know how many departures will come
            # from
            #                 # the battery space we are looking at. If there
            # are
            #                 # more vehicles with the current space than
            # remaining
            #                 # departures, then we take the remaining
            # departures,
            #                 # otherwise we take all the vehicles with the

            #                 # space and move to the next one
            #                 # This needs to be done separately for the
            # current
            #                 # time slot and the next one
            #                 # (because of the issue of effective impact, as
            #                 # some vehicles stay some of the time)

            #                 this_battery_space_departures_impact_this_time: (
            #                     float
            #                 ) = min(
            #                     departures_impact,
            #                     battery_space[start_location].at[
            #                         time_tag, departing_battery_space
            #                     ],
            #                 )

            #                 # We add these departures to the arriving
            # amounts,
            #                 # as these will arrive to the end location

            #                 arriving_amounts.append(
            #                 this_battery_space_departures_impact_this_time
            #                 )

            #     print(
            #         run_mobility_matrix.loc[start_location, end_location,
            # time_tag]
            #     )
            #     departures_impact: float = run_mobility_matrix.loc[
            #         start_location, end_location, time_tag
            #     ]['Departures impact']
            #     print(departures_impact)
            #     exit()

            # # For each leg (start/end location combination), we
            # # look up the consumption
            # this_leg_consumption: float = (
            #     run_mobility_matrix.loc[
            #         start_location, end_location, time_tag
            #     ][distance_header]
            #     * electricity_consumption_kWh_per_km
            # )

            # We also look up how many vehicles depart
            # departures: float = run_mobility_matrix.loc[
            #     start_location, end_location, time_tag
            # ]['Departures amount']
            # if time_tag_index == 1:
            #     print('Soo')
            #     exit()
            # Given that the departures happen uniformly,
            # their impact in the current time slot is reduced,
            # as some will stay for some time. On average, they
            # stay for half of the time. That means that we have to shift some
            # of the impact to thenext time slot.
            # With a partial correction factor,
            # this becomes (1-partial time correction)/2
            # this_location_and_time_slot_partial_time_stay_correction: float
            #  = (
            #     float(
            #         partial_time_stay_corrections.loc[
            # time_tag][start_location]
            #     )
            # )
            # if this_location_and_time_slot_partial_time_stay > 0:
            #     print(this_location_and_time_slot_partial_time_stay)
            #     exit()
            # if (this_location_and_time_slot_partial_time_correction) > 0:
            # print(this_location_and_time_slot_partial_time_correction)

            # this_time_slot_departure_correction_factor: float = (
            #     # 1 / 2
            #     # -
            #     this_location_and_time_slot_partial_time_stay_correction
            #     # * 2
            #     # 1 - this_location_and_time_slot_partial_time_correction
            #     # / 2
            # )

            # print(this_time_slot_departure_correction_factor)
            # exit()
            # else:
            #     this_time_slot_departure_correction_factor = 0
            # next_time_slot_departure_correction_factor: float = (
            #     1 - this_time_slot_departure_correction_factor
            # )
            # # if this_location_and_time_slot_partial_time_stay_correction
            # > 0:
            # print(time_tag_index)
            # print(end_location)
            # print(this_location_and_time_slot_partial_time_stay_correction)
            # print(this_time_slot_departure_correction_factor)
            # print(next_time_slot_departure_correction_factor)
            # print(departures)
            # input()
            # if time_tag_index == 12:
            #     print('RTiii')
            #     print(time_tag)
            #     print(
            #         battery_space['truck_hub']
            #         .iloc[0 : time_tag_index + 2]
            #         .sum(axis=1)
            #     )
            #     # print(run_mobility_matrix.loc['truck_customer'].iloc[0:24])
            #     exit()

            # departures_impact_this_time_slot: float = (
            #     departures * this_time_slot_departure_correction_factor
            # )
            # departures_impact_next_time_slot_store.loc[
            #     start_location, end_location
            # ] = (departures * next_time_slot_departure_correction_factor)
            # if time_tag_index == 10:
            #     print('Foo')
            #     print(departures)
            #     print(next_time_slot_departure_correction_factor)
            # print(time_tag_index)
            # print(start_location, end_location)
            # print(departures_impact_this_time_slot)
            # print(departures_impact_next_time_slot_store)
            # # if departures > 0:
            # #     print('Print')
            # #     exit()
            # if time_tag_index == 3:
            #     exit()
            # if this_location_and_time_slot_partial_time_correction > 0:
            #     print(time_tag_index)
            #     print(this_location_and_time_slot_partial_time_correction)
            #     print(departures_impact_this_time_slot)
            #     print(departures_impact_next_time_slot)
            # if time_tag_index ==4 and end_location == 'truck_hub':
            #     print(departures)
            #     print(departures_impact_this_time_slot)
            #     print(departures_impact_next_time_slot)
            #     exit()
            # print(time_tag_index)
            # print('Dep', departures)
            # if time_tag != run_range[-1]:
            #     battery_space[start_location].iloc[time_tag_index + 1] = (
            #         battery_space[start_location].iloc[time_tag_index + 1]
            #         + battery_space[start_location].iloc[time_tag_index]
            # #     )
            # print(start_location, end_location)
            # print(battery_space[start_location].iloc[0 : time_tag_index + 4])
            # print(battery_space[end_location].iloc[0 : time_tag_index + 4])

            # battery_space = impact_of_departures(
            #     battery_space,
            #     start_location,
            #     end_location,
            #     departures_impact_this_time_slot,
            #     departures_impact_this_time_slot,
            #     time_tag,
            #     next_time_tag,
            #     run_range,
            #     run_mobility_matrix,
            #     distance_header,
            #     electricity_consumption_kWh_per_km,
            #     zero_threshold,
            #     first_wave=False,
            # )
            # print('Impact')
            # print(battery_space[start_location].iloc[0 : time_tag_index + 4])
            # print(battery_space[end_location].iloc[0 : time_tag_index + 4])

            # if time_tag_index == 4 and start_location == 'truck_customer':
            #     exit()
    #         if departures > zero_threshold:
    #             # If there are no departures, we can skip this

    #             # We want to know what the arriving battery spaces
    #             # will be and the amounts/percentages of the fleet vehicles
    #             # for each arriving battery space
    #             arriving_battery_spaces: ty.List[float] = []
    #             arriving_amounts: ty.List[float] = []

    #             # We also need the duration of the leg
    #             travelling_time: float = run_mobility_matrix.loc[
    #                 start_location, end_location, time_tag
    #             ]['Duration (hours)']

    #             # We iterate through the departing battery spaces
    #             # (reminder, they are ordered from lowest to highest,
    #             # as we assumed that the lower the battery space, the higher
    #             # the likelihood to leave, as vehicleswith more battery
    # space/
    #             # less available battery capacity wll want to charge first).
    #             print('Haha')
    #             print(battery_space['truck_customer'].iloc[0:24])
    #             # if time_tag_index >= 0:
    #             #     battery_space[start_location].iloc[time_tag_index + 1]
    #  = (
    #             #         battery_space[start_location].iloc[time_tag_index
    # + 1]
    #             #         + battery_space[start_location].iloc[
    # time_tag_index]
    #             #     )
    #             # print(battery_space['truck_customer'].iloc[0:24])
    #             #     exit()

    #             for departing_battery_space in departing_battery_spaces:
    #                 # We will be removing the departures from the lower
    #                 # battery spaces from the pool, until we have reached
    #                 # all departures. For example, if we have 0.2 departures
    #                 # and 0.19 vehicles with space equal to zero, 0.2
    #                   vehicles
    #                 # with space 1, and 0.3 vehicles with space 1.6,
    #                 # then we will first take all the
    #                 # 0.19 vehicles with space 0,
    #                 # 0.01 vehicles with space 1,
    #                 # and 0 vehicles with space 1.6,
    #                 # leaving us with 0 vehicles wth space 0,
    #                 # 0.19 vehicles with
    #                 # space 1, and 0.3 vehicles with space 1.6
    #                 if departures > zero_threshold:
    #                     # (the departures threshold is there
    #                     # to avoid issues with floating point numbers, where
    #                     # we could have some variable being 0.1+0.2
    #                     # and removing that variabl from 0.3 would not be
    #                   zero

    #                     # We need to know in which slots the vehicles
    #                     # will arrive at their destination and the proprtion
    #                     # of these slots
    #                     travelling_time = float(travelling_time)
    #                     first_arrival_shift: int = (
    # math.floor(travelling_time))
    #                     first_arrival_shift_time = datetime.timedelta(
    #                         hours=first_arrival_shift
    #                     )
    #                     second_arrival_shift_time: datetime.timedelta = (
    #                         datetime.timedelta(hours=first_arrival_shift + 1)
    #                     )
    #                     first_arrival_shift_proportion: float = (
    #                         1 - travelling_time % 1
    #                     )

    #                     # We want to know how many departures will come from
    #                     # the battery space we are looking at. If there are
    #                     # more vehicles with the current space than remaining
    #                     # departures, then we take the remaining departures,
    #                     # otherwise we take all the vehicles with the current
    #                     # space and move to the next one
    #                     # This needs to be done separately for the current
    #                     # time slot and the next one
    #                     # (because of the issue of effective impact, as
    #                     # some vehicles stay some of the time)

    #                     this_battery_space_departures_impact_this_time: (
    #                         float
    #                     ) = min(
    #                         departures_impact_this_time_slot,
    #                         battery_space[start_location].at[
    #                             time_tag, departing_battery_space
    #                         ],
    #                     )
    #                     this_battery_space_departures_impact_nxt_time: (
    #                         float
    #                     ) = min(
    #                         departures_impact_next_time_slot,
    #                         battery_space[start_location].at[
    #                             time_tag, departing_battery_space
    #                         ],
    #                     )
    #                     # We add these departures to the arriving amounts,
    #                     # as these will arrive to the end location

    #                     arriving_amounts.append(
    #                         this_battery_space_departures_impact_this_time
    #                         + this_battery_space_departures_impact_nxt_time
    #                     )
    #                     # this_battery_space_departures_impact_nxt_time: (
    #                     #     float
    #                     # ) = min(
    #                     #     departures_impact_next_time_slot,
    #                     #     battery_space[start_location].at[
    #                     #         time_tag, departing_battery_space
    #                     #     ],
    #                     # )
    #                     if time_tag_index == 10:
    #                         print('Miiiii')
    #                         print(departing_battery_space)
    #                         print(
    #                             this_battery_space_departures_impact_this_time
    #                         )
    #                         print(
    #                             this_battery_space_departures_impact_nxt_time
    #                         )
    #                         if departing_battery_space > 60:
    #                             exit()
    #                         # exit()
    #                     # Note that we use the current time tag for the
    #                     # available battery spaces in looking at the impact
    #                       of
    #                     # in the next time tag/slot. This is because the
    #                     # reference occupancy is in the current time slot.
    #                     # This might lead to negative occupancy values
    #                     # for an iteration, but these will be compensated
    #                     # when copying the occupancies down one step
    #                     # see above, where we add the values from the
    #                     # previous time

    #

    #                     # if start_location == 'home':
    #                     #     print(time_tag, end_location)
    #                     #     print(
    #                     #         battery_space[start_location]
    #                     #         .loc[:time_tag]
    #                     #         .sum(axis=1)
    #                     #     )
    #                     #     print(
    #                     #         battery_space[end_location]
    #                     #         .loc[:time_tag]
    #                     #         .sum(axis=1)
    #                     #     )

    #                     # exit()

    #                     # We add these departures to the arriving amounts,
    #                     # as these will arrive to the end location
    #                     # arriving_amounts.append(
    #                     #     this_battery_space_departures_impact_this_time
    #                     #     # +
    #                        this_battery_space_departures_impact_nxt_time
    #                     # )

    #                     # We also add the corresponding battery space at
    #                     # arrival, given by the original battery space plus
    #                     # the leg's consumption
    #                     arriving_battery_spaces.append(
    #                         departing_battery_space + this_leg_consumption
    #                     )

    #                     # We update the departures (i.e. how many remain
    #                     # for larger battery spaces)
    #                     departures_impact_this_time_slot -= (
    #                         this_battery_space_departures_impact_this_time
    #                     )
    #                     departures_impact_next_time_slot -= (
    #                         this_battery_space_departures_impact_nxt_time
    #                     )

    #                     # Finally, we remove the departures from the start
    #                     # location for the current time slot
    #
    #                     battery_space[start_location].loc[
    #                         time_tag, departing_battery_space
    #                     ] = (
    #                         battery_space[start_location].loc[time_tag][
    #                             departing_battery_space
    #                         ]
    #                         - this_battery_space_departures_impact_this_time
    #                     )
    #                     # if start_location == 'truck_hub':

    #                     # print(time_tag_index, 'zee')
    #                     # print(battery_space['truck_hub'].iloc[
    #                     # time_tag_index-1: time_tag_index+2])
    #                     # The effects on the current time tag are halved,
    #                     # as the vehicles leave unifornmly
    #                     # The rest of the impact is in the next
    #                     # time tag
    #                     if next_time_tag in run_range:

    #                         # Now that we nowthe updated battery spaces that
    #                         # we will copy down, we can look at the next time
    #                         # slot

    #                         battery_space[start_location].loc[
    #                             next_time_tag, departing_battery_space
    #                         ] = (
    #                             battery_space[start_location].loc[
    #                                 next_time_tag
    #                             ][departing_battery_space]
    #                             -
    #                             this_battery_space_departures_impact_nxt_time
    #                         )

    #                     # print(time_tag_index, 'zii')
    #                     # print(battery_space['truck_hub'].iloc
    #                     # [time_tag_index-1: time_tag_index+2])
    #             if time_tag_index == 10:
    #                 print(battery_space['truck_customer'].iloc[0:24])
    #                 # exit()

    #             # # We only need to do this if there are actually
    #             # # travels between
    #             # # the two locations at that time slot
    #             # if len(arriving_battery_spaces) > 0 :

    #             # We now can update the battery spaces in the end location.
    #             for arriving_battery_space, arriving_amount in zip(
    #                 arriving_battery_spaces, arriving_amounts
    #             ):
    #                 print('Lalalal')
    #                 print(time_tag)
    #                 print(end_location)
    #                 print(arriving_battery_spaces)
    #                 print(arriving_amounts)
    #                 print(sum(arriving_amounts))
    #                 if arriving_amount > zero_threshold:
    #                     # No need to compute if there are no arrivals

    #                     # If the end location does not have the incoming
    #                     # battery space in its columns, we add the column
    #                     # (with zeroes)
    #                     if arriving_battery_space not in (
    #                         battery_space[end_location].columns
    #                     ):
    #                         battery_space[end_location][
    #                             arriving_battery_space
    #                         ] = float(0)

    #                     # print('Hoo?')
    #                     # print(time_tag)
    #                     # exit()
    #                     # # print(battery_space['truck_hub'].iloc[54])
    #                     # print(time_tag)
    #                     # print(first_arrival_shift_time)
    #                     # print(arriving_battery_space)
    #                     # print(arriving_amount)
    #                     # print(first_arrival_shift_proportion)
    #                     # print('YYYY')

    #                     if first_arrival_shift_proportion > zero_threshold:
    #                         # Otherwise there is no first shift arrival
    #                         # We check if the arrivals in the first slot
    #                         # are in the run range
    #                         # if they are not, then we don't take them into
    #                         # account (as the are not in the run) and add
    #                         # them
    #                         # in the end_location battery space DataFrame
    #                         if time_tag + first_arrival_shift_time <= (
    #                             run_range[-1]
    #                         ):
    #                             # print('ZZZ')
    #

    #                             battery_space[end_location].loc[
    #                                 time_tag + first_arrival_shift_time,
    #                                 arriving_battery_space,
    #                             ] = battery_space[end_location].loc[
    #                                 time_tag + first_arrival_shift_time
    #                             ][
    #                                 arriving_battery_space
    #                             ] + (
    #                                 arriving_amount
    #                                 * first_arrival_shift_proportion
    #                                 / 2
    #                                 # / 1
    #                             )

    #                             # The effects on the current time tag are
    #                             # halved,
    #                             # as the vehicles arrive unifornmly
    #                             # The rest of the impact is in the next
    #                             # time tag
    #                             if (
    #                                 next_time_tag + first_arrival_shift_time
    #                                 <= (run_range[-1])
    #                             ):
    #                                 battery_space[end_location].loc[
    #                                     next_time_tag
    #                                     + first_arrival_shift_time,
    #                                     arriving_battery_space,
    #                                 ] = battery_space[end_location].loc[
    #                                     next_time_tag
    #                                     + first_arrival_shift_time
    #                                 ][
    #                                     arriving_battery_space
    #                                 ] + (
    #                                     arriving_amount
    #                                     * first_arrival_shift_proportion
    #                                     / 2
    #                                     # * 0
    #                                 )

    #                             # print(
    #                             #     arriving_amount
    #                             #     * first_arrival_shift_proportion
    #                             # )
    #                             # print('HSK')
    #                             # print(
    #                             #     battery_space[end_location].loc[
    #                             #         time_tag + first_arrival_shift_time
    #                             #     ][arriving_battery_space]
    #                             # )
    #                             # print('Lacrosse')
    #                             # print(time_tag_index)
    #                             # moo = time_tag_index + 2 + 6
    #                             # print(battery_space[end_location].columns)
    #                             # print(time_tag + first_arrival_shift_time)
    #                             # too: datetime.datetime = (
    #                             #     time_tag + first_arrival_shift_time
    #                             # )
    #                             # print(too)
    #                             # print(arriving_battery_space)
    #                             # print(
    #                             #     battery_space[end_location].loc[
    #                             #         time_tag +
    #                                       first_arrival_shift_time,
    #                             #         arriving_battery_space,
    #                             #     ]
    #                             # )
    #                             # if moo > 10:
    #                             #     print('Score')
    #                             #     print(
    #                             #         battery_space[end_location].loc[
    #                             #             (too, moo, f't00{moo}'),
    #                             #             arriving_battery_space
    #                             #         ]
    #                             #     )
    #                             # print(battery_space['truck_hub'].iloc[54])

    #                     if (1 - first_arrival_shift_proportion) > (
    #                         zero_threshold
    #                     ):
    #                         # Otherwise there is no first shift arrival
    #                         # We check if the arrivals in the second slot
    #                         # are in the run range
    #                         # if they are not, then we don't take them into
    #                         # account (as the are not in the run)  and add
    #                         # them
    #                         # in the end_location battery space DataFrame
    #                         if time_tag + second_arrival_shift_time <= (
    #                             run_range[-1]
    #                         ):
    #                             battery_space[end_location].loc[
    #                                 time_tag + second_arrival_shift_time,
    #                                 arriving_battery_space,
    #                             ] = battery_space[end_location].loc[
    #                                 time_tag + second_arrival_shift_time
    #                             ][
    #                                 arriving_battery_space
    #                             ] + (
    #                                 arriving_amount
    #                                 * (1 - first_arrival_shift_proportion)
    #                                 / 2
    #                                 # / 1
    #                             )

    #                             # The effects on the current time tag are
    #                             # halved,
    #                             # as the vehicles arrive unifornmly
    #                             # The rest of the impact is in the next
    #                             # time tag
    #                             if (
    #                                 next_time_tag + second_arrival_shift_time
    #                                 <= (run_range[-1])
    #                             ):
    #                                 battery_space[end_location].loc[
    #                                     next_time_tag
    #                                     + second_arrival_shift_time,
    #                                     arriving_battery_space,
    #                                 ] = battery_space[end_location].loc[
    #                                     next_time_tag
    #                                     + second_arrival_shift_time
    #                                 ][
    #                                     arriving_battery_space
    #                                 ] + (
    #                                     arriving_amount
    #                                     * (
    #                                           1
    #                                           -
    #                                           first_arrival_shift_proportion
    #                                       )
    #                                     / 2
    #                                     # * 0
    #                                 )
    #         # print(time_tag_index, 'zoo')
    #         # print(battery_space['truck_hub'].iloc[time_tag_index-1:
    #         #
    #         # time_tag_index+2])

    # # Have  arrivals not connect at all if partial (until leave)
    # # Or assume they move around get connected

    # if time_tag_index == 1:
    #     print('zzzz')
    #     print(departures_impact_next_time_slot_store)
    #     exit()

    return battery_space  # , departures_impact_next_time_slot_store


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
    pd.DataFrame,
    pd.Series,
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
    # run_departures_impact: pd.Series = run_mobility_matrix[
    #     'Departures impact'
    # ].copy()
    # run_departures: pd.Series =
    # run_mobility_matrix['Departures amount'].copy()
    run_arrivals_impact: pd.Series = run_mobility_matrix[
        'Arrivals impact'
    ].copy()

    # battery_space_shift_departures_impact: pd.DataFrame = pd.read_pickle(
    #     f'{output_folder}/{scenario_name}_'
    #     f'run_battery_space_shifts_departures_impact.pkl'
    # )
    battery_space_shift_arrivals_impact: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_'
        f'run_battery_space_shifts_departures_impact.pkl'
    )

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
        battery_space_shift_arrivals_impact,
        run_arrivals_impact,
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
        # zero_threshold: float = general_parameters['numbers']
        # ['zero_threshold']

        # battery_space[location_name] = battery_space[location_name][
        #     battery_space[location_name].columns[
        #         battery_space[location_name].sum() > zero_threshold
        #     ]
        # ]
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
    print(sum_of_battery_spaces.iloc[0:24])
    # sum_of_battery_spaces.to_csv('sumbatt.csv')


def get_charging_profile(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:

    (
        battery_space,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        battery_space_shift_arrivals_impact,
        run_arrivals_impact,
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

    # use_weighted_km: bool = vehicle_parameters['use_weighted']
    # if use_weighted_km:
    #     distance_header: str = 'Weighted distance (km)'
    # else:
    #     distance_header = 'Distance (km)'
    # electricity_consumption_kWh_per_km: float = vehicle_parameters[
    #     'base_consumption_per_km'
    # ]['electricity_kWh']

    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict[str, str] = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    location_split_table_name: str = f'{scenario_name}_location_split'
    location_split: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{location_split_table_name}.pkl'
    )

    # partial_time_stay_corrections_table_name: str = (
    #     f'{scenario_name}_partial_time_stay_corrections'
    # )
    # partial_time_stay_corrections: pd.DataFrame = pd.read_pickle(
    #     f'{output_folder}/{partial_time_stay_corrections_table_name}.pkl'
    # )

    # We look at how the available battery space in the vehicles moves around
    # (it increases with movements and decreases with charging)

    # # We need a storage variable for departures in a subsequent time slot
    # departures_impact_next_time_slot_store: pd.DataFrame = pd.DataFrame(
    #     np.zeros((len(location_names), len(location_names))),
    #     columns=location_names,
    #     index=location_names,
    # )
    # departures_impact_next_time_slot_store.index.name = 'Start location'

    for time_tag_index, (time_tag, run_day_type) in enumerate(
        zip(run_range, run_day_types)
    ):
        print(
            run_arrivals_impact.loc['truck_customer', 'truck_hub'].iloc[0:10]
        )

        if time_tag_index == 9:
            print(time_tag)
            print(
                battery_space['truck_hub']
                .iloc[time_tag_index - 4 : time_tag_index + 1]
                .sum(axis=1)
            )
            print(
                battery_space['truck_customer']
                .iloc[time_tag_index - 4 : time_tag_index + 1]
                .sum(axis=1)
            )
            print(location_split.iloc[time_tag_index - 4 : time_tag_index + 1])
            print(
                run_mobility_matrix.loc['truck_hub', 'truck_customer'].iloc[
                    0:10
                ]
            )
            print(
                run_mobility_matrix.loc['truck_customer', 'truck_hub'].iloc[
                    0:10
                ]
            )
            print(
                run_arrivals_impact.loc['truck_customer', 'truck_hub'].iloc[
                    0:10
                ]
            )

            exit()
        if time_tag.hour == 0:
            print(time_tag)
        # print(time_tag_index)
        # if time_tag_index > 100:
        #     # print(battery_space['truck_hub'].iloc[89:100])
        #     # print(time_tag)
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

            # battery_space_shift_arrivals_impact

            battery_space = travel_space_occupation(
                battery_space,
                time_tag,
                time_tag_index,
                run_mobility_matrix,
                zero_threshold,
                location_names,
                possible_destinations,
                use_day_types_in_charge_computing,
                day_start_hour,
                location_split,
                run_arrivals_impact,
                run_range,
            )
            # if time_tag_index == 10:
            #     print(time_tag)
            #     print(battery_space['truck_hub'].iloc[0:14])
            #     print(departures_impact_next_time_slot_store)
            #     exit()
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

            # print(time_tag)
            # print(battery_space['truck_hub'].iloc[0:11])
            loop_mid: datetime.datetime = datetime.datetime.now()
            # if time_tag_index == 20:

            #     exit()
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
            # print(time_tag, '777')
            # print(battery_space['truck_hub'].iloc[0:11])

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
            battery_space_shift_arrivals_impact,
            run_arrivals_impact,
        ) = get_charging_framework(scenario, case_name, general_parameters)
        print(battery_space_shift_arrivals_impact)
        exit()
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
                # if amount_in_spillover > zero_threshold:
                #     print(amount_in_spillover)
                #     print(battery_space[location_name][0:26])
                #     print('Poisbjdhsjh')
                #     print(
                #         spillover_battery_space[location_name].loc[
                #             day_end_time_tag
                #         ]
                #     )
                #     exit()
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
                    (
                        spillover_battery_space,
                        # departures_impact_next_time_slot,
                    ) = travel_space_occupation(
                        spillover_battery_space,
                        spillover_time_tag,
                        spillover_time_tag_index,
                        run_mobility_matrix,
                        zero_threshold,
                        location_names,
                        possible_destinations,
                        use_day_types_in_charge_computing,
                        day_start_hour,
                        location_split,
                        run_arrivals_impact,
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

    # file_parameters: ty.Dict[str, str] = general_parameters['files']
    # output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    # location_split_table_name: str = f'{scenario_name}_location_split'
    # location_split: pd.DataFrame = pd.read_pickle(
    #     f'{output_folder}/{location_split_table_name}.pkl'
    # )
    print(location_split.iloc[0:24])
    # location_split.to_csv('locsplit.csv')
    # print()
    # for location_name in location_names:
    # print(battery_space[location_name].sum(axis=1).iloc[0:10])
    # print(battery_space['truck_hub'].iloc[0:24].sum(axis=1))
    # print(battery_space['truck_customer'].iloc[0:24].sum(axis=1))
    # print(battery_space['truck_hub'].iloc[0:24])
    # print(battery_space['truck_customer'].iloc[0:24])
    # exit()
    # print('Still some negative battery spaces taying on! Correct that')

    # # print(run_mobility_matrix.lloc['truck_customer'].iloc[0:24])
    # print('Why partial stay correction X 2 (is it actually true?)')
    # print(partial_time_stay_corrections.iloc[0:24])
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
