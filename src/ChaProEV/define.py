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
import math


import numpy as np
import pandas as pd

from ETS_CookBook import ETS_CookBook as cook

try:
    import run_time
except ModuleNotFoundError:
    from ChaProEV import run_time
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
        leg.road_type_mix = leg_parameters['road_type_mix']['mix']


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
        trip.time_between_legs = trip_parameters['time_between_legs']
        trip.percentage_station_users = trip_parameters[
            'percentage_station_users'
        ]
        trip.start_probabilities = trip_parameters[
            'start_probabilities'
        ]
        trip.day_start_hour = parameters['mobility_module']['day_start_hour']
        # We want to create a mobility matrix for the trip. This matrix will
        # have start and end locations (plus hour in day, starting
        # at day start) as an index, and departures, arrivals as columns (
        # each with amounts, distances, weighted distances)
        HOURS_IN_A_DAY = parameters['time']['HOURS_IN_A_DAY']
        mobility_index_tuples = [
            (start_location, end_location, hour_number)
            for start_location in location_names
            for end_location in location_names
            for hour_number in range(HOURS_IN_A_DAY)
        ]
        mobility_index = pd.MultiIndex.from_tuples(
            mobility_index_tuples,
            names=['From', 'To', 'Hour number (from day start)'])
        mobility_quantities = (
            parameters['mobility_module']['mobility_quantities']
        )
        trip.mobility_matrix = pd.DataFrame(
            np.zeros((len(mobility_index), len(mobility_quantities))),
            columns=mobility_quantities,
            index=mobility_index
        )

        trip.mobility_matrix = trip.mobility_matrix.sort_index()

        # We want to track the probabilities and time driving of previous legs
        previous_leg_start_probabilities = trip.start_probabilities
        time_driving_previous_leg = 0

        # To fill in the mobility matrix, we iterate over the legs of the trip
        for leg_index, leg_name in enumerate(trip.legs):
            leg_parameters = parameters['legs'][leg_name]
            start_location = leg_parameters['locations']['start']
            end_location = leg_parameters['locations']['end']
            time_driving = leg_parameters['duration']
            # We want to know the percentage of time driving due to this
            # leg in the current (hour) interval and subsequent ones
            # We first fill the intervals that are fully filled by the driving
            # e.g four ones ifthe driving is 4.2 hours
            time_driving_in_intervals = [1] * math.floor(time_driving)
            # We then append the remainder (which is the duration if the
            # duration is smaller than the (hour) interval)
            remainder = time_driving- math.floor(time_driving)
            # But only if it is not zero (to avoid adding an unnecessary index)
            if remainder > 0:
                time_driving_in_intervals.append(
                    remainder
                )
            distance = leg_parameters['distance']
            road_type_mix = np.array(leg_parameters['road_type_mix']['mix'])
            road_type_weights = np.array(
                parameters['transport_factors']['weights'])
            road_type_factor = sum(road_type_mix * road_type_weights)
            weighted_distance = road_type_factor * distance

            if leg_index > 0:
                # We want to know how much time there is between legs
                # so that we can shift the start probabilities accordingly.
                # To get the time between a leg and the previous leg, we need
                # to know two things: the time spent driving in the
                # previous leg, and the
                # time spent between legs (i.e. the idle time)
                time_spent_at_location = trip.time_between_legs[leg_index-1]
                time_shift = time_driving_previous_leg + time_spent_at_location

            else:
                # The first leg is not shifted, by definition of the trip
                # start probabilities, as the trip starts with the first leg
                time_shift = 0

            # Each leg starts with the computed time shift
            # and ends with the time shift plus the time time driving
            # in the current leg
            # We need to use int() to use the roll function
            # A possible improvement would be to proportionally spread
            # the departures and arrivals with the remainder
            current_leg_start_probabilities = (
                np.roll(previous_leg_start_probabilities, int(time_shift))
            )
            current_leg_end_probabilities = (
                np.roll(
                    previous_leg_start_probabilities,
                    int(time_shift+time_driving))
            )

            # With this, we can add this leg's contribution to the
            # mobility matrix
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Departures amount'] = (
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 'Departures amount'
                    ].values
                    + current_leg_start_probabilities
            )
            # We want to compute the percentage that is driving 
            # due to a departure from the leg's departure location
            # We start with an empty list
            percentage_departures_driving = [0] * HOURS_IN_A_DAY
            # We look how many start in each hour
            for hour_index, start_probability in enumerate(
                current_leg_start_probabilities):
                # The start probability applies to all the future times
                # where there is (partial or total) driving
                driving_percentages = [
                    time_driving_in_interval * start_probability
                    for time_driving_in_interval in time_driving_in_intervals
                ]
                # The corresponding intervals are modified (we need to
                # wrap around if we go into the next calendar day)
                # We first list the modified indices
                modified_indices = [
                    modified_index % HOURS_IN_A_DAY 
                    for modified_index 
                    in range(hour_index,hour_index+len(driving_percentages))]
                # We then add up the corresponding driving percentages
                for driving_percentage, modified_index in zip(
                    driving_percentages, modified_indices):
                    percentage_departures_driving[modified_index] += (
                        driving_percentage
                    )
                
        
            # With this, we can add this leg's contribution to the
            # mobility matrix
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Departures driving time'] = (
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 
                        'Departures driving time'
                    ].values
                    + percentage_departures_driving
                )
            
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Departures kilometers'] = (
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 'Departures kilometers'
                    ].values
                    + current_leg_start_probabilities * distance
            )
            trip.mobility_matrix.loc[
                (start_location, end_location),
                'Departures weighted kilometers'] = (
                    trip.mobility_matrix.loc[
                        (start_location, end_location),
                        'Departures weighted kilometers'
                    ].values
                    + current_leg_start_probabilities * weighted_distance
            )

            trip.mobility_matrix.loc[
                (start_location, end_location), 'Arrivals amount'] = (
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 'Arrivals amount'
                        ].values
                    + current_leg_end_probabilities
            )
            # We want to compute the percentage that is driving 
            # due to an arrival from the leg's departure location
            # We start with an empty list
            percentage_arrivals_driving = [0] * HOURS_IN_A_DAY
            # We look how many start in each hour
            for hour_index, start_probability in enumerate(
                current_leg_start_probabilities):
                # The start probability applies to all the future times
                # where there is (partial or total) driving
                driving_percentages = [
                    time_driving_in_interval * start_probability
                    for time_driving_in_interval in time_driving_in_intervals
                ]
                # The corresponding intervals are modified. This time,
                # we need to go backwards (we need to
                # wrap around if we go into the previous calendar day)
                # The +1 are added to have the right indices
                # We first list the modified indices
                modified_indices = [
                    modified_index % HOURS_IN_A_DAY 
                    for modified_index 
                    in range(
                        hour_index-len(driving_percentages)+1,hour_index+1)]
     

                 
                # We then add up the corresponding driving percentages
                for driving_percentage, modified_index in zip(
                    driving_percentages, modified_indices):
                    percentage_arrivals_driving[modified_index] += (
                        driving_percentage
                    )


            # With this, we can add this leg's contribution to the
            # mobility matrix
            trip.mobility_matrix.loc[
                (start_location, end_location), 'Arrivals driving time'] = (
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 
                        'Arrivals driving time'
                    ].values
                    + percentage_arrivals_driving
                )
    
            

            trip.mobility_matrix.loc[
                (start_location, end_location), 'Arrivals kilometers'] = (
                    trip.mobility_matrix.loc[
                        (start_location, end_location), 'Arrivals kilometers'
                    ].values
                    + current_leg_end_probabilities * distance
            )
            trip.mobility_matrix.loc[
                (start_location, end_location),
                'Arrivals weighted kilometers'] = (
                    trip.mobility_matrix.loc[
                        (start_location, end_location),
                        'Arrivals weighted kilometers'
                    ].values
                    + current_leg_end_probabilities * weighted_distance
            )

            # Fianlly, we update the previous leg values with the current ones
            previous_leg_start_probabilities = current_leg_start_probabilities
            time_driving_previous_leg = time_driving
            

        # We now can create a mobility matrix for the whole run
        run_time_tags = run_time.get_time_range(parameters)[0]
        run_mobility_index_tuples = [
            (start_location, end_location, time_tag)
            for start_location in location_names
            for end_location in location_names
            for time_tag in run_time_tags
        ]
        mobility_index_names = (
            parameters['mobility_module']['mobility_index_names']
        )
        run_mobility_index = pd.MultiIndex.from_tuples(
            run_mobility_index_tuples,
            names=mobility_index_names)
        mobility_quantities = (
            parameters['mobility_module']['mobility_quantities']
        )
        trip.run_mobility_matrix = pd.DataFrame(
            columns=mobility_quantities,
            index=run_mobility_index
        )
        trip.run_mobility_matrix = trip.run_mobility_matrix.sort_index()

        for start_location in location_names:
            for end_location in location_names:

                cloned_mobility_matrix = (
                    run_time.from_day_to_run(
                        trip.mobility_matrix.loc[
                            (start_location, end_location),
                            mobility_quantities
                        ],
                        run_time_tags,
                        trip.day_start_hour, parameters
                    )
                )
                for mobility_quantity in mobility_quantities:
                    trip.run_mobility_matrix.at[
                        (start_location, end_location), mobility_quantity
                        ] = cloned_mobility_matrix[mobility_quantity].values

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

        empty_values = np.empty((len(trip.time_index), len(location_names)))
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
    case_name = parameters['case_name']
    scenario = parameters['scenario']
    file_parameters = parameters['files']
    output_folder = file_parameters['output_folder']
    groupfile_root = file_parameters['groupfile_root']
    legs = declare_class_instances(Leg, parameters)

    vehicles = declare_class_instances(Vehicle, parameters)

    locations = declare_class_instances(Location, parameters)

    trips = declare_class_instances(Trip, parameters)

    # We want to save the mbolity matrixes
    for trip in trips:
        mobility_table_name = (
            f'{case_name}_{scenario}_{trip.name}_mobility_matrix'
        )
        cook.save_dataframe(
            trip.mobility_matrix, mobility_table_name, groupfile_root,
            output_folder, parameters
        )
        run_mobility_table_name = (
            f'{case_name}_{scenario}_{trip.name}_run_mobility_matrix'
        )
        cook.save_dataframe(
            trip.run_mobility_matrix, run_mobility_table_name, groupfile_root,
            output_folder, parameters
        )

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
            trip.start_probabilities, trip.vehicle, 
        )
