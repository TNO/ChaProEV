from dataclasses import dataclass
from statistics import fmean

import polars as pl
from box import Box

from ChaProEV.stochastic_new.define import User
from ChaProEV.stochastic_new.grid import LocalGrid


@dataclass
class UsersPoolStatistics:
    average_kilometrage: float
    average_consumption_kWh: float
    average_purchased_electricity_kWh: float
    average_purchased_electricity_kWh_per_location_type: dict[str, float]
    average_charge_spending_eur: float
    average_charge_spending_eur_per_location_type: dict[str, float]
    average_electricity_sold_kWh: float
    average_discharge_income_eur: float
    pool_average_hourly_power_from_grid_kW: pl.Series
    pool_average_hourly_power_from_grid_kW_per_location_type: dict[
        str, pl.Series
    ]
    pool_average_electricity_costs_eur_kWh: float
    pool_average_travel_costs_eur_km: float
    capacity_overloads: CapacityOverloads | None = None

    @classmethod
    def compute(
        cls,
        *,
        users_pool: list[User],
        location_types: list[str],
    ) -> UsersPoolStatistics:
        average_kilometrage: float = fmean(
            user.run_metrics.kilometrage for user in users_pool
        )

        average_consumption_kWh: float = fmean(
            user.run_metrics.consumption_kWh for user in users_pool
        )

        actual_location_types = {
            location_type
            for user in users_pool
            for location_type in user.run_metrics.purchased_electricity_kWh_per_location_type  # noqa:E501
        }
        assert actual_location_types <= set(
            location_types
        ), f'Missing location types: {actual_location_types - set(location_types)}'  # noqa:E501

        average_purchased_electricity_kWh: float = fmean(
            user.run_metrics.purchased_electricity_kWh for user in users_pool
        )
        average_purchased_electricity_kWh_per_location_type: dict[
            str, float
        ] = {
            location_type: fmean(
                user.run_metrics.purchased_electricity_kWh_per_location_type.get(  # noqa:E501
                    location_type, 0.0
                )
                for user in users_pool
            )
            for location_type in location_types
        }
        average_charge_spending_eur: float = fmean(
            user.run_metrics.charge_spending_eur for user in users_pool
        )
        average_charge_spending_eur_per_location_type: dict[str, float] = {
            location_type: fmean(
                user.run_metrics.charge_spending_eur_per_location_type.get(
                    location_type, 0.0
                )
                for user in users_pool
            )
            for location_type in location_types
        }

        average_electricity_sold_kWh: float = fmean(
            user.run_metrics.electricity_sold_kWh for user in users_pool
        )

        average_discharge_income_eur: float = fmean(
            user.run_metrics.discharge_income_eur for user in users_pool
        )
        pool_average_electricity_costs_eur_kWh: float = fmean(
            user.run_metrics.average_electricity_costs_eur_kWh
            for user in users_pool
        )
        pool_average_travel_costs_eur_km: float = fmean(
            user.run_metrics.average_travel_costs_eur_km for user in users_pool
        )
        pool_average_hourly_power_from_grid_kW: pl.Series = (
            pl.DataFrame(
                [
                    user.run_metrics.average_hourly_power_from_grid_kW.rename(  # noqa: E501
                        str(user_index)
                    )
                    for user_index, user in enumerate(users_pool)
                ]
            )
            .mean_horizontal()
            .rename('Average hourly power from grid (kW)')
        )
        pool_average_hourly_power_from_grid_kW_per_location_type: dict[
            str, pl.Series
        ] = {
            location_type: (
                pl.DataFrame(
                    [
                        user.run_metrics.average_hourly_power_from_grid_kW_per_location_type.get(  # noqa:E501
                            location_type, pl.Series(values=[0.0] * 24)
                        ).rename(  # noqa: E501
                            str(user_index)
                        )
                        for user_index, user in enumerate(users_pool)
                    ]
                )
                .mean_horizontal()
                .rename('Average hourly power from grid (kW)')
            )
            for location_type in location_types
        }

        return cls(
            average_kilometrage=average_kilometrage,
            average_consumption_kWh=average_consumption_kWh,
            average_purchased_electricity_kWh=(
                average_purchased_electricity_kWh
            ),
            average_purchased_electricity_kWh_per_location_type=(
                average_purchased_electricity_kWh_per_location_type
            ),
            average_charge_spending_eur=average_charge_spending_eur,
            average_charge_spending_eur_per_location_type=(
                average_charge_spending_eur_per_location_type
            ),
            average_electricity_sold_kWh=average_electricity_sold_kWh,
            average_discharge_income_eur=average_discharge_income_eur,
            pool_average_hourly_power_from_grid_kW=(
                pool_average_hourly_power_from_grid_kW
            ),
            pool_average_electricity_costs_eur_kWh=(
                pool_average_electricity_costs_eur_kWh
            ),
            pool_average_travel_costs_eur_km=pool_average_travel_costs_eur_km,
            pool_average_hourly_power_from_grid_kW_per_location_type=pool_average_hourly_power_from_grid_kW_per_location_type,  # noqa:E501
        )


