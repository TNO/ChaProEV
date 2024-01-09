'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This module defines and declares classes for the different objects
that define the system (the parameters/defintions come from a parameters file),
namely:
1. **Legs:** Legs are point-to-point vehicle movements (i.e. movements where
    the vehicle goes from a start location and ends/stops at an end location).
2. **Vehicles:** Each vehicle type (or subtype) is defined in this class.
3. **Location:** This class defines the locations where the vehicles are
(available charger power, connectivity, latitude, longitude, etc.).
4. **Trips:** Trips are collections of legs that take place on a given day.
    Note that this day does not necessarily start (and end) at minight,
    but can start (and end) at an hour that is more logical/significant for the
    vehicle user (it could for example be 06:00 for car drivers).

This module also includes two functions to declare a chosen class, and
to run that function for all class types.
'''

import datetime


import numpy as np
import pandas as pd

from ETS_CookBook import ETS_CookBook as cook

try:
    import weather
except ModuleNotFoundError:
    from ChaProEV import weather
# So that it works both as a standalone (1st) and as a package (2nd)


class Leg:
    '''
    This class defines the legs and their properties, from a parameters
    file that contains a list of instances and their properties.
    Legs are point-to-point vehicle movements (i.e. movements where
    the vehicle goes from a start location and ends/stops at an end location).
    '''

    class_name = 'legs'

    def __init__(leg, name, parameters):
        leg.name = name

        leg_parameters = parameters['legs'][name]
        leg.distance = leg_parameters['distance']
        leg.duration = leg_parameters['duration']
        leg.hour_in_day_factors = leg_parameters['hour_in_day_factors']
        locations = leg_parameters['locations']
        leg.start_location = locations['start']
        leg.end_location = locations['end']
        road_type_parameters = leg_parameters['road_type_mix']
        leg.road_type_mix = {}
        for road_type in road_type_parameters:
            leg.road_type_mix[road_type] = road_type_parameters[road_type]


class Vehicle:
    '''
    This class defines the vehicles and their properties, from a parameters
    file that contains a list of instances and their porperties.
    '''

    class_name = 'vehicles'

    def __init__(vehicle,  name, parameters):
        vehicle.name = name

        vehicle_parameters = parameters['vehicles'][name]
        vehicle.base_consumption = vehicle_parameters['base_consumption']
        vehicle.battery_capacity = vehicle_parameters['battery_capacity']
        vehicle.solar_panel_size_kWp = vehicle_parameters[
            'solar_panel_size_kWp']

        road_factor_parameters = vehicle_parameters['road_factors']
        vehicle.road_factors = {}
        for road_type in road_factor_parameters:
            vehicle.road_factors[road_type] = road_factor_parameters[road_type]


class Location:
    '''
    This class defines the locations where the vehicles are
    and their properties,  from a parameters
    file that contains a list of instances and their properties.
    '''

    class_name = 'locations'

    def __init__(location,  name, parameters):
        location.name = name

        location_parameters = parameters['locations'][name]
        location.connectivity = location_parameters['connectivity']
        location.charging_power = location_parameters['charging_power']
        location.latitude = location_parameters['latitude']
        location.longitude = location_parameters['longitude']
        location.base_charging_price = (
            location_parameters['base_charging_price']
        )
        location.charging_desirability = (
            location_parameters['charging_desirability']
        )


class Trip:
    '''
    This class defines the  trips and their properties, from a parameters
    file that contains a list of instances and their properties.
    Trips are collections of legs that take place on a given day.
    Note that this day does not necessarily start (and end) at minight,
    but can start (and end) at an hour that is more logical/significant for the
    vehicle user (it could for example be 06:00 for car drivers).
    This value is set in the parameters files.
    '''

    class_name = 'trips'

    def __init__(trip,  name, parameters):
        trip.name = name

        location_parameters = parameters['locations']
        location_names = [
            location_name for location_name in location_parameters
        ]
        trip_parameters = parameters['trips'][name]
        trip.vehicle = trip_parameters['vehicle']
        trip.legs = trip_parameters['legs']
        trip.percentage_station_users = trip_parameters[
            'percentage_station_users'
        ]
        trip.start_probabilities = trip_parameters[
            'start_probabilities'
        ]
        trip.day_start_hour = trip_parameters['day_start_hour']

        frequency_parameters = parameters['run']['frequency']
        trip_frequency_size = frequency_parameters['size']
        trip_frequency_type = frequency_parameters['type']
        trip_frequency = f'{trip_frequency_size}{trip_frequency_type}'

        # For these, the year, month and day are not important,
        # as they will be omitted, so we put generic values.
        trip_start = datetime.datetime(2001, 1, 1, trip.day_start_hour)
        trip_end = datetime.datetime(2001, 1, 2, trip.day_start_hour)
        trip_time_stamps = pd.date_range(
            start=trip_start, end=trip_end, freq=trip_frequency,
            inclusive='left'
            # We want the start timestamp, but not the end one, so we need
            # to say it is closed left
        )
        trip_time_index_tuples = [
            (time_stamp.hour, time_stamp.minute, time_stamp.second)
            for time_stamp in trip_time_stamps
        ]

        trip.time_index = pd.MultiIndex.from_tuples(
            trip_time_index_tuples, name=['Hour', 'Minute', 'Second']
        )

        trip.base_dataframe = pd.DataFrame(index=trip.time_index)

        location_parameters = parameters['locations']
        locations = list(location_parameters.keys())

        empty_values = np.empty((len(trip.time_index), len(locations)))
        empty_values[:] = np.nan
        trip.base_dataframe[location_names] = empty_values
        trip.located_at = trip.base_dataframe.copy()
        trip.connected = trip.base_dataframe.copy()
        trip.available_power_kW = trip.base_dataframe.copy()
        trip.battery_space_kWh = trip.base_dataframe.copy()
        trip.drawn_charge_kWh = trip.base_dataframe.copy()
        trip.energy_necessary_for_next_leg = trip.base_dataframe.copy()


def declare_class_instances(Chosen_class, parameters):
    '''
    This function creates the instances of a class (Chosen_class),
    based on a parameters file name where the instances and their properties
    are given.
    '''

    class_name = Chosen_class.class_name

    class_names = parameters[class_name]
    instances = []

    for class_name in class_names:
        instances.append(Chosen_class(class_name, parameters))

    return instances


def declare_all_instances(parameters):
    '''
    This declares all instances of the various objects
    (legs,  vehicles,  locations,  trips).
    '''
    legs = declare_class_instances(Leg, parameters)

    vehicles = declare_class_instances(Vehicle, parameters)

    locations = declare_class_instances(Location, parameters)

    trips = declare_class_instances(Trip, parameters)

    return legs, vehicles, locations, trips


if __name__ == '__main__':

    parameters_file_name = 'scenarios/baseline.toml'
    parameters = cook.parameters_from_TOML(parameters_file_name)
    legs, vehicles, locations, trips = declare_all_instances(
        parameters)

    for leg in legs:
        print(
            leg.name, leg.distance, leg.duration, leg.hour_in_day_factors,
            leg.start_location, leg.end_location,
            leg.road_type_mix
        )

    for vehicle in vehicles:
        print(
            vehicle.name, vehicle.base_consumption, vehicle.battery_capacity,
            vehicle.road_factors
        )

    for location in locations:
        print(
            location.name,
            location.connectivity,
            location.charging_power
        )

    for trip in trips:

        print(
            trip.name, trip.legs, trip.percentage_station_users,
            trip.start_probabilities, trip.vehicle, trip.day_start_hour,
        )
        print(trip.base_dataframe)
