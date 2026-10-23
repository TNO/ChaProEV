from pathlib import Path

try:
    import ChaProEV_plus  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import ChaProEV_plus  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again

import matplotlib.pyplot as plt
import polars as pl
import streamlit as st
from box import Box
from ETS_CookBook import ETS_CookBook as cook


def make_dashboard() -> None:

    run_to_OPERA_file: str = 'run_to_OPERA.csv'
    run_to_OPERA: pl.DataFrame = pl.read_csv(
        run_to_OPERA_file, try_parse_dates=True
    )
    run_to_OPERA_per_hour_number = (
        run_to_OPERA.with_columns(
            pl.col('Time Tag').dt.hour().alias('Hour number')
        )
        .group_by('Hour number')
        .agg(
            pl.col('Power (kW)')
            .mean()
            .alias('Average power from network (kW)')
        )
        .sort('Hour number')
    )
    scenario_path: Path = Path('scenarios/plus/test.toml')
    scenario: Box = cook.parameters_from_TOML(scenario_path)

    scenario_A: Box = scenario.copy()
    scenario_B: Box = scenario.copy()

    st.set_page_config(layout='wide')
    sidebar_A = st.sidebar
    sidebar_B = st.sidebar

    with sidebar_A:
        st.title('Scenario A')
        charge_desire_proportion_trigger_A: float = st.slider(
            label='Charge proportion trigger percent',
            min_value=0.0,
            max_value=1.0,
            value=scenario.vehicle.charge_desire_proportion_trigger,
            step=0.01,
            format='percent',
            key='charge_desire_proportion_trigger_A',
        )
        adaptive_A: bool = st.selectbox(
            label='Use adaptve charging',
            options=[True, False],
            key='adaptive_A',
            index=1,
        )
        work_connectivity_A: float = st.slider(
            label='Work connectivity',
            min_value=0.0,
            max_value=1.0,
            value=scenario.locations.work.connectivity,
            step=0.01,
            format='percent',
            key='work_connectivity_A',
        )
        work_start_hour_A: float = st.slider(
            label='Mean start hour work journeys',
            min_value=4.0,
            max_value=11.0,
            value=scenario.trips.commute_to_work.start_time_hours_mean,
            key='work_start_hour_A',
        )
    scenario_A.charging.adaptive = adaptive_A
    scenario_A.vehicle.charge_desire_proportion_trigger = (
        charge_desire_proportion_trigger_A
    )
    scenario_A.locations.work.connectivity = work_connectivity_A
    scenario_A.trips.commute_to_work.start_time_hours_mean = work_start_hour_A
    scenario_A.trips.commute_to_work_and_leisure.start_time_hours_mean = (
        work_start_hour_A
    )

    with sidebar_B:
        st.title('Scenario B')
        charge_desire_proportion_trigger_B: float = st.slider(
            label='Charge proportion trigger percent',
            min_value=0.0,
            max_value=1.0,
            value=scenario.vehicle.charge_desire_proportion_trigger,
            step=0.01,
            format='percent',
            key='charge_desire_proportion_trigger_B',
        )
        adaptive_B: bool = st.selectbox(
            label='Use adaptve charging',
            options=[True, False],
            index=1,
            key='adaptive_B',
        )
        work_connectivity_B: float = st.slider(
            label='Work connectivity',
            min_value=0.0,
            max_value=1.0,
            value=scenario.locations.work.connectivity,
            step=0.01,
            format='percent',
            key='work_connectivity_B',
        )
        work_start_hour_B: float = st.slider(
            label='Mean start hour work journeys',
            min_value=4.0,
            max_value=11.0,
            value=scenario.trips.commute_to_work.start_time_hours_mean,
            key='work_start_hour_B',
        )
        scale_factor_start_times_standard_deviation: float = st.slider(
            label='scale factor start times standard deviation',
            min_value=0.0,
            max_value=50.0,
            value=1.0,
            step=0.01,
            key='scale_factor_start_times_standard_deviation',
        )
    scenario_B.charging.adaptive = adaptive_B
    scenario_B.vehicle.charge_desire_proportion_trigger = (
        charge_desire_proportion_trigger_B
    )
    scenario_B.locations.work.connectivity = work_connectivity_B
    scenario_B.trips.commute_to_work.start_time_hours_mean = work_start_hour_B
    scenario_B.trips.commute_to_work_and_leisure.start_time_hours_mean = (
        work_start_hour_B
    )

    scenario_B.trips.commute_to_work.start_time_hours_standard_deviation = (
        scale_factor_start_times_standard_deviation
        * scenario_A.trips.commute_to_work.start_time_hours_standard_deviation
    )
    scenario_B.trips.commute_to_work_and_leisure.start_time_hours_standard_deviation = (  # noqa: E501
        scale_factor_start_times_standard_deviation
        * scenario_A.trips.commute_to_work_and_leisure.start_time_hours_standard_deviation  # noqa: E501
    )
    scenario_B.trips.leisure_only.start_time_hours_standard_deviation = (
        scale_factor_start_times_standard_deviation
        * scenario_A.trips.leisure_only.start_time_hours_standard_deviation
    )
    scenario_B.trips.holiday_leisure_trip.start_time_hours_standard_deviation = (  # noqa: E501
        scale_factor_start_times_standard_deviation
        * scenario_A.trips.holiday_leisure_trip.start_time_hours_standard_deviation  # noqa: E501
    )
    scenario_B.trips.weekend_trip.start_time_hours_standard_deviation = (
        scale_factor_start_times_standard_deviation
        * scenario_A.trips.weekend_trip.start_time_hours_standard_deviation
    )

    charging_dataframe_A, hourly_values_A = ChaProEV_plus.run_ChaProEV(
        scenario=scenario_A
    )
    charging_dataframe_B, hourly_values_B = ChaProEV_plus.run_ChaProEV(
        scenario=scenario_B
    )

    plt.style.use('fivethirtyeight')
    network_power_figure, network_power_plot = plt.subplots(1, 1)

    network_power_plot.bar(
        x=run_to_OPERA_per_hour_number['Hour number'],
        height=run_to_OPERA_per_hour_number['Average power from network (kW)'],
        label='Data sent to OPERA',
    )

    network_power_plot.bar(
        x=hourly_values_A['Hour number'],
        height=hourly_values_A['Average power drawn from network (kW)'],
        label='Scenario A',
        width=0.5,
    )
    network_power_plot.bar(
        x=hourly_values_B['Hour number'],
        height=hourly_values_B['Average power drawn from network (kW)'],
        label='Scenario B',
        width=0.25,
    )
    network_power_plot.legend()
    plot1, plot2 = st.columns(2)
    with plot1:
        st.pyplot(network_power_figure)
        plt.close(network_power_figure)


if __name__ == '__main__':

    make_dashboard()
