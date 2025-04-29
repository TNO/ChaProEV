# Scenario file description

The models runs through a series of scenarios. For each scenario,
you need to create a scenario file in the scenarios/your_case
folder (or use a [variant](variants.md)).
This page describes the elements of the scenario file (your_scenario.toml).

## run
Run parameters give the elements to produce the time tags of the run range.

### use_day_types_in_charge_computing 
If set to true, the charging computations will be done per day type rather
than for all days of the run, which fastens the computations.
If set to false, the model will compute each day separately, which is considerably slower.
### start
This part gives the year, month, day, hour, and minute of the start of the
computations. It is best to set this to a day hour start for consistency
and then cut off the start for display (see below). For example,
start on 31/12/2019 at 05:00 if your day start hour is 05:00 and if you want
to show results starting on 1/1/2020 at 00:00.
### end
This part gives the year, month, day, hour, and minute of the end of the
computations. Note that the end time tag is not included in the run,
so put 1/1/2021 at 00:00 if you want to compute for 2020.
### display_start
This is the first time tag you want to show in your end results.
### display_end
This is the first time tag that does not appear in your displayed results.
### frequency
The time frequency of the run (size and type).
For the type, use 'H' for hours, 'min' for minutes,
'S' for seconds, 'D' for days. For more info and other types, see 
[here](https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases).
The current model uses  hourly (so 1 and 'h'). Changing that might require
some adjustments in the code.
### display frequency
The frequency of the displayed values can be different than the frequency of the computations.
In the current version, this needs to be the same or less frequent than the computation frequency above.
### extra_downloads
This is to decide if you want to dowload some files (note that this concerns the currently inactive weather module).


#### download_weather_data
Put true if you want to download the weather data. In principle,
you only to do this once, unless you add years and/or areas
#### make_weather_database
Put true if you want to remake the weather database. In principle,
you only to do this once, unless you add years and/or areas. Note
that this refers to other years ans areas than the weather download.

#### download_EV_tool_data
Put true if you want to download the data from the EV tool by geootab
This should only be needed once and is independentr of the case.




## locations
You can modify existing locations or create new ones by copying
exisiting ones (copy everything under '[locations.code]', where
code is the name of your location). You need to have all the elements below.

