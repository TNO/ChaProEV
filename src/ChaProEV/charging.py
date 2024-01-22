
import math
import datetime
import pandas as pd
import numpy as np

from ETS_CookBook import ETS_CookBook as cook

try:
    import run_time
except ModuleNotFoundError:
    from ChaProEV import run_time
# So that it works both as a standalone (1st) and as a package (2nd)

try:
    import mobility
except ModuleNotFoundError:
    from ChaProEV import mobility
# So that it works both as a standalone (1st) and as a package (2nd)  



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
# parameters_file_name = 'scenarios/baseline.toml'
# parameters = cook.parameters_from_TOML(parameters_file_name)


def travel_space_occupation(
        battery_space, time_tag, time_tag_index, run_range,
        run_mobility_matrix,
        parameters):

    # time_batt = False


    # if loop_time > 0.1:
    #     print(run_range[time_tag_index-1])
    #     print(time_tag_index-1)
    #     if time_batt:
    #         print('Batt', batt_time)
    #     if time_cha:
    #         print('Charge', cha_time)
    #     print('Loop', loop_time)
    #     if time_cha:
    #         print('Charge loc', cha_loc)
    #     if time_batt:
    #         if batt_time > 0.1:
    #             print(batt_times)
    #             print(batt_end_loc)
    #             # print(batt_ooo)
    #             # print(departing_battery_spaces)
    #             # print(departures)
    #             for koos in batt_rave.keys():
    #                 print(koos)
    #                 print(batt_rave[koos])
    #             # print(batt_rave)
    #             print(bett_rave_amoos)
    #             print(bett_rave_spas)


    zero_threshold = parameters['numbers']['zero_threshold']
    location_parameters = parameters['locations']
    location_names = [
        location_name for location_name in location_parameters
    ]

    vehicle_parameters = parameters['vehicle']
    use_weighted_km = vehicle_parameters['use_weighted']
    if use_weighted_km:
        distance_header = 'Weighted distance (km)'
    else:
        distance_header = 'Distance (km)'
    electricity_consumption_kWh_per_km = vehicle_parameters[
        'base_consumption_per_km']['electricity_kWh']
    
    # We look at all movements starting at a given location
    for start_location in location_names:

        # if time_batt:
        #     bett_rave_amoos[start_location] = {}
        #     bett_rave_spas[start_location] = {}
            
        #     batt_0 = datetime.datetime.now()
        #     # batt_loc_start = datetime.datetime.now()
        #     batt_times[start_location] = {}

        if time_tag_index > 0 :
            # We add the values from the previous time tag to
            # the battery space. We do so because travels can propagate to
            # future time tags. I f we just copied the value from
            # the previous time tag, we would delete these
            battery_space[start_location].iloc[time_tag_index] = (
                battery_space[start_location].iloc[time_tag_index]
                +
                battery_space[start_location].iloc[time_tag_index-1]
            )

        # if time_batt:
        #     batt_ooo_0 = datetime.datetime.now()
        #     # # # We delete columns where all the amounts per battery space 
        #     # # are zero
        #     # # (for example, ones where we had a battery space that was
        #     # # removed because of charging
        #     # battery_space[start_location] = battery_space[start_location].loc[
        #     #     :, (battery_space[start_location]!=0).any(axis=0)
        #     # ]
            
        #     batt_ooo_1 = datetime.datetime.now()

        # We look at which battery spaces there are at this location
        # and sort them. The lowest battery spaces will be first.
        # These are the ones we assume aremore likely to leave,
        # as others might want to charge first
        departing_battery_spaces = (
                sorted(battery_space[start_location].columns.values)
            )
    
        # if time_batt:
        #     batt_ooo_2 = datetime.datetime.now()
        #     batt_ooo[start_location] = [
        #         (batt_ooo_1-batt_ooo_0).total_seconds(),
        #         (batt_ooo_2-batt_ooo_1).total_seconds(),
        #     ]
        

            
        #     batt_1 = datetime.datetime.now()

        #     batt_times[start_location]['first step'] = (batt_1-batt_0).total_seconds()

        #     batt_end_loc[start_location] ={}

        # We look at all the possible destinations
        for end_location in location_names:
            
            # if time_batt:
            #     batt_end_loc_0 = datetime.datetime.now()


            # For each leg (start/end location combination), we
            # look up the consumption
            this_leg_consumption = (
                run_mobility_matrix.loc[
                            start_location, end_location, time_tag][
                                distance_header]
                *
                electricity_consumption_kWh_per_km
            )

            # if time_batt:
            #     batt_end_loc_1 = datetime.datetime.now()
            

            # We also look up how many vehicles depart
            departures = run_mobility_matrix.loc[
                start_location, end_location, time_tag][
                    'Departures amount']
            if departures > zero_threshold:
                # If there are no departures, we can skip this



                # if time_batt:
                #     batt_end_loc_2 = datetime.datetime.now()
                

    

                # We want to know what the arriving battery spaces
                # will be and the amounts/percentages of the fleet vehicles
                # for each arriving battery space
                arriving_battery_spaces = []
                arriving_amounts = []
                
                # We also need the duration of the leg
                travelling_time = run_mobility_matrix.loc[
                                start_location, end_location, time_tag][
                                    'Duration (hours)']
                
                # if time_batt:
                #     batt_end_loc_3 = datetime.datetime.now()

                

            
                
                # We iterate through the departing battery spaces
                # (reminder, they are ordered from lowest to highest,
                # as we assumed that the lower the battery space, the higher
                # the likelihood to leave, as vehicleswith more battery space/
                # less available battery capacity wll want to charge first).
                for departing_battery_space in departing_battery_spaces:

                    

                    # We will be removing the departures from the lower
                    # battery spaces from the pool, until we have reached
                    # all departures. For example, if we have 0.2 departures 
                    # and 0.19 vehicles with space equal to zero, 0.2 vehicles
                    # with space 1, and 0.3 vehicles with space 1.6,
                    # then we will first take all the 
                    # 0.19 vehicles with space 0,
                    # 0.01 vehicles with space 1, 
                    # and 0 vehicles with space 1.6,
                    # leaving us with 0 vehicles wth space 0, 
                    # 0.19 vehicles with
                    # space 1, and 0.3 vehicles with space 1.6
                    if departures > zero_threshold :
                        # (the departures threshold is there
                        # to avoid issues with floating point numbers, where
                        # we could have some variable being 0.1+0.2
                        # and removing that variabl from 0.3 would not be zero
                        
                    

                        
                        # attempts += 1
                        
                        # if travelling_time:

                        # We need to know in which slots the vehicles
                        # will arrive at their destination and the proprtion
                        # of these slots
                        travelling_time = float(travelling_time)
                        first_arrival_shift = math.floor(travelling_time)
                        first_arrival_shift_time = datetime.timedelta(
                            hours=first_arrival_shift)
                        second_arrival_shift_time = datetime.timedelta(
                            hours=first_arrival_shift+1)
                        first_arrival_shift_proportion = (
                            1 - travelling_time % 1
                        )




                        # We want to know how many dpeartures will come from
                        # the battery space we are looking at. If there are
                        # more vehicles with the current space than remaining
                        # departures, then we take the remaining departures,
                        # otherwise we take all the vehicles with the current
                        # space and move to the next one
                        this_battery_space_departures = min(
                            departures,
                            battery_space[start_location].loc[
                                time_tag][departing_battery_space].values[0]
                        )
                



                        # We add these departures to the arriving amounts,
                        # as these will arrive to the end location
                        arriving_amounts.append(this_battery_space_departures)
                        

                        # We also add the corresponding battery space at
                        # arrival, given by the original battery space plus 
                        # the leg's consumption
                        arriving_battery_spaces.append(
                            departing_battery_space+this_leg_consumption
                        )



                        # We update the departures (i.e. how many remain
                        # for larger battery spaces)
                        departures -= this_battery_space_departures


                
                        
                        # Finally, we remove the departures from the start
                        # location for the current time slot
                    
                        battery_space[start_location].loc[
                            time_tag,
                            departing_battery_space] = (
                                    battery_space[start_location].loc[
                                        time_tag][departing_battery_space]
                                        .values[0]
                                - this_battery_space_departures
                                )
                   

                # if time_batt:
                #     batt_end_loc_4 = datetime.datetime.now()       
                
                # # We only need to do this if there are actually travels between
                # # the two locations at that time slot
                # if len(arriving_battery_spaces) > 0 :
                        
                # We now can update the battery spaces in the end location.
                for arriving_battery_space, arriving_amount in zip(
                    arriving_battery_spaces, arriving_amounts
                ):
                    if arriving_amount > zero_threshold: 
                    # No need to compute if there are no arrivals
                        
                        # if time_batt:
                        #     bett_rave_amoos[start_location][end_location] = (
                        #         arriving_amounts
                        #     )
                        #     bett_rave_spas[start_location][end_location] = (
                        #         arriving_battery_spaces
                        #     )
                        #     batt_rave[f'{arriving_battery_space}_{arriving_amount}'] = (
                        #         batt_rave_base.copy()
                        #     )
                        #     batt_rave_0 = datetime.datetime.now()


                        # If the end location does not have the incoming
                        # battery space in its columns, we add the column 
                        # (with zeroes)
                        if arriving_battery_space not in (
                            battery_space[end_location].columns):
                            battery_space[end_location][
                                arriving_battery_space] = 0
            

                        # if time_batt:
                        #     batt_rave_1 = datetime.datetime.now()
                        #     batt_rave[f'{arriving_battery_space}_{arriving_amount}'].loc[(start_location, end_location), 0] = (
                        #         (batt_rave_1-batt_rave_0).total_seconds()
                        #     )

                        if first_arrival_shift_proportion > zero_threshold :
                            # Otherwise there is no first shift arrival 
                            # We check if the arrivals in the first slot
                            # are in the run range
                            # if they are not, then we don't take them into
                            # account (as the are not in the run) and add them
                            # in the end_location battery space DataFrame
                            if time_tag + first_arrival_shift_time <= (
                                run_range[-1]):
                                battery_space[end_location].loc[
                                    time_tag+first_arrival_shift_time,
                                        arriving_battery_space
                                    ] = (
                                        battery_space[end_location].loc[
                                            time_tag+first_arrival_shift_time][
                                                arriving_battery_space
                                            ].values[0]
                                        +
                                        (
                                            arriving_amount
                                            * 
                                            first_arrival_shift_proportion
                                        )
                                    )
            

                        # if time_batt:
                        #     batt_rave_2 = datetime.datetime.now()
                        #     batt_rave[f'{arriving_battery_space}_{arriving_amount}'].loc[(start_location, end_location), 1] = (
                        #         (batt_rave_2-batt_rave_1).total_seconds()
                            
                        #     )

                        #     batt_rave[f'{arriving_battery_space}_{arriving_amount}'].loc[
                        #         (start_location, end_location), 'arriving BS'] = (
                        #             arriving_battery_space
                        #         )
                        #     batt_rave[f'{arriving_battery_space}_{arriving_amount}'].loc[
                        #         (start_location, end_location), 'arriving amount'] = (
                        #             arriving_amount
                        #         )
                        #     batt_rave[f'{arriving_battery_space}_{arriving_amount}'].loc[
                        #         (start_location, end_location), '1st prop'] = (
                        #             first_arrival_shift_proportion
                        #         )
                        #     batt_rave[f'{arriving_battery_space}_{arriving_amount}'].loc[
                        #         (start_location, end_location), '1BS'] = (
                        #             battery_space[end_location].loc[
                        #                     time_tag+first_arrival_shift_time][
                        #                         arriving_battery_space
                        #                     ].values[0]
                        #         )

                        if (1 - first_arrival_shift_proportion ) > (
                            zero_threshold):
                            # Otherwise there is no first shift arrival  
                            # We check if the arrivals in the second slot 
                            # are in the run range
                            # if they are not, then we don't take them into
                            # account (as the are not in the run)  and add them
                            # in the end_location battery space DataFrame
                            if time_tag + second_arrival_shift_time <= (
                                run_range[-1]):
                                battery_space[end_location].loc[
                                    time_tag+second_arrival_shift_time,
                                        arriving_battery_space
                                    ] = (
                                        battery_space[end_location].loc[
                                            time_tag+second_arrival_shift_time
                                            ][
                                                arriving_battery_space
                                            ].values[0]
                                        +
                                        (
                                            arriving_amount
                                            * 
                                            (1-first_arrival_shift_proportion)
                                        )
                                    )
                                
                                # if time_batt:
                                #     batt_rave[
                                #         f'{arriving_battery_space}_{arriving_amount}'
                                #         ].loc[(start_location, end_location), 'BR'] = (
                                #             (1-first_arrival_shift_proportion)
                                #         )
                                #     batt_rave[
                                #         f'{arriving_battery_space}_{arriving_amount}'
                                #         ].loc[(start_location, end_location), 'AA'] = (
                                #             arriving_amount
                                #         )
                                #     batt_rave[f'{arriving_battery_space}_{arriving_amount}'].loc[
                                #     (start_location, end_location), '2BS'] = (
                                #             battery_space[end_location].loc[
                                #             time_tag+second_arrival_shift_time][
                                #                 arriving_battery_space
                                #             ].values[0]
                                # )


                #     if time_batt:
                #         batt_rave_3 = datetime.datetime.now()
                #         batt_rave[f'{arriving_battery_space}_{arriving_amount}'].loc[(start_location, end_location), 2] = (
                #             (batt_rave_3-batt_rave_2).total_seconds()
                #         )
                
                # if time_batt:      
                #     batt_end_loc_5 = datetime.datetime.now() 

                # We ensure that the columns of the battery space
                # array are ordered
                battery_space[end_location] = (
                    battery_space[end_location].reindex(
                        sorted(battery_space[end_location].columns), axis=1)
                )

                # if time_batt:
                #     batt_end_loc_6 = datetime.datetime.now() 
                #     batt_end_loc[start_location][end_location] = (
                #         [
                #             (batt_end_loc_1-batt_end_loc_0).total_seconds(),
                #             (batt_end_loc_2-batt_end_loc_1).total_seconds(),
                #             (batt_end_loc_3-batt_end_loc_2).total_seconds(),
                #             (batt_end_loc_4-batt_end_loc_3).total_seconds(),
                #             (batt_end_loc_5-batt_end_loc_4).total_seconds(),
                #             (batt_end_loc_6-batt_end_loc_5).total_seconds(),
                #         ]
                #     )
                #     # print(batte6y_space[end_location])
                #     # exit()

            # if time_batt:
            #     batt_2 = datetime.datetime.now()
            #     batt_times[start_location]['second step'] = (batt_2-batt_1).total_seconds()
            

            # We ensure that the columns of the battery space
            # array are ordered
            battery_space[start_location] = battery_space[
                start_location].reindex(
                        sorted(battery_space[start_location].columns), axis=1)

        # if time_batt:
        #     batt_3 = datetime.datetime.now()
        #     batt_times[start_location]['third step'] = (batt_3-batt_2).total_seconds()
                
    
    # Have  arrivals not connect at all if partial (until leave)
    # Or assume they move around get connected later
        

    # Charging
            
    # if time_batt:
    #     batt_end = datetime.datetime.now()
    #     batt_time = (batt_end-batt_start).total_seconds()

    # print(time_tag)
    # print(battery_space['home'])
    return battery_space



