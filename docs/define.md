
# Classes

## Leg
This class defines the legs and their properties, from a scenario
file that contains a list of instances and their properties.
Legs are point-to-point vehicle movements (i.e. movements where
the vehicle goes from a start location and ends/stops at an end location).

### Parameters
The parameters of a leg are:

1. **Name:** The name of the leg
2. **Vehicle:** The vehicle that runs the leg. If this does not correspond
to the [scenario vehicle name](scenario.md#vehicle-name), then the leg is not
declared.  Note that when running a
scenario, you select one vehicle, so this is in principle not necessary.
The reason for having this is to allow the user to copy the baseline file
and keep the location definitions that are not used for this scenario but
might be so for another, thereby reducing the need for changes between
scenarios.
3. **Distance:** The distance driven during the leg (in kilometers)
4. **Duration:** How long it takes to drive the leg (in hours)
5. **Hour in day factors:** These factors add a correction to the vehicle 
consumption that depend on the hour in day (the first is for 00:00 to 00:59,
last for 23:00 to 23:59). Note that these are actual hours,
not hours in the user day (which can start and end at other moments than
midnight). This is used to take into account things like traffic jams.
The default value is 1. ***This factor is a placeholder and is currently not
in use.***

## Location
This class defines the locations where the vehicles are
and their properties, from a scenario
file that contains a list of instances and their proper.

### Parameters

The parameters of a location are:

1. **Name**: The name of the location.
2. **Vehicle:** The vehicle that uses the location. If this does not correspond
to the [scenario vehicle name](scenario.md#vehicle-name), then the trip is not
declared.  Note that when running a
scenario, you select one vehicle, so this is in principle not necessary.
The reason for having this is to allow the user to copy the baseline file
and keep the location definitions that are not used for this scenario but
might be so for another, thereby reducing the need for changes between
scenarios.
3. **Connectivity:** A value between 0 and 1 (0% to 100%) that tells the
probability that a vehicle parked at this location is connected to a
charger.
4. **Charging power:** The (peak) charging power of the charger at this
location (in kW).
5. **Charger efficiency:** A value between 0 and 1 (0% to 100%) that tells how
much of the power drawn from the network is delivered to the battery of the
vehicle.
6. **Latitude:** The latitude of the location. ***This factor is a placeholder
and is currently not in use.***
7. **Longitude:** The longitude of the location. ***This factor is a 
placeholder and is currently not in use.***
8. **Base charging price:** The base/reference (i.e. before
flexibility/temporal changes) charging price at this location, in €/kWh.
***This factor is a placeholder and is currently not in use.***
9. **Charging desirability:** A value between 0 and 1 (0% to 100%) that tells
how much the users like to charge at this location.
***This factor is a placeholder and is currently not in use.***
10. **Percentage in location at run start:** A value between 0 and 1
(0% to 100%) that tells which percentage of the vehicles start the run there.
This is used if we will that in directly instead of computing it. The decision
t use this is controlled by the compute_start_location_split parameter in
the [mobility](mobility.md#module-parameters) module.

## Trip

This class defines the trips and their properties, from a scenario
file that contains a list of instances and their properties.
Trips are collections of legs that take place on a given day.
Note that this day does not necessarily start (and end) at midnight,
but can start (and end) at an hour that is more logical/significant for the
vehicle user (it could for example be 05:00 for car drivers).
This [day start hour](scenario.md#day_start_hour)
parameter is universal for all trips
This value is set in the scenario files.

### Parameters
1. **Name**: The name of the trip.
2. **Vehicle:** The vehicle that does the trip. If this does not correspond
to the [scenario vehicle name](scenario.md#vehicle-name), then the trip is not
declared. Note that when running 
a scenario, you select one vehicle, so this is in principle not necessary.
The reason for having this is to allow the user to copy the baseline file
and keep the trip definitions that are not used for this scenario but
might be so for another, thereby reducing the need for changes between
scenarios.
3. **Legs:** A list of the legs in the trip.
4. **Time between legs:** A list of the time spent at the arrival locations
between each leg (in hours).
5. **Percentage station users:**A value between 0 and 1
(0% to 100%) that tells us which percentage of users use fast charging
stations.
***This factor is a placeholder and is currently not in use.***
6. **Start probabilities:** A list of values between 0 and 1 (0%-100%) adding
up to 1/100% that tells us what the probability of starting the trip is at
a given hour. Note that the hours start at 
 [day start hour](scenario.md#day_start_hour), not at
midnight.
7. **Repeated sequence:** A list of repeated legs 
(which should follow each other) that form a repeated sequence.
8. **Repetition amounts:** How often
the repeated sequence is repeated. This is a list, with one value per leg
repetition (the nth element corresponds to the nth appearance of
the sequence in the leg list).
9. **Time between repetitions:** The time between repetitions of each
repeated sequence (in hours). This is a list, with one value per leg
repetition (the nth element corresponds to the nth appearance of
the sequence in the leg list).


### Mobility matrix

The main aim of the trip initialization/declaration is to create a mobility
matrix for the trip.
This mobility matrix has, for all combinations of possible start and end 
locations (i.e.
locations connected by a leg in the trip) and for each hour in day number
(starting at the [day start hour](scenario.md#day_start_hour)), the following
quantities:
1. **Duration:** The duration (in hours) of a leg between the start location
and the end location.
2. **Distance:** The distance (in kilometers) of a leg between the start 
location.
3. **Weighted distance:** The weighted distance (in kilometers) of a leg 
between the start location and the end location. This corresponds to using
different [road types](scenario.md#road_types), with given
[weights](scenario.md#weights) and given [mixes](scenario.md#mix) to account
for the fact that vehicles consume more on some road types.
4. **Departures amount**: The chance that a vehicle, in a given hour, leaves
the start location,
going to the end location (amount and chance are equivalent
here, as we compute on an individual vehicle basis).
5. **Departures kilometers:** The kilometers driven by vehicles leaving the
start location at a given hour and going to the end location. This is given
by the departures amount times the distance.
6. **Departures weighted kilometers:** The weighted (by road type) kilometers
driven by vehicles leaving the start location at a given hour and going to the 
end location. This is given
by the departures amount times the weighted distance.
7. **Arrivals amount**: The chance that a vehicle, in a given hour,
 arrives to the end
location,
having started the start location (amount and chance are equivalent
here, as we compute on an individual vehicle basis).
8. **Arrivals kilometers:** The kilometers driven by vehicles arriving to the
end location at a given hour, having started at the start location. 
This is given
by the arrivals amount times the distance.
9. **Arrivals weighted kilometers:** The weighted (by road type) kilometers
driven by vehicles arriving to the end location at a given hour, having 
started at the start location. This is given
by the arrivals amount times the weighted distance.

The model also produces a version of this mobility matrix for the whole
run (which is essentially a copy of the above matrix). This run
mobility matrix is the mobility matrix if the trip had a probability of 1
for the whole run.




#### Leg repetitions

Is repeat of leg or two legs????
[0, 5, 5, 0]
If next leg is also repeated/still has repeats left, then it is repeated after the leg
in question
so when putting a leg, check if it is repeated. If so, check if the next is repeated,
until you have no repeats (or end the list). Add on of each repeated legs
then number of repeats goes down by one and redo
Have one trip per day type for non-cars

Reference to day start hour
cross-links with scenario
