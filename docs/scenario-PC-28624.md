# Scenario file description

The models runs through a series of scenarios. For each scenario,
you need to create a scenario file in the scenarios/your_case
folder (or use a [variant](variants.md)).
This page describes the elements of the scenario file (your_scenario.toml).

## run
Run parameters give the elements to produce the time tags of the run range.

### use_day_types_in_charge_computing 
If set to true, the charging computations will be done per [day type](#day_types) rather
than for all days of the run, which fastens the computations in the [charging module](charging.md).
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

If filling it directly instead of [computing it](#compute_start_location_split) (see 
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
This is to put a road type mix for the leg.
The reason for this is that we might want to reflect the fact that vehicles might have different
energy consumptions for different road types.
#### mix
Give the road type mix.
We need a value for each of the road_types 
(see [transport_factors](#transport_factors))
If the road type does not occur in the leg, simply put 0
Note that the total should be 1 (there are no checks to ensure this,
so you need to make sure you do this correctly). 
The list provided in mix needs to correspond to the road types in
[transport_factors](#transport_factors).
This will be used in [computing weighted quantities](mobility.md#make_mobility_data).
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
These parameters are mostly used in the [mobility module](mobility.md).
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

Set to false if  [filling it directly](#percentage_in_location_at_run_start), 
true if computing it (see 
[this function](mobility.md#compute_start_location_split)).


### day_types
A list of day types (i.e. days where mobility patterns repeat, thus where
the same trips occur (either a single one or a mix with given probabilites)).
Thius is used in mobility computations, to compute [trip probabilities per day type](mobility.md#get_trip_probabilities_per_day_type)
You can decide to make [charge computations at the day type level](#use_day_types_in_charge_computing)
in the [charging module](charging.md).
to save computation time.
### mobility_quantities
These are the headers of the [run mobility matrix](mobility.md#get_run_mobility_matrix).
You can change these if you want to change the formulation of the headers.

### battery_space_shift_quantities
These correspond to the quantities computed [here](define.md#compute_travel_impact),
though this list is currently not in use/inactive.
### location_connections_headers
These headers are used in the [run moblity matrix](mobility.md#get_run_mobility_matrix).
You can change these if you want to change the formulation of the headers.

### mobility_index_names
These index names are used in the [run moblity matrix](mobility.md#get_run_mobility_matrix).
You can change these if you want to change the formulation of the headers.
### kilometers_driven_headers
A  currently inactive/not in use list of matrix headers for a kilometers-based matrix.
### holiday_weeks
A list of week numbers that are holiday weeks, used to compute 
[car holiday trip probabilities](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.

### number_of_holiday_weeks
We need to provide the number of holliday weeks seprately,
as counting the elements of the list above might not work, such as
when the above list contains weeks 1 and 53 (which just represent
the fact that years don't necessarily start and/or end at the start/end
of a week).


### holiday_departures_in_weekend_week_numbers
The week numbers when people go on holidays during the weekend, used to compute 
[car holiday trip probabilities](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.

### holiday_returns_in_weekend_week_numbers
The week numbers when people come back from holidays during the weekend, used to compute 
[car holiday trip probabilities](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.


### work_hours_in_a_work_day
Worked hours per day. This is used in the computations to determine
the [probability that a car driver goes to work on a given day](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.



### hours_worked_per_work_week
Amount of hours worked per week.
This is used in the computations to determine
the [probability that a car driver goes to work on a given day](mobility.md#get_car_trip_probabilities_per_day_type), most notably for non-holiday weeks.
As such, this is only relevant for cars in the current implementation of the model.

### hours_in_a_standard_work_week
How many hours there are in a standard work week (default is 40).
This is used in the computations to determine
the [probability that a car driver goes to work on a given day](mobility.md#get_car_trip_probabilities_per_day_type), most notably for non-holiday weeks.
As such, this is only relevant for cars in the current implementation of the model.


### percentage_working_on_a_work_week
The probability that a car driver goes to work in a work (i.e. non-holiday) week.
This is used in the computations to determine
the [probability that a car driver goes to work on a given day](mobility.md#get_car_trip_probabilities_per_day_type), most notably for non-holiday weeks.
As such, this is only relevant for cars in the current implementation of the model.

### worked_hours_per_year
Amount of worked hours per year. 
This is used in the computations to determine
the [probability that a car driver goes to work on a given day](mobility.md#get_car_trip_probabilities_per_day_type), most notably for holiday weeks
(as they are a remainder).
As such, this is only relevant for cars in the current implementation of the model.


### leisure_trips_per_weekend
The amount of leisure trips car users perform in a weekend.
This is used to compute the [probabilities of trips including visits to leisure locations](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.

### leisure_trips_per_week_outside_weekends
The amount of leisure trips car users perform on non-weekend days.
This is used to compute the [probabilities of trips including visits to leisure locations](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.

### maximal_fill_percentage_leisure_trips_on_non_work_weekdays
A factor that puts a cap on the percentage of trips that include a leisure trip on
weekdays where the person does not go to work.

This is used to compute the [probabilities of trips including visits to leisure locations](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.

### weekend_trips_per_year
The amount of weekend trips car users take in a year.
This is used to compute the [probabilities of weeekend trips](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.

### holiday_trips_taken
The amount of holiday trips car users take in a year.
This is used to compute the [probabilities of holiday trips](mobility.md#get_car_trip_probabilities_per_day_type).
As such, this is only relevant for cars in the current implementation of the model.

### time_spent_at_holiday_destination
How long car users stay at their holiday  destination.
This is used to compute the [probabilities of holiday trips](mobility.md#get_car_trip_probabilities_per_day_type), as well as [locations at day start](mobility.md#get_day_type_start_location_split).
As such, this is only relevant for cars in the current implementation of the model.

### trips_per_day_type
For vehicles other than cars, we assume that there is one trip per day type.
This is where we match the trips to their day type.
This is used [here](mobility.md#get_trip_probabilities_per_day_type_other_vehicles).

## transport_factors
These are the factors used if we [use weighted](#use_weighted) 
consumptions per road type
[in legs](#road_type_mix), reflecting the fact that vehicles might have different
energy consumptions for different road types.
### road_types
Provide a list of names for theroad types you want to use.
### weights
Provide one weight/energy use correction factor for each road type.

## weather
Parameters related to [weather computations](weather.md), which
is currently inactive/not integrated in the model itself.

### weather_factors_table_root_name
A root for [saving weather factors](weather.md#get_scenario_weather_data)
for each scenario (the scenario name will be mixed with this when saving the data).
### source_data
Parameters about the source data ([CDS ERA-5](https://cds.climate.copernicus.eu/)) for the [cdsapi library](https://cds.climate.copernicus.eu/how-to-api).

#### start_year
The first year for which you want to get data.
#### end_year
The last year for which you want to get data.
#### quantities
A list of the quantities you want to extract.

#### raw_data_folder
The folder where you want to put your raw data.

#### raw data area
These define the area over which the raw weather data will be
downloaded. The corresponding in the processed weather database is [below](#processed-data-area)
(you need to provide the minimal and maximal longitudes and latitudes of the area).



### processed_data
This is data that you will use in your model/run. It is a subpart of the raw data
(for example: you might want all Europe in your raw data, but just one country in the processed data).
#### raw_data_folder
The folder where you can find your raw data.
#### processed_folder
The folder where you want to store your data.
#### weather_database_file_name
The database file name where you want to store you processed weather data (in the folder above).

#### chunk_size

This parameter is there to avoid issues when writing a too large DataFrame
at once (instead, we split it into chunks).


#### quantities processed
The quantities in your processed weather data. It has to be a subset of [what](#quantities) you can in your raw wether data.

#### KELVIN_TO_CELSIUS
A factor to convert Kelvin to Celsius.
#### quantity_tags
Tags corresponding to the [quantities](#quantities-processed) you want.

#### quantity_processed_names
Output table display names corresponding to the [quantities](#quantities-processed) you want.

#### cumulative_quantity_processed_names
The display names of quantities from [all quantities](#quantity_processed_names) that are cumulative.

#### cumulative_quantities
The quantities from [all quantities](#quantity_processed_names) that are cumulative.


#### queries_for_cumulative_quantities
The SQL queries to get the [cumulative quantities](#cumulative_quantities).
#### temperature_quantities
The quantities from [all quantities](#quantity_processed_names) that are related to temperatures.


#### processed_index_tags
The index name tags for the processed data tables.

#### Processed data area
This is the area for the processed data that you will use in the model.
It is a subpart of the [raw data area](#raw-data-area).
You need to provide the minimal and maximal longitudes and latitudes of the area.


### EV_tool
Parameters for the EV tool data from geotab.
The data is obtained with [this function](weather.md#get_ev_tool_data) and
used in the determination of [capacity changes with temperature](weather.md#range-and-temperature).


#### EV_tool_url
The source URL of the data.
#### user_agent
A string to provide a user agent
#### efficiency_curve_script_index
The [script to get data](weather.md#get_ev_tool_data) produces a list of scripts.
This is the list index that we need.
#### data_splitter
A splitting string needed in the [script to get data](weather.md#get_ev_tool_data).
#### file_name
The file where we store the temperature efficiency data.
#### groupfile_name
The groupfile file (for Excel or SQLite) where we store the temperature efficiency data.

#### folder
The folder where the data is saved.
#### efficiency_factor_column_name
The column name for the efficiency factor.


#### vehicle_temperature_efficiencies
Factors to compute the [capacity changes with temperature](weather.md#range-and-temperature),
namely the source folder, file name, and the order of the fitting polynomial.




## charging
Some parameters related to charging.
### price_reaction_exponent
An exponent factor to compute how users react to a given [charging price](#charging_price) (inactive/not currently implemented).
### desirability_reaction_exponent
An exponent factor to compute how users react to a given [desirability factor](#charging_desirability) (inactive/not currently implemented).

## charging_sessions
Parameters for sessions.
### resolution
A resolution factor used when [getting charging sessions](define.md#get_trip_charging_sessions).