def compute_charging_events(
        battery_space, charge_drawn_by_vehicles, charge_drawn_from_network,
        time_tag, parameters):
        
    zero_threshold = parameters['numbers']['zero_threshold']
    location_parameters = parameters['locations']
    location_names = [
        location_name for location_name in location_parameters
    ]

    for charging_location in location_names:
        
        # if time_cha:
        #     cha_loc_start = datetime.datetime.now()
        #     cha_loc_0 = datetime.datetime.now()


        charging_location_parameters = location_parameters[charging_location]
        charger_efficiency = charging_location_parameters['charger_efficiency']
        percent_charging = charging_location_parameters['connectivity']
        max_charge = charging_location_parameters['charging_power']

        # This variable is useful if new battery spaces
        # are added within this charging procedure
        original_battery_spaces = (
            battery_space[charging_location].columns.values
        )
        charge_drawn_per_charging_vehicle = np.array([
            min(this_battery_space, max_charge)
            for this_battery_space in original_battery_spaces
        ])
        network_charge_drawn_per_charging_vehicle = (
            charge_drawn_per_charging_vehicle
            /
            charger_efficiency
        )

        # if time_cha:
        #     cha_loc_1 = datetime.datetime.now()


        vehicles_charging = (
            percent_charging
            * 
            battery_space[charging_location].loc[time_tag]
        ).values[0]
        charge_drawn_by_vehicles_this_time_tag_per_battery_space = (
            vehicles_charging * charge_drawn_per_charging_vehicle
        )
        charge_drawn_by_vehicles_this_time_tag = sum(
            charge_drawn_by_vehicles_this_time_tag_per_battery_space)
        network_charge_drawn_by_vehicles_this_time_tag_per_battery_space = (
            vehicles_charging * network_charge_drawn_per_charging_vehicle
        )
        network_charge_drawn_by_vehicles_this_time_tag = sum(
            network_charge_drawn_by_vehicles_this_time_tag_per_battery_space)

        # if time_cha:
        #     cha_loc_2 = datetime.datetime.now()



        # We only do the charge computations if there is a charge to be drawn
        if charge_drawn_by_vehicles_this_time_tag > zero_threshold:

            charge_drawn_by_vehicles.loc[time_tag, charging_location] = (
                charge_drawn_by_vehicles
                .loc[time_tag][charging_location]
                +
                charge_drawn_by_vehicles_this_time_tag
            )

            # if time_cha:
            #     cha_loc_3 = datetime.datetime.now()



            charge_drawn_from_network.loc[time_tag, charging_location] = (
                charge_drawn_from_network
                .loc[time_tag][charging_location]
                +
                network_charge_drawn_by_vehicles_this_time_tag
            )

            # if time_cha:
            #     cha_loc_4 = datetime.datetime.now()
                
            
            battery_spaces_after_charging = (
                battery_space[charging_location].columns.values
                -
                charge_drawn_per_charging_vehicle
            )

            # if time_tag_index == 3:
            #     print(battery_space[charging_location].columns.values)
            #     print(charge_drawn_per_charging_vehicle)
            #     print(battery_spaces_after_charging)
            #     print(original_battery_spaces)
            #     if charging_location=='home':
            #         exit()

            # if time_cha:
            #     cha_loc_5 = datetime.datetime.now()
            #     cha_pi[charging_location] = []
            #     cha_pi_a[charging_location] = []
            #     cha_pi_b[charging_location] = []
            #     cha_pi_c[charging_location] = []
            #     kazi[charging_location] = {}
            #     kozi[charging_location] = {}
            #     kuzi[charging_location] = {}
            #     lazi[charging_location] = {}
            #     lozi[charging_location] = {}
            #     luzi[charging_location] = {}
            for (
                battery_space_after_charging,
                original_battery_space,
                vehicles_that_get_to_this_space
            ) in zip(
                battery_spaces_after_charging,
                original_battery_spaces,
                vehicles_charging
            ):
                # To avoid unnecessary calculations
                # USE Thresh?
                if vehicles_that_get_to_this_space > zero_threshold :
                    if original_battery_space > zero_threshold:

                        # if time_cha:
                        #     cha_pi_start = datetime.datetime.now()
                        #     cha_pi_a_start = datetime.datetime.now()
                        #     kazi[charging_location][battery_space_after_charging] = []
                        #     kozi[charging_location][battery_space_after_charging] = []
                        #     kuzi[charging_location][battery_space_after_charging] = []
                        #     lazi[charging_location][original_battery_space] = []
                        #     lozi[charging_location][original_battery_space] = []
                        #     luzi[charging_location][original_battery_space] = []


                        if battery_space_after_charging not in (
                            battery_space[charging_location].columns.values):

                            battery_space[charging_location][
                                battery_space_after_charging] = 0
                            

                        # if time_cha:
                        #     cha_pi_a_end = datetime.datetime.now()
                        #     cha_pi_a[charging_location]= (cha_pi_a_end-cha_pi_a_start).total_seconds()
                        #     cha_pi_b_start = datetime.datetime.now()
            
                        battery_space[charging_location].loc[
                            time_tag, battery_space_after_charging] = (
                                battery_space[charging_location].loc[
                                    time_tag][battery_space_after_charging]
                                    .values[0]
                                +
                                vehicles_that_get_to_this_space
                            )
                        
                        # if time_cha:
                        #     cha_pi_b_end = datetime.datetime.now()
                        #     cha_pi_b[charging_location] = (cha_pi_b_end-cha_pi_b_start).total_seconds()
                            
                        #     kazi[charging_location][battery_space_after_charging] = vehicles_that_get_to_this_space
                        #     kozi[charging_location][battery_space_after_charging] = battery_space[charging_location].loc[
                        #             time_tag][battery_space_after_charging].values[0]
                        #     kuzi[charging_location][battery_space_after_charging] = charge_drawn_per_charging_vehicle
                        #     cha_pi_c_start = datetime.datetime.now()

            
                        battery_space[charging_location].loc[
                            time_tag, original_battery_space] = (
                                battery_space[charging_location].loc[
                                    time_tag][original_battery_space]
                                    .values[0]
                                -
                                vehicles_that_get_to_this_space
                            )
                        
                        # if time_cha:
                        #     cha_pi_c_end = datetime.datetime.now()
                        #     cha_pi_c[charging_location] = (cha_pi_c_end-cha_pi_c_start).total_seconds()
                        #     cha_pi_end = datetime.datetime.now()
                        #     cha_pi[charging_location] = (cha_pi_end-cha_pi_start).total_seconds()
                        #     lazi[charging_location][original_battery_space] = vehicles_that_get_to_this_space
                        #     lozi[charging_location][original_battery_space] = battery_space[charging_location].loc[
                        #             time_tag][original_battery_space].values[0]
                        #     luzi[charging_location][original_battery_space] = original_battery_space
    
            # if time_cha:
            #     cha_loc_6 = datetime.datetime.now()
            
            battery_space[charging_location] = battery_space[
                charging_location].reindex(
                sorted(battery_space[charging_location].columns), axis=1)
            
            # if time_cha:
            #     cha_loc_7 = datetime.datetime.now()
            #     cha_loc_end = datetime.datetime.now()
            #     cha_loc[charging_location] = (cha_loc_end-cha_loc_start).total_seconds()


            # if time_tag_index == 114940:   #284, 740, 1389, 3032, 270,, 680, 1679, 2173, 4552 #  3573, 4552:
            #     print((datetime.datetime.now()-cha_start).total_seconds())
            #     print(time_tag)
            #     print(cha_loc)
            #     print((cha_loc_1-cha_loc_0).total_seconds())
            #     print((cha_loc_2-cha_loc_1).total_seconds())
            #     print((cha_loc_3-cha_loc_2).total_seconds())
            #     print((cha_loc_4-cha_loc_3).total_seconds())
            #     print((cha_loc_5-cha_loc_4).total_seconds())
            #     print((cha_loc_6-cha_loc_5).total_seconds())
            #     print(vehicles_charging)
            #     print(original_battery_spaces)
            #     print(battery_spaces_after_charging)
            #     print(cha_pi)
            #     print(cha_pi_a)
            #     print(cha_pi_b)
        
        
    #     else:
    #         if time_cha:
    #             cha_loc_3 = datetime.datetime.now()
    #             cha_loc_4 = datetime.datetime.now()
    #             cha_loc_5 = datetime.datetime.now()
    #             cha_loc_6 = datetime.datetime.now()
    #             cha_loc_7 = datetime.datetime.now()
    #             cha_loc_end = datetime.datetime.now()
    #             cha_loc[charging_location] = (cha_loc_end-cha_loc_start).total_seconds()
    #                 #     print(cha_pi_c)
    #         #     # exit()
    # if time_cha:
    #     cha_end = datetime.datetime.now()
    #     cha_time = (cha_end-cha_start).total_seconds()
    return battery_space, charge_drawn_by_vehicles, charge_drawn_from_network

