
import math
import datetime
import pandas as pd
import numpy as np

from ETS_CookBook import ETS_CookBook as cook

try:
    import run_time
except ModuleNotFoundError:
    from ChaProEV import run_time
# So that it works both as a standalone (1st) and as a package (2nd)

try:
    import mobility
except ModuleNotFoundError:
    from ChaProEV import mobility
# So that it works both as a standalone (1st) and as a package (2nd)  



# do it per trip
# battery level trigger (below this, will charge)

# then max power or spread

# How to deal with shift to next day? 
# Trip of prior day might correlate with next day
    

# def get_trip_charging_array(trip_name, temperature_correction_factors, parameters):
#     ...
#     or as method/property in trip?
# Dependence on temperatures, but also on battery level at day start 
# So maybe do for each day(?)
# 2
parameters_file_name = 'scenarios/baseline.toml'
parameters = cook.parameters_from_TOML(parameters_file_name)
charging_parameters = parameters['charging']
vehicle_parameters = parameters['vehicle']
use_weighted_km = vehicle_parameters['use_weighted']
if use_weighted_km:
    distance_header = 'Weighted distance (km)'
else:
    distance_header = 'Distance (km)'
electricity_consumption_kWh_per_km = vehicle_parameters[
    'base_consumption_per_km']['electricity_kWh']
run_range, run_hour_numbers = run_time.get_time_range(parameters)
SPINE_hour_numbers = [f't{hour_number:04}' for hour_number in run_hour_numbers]
location_parameters = parameters['locations']
location_names = [
    location_name for location_name in location_parameters
]
scenario = parameters['scenario']
case_name = parameters['case_name']

file_parameters = parameters['files']
output_folder = file_parameters['output_folder']
groupfile_root = file_parameters['groupfile_root']
groupfile_name = f'{groupfile_root}_{case_name}'
location_split_table_name = f'{scenario}_location_split'
location_split = cook.read_table_from_database(
    location_split_table_name, f'{output_folder}/{groupfile_name}.sqlite3'
)
location_split['Time tag'] = pd.to_datetime(location_split['Time tag'])
location_split = location_split.set_index('Time tag')


# We look at the various battery spaces that are available
# at this charging location (i.e. percent of vehicles with
# a given battery space per location)
battery_space = {}
for location_name in location_names:
    battery_space[location_name] = pd.DataFrame(
        run_range,
        columns= ['Time Tag'])
    battery_space[location_name]['Hour Number'] = run_hour_numbers
    battery_space[location_name]['SPINE_Hour_Number'] = SPINE_hour_numbers
    # battery_space[0] = 0
    battery_space[location_name] = battery_space[location_name].set_index(
        ['Time Tag', 'Hour Number', 'SPINE_Hour_Number'])
    battery_space[location_name][0] = 0 
    battery_space[location_name][0].iloc[0] = location_split.loc[run_range[0]][location_name]
# print(battery_space['home'])
# exit()
    
    # battery_space.loc[run_range[2], 5/7] = 19.89
    # battery_space = battery_space.fillna(0)

# location_start_split = mobility.get_location_split(parameters).iloc[0]



run_mobility_matrix = cook.read_table_from_database(
    f'{scenario}_run_mobility_matrix', 
    f'{output_folder}/{groupfile_name}.sqlite3'
)
run_mobility_matrix['Time tag'] = pd.to_datetime(
    run_mobility_matrix['Time tag'])
run_mobility_matrix = run_mobility_matrix.set_index(
    ['From', 'To', 'Time tag'])
# print(run_mobility_matrix.loc['home', 'work'])
charge_drawn_by_vehicles = pd.DataFrame(
    np.zeros((len(run_range), len(location_names))),
    columns=location_names, index=run_range
)
charge_drawn_from_network = pd.DataFrame(
    np.zeros((len(run_range), len(location_names))),
    columns=location_names, index=run_range
)
start_time = datetime.datetime.now()
loop_start = start_time
# too = 0

zoti = 0 
guac = pd.DataFrame(
    # np.zeros((len(location_names), 1)),
    # columns=['ziti'],
    index=location_names
)
guic = pd.DataFrame(
    # np.zeros((len(location_names), 1)),
    # columns=['ziti'],
    index=location_names
)

# We look at how the available battery space in the vehicles moves around
# (it increases with movements and decreases with charging)
for time_tag_index, time_tag in enumerate(run_range):
    loop_end = datetime.datetime.now()
#     thresh = 80
    
#     if len(battery_space['home'].columns.values)>0:
#         if max(battery_space['home'].columns.values) > thresh:
            
