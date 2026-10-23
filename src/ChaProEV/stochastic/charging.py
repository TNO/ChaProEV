from pathlib import Path

import numpy as np
import polars as pl
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print

from ChaProEV.stochastic import auxiliary, define, mobility


@cook.function_timer
def compute_charging(
    *,
    mobility_matrix: pl.DataFrame,
    locations: dict[str, define.Location],
    scenario: Box,
    random_generator: np.random.Generator,
) -> pl.DataFrame:
    driving_location_name: str = scenario.general.driving_location_name
    battery_capacity_kWh: float = scenario.vehicle.battery_size_kWh
    charge_desire_proportion_trigger: float = (
        scenario.vehicle.charge_desire_proportion_trigger
    )
    battery_charge_levels_kWh: list[float] = []
    current_battery_level_kWh: float = battery_capacity_kWh
    power_drawn_from_network_kW: list[float] = []
    power_to_vehicle_kW: list[float] = []

    MINUTES_PER_HOUR: int = scenario.time.MINUTES_PER_HOUR

    if scenario.run.frequency.type != 'm':
        raise ValueError('You need to use minutes for the frequency!')
    run_frequency_size: int = scenario.run.frequency.size
    run_time_resolution_hours: float = run_frequency_size / MINUTES_PER_HOUR

    wants_to_charge: bool = False
    can_charge: bool = False
    does_charge: bool = False

    previous_location_name: str = 'Not relevant before first step.'

    for step_index, (
        time_stamp,
        location_name,
        consumption,
        hours_at_location,
    ) in enumerate(
        zip(
            mobility_matrix['Time Stamp'],
            mobility_matrix['Location'],
            mobility_matrix['Consumption (kWh)'],
            mobility_matrix['Time at location (hours)'],
            strict=True,
        )
    ):
        current_battery_level_kWh -= consumption
        if current_battery_level_kWh < 0:
            raise ValueError('Baatery level is negative!')

        if step_index == 0:
            battery_charge_levels_kWh.append(current_battery_level_kWh)
            power_drawn_from_network_kW.append(0)
            power_to_vehicle_kW.append(0)
            previous_location_name = location_name

        else:
            if location_name == driving_location_name:
                battery_charge_levels_kWh.append(current_battery_level_kWh)
                power_drawn_from_network_kW.append(0)
                power_to_vehicle_kW.append(0)
                previous_location_name = location_name

            else:
                location: define.Location = locations[location_name]
                if (previous_location_name == driving_location_name) and (
                    location_name != driving_location_name
                ):
                    wants_to_charge = (
                        current_battery_level_kWh
                        < charge_desire_proportion_trigger
                        * battery_capacity_kWh
                    )
                    can_charge = (
                        random_generator.random() < location.connectivity
                    )
                    does_charge = wants_to_charge and can_charge

                if does_charge:
                    battery_space_at_session_start_kWh: float = (
                        battery_capacity_kWh - current_battery_level_kWh
                    )
                    available_power_kW: float = location.charging_power_kW
                    hour_in_day: int = time_stamp.hour
                    modulation_factor: float = (
                        location.time_modulation_factors[hour_in_day]
                    )

                    available_power_kW *= modulation_factor
                    available_power_to_vehicle_kW: float = (
                        available_power_kW * location.charger_efficiency
                    )

                    if scenario.charging.adaptive:
                        desired_power_to_vehicle_kW: float = (
                            battery_space_at_session_start_kWh
                            / hours_at_location
                        )
                        desired_power_from_network: float = (
                            desired_power_to_vehicle_kW
                            / location.charger_efficiency
                        )
                        drawn_power_kW: float = min(
                            available_power_kW, desired_power_from_network
                        )
                        drawn_power_to_vehicle_kW = (
                            drawn_power_kW * location.charger_efficiency
                        )
                    else:
                        drawn_power_kW = available_power_kW
                        drawn_power_to_vehicle_kW = (
                            available_power_to_vehicle_kW
                        )

                    charge_to_vehicle: float = (
                        drawn_power_to_vehicle_kW * run_time_resolution_hours
                    )
                    if (
                        current_battery_level_kWh + charge_to_vehicle
                        >= battery_capacity_kWh
                    ):
                        wants_to_charge = False
                        does_charge = False
                        excess_factor: float = charge_to_vehicle / (
                            battery_capacity_kWh - current_battery_level_kWh
                        )
                        drawn_power_kW /= excess_factor
                        drawn_power_to_vehicle_kW /= excess_factor
                        charge_to_vehicle = (
                            battery_capacity_kWh - current_battery_level_kWh
                        )

                    current_battery_level_kWh += charge_to_vehicle
                    battery_charge_levels_kWh.append(current_battery_level_kWh)
                    power_to_vehicle_kW.append(drawn_power_to_vehicle_kW)
                    power_drawn_from_network_kW.append(drawn_power_kW)
                else:
                    battery_charge_levels_kWh.append(current_battery_level_kWh)
                    power_to_vehicle_kW.append(0)
                    power_drawn_from_network_kW.append(0)

                if (previous_location_name != driving_location_name) and (
                    location_name == driving_location_name
                ):
                    can_charge = False
                    does_charge = False

                previous_location_name = location_name

    charging_dataframe: pl.DataFrame = pl.DataFrame(
        {
            'Time Stamp': mobility_matrix['Time Stamp'],
            'Battery charge level (kWh)': battery_charge_levels_kWh,
            'Power to vehicle (kW)': power_to_vehicle_kW,
            'Power drawn from network (kW)': power_drawn_from_network_kW,
        },
        strict=False,
    )
    charging_dataframe = charging_dataframe.with_columns(
        (pl.col('Power to vehicle (kW)') * run_time_resolution_hours).alias(
            'Charge to vehicle (kWh)'
        )
    ).with_columns(
        (
            pl.col('Power drawn from network (kW)') * run_time_resolution_hours
        ).alias('Charge from network (kWh)')
    )

    return charging_dataframe