def get_charging_profile(parameters):
    
    
    time_cha = False
    
    

    # Float precision can mean that we have exteremly small values
    # that are actually zero
    zero_threshold = parameters['numbers']['zero_threshold']
    charging_parameters = parameters['charging']
    
    
    
    run_range, run_hour_numbers = run_time.get_time_range(parameters)
    # print(run_range[3573])
    # exit()
    SPINE_hour_numbers = [f't{hour_number:04}' for hour_number in run_hour_numbers]
    location_parameters = parameters['locations']
    location_names = [
        location_name for location_name in location_parameters
    ]
    scenario = parameters['scenario']
    case_name = parameters['case_name']

    file_parameters = parameters['files']
    output_folder = file_parameters['output_folder']
    groupfile_root = file_parameters['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    location_split_table_name = f'{scenario}_location_split'
    location_split = cook.read_table_from_database(
        location_split_table_name, f'{output_folder}/{groupfile_name}.sqlite3'
    )
    location_split['Time tag'] = pd.to_datetime(location_split['Time tag'])
    location_split = location_split.set_index('Time tag')


    # We look at the various battery spaces that are available
    # at this charging location (i.e. percent of vehicles with
    # a given battery space per location)
    battery_space = {}
    for location_name in location_names:
        battery_space[location_name] = pd.DataFrame(
            run_range,
            columns= ['Time Tag'])
        battery_space[location_name]['Hour Number'] = run_hour_numbers
        battery_space[location_name]['SPINE_Hour_Number'] = SPINE_hour_numbers
        # battery_space[0] = 0
        battery_space[location_name] = battery_space[location_name].set_index(
            ['Time Tag', 'Hour Number', 'SPINE_Hour_Number'])
        battery_space[location_name][0] = 0 
        battery_space[location_name][0].iloc[0] = location_split.loc[run_range[0]][location_name]


    run_mobility_matrix = cook.read_table_from_database(
        f'{scenario}_run_mobility_matrix', 
        f'{output_folder}/{groupfile_name}.sqlite3'
    )
    run_mobility_matrix['Time tag'] = pd.to_datetime(
        run_mobility_matrix['Time tag'])
    run_mobility_matrix = run_mobility_matrix.set_index(
        ['From', 'To', 'Time tag'])

    charge_drawn_by_vehicles = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names, index=run_range
    )
    charge_drawn_from_network = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names, index=run_range
    )
    start_time = datetime.datetime.now()
    loop_start = start_time

    loop_times = pd.DataFrame(
        np.zeros((len(run_range),1)), columns=['Loop duration'],
                index=run_range
    )
        
    # We look at how the available battery space in the vehicles moves around
    # (it increases with movements and decreases with charging)
    for time_tag_index, time_tag in enumerate(run_range):
        # print(time_tag)
        loop_end = datetime.datetime.now()
        loop_time = (loop_end-loop_start).total_seconds()
        loop_times.loc[time_tag,'Loop duration'] = loop_time
        if loop_time > 0.1:
            print(run_range[time_tag_index-1])
            print(time_tag_index-1)
            # if time_batt:
            #     print('Batt', batt_time)
            # if time_cha:
            #     print('Charge', cha_time)
            # print('Loop', loop_time)
            # if time_cha:
            #     print('Charge loc', cha_loc)
            # if time_batt:
            #     if batt_time > 0.1:
            #         print(batt_times)
            #         print(batt_end_loc)
            #         # print(batt_ooo)
            #         # print(departing_battery_spaces)
            #         # print(departures)
            #         for koos in batt_rave.keys():
            #             print(koos)
            #             print(batt_rave[koos])
            #         # print(batt_rave)
            #         print(bett_rave_amoos)
            #         print(bett_rave_spas)
            # if time_cha:
            #     if cha_time > 0.1:
            #         print((cha_loc_1-cha_loc_0).total_seconds())
            #         print((cha_loc_2-cha_loc_1).total_seconds())
            #         print((cha_loc_3-cha_loc_2).total_seconds())
            #         print((cha_loc_4-cha_loc_3).total_seconds())
            #         print((cha_loc_5-cha_loc_4).total_seconds())
            #         print((cha_loc_6-cha_loc_5).total_seconds())
            #         print((cha_loc_7-cha_loc_6).total_seconds())
            #         print(vehicles_charging)
            #         print(original_battery_spaces)
            #         print(battery_spaces_after_charging)
            #         print(cha_pi)
            #         print(cha_pi_a)
            #         print(cha_pi_b)
            #         print(cha_pi_c)
            #         print(kazi, kozi, kuzi)
            #         print(lazi, lozi, luzi)
                # Issue mostly at home, sometimes leisure

                # exit()
        # print(battery_space['home'])
        battery_space = travel_space_occupation(
            battery_space, time_tag, time_tag_index, run_range,
            run_mobility_matrix,
            parameters
        )

        # print(battery_space['home'])
        battery_space, charge_drawn_by_vehicles, charge_drawn_from_network =( 
            compute_charging_events(
            battery_space, charge_drawn_by_vehicles,
            charge_drawn_from_network,
            time_tag, parameters)
        )
        # print(battery_space['home'])
        # if time_tag_index==600:
        #     print(battery_space['home'].loc[time_tag])
        #     print(charge_drawn_by_vehicles.loc[time_tag])
        #     exit()

        loop_start = datetime.datetime.now()
        
    
        # We start with the battery space reduction duw to moving



        # if time_batt:
        #     batt_start = datetime.datetime.now()
        #     batt_times = {}
        #     # print(location_split.loc[time_tag])
        #     batt_ooo = {}
        #     batt_end_loc = {}
        #     batt_rave_index_tuples = [
        #         (b_start_location, b_end_location)
        #         for b_start_location in location_names
        #         for b_end_location in location_names]
        #     batt_rave_index = pd.MultiIndex.from_tuples(
        #         batt_rave_index_tuples, names=['Start', 'End']
        #     )
        #     batt_rave_base = pd.DataFrame(index=batt_rave_index)
        #     batt_rave = {}
        #     bett_rave_amoos = {}
        #     bett_rave_spas = {}

        # battery_space = travel_space_occupation(
        #     battery_space, time_tag, time_tag_index, run_range,
        #     run_mobility_matrix,
        #     parameters
        # )

        # #Charging
        # if time_tag_index == 117848: #7818: #510, 1013, 1384, 1800, 3832 4883  #3856, 4913, 6190, 7818
        #     print(time_tag)
        #     print(batt_time)
        #     print(batt_times)
        #     print(batt_end_loc)
        #     print(batt_ooo)
        #     # exit()

        # if time_cha:
        #     cha_loc = {}
        #     cha_start = datetime.datetime.now()
        #     cha_pi = {}
        #     cha_pi_a = {}
        #     cha_pi_b = {}
        #     cha_pi_c = {}
        #     kazi = {}
        #     kozi = {}
        #     kuzi = {}
        #     lazi = {}
        #     lozi = {}
        #     luzi = {}
  

    print('Empty DF?')
    print('Keep float precision?')
    print('Keep reindex?')
    print('split off in a function?')
    print('Check totals and such?')
    print('Other charging strategies?')
    print((datetime.datetime.now()-start_time).total_seconds())


    for location_name in location_names:

        battery_space[location_name].columns = battery_space[location_name].columns.astype(str)
        cook.save_dataframe(
            battery_space[location_name],
            f'{scenario}_{location_name}_battery_space',
            groupfile_name, output_folder, parameters
        )

    cook.save_dataframe(
            charge_drawn_from_network,
            f'{scenario}_charge_drawn_from_network',
            groupfile_name, output_folder, parameters
        )

    cook.save_dataframe(
            charge_drawn_by_vehicles,
            f'{scenario}_charge_drawn_by_vehicles',
            groupfile_name, output_folder, parameters
        )

    loop_times.to_csv('Lopi.csv')



if __name__ == '__main__':
    parameters_file_name = 'scenarios/baseline.toml'
    parameters = cook.parameters_from_TOML(parameters_file_name)
    start_ = datetime.datetime.now()
    charging_profile = get_charging_profile(parameters)
    print((datetime.datetime.now()-start_).total_seconds())
    exit()   