#             print(time_tag)
#             # print(battery_space['home'].columns.values)
#             for location_name in location_names:
#                 above_tresh = [
#                     space 
#                     for space in battery_space[location_name].columns.values 
#                     if space>thresh
#                 ]
#                 if len(above_tresh) > 0:
#                     print(location_name)
#                     print(battery_space[location_name].loc[time_tag][above_tresh])
#             too += 1
#             if too > 6:
#                 exit()
    # if time_tag_index > 2000 :
    #     exit()


    # print(time_tag)


    # print((loop_end-loop_start).total_seconds())
    # if (loop_end-loop_start).total_seconds() > 0.89:
    #     input()
    # >1 seems to be because of batt  
    # cherck if large batt spaces are gone
    # if (loop_end-loop_start).total_seconds() > 1:
    #     exit()
    loop_start = datetime.datetime.now()
    
 
    # We start with the battery space reduction duw to moving
    batt_start = datetime.datetime.now()
    batt_times = []
    # print(location_split.loc[time_tag])

    # We look at all movements starting at a given location
    for start_location in location_names:
        batt_0 = datetime.datetime.now()
        # batt_loc_start = datetime.datetime.now()

        if time_tag_index > 0 :
            # We add the values from the previous time tag to
            # the battery space. We do so because travels can propagate to
            # future time tags. I f we just copied the value from
            # the previous time tag, we would delete these
            battery_space[start_location].iloc[time_tag_index] = (
                battery_space[start_location].iloc[time_tag_index]
                +
                battery_space[start_location].iloc[time_tag_index-1]
            )
        # if time_tag_index ==24:
        #     print(battery_space['work'].iloc[0:24])
        #     print(charge_drawn_by_vehicles.iloc[0:24].sum())
        #     exit()

        # We delete columns where all the amounts per battery space are zero
        # (for example, ones where we had a battery space that was
        # removed because of charging
        battery_space[start_location] = battery_space[start_location].loc[
            :, (battery_space[start_location]!=0).any(axis=0)
        ]
        
        # We look at which battery spaces there are at this location
        # and sort them. The lowest battery spaces will be first.
        # These are the ones we assume aremore likely to leave,
        # as others might want to charge first
        departing_battery_spaces = (
                sorted(battery_space[start_location].columns.values)
            )
        # if start_location == 'home':
        #     print(departing_battery_spaces)
        # if time_tag_index == 0:
        #     battery_space[start_location].loc[time_tag, 0] = (
        #         location_split.loc[time_tag][start_location]
        #     )
        #     battery_space[start_location] = (
        #         battery_space[start_location].fillna(0)
        #     )
        #     possible_battery_spaces = [0]
        # else:
 
        #     possible_battery_spaces = (
        #         sorted(battery_space[start_location].columns.values)
        #     )
        #     # print(time_tag)
        #     # print(start_location)
        #     # print(battery_space[start_location])
        #     # print(possible_battery_spaces)
        #     # print(battery_space[start_location].loc[
        #     #                     time_tag, possible_battery_spaces] )
        #     if max(battery_space[start_location].iloc[
        #             time_tag_index-1][
        #                 possible_battery_spaces]) >= 0:
        #         battery_space[start_location].loc[
        #                             time_tag, possible_battery_spaces] = (
        #             battery_space[start_location].loc[
        #                                     time_tag, possible_battery_spaces]
        #                                     # .values[0]
        #             +
        #             battery_space[start_location].iloc[
        #                 time_tag_index-1][
        #                     possible_battery_spaces]
        #         )
        #         battery_space[start_location] = battery_space[start_location].fillna(0)
            

            
            # exit()
            # print('Poss', battery_space[start_location])
            # for possible_battery_space in possible_battery_spaces:
            #     # print('Poss', battery_space[start_location])
                
            #     battery_space[start_location].loc[
            #                     time_tag, possible_battery_space] = (
            #                         battery_space[start_location].loc[
            #                             time_tag, possible_battery_space]
            #                             .values
            #                         +
            #                         battery_space[start_location].iloc[
            #                             time_tag_index-1][
            #                                 possible_battery_space]
            #                     )
        
        batt_1 = datetime.datetime.now()
        # print((batt_1-batt_0).total_seconds())
        # input()
        # if (batt_1-batt_0).total_seconds()>1:
        #     print(time_tag)
        #     print(start_location)
        #     print(possible_battery_spaces)
        #     print(battery_space[start_location].loc[time_tag])
        #     print(battery_space[start_location].iloc[time_tag_index-1])
        #     print(battery_space[start_location].loc[time_tag][possible_battery_spaces])
        #     print(battery_space[start_location].iloc[time_tag_index-1][possible_battery_spaces])
        #     print('Do sum on range of spaces at once, not in a loop????')
        #     print('Do that elsewhere?')
        #     exit()
        batt_times.append((batt_1-batt_0).total_seconds())

        # print('Possible battery spaces', possible_battery_spaces)
        # print(battery_space[start_location])
        # if time_tag_index>0:
        #     exit()

        # We look at all the possible destinations
        for end_location in location_names:
            # For each leg (start/end location combination), we
            # look up the consumption
            this_leg_consumption = (
                run_mobility_matrix.loc[
                            start_location, end_location, time_tag][
                                distance_header]
                *
                electricity_consumption_kWh_per_km
            )
            # print(start_location, end_location)
            batt_x = datetime.datetime.now()

            # We also look up how many vehicles depart
            departures = run_mobility_matrix.loc[
                start_location, end_location, time_tag][
                    'Departures amount']
            

            # if start_location == 'work':
            #     if end_location == 'home':
            #         print(departures)
            #         if time_tag_index == 12:
            #             print(time_tag)
            #             print(departing_battery_spaces)
                        # exit()
            # print('Odf', (datetime.datetime.now()-batt_x).total_seconds())
            # print('Doki', departures)
            
            # if time_tag_index > 1:
            #     print(run_mobility_matrix.loc[
            #     :, :, time_tag][
            #         'Departures amount'])
            #     exit()
            # print(time_tag_index)

            # We want to know what the arriving battery spaces
            # will be and the amounts/percentages of the fleet vehicles
            # for each arriving battery space
            arriving_battery_spaces = []
            arriving_amounts = []
            
            # We also need the duration of the leg
            travelling_time = run_mobility_matrix.loc[
                            start_location, end_location, time_tag][
                                'Duration (hours)']
            
                # print('First arrival shift', first_arrival_shift, first_arrival_shift_proportion)
            # attempts = 0

            # print(0.1+0.2-0.3)
            # exit()

            # Float precision can mean that we have exteremly small values
            # that are actually zero
            departures_threshold = charging_parameters['departures_threshold']

            # print('spaces', departing_battery_spaces)
            
            # We iterate through the departing battery spaces
            # (reminder, they are ordered from lowest to highest,
            # as we assumed that the lower the battery space, the higher
            # the likelihood to leave, as vehicleswith more battery space/
            # less available battery capacity wll want to charge first).
            for departing_battery_space in departing_battery_spaces:

                



                # print('Zoooz', battery_space[start_location].loc[
                #             time_tag][possible_battery_spaces])
                # print(possible_battery_spaces)
            # while departures > departures_threshold :
                
                
                #     exit()

                # We will be removing the departures from the lower
                # battery spaces from the pool, until we have reached
                # all departures. For example, if we have 0.2 departures and
                # 0.19 vehicles with space equal to zero, 0.2 vehicles
                # with space 1, and 0.3 vehicles with space 1.6,
                # then we will first take all the 0.19 vehicles with space 0,
                # 0.01 vehicles with space 1, and 0 vehicles with space 1.6,
                # leaving us with 0 vehicles wth space 0, 0.19 vehicles with
                # space 1, and 0.3 vehicles with space 1.6
                if departures > departures_threshold :
                    # (the departures threshold is there
                    # to avoid issues with floating point numbers, where
                    # we could have some variable being 0.1+0.2
                    # and remvong that variabl from 0.3 would not be zero
                    
                

                    
                    # attempts += 1
                    
                    # if travelling_time:

                    # We need to know in which slots the vehicles
                    # will arrive at their destination and the proprtion
                    # of these slots
                    travelling_time = float(travelling_time)
                    first_arrival_shift = math.floor(travelling_time)
                    first_arrival_shift_time = datetime.timedelta(
                        hours=first_arrival_shift)
                    second_arrival_shift_time = datetime.timedelta(
                        hours=first_arrival_shift+1)
                    first_arrival_shift_proportion = (1 - travelling_time % 1 )



                    # if start_location == 'work':
                    #     if end_location == 'home':
                    #         print(departures)
                    #         if time_tag_index == 12:
                    #             print(time_tag)
                    #             print(departing_battery_spaces)
                    #             print('HSK')
                    #             print(travelling_time)
                    #             print(first_arrival_shift_proportion)
                    #             print(time_tag+second_arrival_shift_time)
                    #             # exit()
                
                    # if start_location == 'leisure':
                    #     if end_location == 'home':
                    #         print('tt', first_arrival_shift_proportion)
                    # print(start_location, end_location)
                    # # print('Poss dep00', battery_space[start_location].iloc[
                    # #         0:time_tag_index])
                    # print('Poss dep', battery_space[start_location].iloc[
                    #         time_tag_index-first_arrival_shift])
                    # print('Poss dep', battery_space[start_location].iloc[
                    #         time_tag_index-first_arrival_shift-1])
                    # print(time_tag_index)
                    # exit()
                   
                    # print('Possible', possible_battery_spaces)
                    # print(start_location)
                    # print(departing_battery_space)
                    # print(departures)
                    # print(departures)
                    # print(start_location)
                    # print(time_tag_index)
                    # arriving_battery_spaces.append(battery_space_value)

                    # We want to know how many dpeartures will come from the
                    # battery space we are looking at. If there are
                    # more vehicles with the current space than remaining
                    # departures, then we take the remaining departures,
                    # otherwise we take all the vehicles with the current
                    # space and move to the next one
                    this_battery_space_departures = min(
                        departures,
                        battery_space[start_location].loc[
                            time_tag][departing_battery_space].values[0]
                    )
                    # if start_location == 'work':
                    #     if end_location == 'home':
                    #         print(departures)
                    #         if time_tag_index == 15:
                    #             print('Floorball')
                    #             print(time_tag)
                    #             print(departing_battery_space)
                    #             print('HSK')
                    #             print('Lacrosse')
                    #             print(travelling_time)
                    #             print(first_arrival_shift_proportion)
                    #             print(time_tag+second_arrival_shift_time)
                    #             print(this_battery_space_departures)
                    #             print(battery_space[start_location].iloc[
                    #                 0:16])
                    #             exit()
                    # if time_tag_index == 12:
                    #     if start_location == 'work':
                    #         if end_location == 'home':
                    #             print(this_battery_space_departures)
                    #             exit()


                    # print('This dep', this_battery_space_departures)
                    # exit()
                    # if time_tag_index > 13 :
                    # # if len (possible_battery_spaces) > 2 :
                    #     print(departures)
                    # #     print(time_tag)
                    #     print(start_location)
                    #     print(end_location)
                    #     print(battery_space[start_location].loc[
                    #         time_tag])
                    #     exit()
                    #     print(battery_space[start_location].loc[
                    #         time_tag])
                    #     print((battery_space[start_location]))
                    #     print(location_split)
                        # exit()
                    # print(this_battery_space_departures)

                    # We add these departures to the arriving amounts,
                    # as these will arrive to the end location
                    arriving_amounts.append(this_battery_space_departures)
                    

                    # We also add the corresponding battery space at arrival,
                    # given by the original battery space plus the leg's
                    # consumption
                    arriving_battery_spaces.append(
                        departing_battery_space+this_leg_consumption
                    )


                    # if end_location == 'home':
                    #     print('lll')
                    #     print(start_location)
                    #     print(arriving_amounts)
                    #     print(arriving_battery_spaces)

                    # print(arriving_amounts)
                    # exit()
                    # print(battery_space[start_location].loc[
                    #         time_tag][battery_space_value].values[0])
                    # print('TT', time_tag)
                    # print('Dep', departures)
                    # print('BS val', battery_space_value)
                    # print('BS dep', this_battery_space_departures)
                    # print(battery_space[start_location].loc[
                    #         time_tag][battery_space_value].values[0])
                    # print('ga', departures-this_battery_space_departures)
                    # print('go', (departures-this_battery_space_departures)>departures_threshold)
                    # print(possible_battery_spaces)

                    # We update the departures (i.e. how many remain
                    # for larger battery spaces)
                    departures -= this_battery_space_departures


                    # print('Dodo')
                    # print(battery_space[start_location].iloc[
                    #         time_tag_index][departing_battery_space])
                    # print(battery_space[start_location])
                    
                    # print('BSD', departing_battery_space)
                    # print('Mii', this_battery_space_departures)
                    # print('Moo', departures)





                    # print(departures)
                    # exit()
                    # this_battery_space_consumption = (
                    #     run_mobility_matrix.loc[
                    #         start_location, end_location, time_tag][
                    #             distance_header]
                    #     *
                    #     electricity_consumption_kWh_per_km
                    # )
                    # print(this_leg_consumption)
                    # exit()
                    # if (battery_space_value+this_battery_space_consumption) > thresh+5:
                    #     print('YT')
                    #     print(time_tag)
                    #     print(start_location)
                    #     print(end_location)
                    #     print(battery_space_value)
                    #     print(this_battery_space_consumption)
                    #     print(battery_space[start_location].loc[time_tag])
                    #     print(departures)
                    #     print(this_battery_space_departures)
                    #     print(location_split.loc[time_tag])
                    #     exit()

                    # )

                    # print(this_battery_space_consumption)
                    # arrivals[n+M][bs_value+this_battery_space_consumption] += ...
                    # (and set if not existing)
                    # exit()
                    # print(departures)
                    # # exit()
                    # print(time_tag)
                    # print(battery_space[start_location].loc[
                    #         time_tag, battery_space_value])
                    # print(battery_space[start_location].iloc[time_tag_index:])

                    # print(battery_space[start_location].loc[
                    #                 time_tag])
                    # print(battery_space[start_location].loc[
                    #                 time_tag][departing_battery_space]
                    #                 .values[0])

                    # battery_space[start_location] = battery_space[start_location].fillna(0)
                    
                    
                    # Finally, we remove the departures from the start location
                    # for the current time slot
                    
                    battery_space[start_location].loc[
                        time_tag,
                        departing_battery_space] = (
                                battery_space[start_location].loc[
                                    time_tag][departing_battery_space]
                                    .values[0]
                            - this_battery_space_departures
                            )

                    #Mango

                    # Finally, we remove the departures from the start location
                    # for the current time slot and future ones
                    # Note that we remove the departure from existing values
                    # rather than replacing all current and future values
                    # by the new current ones, as the future values might
                    # have been mofified by other legs
                    # current_and_future_run_range = run_range[time_tag_index:]
                    # battery_space[start_location].loc[
                    #     current_and_future_run_range,
                    #     departing_battery_space] = (
                    #             battery_space[start_location].loc[
                    #                 time_tag][departing_battery_space]
                    #                 .values[0]
                    #         - this_battery_space_departures
                    #         )
                    
                    # print(battery_space[start_location])
                    # exit()
                    # battery_space[start_location].loc[
                    #         time_tag, departing_battery_space] = (
                    #             battery_space[start_location].loc[
                    #         time_tag, departing_battery_space].values
                    #         - this_battery_space_departures
                    #         )
                    # print(battery_space[start_location])
                    # exit()
                    # print('Battery space', battery_space[start_location])
                    # print(battery_space[start_location])
                    # exit()
            # print('Arriving', arriving_battery_spaces, arriving_amounts)
            # if attempts > 10:
            #         print(attempts)
            #         print(time_tag)
            #         print(start_location)
            #         print(end_location)
            #         print(departures)
            # print('Attempts', attempts)
            # print('Xdf', (datetime.datetime.now()-batt_x).total_seconds())
            # print('hoo', end_location,  (datetime.datetime.now()-batt_1).total_seconds())
                    
            
            # # We only need to do this if there are actually travels between
            # # the two locations at that time slot
            # if len(arriving_battery_spaces) > 0 :
                    
            # We now can update the battery spaces in the end location.
            for arriving_battery_space, arriving_amount in zip(
                arriving_battery_spaces, arriving_amounts
            ):
                
                # If the end location does not have the incoming battery space
                # in its columns, we add the column (with zeroes)
                if arriving_battery_space not in (
                    battery_space[end_location].columns):
                    battery_space[end_location][
                        arriving_battery_space] = 0
        
                    # battery_space[end_location].iloc[
                    #     time_tag_index+first_arrival_shift][
                    #         arriving_battery_space
                    #     ] = (
                    #         arriving_amount
                    #         * 
                    #         first_arrival_shift_proportion
                    #     )
                    # battery_space[end_location].iloc[
                    #     time_tag_index+first_arrival_shift+1][
                    #         arriving_battery_space
                    #     ] = (
                    #         (1-arriving_amount)
                    #         * 
                    #         first_arrival_shift_proportion
                    #     )
                    # battery_space[end_location].fillna(0)
                # else:
                # print(arriving_amount)
                # print(first_arrival_shift_proportion)
                # row_to_modify = battery_space[end_location].iloc[time_tag_index+first_arrival_shift]
                # row_to_modify[arriving_battery_space] = 2
                    

                # current_and_future_run_range = run_range[time_tag_index+first_arrival_shift:]
                    
                # We check if the arrivals in the first slot
                # are in the run range
                # if they are not, then we don't take them into
                # account (as the are not in the run) and add them
                # in the end_location battery space DataFrame
                
                if time_tag+first_arrival_shift_time <= run_range[-1]:
                    battery_space[end_location].loc[
                        time_tag+first_arrival_shift_time,
                            arriving_battery_space
                        ] = (
                            battery_space[end_location].loc[
                                time_tag+first_arrival_shift_time][
                                    arriving_battery_space
                                ].values[0]
                            +
                            (
                                arriving_amount
                                * 
                                first_arrival_shift_proportion
                            )
                        )
                # print(arriving_battery_space)
                # print(second_arrival_shift_time)
                # print(start_location)
                # print(end_location)
                # print(battery_space[end_location].loc[
                #     time_tag+second_arrival_shift_time,
                #         arriving_battery_space
                #     ] )
                # print(battery_space[end_location].loc[
                #             time_tag+second_arrival_shift_time,
                #                 arriving_battery_space
                #             ].values[0])
                # print(
                #             arriving_amount
                #             * 
                #             (1-first_arrival_shift_proportion)
                #         )
                    

                # current_and_future_run_range = run_range[time_tag_index+first_arrival_shift+1:]
                    
                # We check if the arrivals in thesecond slot 
                # are in the run range
                # if they are not, then we don't take them into
                # account (as the are not in the run)  and add them
                # in the end_location battery space DataFrame
                
                if time_tag+second_arrival_shift_time <= run_range[-1]:
                    battery_space[end_location].loc[
                        time_tag+second_arrival_shift_time,
                            arriving_battery_space
                        ] = (
                            battery_space[end_location].loc[
                                time_tag+second_arrival_shift_time][
                                    arriving_battery_space
                                ].values[0]
                            +
                            (
                                arriving_amount
                                * 
                                (1-first_arrival_shift_proportion)
                            )
                        )
                    # battery_space[end_location].iloc[
                    #     time_tag_index+first_arrival_shift+1][
                    #         arriving_battery_space
                    #     ] += (
                    #         (1-arriving_amount)
                    #         * 
                    #         first_arrival_shift_proportion
                    #     )
                # print(battery_space[end_location])
                # exit()
            # battery_space[end_location] = battery_space[end_location].loc[:,
            #     (battery_space[end_location]!=0).any(axis=0)
            # ]
                    


            # We ensure that the columns of the battery space
            # array are ordered
            battery_space[end_location] = (
                battery_space[end_location].reindex(
                    sorted(battery_space[end_location].columns), axis=1)
            )
            # print(battery_space[end_location])
            # exit()
        batt_2 = datetime.datetime.now()
        # batt_times.append((batt_2-batt_1).total_seconds())
        # boo = (batt_2-batt_1).total_seconds()
        # if boo > 0.1:
        #     print(time_tag)
        #     print(start_location)
        #     print(end_location)
        #     print(battery_space[start_location].loc[time_tag])
        #     print(battery_space[start_location].loc[time_tag-datetime.timedelta(hours=1)])
        #     print(battery_space[end_location].loc[time_tag])
        #     print('Boo',boo)
        #     exit()
        # battery_space[start_location] = battery_space[start_location].loc[
        #         :, (battery_space[start_location]!=0).any(axis=0)
        #     ]

        # We ensure that the columns of the battery space
        # array are ordered
        battery_space[start_location] = battery_space[start_location].reindex(
                    sorted(battery_space[start_location].columns), axis=1)


        batt_3 = datetime.datetime.now()
        batt_times.append((batt_3-batt_2).total_seconds())
            
        # print(start_location, (datetime.datetime.now()-batt_loc_start).total_seconds())
            # print(departures)
        # print(start_location)
        # print(battery_space[start_location])
        # print(location_split.loc[time_tag][start_location])
        # print(run_mobility_matrix.loc[start_location,:,time_tag]['Departures amount'])
    # Have  arrivals not connect at all if partial (until leave)
    # Or assume they move around get connected later
    # Charging
    # print('Batt',(datetime.datetime.now()-batt_start).total_seconds())
    # print(batt_times)
    # print(battery_space['home'])
    # input()

    # exit()
    # if time_tag.isocalendar().week == 1:
    #     exit()
    cha_start = datetime.datetime.now()
    for charging_location in location_names:
        cha_loc = datetime.datetime.now()
        charging_location_parameters = location_parameters[charging_location]
        # print(battery_space[charging_location].loc[time_tag])
        # exit()
        # boo = pd.DataFrame(index=range(3))
        # boo[0] = 1
        # boo[5/7] = 6
        # print(boo)
        # drop = 5/7
        # print('zzz')
        # if charging_location == 'home':
        #         print(battery_space[charging_location].columns)
        #         print(battery_space['home'].iloc[0:time_tag_index+1])
        # if time_tag_index > 48:
        #         print(time_tag)
        # if time_tag_index>24:
        #     exit()
        
        # tbs = []
        # if time_tag_index == 14:
        #     print(time_tag)
        #     exit()
        # print(time_tag)
        # print(battery_space['home'].iloc[0:15])
        for this_battery_space in battery_space[charging_location].columns:
            
            # tbs_start = datetime.datetime.now()
        
            percent_charging = charging_location_parameters['connectivity']
            max_charge = charging_location_parameters['charging_power']
            amount_charged = min(max_charge, this_battery_space)
          
            charger_efficiency = charging_location_parameters['charger_efficiency']
            amount_drawn_from_network = amount_charged / charger_efficiency
            # if charging_location =='home':
            #     print('batt_space', this_battery_space)
            #     print('% cha', percent_charging)
            #     print('max', max_charge)
            #     print('amo', amount_charged)
            old_battery_space_occupancy = (
                battery_space[charging_location]
                .loc[time_tag][this_battery_space]
                .values[0]
            )
            amount_charging = percent_charging * old_battery_space_occupancy
            
            


            charge_drawn_by_vehicles.loc[time_tag, charging_location] = (
                charge_drawn_by_vehicles.loc[time_tag, charging_location]
                +
                amount_charged * old_battery_space_occupancy * percent_charging
            )
            charge_drawn_from_network.loc[time_tag, charging_location] = (
                charge_drawn_from_network.loc[time_tag, charging_location]
                +
                amount_drawn_from_network
                * old_battery_space_occupancy * percent_charging
            )
            
            # if charging_location == 'home':
            #     print(charge_drawn_by_vehicles.loc[time_tag, charging_location] )

            # if charging_location =='home':
            #     print(battery_space[charging_location]
            #     .loc[time_tag])
            #     print('occu', old_battery_space_occupancy)
            #     print(charge_drawn_by_vehicles.loc[time_tag, charging_location])
            new_battery_space = this_battery_space - amount_charged


            
            # print('New battery space', new_battery_space)
            # print(this_battery_space)
            if new_battery_space not in battery_space[charging_location].columns:
                # print(time_tag)
                # print(new_battery_space)
                battery_space[charging_location][new_battery_space] = 0
            # print(battery_space[charging_location].iloc[0:time_tag_index])
            
            
            # print(old_battery_space_occupancy)
            # print((datetime.datetime.now()-tbs_start).total_seconds())
            # print(colo, noo)
            # if  >= 0:
            # print('NBS', new_battery_space)
            # print(battery_space[charging_location]
            #     .loc[time_tag, this_battery_space])
            # print('Coco')
            # print(battery_space[charging_location]
            #     .loc[time_tag][this_battery_space])
            # print('OBA', old_battery_space_occupancy)
            # print(new_battery_space)
            # print('NHL', old_battery_space_occupancy*percent_charging)
            # print(percent_charging)
            # print(charging_location)
            # print(battery_space[charging_location].loc[
            #     time_tag, new_battery_space] )
            # print(battery_space[charging_location].loc[
            #     time_tag] )
            # print('na', (datetime.datetime.now()-tbs_start).total_seconds())
            zoti_start = datetime.datetime.now()

            # 126 with 0
            # 524 with 0.1 (no triggers of 0.1 threshold)
            # 600+ with batt_space (does trigger 0.1 threshold)
            # Is it because of matix extension?
            # Not using it further (i.e. setting updated new battery space occ
            # with zero or something similar is faster: triggers threshold
            # and 274 sec)

            previous_new_battery_space_occupation = (
                # 0.1
                battery_space[charging_location].loc[
                        time_tag,
                        new_battery_space
                        ].values[0]
            )
            # THIS IS THE SLOW PART
            ziti = (datetime.datetime.now()-zoti_start).total_seconds()
            #  SLOW PART IS one of the above ?
            # Also, fragmented DF. Is it because of changes in formulas?


            zoti_start = datetime.datetime.now()
            updated_new_battery_space_occupation = (
                previous_new_battery_space_occupation
                +
                amount_charging
            )
           

            



            battery_space[charging_location].loc[
                time_tag, new_battery_space] =  (
                    updated_new_battery_space_occupation
                    # battery_space[charging_location].loc[
                    #     time_tag][new_battery_space].values[0]
                    # +
                    # amount_charging
                    # # old_battery_space_occupancy * percent_charging
            ) 
            if new_battery_space not in guac.columns:
                guac.loc[:, new_battery_space]  = 0
                guac = (
                guac.reindex(
                    sorted(guac.columns), axis=1)
                )
                guic.loc[:, new_battery_space]  = 0
                guic = (
                guic.reindex(
                    sorted(guic.columns), axis=1)
                )
            
            guac.loc[charging_location, new_battery_space]  = (
                guac.loc[charging_location][new_battery_space] + ziti)
            guic.loc[charging_location, new_battery_space]  = (
                guic.loc[charging_location][new_battery_space] + 1)
            # if time_tag_index == 200:
            #     print(guac)
            #     exit()
            if ziti > 0.1:
                print(time_tag)
                print(charging_location)
                print(ziti)
                # print(new_battery_space)
                # print(battery_space[charging_location].loc[
                # time_tag, new_battery_space])
                # print(battery_space[charging_location].loc[
                # time_tag][new_battery_space].values[0])
                # print(battery_space[charging_location].columns)

                # exit()
            zoti += ziti

            previous_this_battery_space_occupation = (
                battery_space[charging_location].loc[
                        time_tag, this_battery_space].values[0]
            )
            updated_this_battery_space_occupation = (
                previous_this_battery_space_occupation
                -
                amount_charging
            )
            
            # print(battery_space[charging_location].loc[
            #     time_tag, this_battery_space])
            # print('wa', (datetime.datetime.now()-tbs_start).total_seconds())
            battery_space[charging_location].loc[
                time_tag, this_battery_space] = (
                    updated_this_battery_space_occupation
                    # battery_space[charging_location].loc[
                    #     time_tag][this_battery_space].values[0]
                    # -
                    # amount_charging
                    # # old_battery_space_occupancy * percent_charging
            )
        #     print('too', (datetime.datetime.now()-tbs_start).total_seconds())
        #     tbs.append((datetime.datetime.now()-tbs_start).total_seconds())

        # cha_time = (datetime.datetime.now()-cha_loc).total_seconds()
        # if cha_time > 1:
        #     print(charging_location, cha_time, time_tag)
        #     print(battery_space[charging_location].columns.values)
        #     print(tbs)

        #     exit()
            # input()
        # battery_space[charging_location] = battery_space[charging_location].loc[
        #         :, (battery_space[charging_location]!=0).any(axis=0)
        #     ]
        battery_space[charging_location] = battery_space[charging_location].reindex(
                    sorted(battery_space[charging_location].columns), axis=1)
        

        # if time_tag_index == 13:
        #     if charging_location == 'home':
        #         exit()
        # if time_tag_index > 240:
        #     print(battery_space['work'].iloc[0:time_tag_index+1])
        #     print(charge_drawn_from_network.iloc[0:time_tag_index+1])
        #     print(charge_drawn_by_vehicles.iloc[0:time_tag_index+1])
        #     exit()
    # if time_tag_index > 240:
    #     # battery_space['home'] = battery_space['home'].loc[:,(battery_space['home']!=0).any(axis=0)]
    #     # print(battery_space['home'].iloc[240-24:240])
    #     # print(battery_space['home'].columns.values)
    #     # print(battery_space['home'].columns.values[1])
    #     # print(battery_space['home'].columns.values[1]==2.4)
    #     drop = 5/7
    #     print('zzz')
    #     for colo in boo.columns:
    #         noo = colo - drop
    #         print(colo, noo)
    #         if noo >= 0:
    #             boo.loc[:, noo] = boo.loc[noo] + boo[colo]
    #     # print(boo)
    #     exit()
    # print('Cha',(datetime.datetime.now()-cha_start).total_seconds())

