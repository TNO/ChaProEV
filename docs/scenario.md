# Scenario file description

This page describes the elements of the scenario file

## run

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