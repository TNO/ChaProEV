


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


import pandas as pd
import numpy as np
moo = 5 / 7
koo = 7 / 9
replace nan by zero

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