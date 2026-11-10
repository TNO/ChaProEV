import uuid
from dataclasses import dataclass

import polars as pl
from box import Box

from ChaProEV.stochastic_new.define import User

# class GrisStatus


@dataclass
class PreCharge:
    locations: pl.Series
    kilometers_driven_run: pl.Series
    consumptions: pl.Series
    can_charge_run: pl.Series
    session_starts: pl.Series
    session_durations_hours: pl.Series
    available_charge_powers_to_vehicle: pl.Series
    available_charge_powers_from_network: pl.Series

    def initialise(*, user: User, scenario: Box) -> PreCharge:

        charging_settings: Box = scenario.charging_dataframe
        location_header: str = charging_settings.location_header
        can_charge_header: str = charging_settings.can_charge_header

        available_charge_power_to_vehicle_header: str = (
            charging_settings.available_charge_power_to_vehicle_header
        )
        available_charge_power_from_network_header: str = (
            charging_settings.available_charge_power_from_network_header
        )
        driven_header: str = charging_settings.driven_header
        session_start_header: str = charging_settings.session_start_header
        consumption_header: str = charging_settings.consumption_header
        session_duration_header: str = (
            charging_settings.session_duration_header
        )

        return PreCharge(
            locations=user.charge[location_header],
            kilometers_driven_run=user.charge[driven_header],
            consumptions=user.charge[consumption_header],
            can_charge_run=user.charge[can_charge_header],
            session_starts=user.charge[session_start_header],
            session_durations_hours=user.charge[session_duration_header],
            available_charge_powers_to_vehicle=user.charge[
                available_charge_power_to_vehicle_header
            ],
            available_charge_powers_from_network=user.charge[
                available_charge_power_from_network_header
            ],
        )


