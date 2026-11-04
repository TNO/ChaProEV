from datetime import datetime

import numpy as np
import polars as pl
from box import Box
from ETS_CookBook import ETS_CookBook as cook

from ChaProEV.stochastic_new.define import (
    ChargingBehaviour,
    Location,
    TimeConstants,
    TimeRange,
    User,
    Vehicle,
)


# def compute_charging_step(
#     *


# emergency fast charge: shift DF (then mobility is out of date, so document that)
# or chnage loc to fast station for e.g. 15 minutes (compute based on charge needed)
# then replace next 15 minutes by road (but what if within less than 15min of next stop?)
# concurrent user charging
# or batch users


# @cook.function_timer
def compute_charging(
    *,
    charging_behaviour: ChargingBehaviour,
    charge: pl.DataFrame,
    charging_settings: Box,
    vehicle: Vehicle,
    scenario: Box,
    locations: dict[str, Location],
) -> pl.DataFrame:

    time_index_name: str = charging_settings.time_index_name
    modulation_factor_header: str = charging_settings.modulation_factor_header
    location_header: str = charging_settings.location_header
    connectivity_header: str = charging_settings.connectivity_header
    session_header: str = charging_settings.session_header
    can_charge_header: str = charging_settings.can_charge_header
    wants_to_charge_header: str = charging_settings.wants_to_charge_header
    does_charge_header: str = charging_settings.does_charge_header
    battery_level_header: str = charging_settings.battery_level_header
    nominal_charge_power_to_vehicle_header: str = (
        charging_settings.nominal_charge_power_to_vehicle_header
    )
    nominal_charge_power_from_network_header: str = (
        charging_settings.nominal_charge_power_from_network_header
    )
    nominal_discharge_power_from_vehicle_header: str = (
        charging_settings.nominal_discharge_power_from_vehicle_header
    )
    nominal_discharge_power_to_network_header: str = (
        charging_settings.nominal_discharge_power_to_network_header
    )

    available_charge_power_to_vehicle_header: str = (
        charging_settings.available_charge_power_to_vehicle_header
    )
    available_charge_power_from_network_header: str = (
        charging_settings.available_charge_power_from_network_header
    )
    available_discharge_power_from_vehicle_header: str = (
        charging_settings.available_discharge_power_from_vehicle_header
    )
    available_discharge_power_to_network_header: str = (
        charging_settings.available_discharge_power_to_network_header
    )

    power_to_vehicle_header: str = charging_settings.power_to_vehicle_header
    power_from_network_header: str = (
        charging_settings.power_from_network_header
    )
    charge_to_vehicle_header: str = charging_settings.charge_to_vehicle_header
    charge_from_network_header: str = (
        charging_settings.charge_from_network_header
    )
    session_start_header: str = charging_settings.session_start_header
    consumption_header: str = charging_settings.consumption_header
    session_duration_header: str = charging_settings.session_duration_header
    electricity_spending_header: str = (
        charging_settings.electricity_spending_header
    )
    driving_location_name: str = vehicle.driving_location_name
    battery_capacity_kWh: float = vehicle.battery_size_kWh
    charge_desire_proportion_trigger: float = (
        charging_behaviour.charge_desire_proportion_trigger
    )
    charge_stop_proportion_trigger: float = (
        charging_behaviour.charge_stop_proportion_trigger
    )
    battery_charge_levels_kWh: list[float] = []
    current_battery_level_kWh: float = battery_capacity_kWh
    power_drawn_from_network_kW: list[float] = []
    power_to_vehicle_kW: list[float] = []

    time_constants: TimeConstants = TimeConstants.read_parameters(
        scenario.time
    )
    run_parameters: Box = scenario.run
    time_ranges: TimeRange = TimeRange.set_ranges(
        run_parameters=run_parameters,
        time_constants=time_constants,
    )

    MINUTES_PER_HOUR: int = time_constants.MINUTES_PER_HOUR

    if time_ranges.frequency_type != 'm':
        raise ValueError('You need to use minutes for the frequency!')
    run_frequency_size: int = time_ranges.frequency_size
    run_time_resolution_hours: float = run_frequency_size / MINUTES_PER_HOUR

    wants_to_charge: bool = (
        current_battery_level_kWh
        < charge_desire_proportion_trigger * battery_capacity_kWh
    )
    # print(charge_desire_proportion_trigger * battery_capacity_kWh)
    # print(battery_capacity_kWh)
    # exit()
    battery_space_at_session_start_kWh: float = (
        battery_capacity_kWh - current_battery_level_kWh
    )
    previous_step_power_to_vehicle_kW: float = 0
    previous_step_power_drawn_from_network_kW: float = 0

    for (
        can_charge,
        consumption,
        session_start,
        session_duration,
        available_charge_power_to_vehicle,
        available_charge_power_from_network,
    ) in zip(
        charge[can_charge_header],
        charge[consumption_header],
        charge[session_start_header],
        charge[session_duration_header],
        charge[available_charge_power_to_vehicle_header],
        charge[available_charge_power_from_network_header],
    ):

        current_battery_level_kWh -= consumption
        if current_battery_level_kWh < 0:
            raise ValueError(
                'Battery level is negative! '
                'This can for xample happen if your base connctivity is too'
                'low, which can lead to a situation where a vehicle drives'
                'and wants to charge, but cannot.'
            )

        # The quantities we track are only updated if we can charge
        if can_charge:

            if session_start:
                # If there is a new session, we check if the user wants
                # to charge. We do this one time, because if we did during the
                # session, the battery might go above the threshold at
                # which the user wants to charge, but still below the maximal
                # charge they want (charge_stop_proortion_trigger).
                wants_to_charge = (
                    current_battery_level_kWh
                    < charge_desire_proportion_trigger * battery_capacity_kWh
                )
                # We also need the battery space at session start
                # for adaptive charging
                battery_space_at_session_start_kWh = (
                    battery_capacity_kWh - current_battery_level_kWh
                )

                if charging_behaviour.adaptive:
                    charger_efficiency: float = (
                        available_charge_power_to_vehicle
                        / available_charge_power_from_network
                    )
                    desired_power_to_vehicle_kW: float = (
                        battery_space_at_session_start_kWh / session_duration
                    )
                    desired_power_from_network: float = (
                        desired_power_to_vehicle_kW / charger_efficiency
                    )
                    this_step_power_drawn_from_network_kW: float = min(
                        available_charge_power_to_vehicle,
                        desired_power_from_network,
                    )
                    this_step_power_to_vehicle_kW: float = (
                        this_step_power_drawn_from_network_kW
                        * charger_efficiency
                    )
                else:
                    this_step_power_drawn_from_network_kW = (
                        available_charge_power_from_network
                    )
                    this_step_power_to_vehicle_kW = (
                        available_charge_power_to_vehicle
                    )
            else:
                this_step_power_to_vehicle_kW = (
                    previous_step_power_to_vehicle_kW
                )
                this_step_power_drawn_from_network_kW = (
                    previous_step_power_drawn_from_network_kW
                )
            if wants_to_charge:
                charge_to_vehicle_kWh: float = (
                    this_step_power_to_vehicle_kW * run_time_resolution_hours
                )

                if (
                    current_battery_level_kWh + charge_to_vehicle_kWh
                    >= battery_capacity_kWh * charge_stop_proportion_trigger
                ):
                    # If we exceed the charge stop level (100% or lower,
                    # set in charging behaviour), the user does not want
                    # to charge anymore. The charge drawn during the session
                    # might have gone higher than the maximum,
                    # so we need to scale back (essentially stop partly during
                    # the step).
                    wants_to_charge = False

                    excess_factor: float = charge_to_vehicle_kWh / (
                        battery_capacity_kWh * charge_stop_proportion_trigger
                        - current_battery_level_kWh
                    )
                    this_step_power_drawn_from_network_kW /= excess_factor
                    this_step_power_to_vehicle_kW /= excess_factor
            else:
                this_step_power_to_vehicle_kW = 0
                this_step_power_drawn_from_network_kW = 0
        else:
            this_step_power_to_vehicle_kW = 0
            this_step_power_drawn_from_network_kW = 0

        # Now that we know how much power was drawn,
        # we can update the battery level
        current_battery_level_kWh += (
            this_step_power_to_vehicle_kW * run_time_resolution_hours
        )

        # And add the values we track to our trackers
        battery_charge_levels_kWh.append(current_battery_level_kWh)
        power_to_vehicle_kW.append(this_step_power_to_vehicle_kW)
        power_drawn_from_network_kW.append(
            this_step_power_drawn_from_network_kW
        )

        previous_step_power_to_vehicle_kW = this_step_power_to_vehicle_kW
        previous_step_power_drawn_from_network_kW = (
            this_step_power_drawn_from_network_kW
        )
    # print(power_drawn_from_network_kW)
    charge = charge.with_columns(
        pl.Series(
            name=battery_level_header,
            values=battery_charge_levels_kWh,
            dtype=pl.Float64,
        ),
        pl.Series(
            name=power_to_vehicle_header,
            values=power_to_vehicle_kW,
            dtype=pl.Float64,
        ),
        pl.Series(
            name=power_from_network_header,
            values=power_drawn_from_network_kW,
            dtype=pl.Float64,
        ),
    )
    charge = charge.with_columns(
        (pl.col(power_from_network_header) * run_time_resolution_hours).alias(
            charge_from_network_header
        ),
        (pl.col(power_to_vehicle_header) * run_time_resolution_hours).alias(
            charge_to_vehicle_header
        ),
    )

    location_hourly_charging_prices: dict[str, list[float]] = {
        location_name: locations[location_name].charging_price_eur_kWh
        for location_name in locations
    }
    location_hourly_charging_prices[vehicle.driving_location_name] = [
        0
    ] * time_constants.HOURS_IN_A_DAY

    charge = (
        charge.with_columns(
            pl.col(location_header)
            .replace_strict(location_hourly_charging_prices)
            .alias('Hourly charging prices')
        )
        .with_columns(
            pl.col('Hourly charging prices')
            .list.get(pl.col(time_index_name).dt.hour())
            .alias('Cost (€/kWh)'),
        )
        .with_columns(
            (
                pl.col(charge_from_network_header) * pl.col('Cost (€/kWh)')
            ).alias(electricity_spending_header)
        )
    ).drop('Hourly charging prices', 'Cost (€/kWh)')

    return charge


