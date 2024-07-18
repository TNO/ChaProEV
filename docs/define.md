
# Classes

## Leg
This class defines the legs and their properties, from a scenario
file that contains a list of instances and their properties.
Legs are point-to-point vehicle movements (i.e. movements where
the vehicle goes from a start location and ends/stops at an end location).

### Parameters
The parameters of a leg are:

1. **Name:** The name of the leg
2. **Distance:** The distance driven during the leg (in kilometers)
3. **Duration:** How long it takes to drive the leg (in hours)
4. **Hour in day factors:** These factors add a correction to the vehicle 
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
vehicle user (it could for example be 06:00 for car drivers).
This day_start_hour
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
a given hour. Note that the hours start at the day start hour, not at
midnight.
7. **Leg repetitions:** A list for repetitions for each leg (set at zero
if the leg is not repeated), of the same length as the amount of legs. Note
that if two (or more) consecutive legs have repetitions, then they are
the sequences of legs is repeated. For more detail, see 
[here](#leg-repetitions).
8. **Time between repetitions:** A list of times (in hours) between two
repetitions of a leg. Note that the index/position in the list starts the day 
start hour, not at midnight. This allows for things like more frequent
repeats of legs at peak hours, for example.

### Initialisation



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
send Profiles to Berlin