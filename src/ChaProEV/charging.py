

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
run_range, run_hour_numbers = run_time.get_time_range(parameters)
SPINE_hour_numbers = [f't{hour_number:04}' for hour_number in run_hour_numbers]

battery_space = pd.DataFrame(
    run_range,
    columns= ['Time Tag'])
battery_space['Hour Number'] = run_hour_numbers
battery_space['SPINE_Hour_Number'] = SPINE_hour_numbers
battery_space[0] = 0
battery_space = battery_space.set_index(
    ['Time Tag', 'Hour Number', 'SPINE_Hour_Number'])
battery_space.loc[run_range[2], 5/7] = 19.89
battery_space = battery_space.fillna(0)
print(battery_space)
# location_start_split = mobility.get_location_split(parameters).iloc[0]
scenario = parameters['scenario']
case_name = parameters['case_name']

file_parameters = parameters['files']
output_folder = file_parameters['output_folder']
groupfile_root = file_parameters['groupfile_root']
groupfile_name = f'{groupfile_root}_{case_name}'
location_parameters = parameters['locations']
location_names = [
    location_name for location_name in location_parameters
]
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