# DO WE ACTUALLY NEED DOESS CHARGE?????
# IF WE FILTER ON CAN CHARGE< MAybe NOT


# for
#     time_stamp, can_charge, consumption, session_duration,
# available_charge_power_to_vehicle,
# available_charge_power_to_vehicle

# @cook.function_timer
# def compute_charging

# step_index (though maybe first stime stamp or a bool that is done first)

# Maybe have


# We initialised previous_loation_name to 'Not relevant before first step'
# so the check previous_location_name == driving will fail

# so no need for step_index

# Have this below function for each step

# current_battery_level_kWh -= consumption
# if current_battery_level_kWh < 0:
#     raise ValueError('Baatery level is negative!')

# this_step_power_to_vehicle_kW: float = 0
# this_step_power_drawn_from_network_kW: float = 0
# ...

# if can_charge
#     if session start:
#         set wants_to_charge and space_at_start

#     if wants_to_charge:
#         ....


# Less tests
# if can_charge:
#     wants_to_charge: bool = hdsjd NO! Wants is set at session start. Otherwise it switches WHILE CHARGINGE
#     FLIP ONLY IF FULL (or max batt level)


#     if wants_to_charge:
#         power_to_)veh=...
#         power_from_net = ...

# WE DO NEED battery_space_at_session_start_kWh

