import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
import streamlit as st
from box import Box
from ETS_CookBook import ETS_CookBook as cook

from ChaProEV.stochastic_new.ChaProEV_run import (
    UsersPoolStatistics,
    run_scenario,
)


def make_dashboard() -> None:

    scenario_name: str = 'cars'
    case_name: str = 'plus'
    scenario_path: Path = (
        Path('scenarios') / case_name / f'{scenario_name}.toml'
    )
    general_definitions_file_path: Path = Path('ChaProEV.toml')
    general_definitions: Box = cook.parameters_from_TOML(
        general_definitions_file_path
    )

    scenario: Box = cook.parameters_from_TOML(scenario_path)
    scenario.name = scenario_name
    scenario.case_name = case_name

    scenario_A: Box = scenario.copy()
    scenario_B: Box = scenario.copy()

    st.set_page_config(layout='wide')

    metrics_A, metrics_B = st.columns(2)
    plots_A, plots_B = st.columns(2)
    _, plot_box_1, _ = st.columns([1, 2, 1])
    sliders_A, sliders_B = st.columns(2)

    with sliders_A:
        adaptive_proportion_A: float = st.slider(
            label='Adaptive proportion',
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.01,
            format='percent',
            key='dapative_proportion_A',
        )
        (
            charge_desire_proportion_trigger_min_A,
            charge_desire_proportion_trigger_max_A,
        ) = st.slider(
            label='Charge desire proportion trigger',
            min_value=0.0,
            max_value=100.0,
            value=(40.0, 60.0),
            step=1.0,
            format='%.0f%%',
            key='charge_desire_proportion_trigger_A',
        )
        charge_desire_proportion_trigger_min_A /= 100
        charge_desire_proportion_trigger_max_A /= 100
        charge_desire_proportion_trigger_typical_A: float = (
            charge_desire_proportion_trigger_min_A
            + charge_desire_proportion_trigger_max_A
        ) / 2

    with sliders_B:
        adaptive_proportion_B: float = st.slider(
            label='Adaptive proportion',
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.01,
            format='percent',
            key='dapative_proportion_B',
        )
        (
            charge_desire_proportion_trigger_min_B,
            charge_desire_proportion_trigger_max_B,
        ) = st.slider(
            label='Charge desire proportion trigger',
            min_value=0.0,
            max_value=100.0,
            value=(40.0, 60.0),
            step=1.0,
            format='%.0f%%',
            key='charge_desire_proportion_trigger_B',
        )
        charge_desire_proportion_trigger_min_B /= 100
        charge_desire_proportion_trigger_max_B /= 100
        charge_desire_proportion_trigger_typical_B: float = (
            charge_desire_proportion_trigger_min_B
            + charge_desire_proportion_trigger_max_B
        ) / 2
    scenario_A.charging_behaviour.adaptive_proportion = adaptive_proportion_A
    scenario_A.charging_behaviour.charge_desire_proportion_trigger_min = (
        charge_desire_proportion_trigger_min_A
    )
    scenario_A.charging_behaviour.charge_desire_proportion_trigger_typical = (
        charge_desire_proportion_trigger_typical_A
    )
    scenario_A.charging_behaviour.charge_desire_proportion_trigger_max = (
        charge_desire_proportion_trigger_max_A
    )

    scenario_B.charging_behaviour.adaptive_proportion = adaptive_proportion_B

    scenario_B.charging_behaviour.charge_desire_proportion_trigger_min = (
        charge_desire_proportion_trigger_min_B
    )
    scenario_B.charging_behaviour.charge_desire_proportion_trigger_typical = (
        charge_desire_proportion_trigger_typical_B
    )
    scenario_B.charging_behaviour.charge_desire_proportion_trigger_max = (
        charge_desire_proportion_trigger_max_B
    )

    statistics_A: UsersPoolStatistics = run_scenario(scenario_A)
    statistics_B: UsersPoolStatistics = run_scenario(scenario_B)
    with metrics_A:
        st.subheader('Scenario A')
        st.metric(
            label='Kilometrage',
            value=f'{statistics_A.average_kilometrage:.0f} km',
        )
        st.metric(
            label='Consumption',
            value=f'{statistics_A.average_consumption_kWh:.0F} kWh',
        )
        st.metric(
            label='Purchased electricity',
            value=f'{statistics_A.average_purchased_electricity_kWh:.0f} kWh',
        )
        st.metric(
            label='Charge spending',
            value=f'{statistics_A.average_charge_spending_eur:.0f} €',
        )

    with metrics_B:
        st.subheader('Scenario B')
        st.metric(
            label='Kilometrage',
            value=f'{statistics_B.average_kilometrage:.0f} km',
        )
        st.metric(
            label='Consumption',
            value=f'{statistics_B.average_consumption_kWh:.0f} kWh',
        )
        st.metric(
            label='Purchased electricity',
            value=f'{statistics_B.average_purchased_electricity_kWh:.0f} kWh',
        )
        st.metric(
            label='Charge spending',
            value=f'{statistics_B.average_charge_spending_eur:.0f} €',
        )

    plt.style.use('fivethirtyeight')

    power_from_network_W_A: pl.Series = (
        statistics_A.pool_average_hourly_power_from_network_kW
    ) * 1_000
    power_from_network_W_B: pl.Series = (
        statistics_B.pool_average_hourly_power_from_network_kW
    ) * 1_000
    network_power_figure, network_power_plot = plt.subplots(
        1, 1, figsize=(16, 9)
    )

    hours: int = len(power_from_network_W_A)
    color_A_name: str = 'TNO_action_blue'
    color_B_name: str = 'TNO_action_orange'
    color_A: tuple[float, float, float] = cook.get_rgb_from_name(
        color_name=color_A_name, color_definitions=general_definitions.colors
    )
    color_B: tuple[float, float, float] = cook.get_rgb_from_name(
        color_name=color_B_name, color_definitions=general_definitions.colors
    )
    # powere per location type! filter street
    # required kWH and obtained
    # based on trafo ID and line id
    # and a queueu of available powers
    # first comes in
    # You will be allowed if there is space
    # Alllow queuing (waiting --> tolerance (e.g. leave queue
    # if 25% of the session time is done)
    # ) queueu
    network_power_plot.bar(
        x=range(hours),
        height=power_from_network_W_A,
        label='Scenario A',
        width=1.0,
        color=color_A,
    )
    network_power_plot.bar(
        x=range(hours),
        height=power_from_network_W_B,
        label='Scenario B',
        width=0.5,
        color=color_B,
    )
    network_power_plot.set_title('Average power draw from netowrk')
    network_power_plot.set_xlabel('Hour in day')
    network_power_plot.set_ylabel('Average draw from network (W)')
    network_power_plot.legend()

    with plot_box_1:
        st.pyplot(network_power_figure, use_container_width=True)

        plt.close(network_power_figure)


def run_dashboard() -> None:
    app_path: Path = Path(__file__).resolve()
    subprocess.run(
        [sys.executable, '-m', 'streamlit', 'run', str(app_path)], check=True
    )


if __name__ == '__main__':

    make_dashboard()