def get_hourly_values(charging_dataframe: pl.DataFrame) -> pl.DataFrame:
    hourly_values: pl.DataFrame = (
        charging_dataframe.with_columns(
            pl.col('Time Stamp').dt.hour().alias('Hour number')
        )
        .group_by('Hour number')
        .agg(
            pl.col('Power to vehicle (kW)')
            .mean()
            .alias('Average power to vehicle (kW)'),
            pl.col('Power drawn from network (kW)')
            .mean()
            .alias('Average power drawn from network (kW)'),
            pl.col('Charge to vehicle (kWh)')
            .sum()
            .alias('Cumulative charge to vehicle (kWh)'),
            pl.col('Charge from network (kWh)')
            .sum()
            .alias('Cumulative charge from network (kWh)'),
        )
        .sort('Hour number')
    )

    return hourly_values


if __name__ == '__main__':
    scenario_path: Path = Path('scenarios/plus/test.toml')
    scenario: Box = cook.parameters_from_TOML(scenario_path)
    random_generators: auxiliary.RandomGenerators = (
        auxiliary.RandomGenerators.create_generators(scenario=scenario)
    )

    (
        time_ranges,
        run_trips,
        base_trips,
        locations,
    ) = define.define_user(
        scenario=scenario, random_generator=random_generators.define
    )

    mobility_matrix: pl.DataFrame = mobility.compute_mobility_matrix(
        time_ranges=time_ranges,
        run_trips=run_trips,
        base_trips=base_trips,
        scenario=scenario,
    )

    charging_dataframe = compute_charging(
        mobility_matrix=mobility_matrix,
        locations=locations,
        scenario=scenario,
        random_generator=random_generators.charging,
    )
    print(charging_dataframe)
    print(charging_dataframe['Power to vehicle (kW)'].sum() / 60)
    # with pl.Config(tbl_rows=26):
    #     print(charging_averages)