print(charge_drawn_by_vehicles)
for location_name in location_names:
    print(battery_space[location_name])
print('Empty DF?')
print('Keep float precision?')
print('Keep reindex?')
print('split off in a function?')
print('Check totals and such?')
print('Other charging strategies?')
print((datetime.datetime.now()-start_time).total_seconds())
print(zoti)
print(guac)
print(guic)
guoc = 10000 * guac/guic
guoc = guoc.fillna(0)
print(guoc)
exit()
for location_name in location_names:
    # print(battery_space[location_name].columns)
    battery_space[location_name].columns = battery_space[location_name].columns.astype(str)
    cook.save_dataframe(
        battery_space[location_name],
        f'{scenario}_{location_name}_battery_space',
        groupfile_name, output_folder, parameters
    )
# print(charge_drawn_from_network)
cook.save_dataframe(
        charge_drawn_from_network,
        f'{scenario}_charge_drawn_from_network',
        groupfile_name, output_folder, parameters
    )
# print(charge_drawn_by_vehicles)
cook.save_dataframe(
        charge_drawn_by_vehicles,
        f'{scenario}_charge_drawn_by_vehicles',
        groupfile_name, output_folder, parameters
    )
exit()

consumption_matrix = cook.read_table_from_database(
    f'{scenario}_consumption_matrix', 
    f'{output_folder}/{groupfile_name}.sqlite3'
)
consumption_matrix['Time tag'] = pd.to_datetime(
    consumption_matrix['Time tag'])
