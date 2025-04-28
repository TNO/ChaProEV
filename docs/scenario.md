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
The frequency of the displayed values can be different than the frequency of the compuatations.
In the current version, this needs to be the same or less frequent than the computation frequencey above.
### extra_downloads
This is to decide if you want to dowload some files (note that this concerns the
currently inactive weather module).
## locations


### vehicle
### connectivity
### charging_power
### charger_efficiency
### latitude
### longitude
### charging_price
### charging_desirability 
An indicator (0-1) of how much people like to charge at this location
### percentage_in_location_at_run_start
If filling it directly instead of computing it (controlled by
compute_start_location_split in mobility_module below)

### vehicle_discharge_power
### proportion_of_discharge_to_network
### time_modulation_factors


Starts at midinight

## legs


### vehicle
### distance
### duration

### hour_in_day_factors

This factor adds a correction to the vehicle consumption that depends
on the hour in day (the first is for 00:00 to 00:59,
the last for 23:00 to 23:59). Note that these are actual hours,
not hours in the user day (which can start and end at other moments than
midnight). This is used to take into account things like traffic jams.
The default value is 1.



### locations
### road_type_mix
Give the road type mix
We need a value for each of the road_types (see above in [transport_factors])
If the road type does not occur in the leg, simply put 0
Note that the total should be 1 (there are not checks to ensure this,
so you need to make sure you do this correctly)
road_types = ['highway', 'city']



### mix

## vehicle
These parameters define the scenario's vehicle. If you want profiles
for several vehicles, run separate scenarios.
### name
This is the name of the vehicle, which will be checked to see if trips
and locations are actually declared.

### base_location
not relevant for cars
### yearly_kilometrage

Not relevant for cars, as it is built bottom-up
### kilometers_column_for_consumption
### use_weighted
### battery_capacity

### solar_panel_size_kWp
### base_consumption_per_km
electricity_kWh = 0.76
gasoline_litres = 0.3399
diesel_litres = 0.2917
hydrogen_kg = 0.0398
CNG_kg = 0.2415
LNG_kg = 0.2415

## trips

### vehicle
### legs
### time_between_legs

This is the time spent at each interim location (same units as used
general)



### percentage_station_users
### start_probabilities
### repeated_sequence
### repetition_amounts
### time_between_repetitions

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