@dataclass
class CapacityOverloads:
    excess_occurrences: pl.Series
    average_overloaded_lines: float
    proportion_timesteps_with_overload: float
    excess_per_hour: pl.DataFrame

    @classmethod
    def get_excesses(
        cls, *, local_grid: LocalGrid, grid_parameters: Box
    ) -> CapacityOverloads:
        '''
        Calculate residential power-line congestion statistics.

        For each timestep, determine how many power lines exceed their
        capacity and whether at least one line is overloaded. Aggregate these
        results over the complete simulation and by hour of day.

        The calculated statistics distinguish between the average number of
        overloaded lines per timestep and the proportion of timesteps during
        which at least one line is overloaded.
        '''

        capacity_exceeded_series: list[pl.Series] = [
            power_line.EV_demand_matching.get_column(
                grid_parameters.EV_demand_matching_DF.capacity_exceeded_header
            ).cast(pl.Int64)
            for power_line in local_grid.power_lines
        ]

        # Determine the number of overloaded power lines at each timestep.
        excess_occurrences: pl.Series = capacity_exceeded_series[0]

        for series in capacity_exceeded_series[1:]:
            excess_occurrences = excess_occurrences + series

        # Calculate statistics over the complete simulation.
        average_overloaded_lines: float = sum(excess_occurrences) / len(
            excess_occurrences
        )

        proportion_timesteps_with_overload: float = sum(
            excess_occurrences > 0
        ) / len(excess_occurrences)

        time_header = grid_parameters.EV_demand_matching_DF.time_header

        # Calculate the same congestion statistics by hour of day.
        excess_per_hour: pl.DataFrame = (
            pl.DataFrame(
                {
                    'time': local_grid.power_lines[
                        0
                    ].EV_demand_matching.get_column(time_header),
                    'excess_occurrences': excess_occurrences,
                }
            )
            .with_columns(pl.col('time').dt.hour().alias('hour'))
            .group_by('hour')
            .agg(
                pl.col('excess_occurrences').sum().alias('excess_occurrences'),
                (pl.col('excess_occurrences').sum() / pl.len()).alias(
                    'average_overloaded_lines'
                ),
                (pl.col('excess_occurrences') > 0)
                .sum()
                .alias('timesteps_with_overload'),
                ((pl.col('excess_occurrences') > 0).sum() / pl.len()).alias(
                    'proportion_timesteps_with_overload'
                ),
            )
            .sort('hour')
        )

        return cls(
            excess_occurrences == excess_occurrences,
            average_overloaded_lines=average_overloaded_lines,
            proportion_timesteps_with_overload=(
                proportion_timesteps_with_overload
            ),
            excess_per_hour=excess_per_hour,
        )