### vehicle
This is the name of the vehicle that goes to that location.
This name needs to match the scenario's vehicle name (in [vehicle](#vehicle)) 
for the location to
[be included](define.md#declare_class_instances) in the scenario.
The reason for this check is to avoid including unnecessary locations (a user
could put all locations for all vehicles in their scenario files so that they
could copy the whole list between scenarios without having to filter locations
by hand). 
If a location is used by different vehicles, simply create one location per
vehicle (e.g. stadium_car and stadium_bus).

### connectivity
This is a (float) number between 0 and 1 that gives us the probability
that a vehicle is connected to a charger when it is at this location (essentially,
it is the ratio between parking places with a charger and the total amount of parkin places).
### charging_power
The available charging power (in kW).
### charger_efficiency
This is a (float) number between 0 and 1 that gives us the charger efficiency.
Essentially, it is the ratio between the power received by the vehicle and the
power drwan from the network.
### latitude
The location's latitude, used for [weather-related](weather.md) computations (currenly inactive).
### longitude
The location's longitude, used for [weather-related](weather.md) computations (currenly inactive).
### charging_price
The standard charging price (in €/kWh), currently inactive.
### charging_desirability 
An indicator (0-1) of how much people like to charge at this location. Currently inactive.
### percentage_in_location_at_run_start
If filling it directly instead of computing it (see 
[this function](mobility.md#compute_start_location_split)), you can put a probability
(float between 0 and 1) that the vehicle is at that location at the start of the run.

### vehicle_discharge_power
The available discharging power (in kW).

### proportion_of_discharge_to_network
This is a (float) number between 0 and 1 that gives us the discharging.
Essentially, it is the ratio between the power going to the network and the power
discharged by the vehicle.
### time_modulation_factors
For each hour (starting at midnight), a factor between 0 and 1 that tells us
how much oof the charging power is available (1 means that it is fully available,
and 0 that the charger is entirely shut down during that hour).


## legs
Legs are vehicle movements between two locations. You can modify existing 
legs or create new ones by copying
exisiting ones (copy everything under '[legs.code]', where
code is the name of your leg). You need to have all the elements below.


### vehicle
This is the name of the vehicle that performs that leg.
This name needs to match the scenario's vehicle name (in [vehicle](#vehicle)) 
for the leg to
[be included](define.md#declare_class_instances) in the scenario.
The reason for this check is to avoid including unnecessary legs (a user
could put all legs for all vehicles in their scenario files so that they
could copy the whole list between scenarios without having to filter legs
by hand). 
If a le is used by different vehicles, simply create one leg per
vehicle (e.g. from_stadium_to_home_car and from_stadium_to_home_bus).
### distance
The distance between the start and and end of the loation (in kilometers).
### duration
Hoe long ot takes for the vehicle to perform the leg
(in hours: 30 minutes= 0.5 hours).

### hour_in_day_factors

This factor adds a correction to the vehicle consumption that depends
on the hour in day (the first is for 00:00 to 00:59,
the last for 23:00 to 23:59). Note that these are actual hours,
not hours in the user day (which can start and end at other moments than
midnight). This is used to take into account things like traffic jams.
The default value is 1.
(Note that this is currently inactive/not used in the model).


### locations
Provide the names of the start and end locations (which need to be among
the [locations](#locations) provided above).
### road_type_mix
#### mix
Give the road type mix
We need a value for each of the road_types 
(see [transport_factors](#transport_factors))
If the road type does not occur in the leg, simply put 0
Note that the total should be 1 (there are no checks to ensure this,
so you need to make sure you do this correctly). 
The list provided in mix needs to correspond to the road types in
[transport_factors](#transport_factors).
This will be used in [computing weighted quantities][#mobility.md#weighted_quantities].
Note that these weighted quantities are partly inactive (in the sense that they
are not the focus of current runs/have not been tested).





## vehicle
These parameters define the scenario's vehicle. If you want profiles
for several vehicles, run separate scenarios.
### name
This is the name of the vehicle, which will be
[checked](define.md#declare_class_instances) to see if legs, trips,
and locations are actually declared.

### base_location
Choose one of the [locations][#locations] as a base location (at day start).
This is not relevant for cars, as they can be split between different locations
at day start (say home and holiday), as seen in the [computation of location at
day start](mobility.md#get_day_type_start_location_split).
### yearly_kilometrage
Provide the yearly kilometrage for this vehicle. This could be used for
checking/testing purposes, but is currently not used/inactive.
### kilometers_column_for_consumption
Tells which column from the [run mobility matrix](mobility.md#get_run_mobility_matrix)
is used when [creating consumption tables](consumption.md#create_consumption_tables)
(it should be 'Arrivals' or 'Departures', with the current default being 'Arrivals').
### use_weighted
Set it to true if you want to [use](consumption.md#create_consumption_tables)
[weights][#weights] for [road types][#road_types] for your [legs](#road_type_mix).

### battery_capacity
The standard/nominal capacity of the vehicle's battery. Note that the battery
[capacity changes with temperature](weather.md#range-and-temperature),
but that the impact of this is inactove/not modelled yet.

### solar_panel_size_kWp
The capacity (kWp) of the solar panels on the vehicle (currently inactive/not implemented).
### base_consumption_per_km
A set of vehicle base consumptions (reference values that can be modified
by using [weights][#use_weighted]).
They are all in values per kilometer, in units in which the energy carrier
is typically sold.


## trips
Trips are collections of [legs](#legs) on a given day.
You can modify existing 
trips or create new ones by copying
exisiting ones (copy everything under '[trips.code]', where
code is the name of your trip). You need to have all the elements below.
### vehicle
This is the name of the vehicle that performs that trip.
This name needs to match the scenario's vehicle name (in [vehicle](#vehicle)) 
for the trip to
[be included](define.md#declare_class_instances) in the scenario.
The reason for this check is to avoid including unnecessary trips (a user
could put all trips for all vehicles in their scenario files so that they
could copy the whole list between scenarios without having to filter trips
by hand). 
If a le is used by different vehicles, simply create one leg per
vehicle (e.g. weekend_trip_car and weekend_trip_bus).
### legs
A list of [legs](#legs) that constitute the trip (in order they are performed).
### time_between_legs

This is the time spent at each interim location (same units as used
in general (hours in the current version of the model)).
You need one value less than the amount of legs, even if the vehicle
doesn't stay there (in that case, set the value to 0).



### percentage_station_users
This is a placeholder for future management of fast-charging stations users
and is currently inactive.
### start_probabilities
This is a list of start probabilities (sum has to add up to one), with
enough values to cover a whole day (24 in the current implementation, as the
base unit is an hour). The first value is for the [day start hour](#day_start_hour).
### repeated_sequence
This is used to repeat a sequence of two legs, whic you provide here as a leg
(put an empty list if no legs repeat). This is for example used for busses that
go between the start and the end of a route. 
### repetition_amounts
This is the amount of times the sequence is repeated.
If the sequence of two legs
appear several times in the trip, you need to provide one value per appearance
of the sequence (even if that repetition amount is 1). Using the same sequence
repeatedlly can be used in cases where a van performs legs between two locations
in clusters (something like before morning peak, morning peak, between peaks, 
evening peak, after evening peak) and tell how often per cluster the van travels.
### time_between_repetitions
This is the time between repetitions (in your standard time units, hours in the current version).
Similarly to the amounts, you need to provide one value (even if it is zero) per
appearance of the sequence.

## mobility_module
### day_start_hour
This parameter defines the start of the day for the scenario. It is chosen
so that there are no movements during that hour number. It represents the
shift from midnight, so a day start hour of 5 means that the day starts
at hour 5 (i.e. 05.00). The idea is to choose an hour that is logical
for the users/matches their patterns. This is connected to the 
[day types](#day_types), as a given day will correspond to a day type.
For example, the hours between 00:00 and 05:00 on a Saturday belong to
the Thursday before and are as such on a week day 
(as opposed to a weekend day).


### compute_start_location_split

### day_types

### mobility_quantities

### battery_space_shift_quantities
### location_connections_headers
### mobility_index_names
### kilometers_driven_headers
### holiday_weeks

### number_of_holiday_weeks
We need to provide the number of holliday weeks seprately,
as counting the elements of the list above might not work, such as
when the above list contains weeks 1 and 53 (which just represent
the fact that years don't necessarily start and/or end at the start/end
of a week).


### holiday_departures_in_weekend_week_numbers

### holiday_returns_in_weekend_week_numbers

### work_hours_in_a_work_day



### hours_worked_per_work_week
### hours_in_a_standard_work_week
### percentage_working_on_a_work_week
### worked_hours_per_year

### leisure_trips_per_weekend
### leisure_trips_per_week_outside_weekends
### maximal_fill_percentage_leisure_trips_on_non_work_weekdays
### weekday_leisure_trips
### percentage_of_weekday_leisure_trips_on_a_work_day

### weekend_trips_per_year


### holiday_trips_taken
### time_spent_at_holiday_destination

### trips_per_day_type
For vehicles other than cars, we assume that there is one trip per day type.
This is where we match the trips to their day type

## transport_factors

### road_types

### weights

## weather

### weather_factors_table_root_name

### source_data


#### start_year
#### end_year
#### quantities
#### raw_data_folder
The following define the area over which the raw weather data will be
downloaded. The corresponding in the processed weather database is below.
#### latitude_min
#### latitude_max
#### longitude_min
#### longitude_max


### processed_data


#### raw_data_folder
#### processed_folder
#### weather_database_file_name 

#### chunk_size

This parameter is there to avoid issues when writing a too large DataFrame
at once (instead, we split it into chunks).


#### quantities


#### KELVIN_TO_CELSIUS
#### quantity_tags

#### quantity_processed_names

#### cumulative_quantity_processed_names

#### cumulative_quantities

#### queries_for_cumulative_quantities
#### temperature_quantities

#### processed_index_tags 


These define the area of the processed data in the weather database
#### latitude_min
#### latitude_max
#### longitude_min
#### longitude_max
#### coordinate_step

### EV_tool
Parameters for the EV tool data from geotab


#### EV_tool_url
#### user_agent
#### efficiency_curve_script_index
#### data_splitter
#### file_name
#### groupfile_name
#### folder
#### efficiency_factor_column_name

## charging
### price_reaction_exponent
### desirability_reaction_exponent

## charging_sessions
### resolution