@dataclass
class TrackingVariables:
    run_locations: list[str]  # We have to retrack these if using fast
    # charging
    run_kilometers_driven: list[float]  # Same as run_locations
    run_consumptions: list[float]  # Same as locations and kilometers
    power_drawn_from_network_kW: list[float]
    power_to_vehicle_kW: list[float]
    battery_charge_levels_kWh: list[float]
    current_battery_level_kWh: float
    wants_to_charge: bool
    previous_step_power_to_vehicle_kW: float
    previous_step_power_drawn_from_network_kW: float
    at_fast_station: bool
    catching_up: bool
    catch_up_locations: list[str]
    catch_up_kilometers_driven: list[float]
    catch_up_consumptions: list[float]
    buffer_steps: int
    catch_up_steps: int

    @staticmethod
    def initialise(*, user: User) -> TrackingVariables:

        run_locations: list[str] = []  # We have to retrack these if using fast
        # charging
        run_kilometers_driven: list[float] = []  # Same as run_locations
        run_consumptions: list[float] = []  # Same as locations and kilometers
        power_drawn_from_network_kW: list[float] = []
        power_to_vehicle_kW: list[float] = []
        battery_charge_levels_kWh: list[float] = []

        current_battery_level_kWh: float = user.vehicle.battery_size_kWh

        wants_to_charge: bool = (
            current_battery_level_kWh
            < user.vehicle.battery_size_kWh
            * user.charging_behaviour.charge_desire_proportion_trigger
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

        return TrackingVariables(
            run_locations=run_locations,
            run_kilometers_driven=run_kilometers_driven,
            run_consumptions=run_consumptions,
            power_drawn_from_network_kW=power_drawn_from_network_kW,
            power_to_vehicle_kW=power_to_vehicle_kW,
            battery_charge_levels_kWh=battery_charge_levels_kWh,
            current_battery_level_kWh=current_battery_level_kWh,
            wants_to_charge=wants_to_charge,
            previous_step_power_to_vehicle_kW=(
                previous_step_power_to_vehicle_kW
            ),
            previous_step_power_drawn_from_network_kW=(
                previous_step_power_drawn_from_network_kW
            ),
            at_fast_station=at_fast_station,
            catching_up=catching_up,
            catch_up_locations=catch_up_locations,
            catch_up_kilometers_driven=catch_up_kilometers_driven,
            catch_up_consumptions=catch_up_consumptions,
            buffer_steps=buffer_steps,
            catch_up_steps=catch_up_steps,
        )


# def charge_update(*, time_stamp: datetime, user: User) -> None:
#     print(user.vehicle.)


def compute_fleet_charging(
    *,
    users_pool: list[User],
    scenario: Box,
    run_time_resolution_hours: float,
    HOURS_IN_A_DAY: int,
) -> list[User]:
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
    tracking_pool: dict[uuid.UUID, TrackingVariables] = {
        user.ID: TrackingVariables.initialise(user=user) for user in users_pool
    }
    pre_charge_pool: dict[uuid.UUID, PreCharge] = {
        user.ID: PreCharge.initialise(user=user, scenario=scenario)
        for user in users_pool
    }
    for user in users_pool:
        print(user.ID)
        compute_charging(
            user=user,
            scenario=scenario,
            tracking=tracking_pool[user.ID],
            pre_charge=pre_charge_pool[user.ID],
            run_time_resolution_hours=run_time_resolution_hours,
            HOURS_IN_A_DAY=HOURS_IN_A_DAY,
        )
        user.run_metrics.charge_update(
            charge_dataframe=user.charge,
            charging_settings=scenario.charging_dataframe,
            locations=user.locations,
        )

    return users_pool


def write_charge_to_user(
    *,
    user: User,
    tracking: TrackingVariables,
    scenario: Box,
    run_time_resolution_hours: float,
    HOURS_IN_A_DAY: int,
) -> User:

    charging_settings: Box = scenario.charging_dataframe
    time_index_name: str = charging_settings.time_index_name
    location_header: str = charging_settings.location_header
    driven_header: str = charging_settings.driven_header
    consumption_header: str = charging_settings.consumption_header
    battery_level_header: str = charging_settings.battery_level_header
    power_to_vehicle_header: str = charging_settings.power_to_vehicle_header
    power_from_network_header: str = (
        charging_settings.power_from_network_header
    )
    charge_to_vehicle_header: str = charging_settings.charge_to_vehicle_header
    charge_from_network_header: str = (
        charging_settings.charge_from_network_header
    )
    electricity_spending_header: str = (
        charging_settings.electricity_spending_header
    )

    new_charge: pl.DataFrame = user.charge.select(time_index_name)

    new_charge = new_charge.with_columns(
        pl.Series(
            name=location_header,
            values=tracking.run_locations,
            dtype=pl.String,
        ),
        pl.Series(
            name=driven_header,
            values=tracking.run_kilometers_driven,
            dtype=pl.Float64,
        ),
        pl.Series(
            name=consumption_header,
            values=tracking.run_consumptions,
            dtype=pl.Float64,
        ),
        pl.Series(
            name=battery_level_header,
            values=tracking.battery_charge_levels_kWh,
            dtype=pl.Float64,
        ),
        pl.Series(
            name=power_to_vehicle_header,
            values=tracking.power_to_vehicle_kW,
            dtype=pl.Float64,
        ),
        pl.Series(
            name=power_from_network_header,
            values=tracking.power_drawn_from_network_kW,
            dtype=pl.Float64,
        ),
    )

    new_charge = new_charge.with_columns(
        (pl.col(power_from_network_header) * run_time_resolution_hours).alias(
            charge_from_network_header
        ),
        (pl.col(power_to_vehicle_header) * run_time_resolution_hours).alias(
            charge_to_vehicle_header
        ),
    )

    location_hourly_charging_prices: dict[str, list[float]] = {
        location_name: user.locations[location_name].charging_price_eur_kWh
        for location_name in user.locations
    }
    location_hourly_charging_prices[user.vehicle.driving_location_name] = [
        0
    ] * HOURS_IN_A_DAY

    new_charge = (
        new_charge.with_columns(
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

    user.charge = new_charge
    return user


# @cook.function_timer
def compute_charging(
    *,
    user: User,
    scenario: Box,
    tracking: TrackingVariables,
    pre_charge: PreCharge,
    run_time_resolution_hours: float,
    HOURS_IN_A_DAY: int,
) -> User:

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
        pre_charge.locations,
        pre_charge.kilometers_driven_run,
        pre_charge.consumptions,
        pre_charge.can_charge_run,
        pre_charge.session_starts,
        pre_charge.session_durations_hours,
        pre_charge.available_charge_powers_to_vehicle,
        pre_charge.available_charge_powers_from_network,
    ):

        if (
            tracking.current_battery_level_kWh - consumption
            <= user.charging_behaviour.fast_charge_desire_proportion_trigger
            * user.vehicle.battery_size_kWh
        ):
            if not tracking.at_fast_station and not tracking.catching_up:
                tracking.at_fast_station = True

        if tracking.at_fast_station:
            tracking.catch_up_locations.append(location)
            tracking.catch_up_consumptions.append(consumption)
            tracking.catch_up_kilometers_driven.append(kilometers_driven)
            location = user.vehicle.fast_charging_location_name
            consumption = 0.0
            kilometers_driven = 0.0
            remaining_energy_to_supply_kWh: float = (
                user.charging_behaviour.fast_charge_stop_proportion_trigger
                * user.vehicle.battery_size_kWh
                - tracking.current_battery_level_kWh
            )
            this_step_power_to_vehicle_kW = min(
                user.locations[
                    user.vehicle.fast_charging_location_name
                ].charging_power_kW
                * user.locations[
                    user.vehicle.fast_charging_location_name
                ].charger_efficiency,
                remaining_energy_to_supply_kWh / run_time_resolution_hours,
            )
            this_step_power_drawn_from_network_kW = (
                this_step_power_to_vehicle_kW
                / user.locations[
                    user.vehicle.fast_charging_location_name
                ].charger_efficiency
            )

        elif tracking.catching_up:
            location = tracking.catch_up_locations[
                tracking.buffer_steps - tracking.catch_up_steps
            ]
            consumption = tracking.catch_up_consumptions[
                tracking.buffer_steps - tracking.catch_up_steps
            ]
            kilometers_driven = tracking.catch_up_kilometers_driven[
                tracking.buffer_steps - tracking.catch_up_steps
            ]
            # Normal charging is deliberately disabled while replaying delayed
            # mobility. This assumes that the short delay does not contain a
            # material normal-charging opportunity.
            this_step_power_drawn_from_network_kW = 0.0
            this_step_power_to_vehicle_kW = 0.0
            tracking.catch_up_steps -= 1
            if tracking.catch_up_steps == 0:
                tracking.catching_up = False
                tracking.catch_up_locations = []
                tracking.catch_up_kilometers_driven = []
                tracking.catch_up_consumptions = []

        # The quantities we track are only updated if we can charge
        elif can_charge:

            if session_start:
                # If there is a new session, we check if the user wants
                # to charge. We do this one time, because if we did during the
                # session, the battery might go above the threshold at
                # which the user wants to charge, but still below the maximal
                # charge they want (charge_stop_proportion_trigger).
                tracking.wants_to_charge = (
                    tracking.current_battery_level_kWh
                    < user.charging_behaviour.charge_desire_proportion_trigger
                    * user.vehicle.battery_size_kWh
                )

                if user.charging_behaviour.adaptive:
                    charger_efficiency: float = (
                        available_charge_power_to_vehicle
                        / available_charge_power_from_network
                    )
                    energy_required_at_session_start_kWh: float = max(
                        0.0,
                        user.charging_behaviour.charge_stop_proportion_trigger
                        * user.vehicle.battery_size_kWh
                        - tracking.current_battery_level_kWh,
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
                    tracking.previous_step_power_to_vehicle_kW
                )
                this_step_power_drawn_from_network_kW = (
                    tracking.previous_step_power_drawn_from_network_kW
                )
            if tracking.wants_to_charge:
                charge_to_vehicle_kWh: float = (
                    this_step_power_to_vehicle_kW * run_time_resolution_hours
                )

                if (
                    tracking.current_battery_level_kWh + charge_to_vehicle_kWh
                    >= user.charging_behaviour.charge_stop_proportion_trigger
                    * user.vehicle.battery_size_kWh
                ):
                    # If we exceed the charge stop level (100% or lower,
                    # set in charging behaviour), the user does not want
                    # to charge anymore. The charge drawn during the session
                    # might have gone higher than the maximum,
                    # so we need to scale back (essentially stop partly during
                    # the step).
                    tracking.wants_to_charge = False

                    excess_factor: float = charge_to_vehicle_kWh / (
                        user.charging_behaviour.charge_stop_proportion_trigger
                        * user.vehicle.battery_size_kWh
                        - tracking.current_battery_level_kWh
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
        tracking.current_battery_level_kWh += (
            this_step_power_to_vehicle_kW * run_time_resolution_hours
            - consumption
        )

        if (
            tracking.at_fast_station
            and tracking.current_battery_level_kWh
            >= user.charging_behaviour.fast_charge_stop_proportion_trigger
            * user.vehicle.battery_size_kWh
        ):
            tracking.at_fast_station = False
            tracking.catching_up = True
            tracking.catch_up_steps = len(tracking.catch_up_locations)
            tracking.buffer_steps = len(tracking.catch_up_locations)

        if tracking.current_battery_level_kWh < 0:
            raise ValueError(
                'Battery level is negative! '
                'This can for example happen if your base connectivity is too '
                'low, which can lead to a situation where a vehicle drives '
                'and wants to charge, but cannot.'
            )

        # And add the values we track to our trackers
        tracking.run_locations.append(location)
        tracking.run_kilometers_driven.append(kilometers_driven)
        tracking.run_consumptions.append(consumption)
        tracking.battery_charge_levels_kWh.append(
            tracking.current_battery_level_kWh
        )
        tracking.power_to_vehicle_kW.append(this_step_power_to_vehicle_kW)
        tracking.power_drawn_from_network_kW.append(
            this_step_power_drawn_from_network_kW
        )

        tracking.previous_step_power_to_vehicle_kW = (
            this_step_power_to_vehicle_kW
        )
        tracking.previous_step_power_drawn_from_network_kW = (
            this_step_power_drawn_from_network_kW
        )

    user = write_charge_to_user(
        user=user,
        tracking=tracking,
        scenario=scenario,
        run_time_resolution_hours=run_time_resolution_hours,
        HOURS_IN_A_DAY=HOURS_IN_A_DAY,
    )
    return user
