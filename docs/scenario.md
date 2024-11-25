# Scenario file description

This page describes the elements of the scenario file

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

## legs

### mix

## vehicle
These parameters define the scenario's vehicle. If you want profiles
for several vehicles, run separate scenarios.
### vehicle name
This is the name of the vehicle, which will be checked to see if trips
and locations are actually declared.

## trips

## mobility_module
### day_start_hour
This parameter defines the start of the day for the scenario. It is chosen
so that there are no movements during that hour number. It represents the
shift from midnight, so a day start hour of 5 means that the day starts
at hour 5 (i.e. 05.00). The idea is to choose an hour that is logical
for the users/matches their patterns. This is connected to the 
[day types](day_types), as a given day will correspond to a day type.
For example, the hours between 00:00 and 05:00 on a Saturday belong to
the Thursday before and are as such on a week day 
(as opposed to a weekend day).

### day_types

### trips_per_day_type
For vehicles other than cars, we assume that there is one trip per day type.
This is where we match the trips to their day type

## transport_factors

### road_types

### weights

## weather

## charging

## plots

## files

## maps

## colors

## color_bars

## unit_conversion

## time

## numbers