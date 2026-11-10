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
    '''
    This includes fast charging, used if the battery level goes too low.
    That can be an issue if the connectivity at base is lower than one.
    Fast-charging events are as follows:
    The user notices that the battery is very low, so they stop
    at a fast charging station, delaying their arrival at their next
    destination. We buffer these and catch them up later.
    Some mobility events might occur after the end of the run
    because of a fast-charging shift. This is okay because
    we are looking at charging events within the run and
    mobility after the run end is not in scope.
    Also, this is a small issue, as the shift is of the order of 15 minutes
    and travel on the night of December 31st is not likely to be large.
    '''

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

    previous_step_power_to_vehicle_kW: float = 0
    previous_step_power_drawn_from_network_kW: float = 0
    at_fast_station: bool = False
    catching_up: bool = False
    catch_up_locations: list[str] = []
    catch_up_kilometers_driven: list[float] = []
    catch_up_consumptions: list[float] = []
    buffer_steps: int = 0
    catch_up_steps: int = 0

    for (
        location,
        kilometers_driven,
        consumption,
        can_charge,
        session_start,
        session_duration_hours,
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

        if (
            current_battery_level_kWh - consumption
            <= fast_charge_desire_trigger_kWh
        ):
            if not at_fast_station and not catching_up:
                at_fast_station = True

        if at_fast_station:
            catch_up_locations.append(location)
            catch_up_consumptions.append(consumption)
            catch_up_kilometers_driven.append(kilometers_driven)
            location = fast_charging_location_name
            consumption = 0.0
            kilometers_driven = 0.0
            remaining_energy_to_supply_kWh: float = (
                fast_charge_stop_trigger_kWh - current_battery_level_kWh
            )
            this_step_power_to_vehicle_kW = min(
                fast_charging_power_to_vehicle,
                remaining_energy_to_supply_kWh / run_time_resolution_hours,
            )
            this_step_power_drawn_from_network_kW = (
                this_step_power_to_vehicle_kW
                / locations[fast_charging_location_name].charger_efficiency
            )

        elif catching_up:
            location = catch_up_locations[buffer_steps - catch_up_steps]
            consumption = catch_up_consumptions[buffer_steps - catch_up_steps]
            kilometers_driven = catch_up_kilometers_driven[
                buffer_steps - catch_up_steps
            ]
            # Normal charging is deliberately disabled while replaying delayed
            # mobility. This assumes that the short delay does not contain a
            # material normal-charging opportunity.
            this_step_power_drawn_from_network_kW = 0.0
            this_step_power_to_vehicle_kW = 0.0
            catch_up_steps -= 1
            if catch_up_steps == 0:
                catching_up = False
                catch_up_locations = []
                catch_up_kilometers_driven = []
                catch_up_consumptions = []

        # The quantities we track are only updated if we can charge
        elif can_charge:

            if session_start:
                # If there is a new session, we check if the user wants
                # to charge. We do this one time, because if we did during the
                # session, the battery might go above the threshold at
                # which the user wants to charge, but still below the maximal
                # charge they want (charge_stop_proportion_trigger).
                wants_to_charge = (
                    current_battery_level_kWh < charge_desire_trigger_kWh
                )

                if charging_behaviour.adaptive:
                    charger_efficiency: float = (
                        available_charge_power_to_vehicle
                        / available_charge_power_from_network
                    )
                    energy_required_at_session_start_kWh: float = max(
                        0.0,
                        charge_stop_trigger_kWh - current_battery_level_kWh,
                    )

                    desired_power_to_vehicle_kW: float = (
                        energy_required_at_session_start_kWh
                        / session_duration_hours
                    )
                    desired_power_from_network: float = (
                        desired_power_to_vehicle_kW / charger_efficiency
                    )
                    this_step_power_drawn_from_network_kW: float = min(
                        available_charge_power_from_network,
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

        # Now that we know how much power was drawn,
        # we can update the battery level
        current_battery_level_kWh += (
            this_step_power_to_vehicle_kW * run_time_resolution_hours
            - consumption
        )

        if (
            at_fast_station
            and current_battery_level_kWh >= fast_charge_stop_trigger_kWh
        ):
            at_fast_station = False
            catching_up = True
            catch_up_steps = len(catch_up_locations)
            buffer_steps = len(catch_up_locations)

        if current_battery_level_kWh < 0:
            raise ValueError(
                'Battery level is negative! '
                'This can for example happen if your base connectivity is too '
                'low, which can lead to a situation where a vehicle drives '
                'and wants to charge, but cannot.'
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
