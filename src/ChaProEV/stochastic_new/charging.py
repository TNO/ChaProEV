import polars as pl
from box import Box

from ChaProEV.stochastic_new.define import (
    ChargingBehaviour,
    Location,
    TimeConstants,
    TimeRange,
    Vehicle,
)

# def compute_charging_step(
#     *


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
    location_header: str = charging_settings.location_header
    can_charge_header: str = charging_settings.can_charge_header
    battery_level_header: str = charging_settings.battery_level_header

    available_charge_power_to_vehicle_header: str = (
        charging_settings.available_charge_power_to_vehicle_header
    )
    available_charge_power_from_network_header: str = (
        charging_settings.available_charge_power_from_network_header
    )

    power_to_vehicle_header: str = charging_settings.power_to_vehicle_header
    power_from_network_header: str = (
        charging_settings.power_from_network_header
    )
    charge_to_vehicle_header: str = charging_settings.charge_to_vehicle_header
    charge_from_network_header: str = (
        charging_settings.charge_from_network_header
    )
    driven_header: str = charging_settings.driven_header
    session_start_header: str = charging_settings.session_start_header
    consumption_header: str = charging_settings.consumption_header
    session_duration_header: str = charging_settings.session_duration_header
    electricity_spending_header: str = (
        charging_settings.electricity_spending_header
    )
    fast_charging_location_name: str = vehicle.fast_charging_location_name
    battery_capacity_kWh: float = vehicle.battery_size_kWh
    charge_desire_proportion_trigger: float = (
        charging_behaviour.charge_desire_proportion_trigger
    )
    charge_stop_proportion_trigger: float = (
        charging_behaviour.charge_stop_proportion_trigger
    )
    charge_desire_trigger_kWh: float = (
        charge_desire_proportion_trigger * vehicle.battery_size_kWh
    )
    charge_stop_trigger_kWh: float = (
        charge_stop_proportion_trigger * vehicle.battery_size_kWh
    )

    fast_charge_desire_proportion_trigger: float = (
        charging_behaviour.fast_charge_desire_proportion_trigger
    )
    fast_charge_stop_proportion_trigger: float = (
        charging_behaviour.fast_charge_stop_proportion_trigger
    )

    fast_charge_desire_trigger_kWh: float = (
        fast_charge_desire_proportion_trigger * vehicle.battery_size_kWh
    )
    fast_charge_stop_trigger_kWh: float = (
        fast_charge_stop_proportion_trigger * vehicle.battery_size_kWh
    )
    fast_charging_location_name: str = vehicle.fast_charging_location_name

    fast_charging_power_from_network: float = locations[
        fast_charging_location_name
    ].charging_power_kW
    fast_charging_power_to_vehicle: float = (
        locations[fast_charging_location_name].charging_power_kW
        * locations[fast_charging_location_name].charger_efficiency
    )

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

    # print(charge_desire_proportion_trigger * battery_capacity_kWh)
    # print(battery_capacity_kWh)
    # exit()

    run_locations: list[str] = []  # We have to retrack these if using fast
    # charging
    run_kilometers_driven: list[float] = []  # Same as run_locations
    run_consumptions: list[float] = []  # Same as locations and kilometers
    power_drawn_from_network_kW: list[float] = []
    power_to_vehicle_kW: list[float] = []
    battery_charge_levels_kWh: list[float] = []

    current_battery_level_kWh: float = battery_capacity_kWh
    wants_to_charge: bool = (
        current_battery_level_kWh < charge_desire_trigger_kWh
    )

    battery_space_at_session_start_kWh: float = (
        battery_capacity_kWh - current_battery_level_kWh
    )
    previous_step_power_to_vehicle_kW: float = 0
    previous_step_power_drawn_from_network_kW: float = 0
    at_fast_station: bool = False
    catching_up: bool = False
    catch_up_locations: list[str] = []
    catch_up_kilometers_driven: list[float] = []
    catch_up_consumptions: list[float] = []
    fast_charging_duration_minutes: int = 0
    buffer_minutes: int = 0
    catching_up_minutes: int = 0

    for (
        location,
        kilometers_driven,
        consumption,
        can_charge,
        session_start,
        session_duration,
        available_charge_power_to_vehicle,
        available_charge_power_from_network,
    ) in zip(
        charge[location_header],
        charge[driven_header],
        charge[consumption_header],
        charge[can_charge_header],
        charge[session_start_header],
        charge[session_duration_header],
        charge[available_charge_power_to_vehicle_header],
        charge[available_charge_power_from_network_header],
    ):

        current_battery_level_kWh -= consumption

        if current_battery_level_kWh < 0:
            raise ValueError(
                'Battery level is negative! '
                'This can for example happen if your base connectivity is too'
                'low, which can lead to a situation where a vehicle drives'
                'and wants to charge, but cannot.'
            )
        if current_battery_level_kWh <= fast_charge_desire_trigger_kWh:
            if not at_fast_station and not catching_up:
                fast_charging_duration_minutes = int(
                    MINUTES_PER_HOUR
                    * (
                        fast_charge_stop_trigger_kWh
                        - current_battery_level_kWh
                    )
                    / fast_charging_power_to_vehicle
                )  # int rather than round, because we want to avoid going over
                # The stop limit (especially if that one is 100% of the
                # battery capacity.
                buffer_minutes = fast_charging_duration_minutes
                catching_up_minutes: int = buffer_minutes
                at_fast_station = True

        # The quantities we track are only updated if we can charge
        if can_charge:

            if session_start:
                # If there is a new session, we check if the user wants
                # to charge. We do this one time, because if we did during the
                # session, the battery might go above the threshold at
                # which the user wants to charge, but still below the maximal
                # charge they want (charge_stop_proortion_trigger).
                wants_to_charge = (
                    current_battery_level_kWh < charge_desire_trigger_kWh
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
                    >= charge_stop_trigger_kWh
                ):
                    # If we exceed the charge stop level (100% or lower,
                    # set in charging behaviour), the user does not want
                    # to charge anymore. The charge drawn during the session
                    # might have gone higher than the maximum,
                    # so we need to scale back (essentially stop partly during
                    # the step).
                    wants_to_charge = False

                    excess_factor: float = charge_to_vehicle_kWh / (
                        charge_stop_trigger_kWh - current_battery_level_kWh
                    )
                    this_step_power_drawn_from_network_kW /= excess_factor
                    this_step_power_to_vehicle_kW /= excess_factor
            else:
                this_step_power_to_vehicle_kW = 0
                this_step_power_drawn_from_network_kW = 0
        else:
            this_step_power_to_vehicle_kW = 0
            this_step_power_drawn_from_network_kW = 0

        if at_fast_station:
            catch_up_locations.append(location)
            catch_up_consumptions.append(consumption)
            catch_up_kilometers_driven.append(kilometers_driven)
            location = fast_charging_location_name
            consumption = 0.0
            kilometers_driven = 0.0
            this_step_power_to_vehicle_kW = fast_charging_power_to_vehicle
            this_step_power_drawn_from_network_kW = (
                fast_charging_power_from_network
            )
            fast_charging_duration_minutes -= 1

            if fast_charging_duration_minutes == 0:
                at_fast_station = False
                catching_up = True

        if catching_up:
            location = catch_up_locations[buffer_minutes - catching_up_minutes]
            consumption = catch_up_consumptions[
                buffer_minutes - catching_up_minutes
            ]
            kilometers_driven = catch_up_kilometers_driven[
                buffer_minutes - catching_up_minutes
            ]
            # Catching up is either on the road
            # or (assumption) with a battery level higher than
            # the trigger for normal charging
            this_step_power_drawn_from_network_kW = 0.0
            this_step_power_to_vehicle_kW = 0.0
            catching_up_minutes -= 1
            if catching_up_minutes == 0:
                catching_up = False
                catch_up_locations = []
                catch_up_kilometers_driven = []
                catch_up_consumptions = []

        # Now that we know how much power was drawn,
        # we can update the battery level
        current_battery_level_kWh += (
            this_step_power_to_vehicle_kW * run_time_resolution_hours
        )

        # And add the values we track to our trackers
        run_locations.append(location)
        run_kilometers_driven.append(kilometers_driven)
        run_consumptions.append(consumption)
        battery_charge_levels_kWh.append(current_battery_level_kWh)
        power_to_vehicle_kW.append(this_step_power_to_vehicle_kW)
        power_drawn_from_network_kW.append(
            this_step_power_drawn_from_network_kW
        )

        previous_step_power_to_vehicle_kW = this_step_power_to_vehicle_kW
        previous_step_power_drawn_from_network_kW = (
            this_step_power_drawn_from_network_kW
        )

    charge = charge.select(time_index_name)

    charge = charge.with_columns(
        pl.Series(name=location_header, values=run_locations, dtype=pl.String),
        pl.Series(
            name=driven_header, values=run_kilometers_driven, dtype=pl.Float64
        ),
        pl.Series(
            name=consumption_header, values=run_consumptions, dtype=pl.Float64
        ),
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