# Maybe with Session start bool parameters (also false if road) Initialised at (value from scenario)


# If xxx --> compute wants and can (and does)

# if does --> power dance (separate function)

# ....
# current_battery_level_kWh += this_step_power_to_vehicle_kW * run_time_resolution_hours

# (and discharge?)


#  battery_charge_levels_kWh.append(current_battery_level_kWh)
# power_to_vehicle_kW.append(this_step_power_to_vehicle_kW)
# power_drawn_from_network_kW.append(this_step_power_drawn_from_network_kW)
# previous_location_name = location_name


# vectorisation __path__
# start with DF   that also has can charge, wants to charge, does charge

# if road --> power drawn and power to car are zero also can charge is False
# identify road --> parking steps
# here can_charge can be computed/vectorized (with random draws)
# Propafares down to departure <-- How to manage?

# If we get a way to do can charge in advance.vectorally that would help
# DOCUMENT IT SAY THAT WE DO NOT NEED TO actually draw when it occurs (INCLUDING IF DRAW DEPENDS ON TIME STAMP <--COOL FEATURE TO placeholder)
# If not doinf discharge, no need to propagate, as we only test at arrival
# But we want discharge (evntually), so explore that

# KEY= session ID (driven by transitions) Then can_charge(session_ID, location ) as a funcrion
# Better name for session_ID

# df = df.with_columns(
#     (
#         pl.col("Location") != pl.col("Location").shift(1)
#     )
#     .fill_null(True)
#     .cum_sum()
#     .alias("Location ID")
# )


# location_blocks = df.group_by("Location ID", maintain_order=True).agg(
#     pl.col("Connectivity").first()
# )

# can_connect = (
#     random_generator.random(location_blocks.height)
#     < location_blocks["Connectivity"].to_numpy()
# )

# location_blocks = location_blocks.with_columns(
#     pl.Series("Can connect", can_connect)
# )

# df = df.join(
#     location_blocks.select("Location ID", "Can connect"),
#     on="Location ID",
#     how="left",
# )

# We also have hours at location from mobility (copy it to DF)

# Use that for road --> park too?


# Add nominal and availavle power to Charge DF (from net and to veh) (nominal --> available: through modulation)
# also dischgarge