consumption_matrix = consumption_matrix.set_index(
    ['Time tag', 'From', 'To'])

print(location_split.loc[run_range[0]])
battery_space  = {}


location_parameters = parameters['locations']
for location_name in location_names:
    battery_space[location_name]  = pd.DataFrame(
        run_range,
        columns= ['Time Tag']
    )
    battery_space[location_name]['Hour Number'] = run_hour_numbers
    battery_space[location_name]['SPINE_Hour_Number'] = SPINE_hour_numbers
    battery_space[location_name] = battery_space[location_name].set_index(
        ['Time Tag', 'Hour Number', 'SPINE_Hour_Number']
    )
    battery_space[location_name].loc[run_range[0], 0] = (
        location_split.loc[run_range[0]][location_name]
    )
    battery_space[location_name] = battery_space[location_name].fillna(0)
    print(location_name)
    print(battery_space[location_name])
for time_tag in run_range[1:]:
    for location_name in location_names:
        # print(run_mobility_matrix.loc[time_tag,:,location_name])
        
        incoming_consumption = (
            sum(consumption_matrix.loc[time_tag,:,location_name]
                ['electricity consumption kWh'])
            )
        
        if incoming_consumption != 0 :
            print(location_name, incoming_consumption)
            battery_space[location_name].loc[time_tag,incoming_consumption] = 19.89
            # USE BATTERY LEVELS???
            # new table with from/to index and dist/duration columns
            #     OR have it in tun matrix (so time can change)
            # print(battery_space[location_name])
            # starting_spaces = jjjf
            # Use amounts as columns
            # and space (per vehicle?) as values? or swap?
            # We have X vehicles with a given battery space (percent of batt?) split
            
            # a given ditribution of spaces leaves LD at time N 
            # It arrives at LA at times N+M and N+M+1 (dependind on journey duration)
            # with a distribution shifted by the distance (so have distance and duration in matrix)
            # so iterate over destination locations 
            # and update dep location at time N and dest locationS at times N+M and N+M+1
            exit()
            # First update existing spaces with +=
            # Then do new ones
            updated_spaces = [
                available_space-0.01 if available_space>0.01
                else 0
                for available_space in battery_space[location_name].columns
            ]
            print(updated_spaces)

            exit()
    if time_tag.day > 1:
        exit()
# - departures (distr starting at least)    
# + arrivals with departures from previous distr plus consmption
# above threshold -->charge and uupdate
# exit()
import pandas as pd
import numpy as np
moo = 5 / 7
koo = 7 / 9
# replace nan by zero

zoo = pd.DataFrame(np.zeros((2,2)), columns=[moo, koo])
zoo[1989/26] = 2.6
# zoo[26/7] = 42
zoo.loc[1, 26/7] = 89
print(zoo[5/7])
zoo = zoo.reindex(sorted(zoo.columns), axis=1)
print(zoo)
print(zoo.loc[1].keys().values)
print(zoo.columns.values)
for battery_space in zoo.columns:
    print(battery_space)

print(0.1+0.2)
print(0.15+0.15)
if 0.1+0.2 == 0.15+0.15:
    print('fgf')
else:
    print('LO')