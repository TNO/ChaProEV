
import math
import datetime
import pandas as pd

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
    # battery_space.loc[run_range[2], 5/7] = 19.89
    # battery_space = battery_space.fillna(0)

# location_start_split = mobility.get_location_split(parameters).iloc[0]
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
run_mobility_matrix = cook.read_table_from_database(
    f'{scenario}_run_mobility_matrix', 
    f'{output_folder}/{groupfile_name}.sqlite3'
)
run_mobility_matrix['Time tag'] = pd.to_datetime(
    run_mobility_matrix['Time tag'])
run_mobility_matrix = run_mobility_matrix.set_index(
    ['From', 'To', 'Time tag'])
print(run_mobility_matrix.loc['home', 'work'])
for time_tag_index, time_tag in enumerate(run_range):
    print(time_tag)


    # print(location_split.loc[time_tag])
    for start_location in location_names:
        if time_tag_index == 0:
            battery_space[start_location].loc[time_tag, 0] = (
                location_split.loc[time_tag][start_location]
            )
            battery_space[start_location] = (
                battery_space[start_location].fillna(0)
            )
        else:
            possible_battery_spaces = (
                sorted(battery_space[start_location].columns.values)
            )
            # print('Poss', battery_space[start_location])
            for possible_battery_space in possible_battery_spaces:
                # print('Poss', battery_space[start_location])
                
                battery_space[start_location].loc[
                                time_tag, possible_battery_space] = (
                                    battery_space[start_location].loc[
                                        time_tag, possible_battery_space]
                                        .values
                                    +
                                    battery_space[start_location].iloc[
                                        time_tag_index-1][
                                            possible_battery_space]
                                )
        
        
        # print('Possible battery spaces', possible_battery_spaces)
        # print(battery_space[start_location])
        # if time_tag_index>0:
        #     exit()
    
        for end_location in location_names:
            # print(start_location, end_location)
            departures = run_mobility_matrix.loc[
                start_location, end_location, time_tag][
                    'Departures amount']
            # print(time_tag_index)
            arriving_battery_spaces = []
            arriving_amounts = []
            travelling_time = run_mobility_matrix.loc[
                            start_location, end_location, time_tag][
                                'Duration (hours)']
            if travelling_time:
                travelling_time = float(travelling_time)
                # print(start_location, end_location)
                first_arrival_shift = math.floor(travelling_time)
                first_arrival_shift_time = datetime.timedelta(
                    hours=first_arrival_shift)
                second_arrival_shift_time = datetime.timedelta(
                    hours=first_arrival_shift+1)
                first_arrival_shift_proportion = (1 - travelling_time % 1 )
      
                # print('First arrival shift', first_arrival_shift, first_arrival_shift_proportion)
            attempts = 0
            # Float precision can mean that we have exteremly small values
            # that are actually zero
            departures_threshold = charging_parameters['departures_threshold']
            while departures > departures_threshold :
                attempts += 1
                if attempts > 100:
                    print(start_location)
                    print(end_location)
                    print(departures)
                    exit()
                for battery_space_value in possible_battery_spaces:
                    # print('Possible', possible_battery_spaces)
                    
                    # print(departures)
                    # print(start_location)
                    # print(time_tag_index)
                    # arriving_battery_spaces.append(battery_space_value)
                    this_battery_space_departures = min(
                        departures,
                        battery_space[start_location].loc[
                            time_tag][battery_space_value].values[0]
                    )
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
                    arriving_amounts.append(this_battery_space_departures)
                    # print(battery_space[start_location].loc[
                    #         time_tag][battery_space_value].values[0])
                    departures -= this_battery_space_departures
                    this_battery_space_consumption = (
                        run_mobility_matrix.loc[
                            start_location, end_location, time_tag][
                                distance_header]
                        *
                        electricity_consumption_kWh_per_km
                    )
                    
                    arriving_battery_spaces.append(
                        battery_space_value+this_battery_space_consumption)
                    # print(this_battery_space_consumption)
                    # arrivals[n+M][bs_value+this_battery_space_consumption] += ...
                    # (and set if not existing)
                    # exit()
                    # print(departures)
                    # # exit()
                    # print(time_tag)
                    # print(battery_space[start_location].loc[
                    #         time_tag, battery_space_value])
                    
                    battery_space[start_location].loc[
                            time_tag, battery_space_value] = (
                                battery_space[start_location].loc[
                            time_tag, battery_space_value].values
                            - this_battery_space_departures
                            )
                   
                    # print('Battery space', battery_space[start_location])
                    # print(battery_space[start_location])
                    # exit()
            # print('Arriving', arriving_battery_spaces, arriving_amounts)
            if travelling_time:
                # print('TT', travelling_time)
                if len(arriving_battery_spaces) > 0 :
                    for arriving_battery_space, arriving_amount in zip(
                        arriving_battery_spaces, arriving_amounts
                    ):
                        # print(arriving_battery_space)
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
                        battery_space[end_location].loc[
                            time_tag+first_arrival_shift_time,
                                arriving_battery_space
                            ] = (
                                battery_space[end_location].loc[
                                    time_tag+first_arrival_shift_time,
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
                        battery_space[end_location].loc[
                            time_tag+second_arrival_shift_time,
                                arriving_battery_space
                            ] = (
                                battery_space[end_location].loc[
                                    time_tag+second_arrival_shift_time,
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
            battery_space[end_location] = battery_space[end_location].loc[:,
                (battery_space[end_location]!=0).any(axis=0)
            ]
            battery_space[end_location] = (
                battery_space[end_location].reindex(
                    sorted(battery_space[end_location].columns), axis=1)
            )
            # print(battery_space[end_location])
            # exit()
        battery_space[start_location] = battery_space[start_location].loc[
                :, (battery_space[start_location]!=0).any(axis=0)
            ]
        battery_space[start_location] = battery_space[start_location].reindex(
                    sorted(battery_space[start_location].columns), axis=1)
            
        
            # print(departures)
        # print(start_location)
        # print(battery_space[start_location])
        # print(location_split.loc[time_tag][start_location])
        # print(run_mobility_matrix.loc[start_location,:,time_tag]['Departures amount'])
    
    # Charging
    for charging_location in location_names:
        charging_location_parameters = location_parameters[charging_location]
        print(battery_space[charging_location].loc[time_tag])
        # exit()
        # boo = pd.DataFrame(index=range(3))
        # boo[0] = 1
        # boo[5/7] = 6
        # print(boo)
        # drop = 5/7
        # print('zzz')
        if charging_location == 'home':
                print(battery_space[charging_location].columns)
                print(battery_space['home'].iloc[0:time_tag_index+1])
        if time_tag_index > 48:
                print(time_tag)
        for this_battery_space in battery_space[charging_location].columns:
            
            percent_charging = charging_location_parameters['connectivity']
            max_charge = charging_location_parameters['charging_power']
            amount_charged = min(max_charge, this_battery_space)
            new_battery_space = this_battery_space - amount_charged
            # print('New battery space', new_battery_space)
            # print(this_battery_space)
            if new_battery_space not in battery_space[charging_location].columns:
                battery_space[charging_location][new_battery_space] = 0
            # print(battery_space[charging_location].iloc[0:time_tag_index])
            
            old_battery_space_occupancy = (
                battery_space[charging_location]
                .loc[time_tag, this_battery_space]
                .values[0]
            )
            # print(old_battery_space_occupancy)
            
            # print(colo, noo)
            # if  >= 0:
            battery_space[charging_location].loc[
                time_tag, new_battery_space] =  (
                    battery_space[charging_location].loc[
                        time_tag, new_battery_space] .values[0]
                    +
                    old_battery_space_occupancy * percent_charging
            ) 
            battery_space[charging_location].loc[
                time_tag, this_battery_space] = (
                    battery_space[charging_location].loc[
                        time_tag, this_battery_space].values[0]
                    -
                    old_battery_space_occupancy * percent_charging
            )
        battery_space[charging_location] = battery_space[charging_location].loc[
                :, (battery_space[charging_location]!=0).any(axis=0)
            ]
        battery_space[charging_location] = battery_space[charging_location].reindex(
                    sorted(battery_space[charging_location].columns), axis=1)
        if time_tag_index > 48:
            print(battery_space['work'].iloc[0:time_tag_index+1])
            exit()
    if time_tag_index > 240:
        # battery_space['home'] = battery_space['home'].loc[:,(battery_space['home']!=0).any(axis=0)]
        # print(battery_space['home'].iloc[240-24:240])
        # print(battery_space['home'].columns.values)
        # print(battery_space['home'].columns.values[1])
        # print(battery_space['home'].columns.values[1]==2.4)
        drop = 5/7
        print('zzz')
        for colo in boo.columns:
            noo = colo - drop
            print(colo, noo)
            if noo >= 0:
                boo.loc[:, noo] = boo.loc[noo] + boo[colo]
        # print(boo)
        exit()
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