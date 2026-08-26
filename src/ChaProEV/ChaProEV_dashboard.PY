import streamlit as st
from ETS_CookBook import ETS_CookBook as cook
import ChaProEV_plus
from pathlib import Path
from box import Box
import matplotlib.pyplot as plt

def make_dashboard() -> None:
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
            index=1
    )
    scenario_A.charging.adaptive = adaptive_A
    scenario_A.vehicle.charge_desire_proportion_trigger = charge_desire_proportion_trigger_A


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
            key='adaptive_B'
    )
    scenario_B.charging.adaptive = adaptive_B
    scenario_B.vehicle.charge_desire_proportion_trigger = charge_desire_proportion_trigger_B

    charging_dataframe_A, hourly_values_A = ChaProEV_plus.run_ChaProEV(scenario=scenario_A)
    charging_dataframe_B, hourly_values_B = ChaProEV_plus.run_ChaProEV(scenario=scenario_B)

    plt.style.use('fivethirtyeight')
    network_power_figure, network_power_plot = plt.subplots(1, 1)

    network_power_plot.bar(
        x=hourly_values_A['Hour number'],
        height=hourly_values_A['Average power drawn from network (kW)'],
        label='Scenario A'
    )
    network_power_plot.bar(
        x=hourly_values_B['Hour number'],
        height=hourly_values_B['Average power drawn from network (kW)'],
        label='Scenario B'
    )
    network_power_plot.legend()
    plot1, plot2 = st.columns(2)
    with plot1:
        st.pyplot(network_power_figure)
        plt.close(network_power_figure)

    





if __name__ == '__main__':

    make_dashboard()