import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
import streamlit as st
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ChaProEV.stochastic_new.ChaProEV_run import (
    UsersPoolStatistics,
    run_scenario,
)


def get_network_power_figure(
    *,
    location_type: str,
    power_from_network_W_A: pl.Series,
    power_from_network_W_B: pl.Series,
    color_A: tuple[float, float, float],
    color_B: tuple[float, float, float],
    metrics_text_color: tuple[float, float, float],
) -> Figure:

    network_power_figure, network_power_plot = plt.subplots(
        1, 1, figsize=(16, 9)
    )

    hours: int = len(power_from_network_W_A)

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
    network_power_plot.set_title(
        f'Average power draw from network in {location_type}',
        color=metrics_text_color,
    )
    network_power_plot.set_xlabel('Hour in day', color=metrics_text_color)
    network_power_plot.set_ylabel(
        'Average draw from network (W)', color=metrics_text_color
    )
    network_power_plot.legend(frameon=False, labelcolor=metrics_text_color)

    network_power_plot.tick_params(axis='x', colors=metrics_text_color)
    network_power_plot.tick_params(axis='y', colors=metrics_text_color)
    network_power_plot.spines['left'].set_color(metrics_text_color)
    network_power_plot.spines['top'].set_visible(False)
    network_power_plot.spines['right'].set_visible(False)
    network_power_plot.spines['bottom'].set_color(metrics_text_color)
    network_power_plot.set_facecolor('none')

    network_power_figure.patch.set_alpha(0)
    network_power_figure.tight_layout()

    return network_power_figure


def get_network_locations_figure(
    network_power_per_location_type: dict[str, pl.Series],
    location_types_colors: dict[str, tuple[float, float, float]],
    metrics_text_color: tuple[float, float, float],
    max_power_scale: float,
) -> Figure:

    network_locations_figure, network_locations_plot = plt.subplots(1, 1)

    for (
        location_type,
        power_per_hour,
    ) in network_power_per_location_type.items():
        network_locations_plot.plot(
            power_per_hour * 1000,
            label=location_type,
            color=location_types_colors[location_type],
        )

    network_locations_plot.set_title(
        'Average power draw from network', color=metrics_text_color
    )
    network_locations_plot.set_xlabel('Hour in day', color=metrics_text_color)
    network_locations_plot.set_ylabel('Watt', color=metrics_text_color)
    network_locations_plot.legend(
        ncol=4,
        frameon=False,
        labelcolor=metrics_text_color,
        fontsize=10,
        loc='lower center',
        bbox_to_anchor=(0.5, -0.5),
    )
    network_locations_plot.set_ylim(0, max_power_scale * 1000)

    network_locations_plot.tick_params(axis='x', colors=metrics_text_color)
    network_locations_plot.tick_params(axis='y', colors=metrics_text_color)
    network_locations_plot.spines['left'].set_color(metrics_text_color)
    network_locations_plot.spines['top'].set_visible(False)
    network_locations_plot.spines['right'].set_visible(False)
    network_locations_plot.spines['bottom'].set_color(metrics_text_color)
    network_locations_plot.set_facecolor('none')

    network_locations_figure.patch.set_alpha(0)
    network_locations_figure.tight_layout()

    return network_locations_figure


def draw_metric(
    *,
    values_dict: dict[str, float],
    metric_plot: Axes,
    metric: str,
    y_max: float,
    total_prefix: str,
    total_suffix: str,
    location_types_colors: dict[str, tuple[float, float, float]],
    metrics_text_color: tuple[float, float, float],
) -> None:

    bottom: float = 0.0
    for location_type, step_value in values_dict.items():
        metric_plot.bar(
            x=metric,
            height=step_value,
            bottom=bottom,
            label=location_type,
            color=location_types_colors[location_type],
        )
        bottom += step_value
    metric_plot.set_ylim(0, ymax=y_max)
    metric_plot.text(
        x=0,
        y=bottom,
        s=f'{total_prefix}{bottom:.0f}{total_suffix}',
        ha='center',
        va='bottom',
        color=metrics_text_color,
    )
    metric_plot.tick_params(axis='y', colors=metrics_text_color)
    metric_plot.spines['left'].set_color(metrics_text_color)
    metric_plot.xaxis.set_visible(False)
    metric_plot.spines['top'].set_visible(False)
    metric_plot.spines['right'].set_visible(False)
    metric_plot.spines['bottom'].set_visible(False)
    metric_plot.set_facecolor('none')


def get_metrics_figure(
    metrics_values: list[dict[str, float]],
    metrics: list[str],
    y_maxes: list[float],
    total_prefixes: list[str],
    total_suffixes: list[str],
    location_types_colors: dict[str, tuple[float, float, float]],
    metrics_text_color: tuple[float, float, float],
) -> Figure:
    metrics_figure, metrics_plots = plt.subplots(1, len(metrics_values))

    for (
        metric_values,
        metric_plot,
        metric,
        y_max,
        total_prefix,
        total_suffix,
    ) in zip(
        metrics_values,
        metrics_plots,
        metrics,
        y_maxes,
        total_prefixes,
        total_suffixes,
    ):
        draw_metric(
            values_dict=metric_values,
            metric_plot=metric_plot,
            metric=metric,
            y_max=y_max,
            total_prefix=total_prefix,
            total_suffix=total_suffix,
            location_types_colors=location_types_colors,
            metrics_text_color=metrics_text_color,
        )
    legend_colors, lgend_labels = metrics_plots[0].get_legend_handles_labels()
    metrics_figure.legend(
        legend_colors,
        lgend_labels,
        ncol=4,
        frameon=False,
        labelcolor=metrics_text_color,
        fontsize=10,
        loc='lower center',
        bbox_to_anchor=(0.5, -0.05),
    )
    metrics_figure.patch.set_alpha(0)
    metrics_figure.tight_layout()
    return metrics_figure


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

    metric_plots_A, metric_plots_B = st.columns(2)
    network_A, network_B = st.columns(2)
    _, plot_box_1, _ = st.columns([1, 2, 1])

    with st.sidebar:
        with st.form('scenario_settings'):
            sliders_A, sliders_B = st.columns(2)
            with sliders_A:
                st.subheader('Scenario A')
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
                (
                    fast_charge_desire_proportion_trigger_min_A,
                    fast_charge_desire_proportion_trigger_max_A,
                ) = st.slider(
                    label='Fast charge desire proportion trigger',
                    min_value=0.0,
                    max_value=100.0,
                    value=(10.0, 20.0),
                    step=1.0,
                    format='%.0f%%',
                    key='fast_charge_desire_proportion_trigger_A',
                )
                (
                    charge_stop_proportion_trigger_min_A,
                    charge_stop_proportion_trigger_max_A,
                ) = st.slider(
                    label='Charge stop proportion trigger',
                    min_value=0.0,
                    max_value=100.0,
                    value=(100.0, 100.0),
                    step=1.0,
                    format='%.0f%%',
                    key='charge_stop_proportion_trigger_A',
                )

                (
                    fast_charge_stop_proportion_trigger_min_A,
                    fast_charge_stop_proportion_trigger_max_A,
                ) = st.slider(
                    label='Fast charge stop proportion trigger',
                    min_value=0.0,
                    max_value=100.0,
                    value=(70.0, 80.0),
                    step=1.0,
                    format='%.0f%%',
                    key='fast_charge_stop_proportion_trigger_A',
                )

                proportion_own_driveway_A: float = st.slider(
                    label='Percentage of households with own driveways',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.25,
                    step=0.01,
                    format='percent',
                    key='proportion_own_driveway_A',
                )
                own_driveway_connectivity_A: float = st.slider(
                    label='Own driveway connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.01,
                    format='percent',
                    key='own_driveway_connectivity_A',
                )

                street_parking_connectivity_A: float = st.slider(
                    label='Street parking connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.25,
                    step=0.01,
                    format='percent',
                    key='street_parking_connectivity_A',
                )

                work_connectivity_A: float = st.slider(
                    label='Work connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    step=0.01,
                    format='percent',
                    key='work_connectivity_A',
                )

                leisure_connectivity_A: float = st.slider(
                    label='Leisure connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.25,
                    step=0.01,
                    format='percent',
                    key='leisure_connectivity_A',
                )

                weekend_connectivity_A: float = st.slider(
                    label='Weekend connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.125,
                    step=0.01,
                    format='percent',
                    key='weekend_connectivity_A',
                )

                holiday_connectivity_A: float = st.slider(
                    label='Holiday connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.01,
                    format='percent',
                    key='holiday_connectivity_A',
                )
                home_work_distance_min_A, home_work_distance_max_A = st.slider(
                    label='Home-work distance (km)',
                    min_value=0.0,
                    max_value=100.0,
                    value=(17.0, 31.0),
                    step=1.0,
                    format='%.0f',
                    key='home_work_distance_A',
                )
                home_leisure_distance_min_A, home_leisure_distance_max_A = (
                    st.slider(
                        label='Home-leisure distance (km)',
                        min_value=0.0,
                        max_value=100.0,
                        value=(10.0, 26.0),
                        step=1.0,
                        format='%.0f',
                        key='home_leisure_distance_A',
                    )
                )
                work_leisure_distance_min_A, work_leisure_distance_max_A = (
                    st.slider(
                        label='Work-leisure distance (km)',
                        min_value=0.0,
                        max_value=100.0,
                        value=(16.0, 30.0),
                        step=1.0,
                        format='%.0f',
                        key='work_leisure_distance_A',
                    )
                )
                (
                    holiday_leisure_distance_min_A,
                    holiday_leisure_distance_max_A,
                ) = st.slider(
                    label='Holiday-leisure distance (km)',
                    min_value=10.0,
                    max_value=100.0,
                    value=(10.0, 20.0),
                    step=1.0,
                    format='%.0f',
                    key='holiday_leisure_distance_A',
                )
                home_weekend_distance_min_A, home_weekend_distance_max_A = (
                    st.slider(
                        label='Home-weekend distance (km)',
                        min_value=0.0,
                        max_value=400.0,
                        value=(80.0, 100.0),
                        step=1.0,
                        format='%.0f',
                        key='home_weekend_distance_A',
                    )
                )
                home_holiday_distance_min_A, home_holiday_distance_max_A = (
                    st.slider(
                        label='Home-holiday distance (km)',
                        min_value=0.0,
                        max_value=1_000.0,
                        value=(200.0, 400.0),
                        step=1.0,
                        format='%.0f',
                        key='home_holiday_distance_A',
                    )
                )
                lunch_leisure_proportion_A: float = st.slider(
                    label='Percentage of leisure trips at lunchtime',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.2,
                    step=0.01,
                    format='percent',
                    key='lunch_leisure_proportion_A',
                )

            with sliders_B:
                st.subheader('Scenario B')
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
                (
                    fast_charge_desire_proportion_trigger_min_B,
                    fast_charge_desire_proportion_trigger_max_B,
                ) = st.slider(
                    label='Fast charge desire proportion trigger',
                    min_value=0.0,
                    max_value=100.0,
                    value=(10.0, 20.0),
                    step=1.0,
                    format='%.0f%%',
                    key='fast_charge_desire_proportion_trigger_B',
                )

                (
                    charge_stop_proportion_trigger_min_B,
                    charge_stop_proportion_trigger_max_B,
                ) = st.slider(
                    label='Charge stop proportion trigger',
                    min_value=0.0,
                    max_value=100.0,
                    value=(100.0, 100.0),
                    step=1.0,
                    format='%.0f%%',
                    key='charge_stop_proportion_trigger_B',
                )

                (
                    fast_charge_stop_proportion_trigger_min_B,
                    fast_charge_stop_proportion_trigger_max_B,
                ) = st.slider(
                    label='Fast charge stop proportion trigger',
                    min_value=0.0,
                    max_value=100.0,
                    value=(70.0, 80.0),
                    step=1.0,
                    format='%.0f%%',
                    key='fast_charge_stop_proportion_trigger_B',
                )
                proportion_own_driveway_B: float = st.slider(
                    label='Percentage of households with own driveways',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.25,
                    step=0.01,
                    format='percent',
                    key='proportion_own_driveway_B',
                )
                own_driveway_connectivity_B: float = st.slider(
                    label='Own driveway connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.01,
                    format='percent',
                    key='own_driveway_connectivity_B',
                )

                street_parking_connectivity_B: float = st.slider(
                    label='Street parking connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.25,
                    step=0.01,
                    format='percent',
                    key='street_parking_connectivity_B',
                )

                work_connectivity_B: float = st.slider(
                    label='Work connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    step=0.01,
                    format='percent',
                    key='work_connectivity_B',
                )

                leisure_connectivity_B: float = st.slider(
                    label='Leisure connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.25,
                    step=0.01,
                    format='percent',
                    key='leisure_connectivity_B',
                )

                weekend_connectivity_B: float = st.slider(
                    label='Weekend connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.125,
                    step=0.01,
                    format='percent',
                    key='weekend_connectivity_B',
                )

                holiday_connectivity_B: float = st.slider(
                    label='Holiday connectivity',
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.01,
                    format='percent',
                    key='holiday_connectivity_B',
                )
                home_work_distance_min_B, home_work_distance_max_B = st.slider(
                    label='Home-work distance (km)',
                    min_value=0.0,
                    max_value=100.0,
                    value=(17.0, 31.0),
                    step=1.0,
                    format='%.0f',
                    key='home_work_distance_B',
                )
                home_leisure_distance_min_B, home_leisure_distance_max_B = (
                    st.slider(
                        label='Home-leisure distance (km)',
                        min_value=0.0,
                        max_value=100.0,
                        value=(10.0, 26.0),
                        step=1.0,
                        format='%.0f',
                        key='home_leisure_distance_B',
                    )
                )
                work_leisure_distance_min_B, work_leisure_distance_max_B = (
                    st.slider(
                        label='Work-leisure distance (km)',
                        min_value=0.0,
                        max_value=100.0,
                        value=(16.0, 30.0),
                        step=1.0,
                        format='%.0f',
                        key='work_leisure_distance_B',
                    )
                )
                (
                    holiday_leisure_distance_min_B,
                    holiday_leisure_distance_max_B,
                ) = st.slider(
                    label='Holiday-leisure distance (km)',
                    min_value=10.0,
                    max_value=100.0,
                    value=(10.0, 20.0),
                    step=1.0,
                    format='%.0f',
                    key='holiday_leisure_distance_B',
                )
                home_weekend_distance_min_B, home_weekend_distance_max_B = (
                    st.slider(
                        label='Home-weekend distance (km)',
                        min_value=0.0,
                        max_value=400.0,
                        value=(80.0, 100.0),
                        step=1.0,
                        format='%.0f',
                        key='home_weekend_distance_B',
                    )
                )
                home_holiday_distance_min_B, home_holiday_distance_max_B = (
                    st.slider(
                        label='Home-holiday distance (km)',
                        min_value=0.0,
                        max_value=1_000.0,
                        value=(200.0, 400.0),
                        step=1.0,
                        format='%.0f',
                        key='home_holiday_distance_B',
                    )
                )
                lunch_leisure_proportion_B: float = st.slider(
                    label='Percentage of leisure trips at lunchtime',
                    min_value=0.0,
                    max_value=1.0,
                    value=0.2,
                    step=0.01,
                    format='percent',
                    key='lunch_leisure_proportion_B',
                )
            run_button = st.form_submit_button("Run")
    charge_desire_proportion_trigger_min_A /= 100
    charge_desire_proportion_trigger_max_A /= 100
    charge_desire_proportion_trigger_typical_A: float = (
        charge_desire_proportion_trigger_min_A
        + charge_desire_proportion_trigger_max_A
    ) / 2
    charge_desire_proportion_trigger_min_B /= 100
    charge_desire_proportion_trigger_max_B /= 100
    charge_desire_proportion_trigger_typical_B: float = (
        charge_desire_proportion_trigger_min_B
        + charge_desire_proportion_trigger_max_B
    ) / 2
    fast_charge_desire_proportion_trigger_min_A /= 100
    fast_charge_desire_proportion_trigger_max_A /= 100
    fast_charge_desire_proportion_trigger_typical_A: float = (
        fast_charge_desire_proportion_trigger_min_A
        + fast_charge_desire_proportion_trigger_max_A
    ) / 2
    fast_charge_desire_proportion_trigger_min_B /= 100
    fast_charge_desire_proportion_trigger_max_B /= 100
    fast_charge_desire_proportion_trigger_typical_B: float = (
        fast_charge_desire_proportion_trigger_min_B
        + fast_charge_desire_proportion_trigger_max_B
    ) / 2

    charge_stop_proportion_trigger_min_A /= 100
    charge_stop_proportion_trigger_max_A /= 100
    charge_stop_proportion_trigger_typical_A: float = (
        charge_stop_proportion_trigger_min_A
        + charge_stop_proportion_trigger_max_A
    ) / 2

    fast_charge_stop_proportion_trigger_min_A /= 100
    fast_charge_stop_proportion_trigger_max_A /= 100
    fast_charge_stop_proportion_trigger_typical_A: float = (
        fast_charge_stop_proportion_trigger_min_A
        + fast_charge_stop_proportion_trigger_max_A
    ) / 2

    charge_stop_proportion_trigger_min_B /= 100
    charge_stop_proportion_trigger_max_B /= 100
    charge_stop_proportion_trigger_typical_B: float = (
        charge_stop_proportion_trigger_min_B
        + charge_stop_proportion_trigger_max_B
    ) / 2

    fast_charge_stop_proportion_trigger_min_B /= 100
    fast_charge_stop_proportion_trigger_max_B /= 100
    fast_charge_stop_proportion_trigger_typical_B: float = (
        fast_charge_stop_proportion_trigger_min_B
        + fast_charge_stop_proportion_trigger_max_B
    ) / 2
    own_driveway_variant_weights_A: list[float] = [
        proportion_own_driveway_A,
        1 - proportion_own_driveway_A,
    ]
    own_driveway_variant_weights_B: list[float] = [
        proportion_own_driveway_B,
        1 - proportion_own_driveway_B,
    ]
    home_work_distance_typical_A: float = (
        home_work_distance_min_A + home_work_distance_max_A
    ) / 2

    home_leisure_distance_typical_A: float = (
        home_leisure_distance_min_A + home_leisure_distance_max_A
    ) / 2

    work_leisure_distance_typical_A: float = (
        work_leisure_distance_min_A + work_leisure_distance_max_A
    ) / 2

    holiday_leisure_distance_typical_A: float = (
        holiday_leisure_distance_min_A + holiday_leisure_distance_max_A
    ) / 2

    home_weekend_distance_typical_A: float = (
        home_weekend_distance_min_A + home_weekend_distance_max_A
    ) / 2

    home_holiday_distance_typical_A: float = (
        home_holiday_distance_min_A + home_holiday_distance_max_A
    ) / 2

    home_work_distance_typical_B: float = (
        home_work_distance_min_B + home_work_distance_max_B
    ) / 2

    home_leisure_distance_typical_B: float = (
        home_leisure_distance_min_B + home_leisure_distance_max_B
    ) / 2

    work_leisure_distance_typical_B: float = (
        work_leisure_distance_min_B + work_leisure_distance_max_B
    ) / 2

    holiday_leisure_distance_typical_B: float = (
        holiday_leisure_distance_min_B + holiday_leisure_distance_max_B
    ) / 2

    home_weekend_distance_typical_B: float = (
        home_weekend_distance_min_B + home_weekend_distance_max_B
    ) / 2

    home_holiday_distance_typical_B: float = (
        home_holiday_distance_min_B + home_holiday_distance_max_B
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
    scenario_A.charging_behaviour.charge_stop_proportion_trigger_min = (
        charge_stop_proportion_trigger_min_A
    )
    scenario_A.charging_behaviour.charge_stop_proportion_trigger_typical = (
        charge_stop_proportion_trigger_typical_A
    )
    scenario_A.charging_behaviour.charge_stop_proportion_trigger_max = (
        charge_stop_proportion_trigger_max_A
    )

    scenario_A.charging_behaviour.fast_charge_stop_proportion_trigger_min = (
        fast_charge_stop_proportion_trigger_min_A
    )
    scenario_A.charging_behaviour.fast_charge_stop_proportion_trigger_typical = (  # noqa:E501
        fast_charge_stop_proportion_trigger_typical_A
    )
    scenario_A.charging_behaviour.fast_charge_stop_proportion_trigger_max = (
        fast_charge_stop_proportion_trigger_max_A
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
    scenario_A.charging_behaviour.fast_charge_desire_proportion_trigger_min = (
        fast_charge_desire_proportion_trigger_min_A
    )
    scenario_A.charging_behaviour.fast_charge_desire_proportion_trigger_typical = (  # noqa:E501
        fast_charge_desire_proportion_trigger_typical_A
    )
    scenario_A.charging_behaviour.fast_charge_desire_proportion_trigger_max = (
        fast_charge_desire_proportion_trigger_max_A
    )

    scenario_B.charging_behaviour.fast_charge_desire_proportion_trigger_min = (
        fast_charge_desire_proportion_trigger_min_B
    )
    scenario_B.charging_behaviour.fast_charge_desire_proportion_trigger_typical = (  # noqa:E501
        fast_charge_desire_proportion_trigger_typical_B
    )
    scenario_B.charging_behaviour.fast_charge_desire_proportion_trigger_max = (
        fast_charge_desire_proportion_trigger_max_B
    )

    scenario_B.charging_behaviour.charge_stop_proportion_trigger_min = (
        charge_stop_proportion_trigger_min_B
    )
    scenario_B.charging_behaviour.charge_stop_proportion_trigger_typical = (
        charge_stop_proportion_trigger_typical_B
    )
    scenario_B.charging_behaviour.charge_stop_proportion_trigger_max = (
        charge_stop_proportion_trigger_max_B
    )

    scenario_B.charging_behaviour.fast_charge_stop_proportion_trigger_min = (
        fast_charge_stop_proportion_trigger_min_B
    )
    scenario_B.charging_behaviour.fast_charge_stop_proportion_trigger_typical = (  # noqa:E501
        fast_charge_stop_proportion_trigger_typical_B
    )
    scenario_B.charging_behaviour.fast_charge_stop_proportion_trigger_max = (
        fast_charge_stop_proportion_trigger_max_B
    )

    scenario_A.locations.home.variant_weights = own_driveway_variant_weights_A
    scenario_B.locations.home.variant_weights = own_driveway_variant_weights_B
    scenario_A.locations.home.own_driveway.connectivity = (
        own_driveway_connectivity_A
    )
    scenario_A.locations.home.street_parking.connectivity = (
        street_parking_connectivity_A
    )
    scenario_A.locations.work.connectivity = work_connectivity_A
    scenario_A.locations.leisure.connectivity = leisure_connectivity_A
    scenario_A.locations.weekend.connectivity = weekend_connectivity_A
    scenario_A.locations.holiday.connectivity = holiday_connectivity_A

    scenario_B.locations.home.own_driveway.connectivity = (
        own_driveway_connectivity_B
    )
    scenario_B.locations.home.street_parking.connectivity = (
        street_parking_connectivity_B
    )
    scenario_B.locations.work.connectivity = work_connectivity_B
    scenario_B.locations.leisure.connectivity = leisure_connectivity_B
    scenario_B.locations.weekend.connectivity = weekend_connectivity_B
    scenario_B.locations.holiday.connectivity = holiday_connectivity_B

    scenario_A.legs_references.home_work.distance_km_min = (
        home_work_distance_min_A
    )
    scenario_A.legs_references.home_work.distance_km_typical = (
        home_work_distance_typical_A
    )
    scenario_A.legs_references.home_work.distance_km_max = (
        home_work_distance_max_A
    )

    scenario_A.legs_references.home_leisure.distance_km_min = (
        home_leisure_distance_min_A
    )
    scenario_A.legs_references.home_leisure.distance_km_typical = (
        home_leisure_distance_typical_A
    )
    scenario_A.legs_references.home_leisure.distance_km_max = (
        home_leisure_distance_max_A
    )

    scenario_A.legs_references.work_leisure.distance_km_min = (
        work_leisure_distance_min_A
    )
    scenario_A.legs_references.work_leisure.distance_km_typical = (
        work_leisure_distance_typical_A
    )
    scenario_A.legs_references.work_leisure.distance_km_max = (
        work_leisure_distance_max_A
    )

    scenario_A.legs_references.holiday_leisure.distance_km_min = (
        holiday_leisure_distance_min_A
    )
    scenario_A.legs_references.holiday_leisure.distance_km_typical = (
        holiday_leisure_distance_typical_A
    )
    scenario_A.legs_references.holiday_leisure.distance_km_max = (
        holiday_leisure_distance_max_A
    )

    scenario_A.legs_references.home_weekend.distance_km_min = (
        home_weekend_distance_min_A
    )
    scenario_A.legs_references.home_weekend.distance_km_typical = (
        home_weekend_distance_typical_A
    )
    scenario_A.legs_references.home_weekend.distance_km_max = (
        home_weekend_distance_max_A
    )

    scenario_A.legs_references.home_holiday.distance_km_min = (
        home_holiday_distance_min_A
    )
    scenario_A.legs_references.home_holiday.distance_km_typical = (
        home_holiday_distance_typical_A
    )
    scenario_A.legs_references.home_holiday.distance_km_max = (
        home_holiday_distance_max_A
    )

    scenario_B.legs_references.home_work.distance_km_min = (
        home_work_distance_min_B
    )
    scenario_B.legs_references.home_work.distance_km_typical = (
        home_work_distance_typical_B
    )
    scenario_B.legs_references.home_work.distance_km_max = (
        home_work_distance_max_B
    )

    scenario_B.legs_references.home_leisure.distance_km_min = (
        home_leisure_distance_min_B
    )
    scenario_B.legs_references.home_leisure.distance_km_typical = (
        home_leisure_distance_typical_B
    )
    scenario_B.legs_references.home_leisure.distance_km_max = (
        home_leisure_distance_max_B
    )

    scenario_B.legs_references.work_leisure.distance_km_min = (
        work_leisure_distance_min_B
    )
    scenario_B.legs_references.work_leisure.distance_km_typical = (
        work_leisure_distance_typical_B
    )
    scenario_B.legs_references.work_leisure.distance_km_max = (
        work_leisure_distance_max_B
    )

    scenario_B.legs_references.holiday_leisure.distance_km_min = (
        holiday_leisure_distance_min_B
    )
    scenario_B.legs_references.holiday_leisure.distance_km_typical = (
        holiday_leisure_distance_typical_B
    )
    scenario_B.legs_references.holiday_leisure.distance_km_max = (
        holiday_leisure_distance_max_B
    )

    scenario_B.legs_references.home_weekend.distance_km_min = (
        home_weekend_distance_min_B
    )
    scenario_B.legs_references.home_weekend.distance_km_typical = (
        home_weekend_distance_typical_B
    )
    scenario_B.legs_references.home_weekend.distance_km_max = (
        home_weekend_distance_max_B
    )

    scenario_B.legs_references.home_holiday.distance_km_min = (
        home_holiday_distance_min_B
    )
    scenario_B.legs_references.home_holiday.distance_km_typical = (
        home_holiday_distance_typical_B
    )
    scenario_B.legs_references.home_holiday.distance_km_max = (
        home_holiday_distance_max_B
    )

    scenario_A.activity_parameters.trips.work_and_leisure_trip_split = [
        lunch_leisure_proportion_A,
        1 - lunch_leisure_proportion_A,
    ]
    scenario_B.activity_parameters.trips.work_and_leisure_trip_split = [
        lunch_leisure_proportion_B,
        1 - lunch_leisure_proportion_B,
    ]
    if (
        'statistics_A' not in st.session_state
        or 'statistics_B' not in st.session_state
        or run_button
    ):
        st.session_state.statistics_A = run_scenario(scenario_A)
        st.session_state.statistics_B = run_scenario(scenario_B)

        # Store the initial metrics as the reference
        if 'initial_average_kilometrage_A' not in st.session_state:
            st.session_state.initial_average_kilometrage_A = (
                st.session_state.statistics_A.average_kilometrage
            )

        if 'initial_average_consumption_kWh_A' not in st.session_state:
            st.session_state.initial_average_consumption_kWh_A = (
                st.session_state.statistics_A.average_consumption_kWh
            )
        if 'initial_average_kilometrage_B' not in st.session_state:
            st.session_state.initial_average_kilometrage_B = (
                st.session_state.statistics_B.average_kilometrage
            )

        if 'initial_average_consumption_kWh_B' not in st.session_state:
            st.session_state.initial_average_consumption_kWh_B = (
                st.session_state.statistics_B.average_consumption_kWh
            )

    statistics_A: UsersPoolStatistics = st.session_state.statistics_A
    statistics_B: UsersPoolStatistics = st.session_state.statistics_B

    with metrics_A:
        st.subheader('Scenario A')
        metrics_A_1, metrics_A_2 = st.columns(2)
        with metrics_A_1:

            st.metric(
                label='Kilometrage',
                value=f'{statistics_A.average_kilometrage:.0f} km',
                delta=(
                    f'{statistics_A.average_kilometrage - st.session_state.initial_average_kilometrage_A:+.0f} km'  # noqa:E501
                ),
            )
        with metrics_A_2:
            st.metric(
                label='Consumption',
                value=f'{statistics_A.average_consumption_kWh:.0F} kWh',
                delta=(
                    f'{statistics_A.average_consumption_kWh - st.session_state.initial_average_consumption_kWh_A:+.0f} kWh'  # noqa:E501
                ),
            )

    with metrics_B:
        st.subheader('Scenario B')
        metrics_B_1, metrics_B_2 = st.columns(2)
        with metrics_B_1:
            st.metric(
                label='Kilometrage',
                value=f'{statistics_B.average_kilometrage:.0f} km',
                delta=(
                    f'{statistics_B.average_kilometrage - st.session_state.initial_average_kilometrage_B:+.0f} km'  # noqa:E501
                ),
            )
        with metrics_B_2:
            st.metric(
                label='Consumption',
                value=f'{statistics_B.average_consumption_kWh:.0f} kWh',
                delta=(
                    f'{statistics_B.average_consumption_kWh - st.session_state.initial_average_consumption_kWh_B:+.0f} kWh'  # noqa:E501
                ),
            )

    plt.style.use('fivethirtyeight')

    metrics_settings: Box = scenario.metrics
    location_types: list[str] = metrics_settings.location_types
    location_types_colors_list: list[str] = (
        metrics_settings.location_types_colors
    )
    location_types_color_names: dict[str, str] = dict(
        zip(location_types, location_types_colors_list)
    )
    location_types_colors: dict[str, tuple[float, float, float]] = {
        location_type: cook.get_rgb_from_name(
            location_types_color_names[location_type],
            general_definitions.colors,
        )
        for location_type in location_types
    }
    metrics_text_color_name: str = scenario.metrics.text_color
    metrics_text_color: tuple[float, float, float] = cook.get_rgb_from_name(
        metrics_text_color_name, general_definitions.colors
    )
    spending_A: dict[str, float] = (
        statistics_A.average_charge_spending_eur_per_location_type
    )
    electricity_purchased_A: dict[str, float] = (
        statistics_A.average_purchased_electricity_kWh_per_location_type
    )

    spending_B: dict[str, float] = (
        statistics_B.average_charge_spending_eur_per_location_type
    )

    electricity_purchased_B: dict[str, float] = (
        statistics_B.average_purchased_electricity_kWh_per_location_type
    )
    spending_scale = cook.reference_scale(
        [sum(list(spending_A.values())), sum(list(spending_B.values()))]
    )
    electricity_purchased_scale = cook.reference_scale(
        [
            sum(list(electricity_purchased_A.values())),
            sum(list(electricity_purchased_B.values())),
        ]
    )

    figure_A = get_metrics_figure(
        metrics_values=[electricity_purchased_A, spending_A],
        metrics=[
            'Yearly electricity purchasesd (kWh)',
            'Yearly electricity spending (€)',
        ],
        y_maxes=[electricity_purchased_scale[1], spending_scale[1]],
        total_prefixes=['Total = ', '€'],
        total_suffixes=[' kWh', ' total'],
        location_types_colors=location_types_colors,
        metrics_text_color=metrics_text_color,
    )

    figure_B = get_metrics_figure(
        metrics_values=[electricity_purchased_B, spending_B],
        metrics=[
            'Yearly electricity purchasesd (kWh)',
            'Yearly electricity spending (€)',
        ],
        y_maxes=[electricity_purchased_scale[1], spending_scale[1]],
        total_prefixes=['Total = ', '€'],
        total_suffixes=[' kWh', ' total'],
        location_types_colors=location_types_colors,
        metrics_text_color=metrics_text_color,
    )

    with metric_plots_A:

        st.pyplot(fig=figure_A)
        plt.close(figure_A)

    with metric_plots_B:

        st.pyplot(fig=figure_B)
        plt.close(figure_B)

    network_power_per_location_type_A: dict[str, pl.Series] = (
        statistics_A.pool_average_hourly_power_from_network_kW_per_location_type  # noqa:E501
    )

    network_power_per_location_type_B: dict[str, pl.Series] = (
        statistics_B.pool_average_hourly_power_from_network_kW_per_location_type  # noqa:E501
    )

    network_power_values: list[float] = []
    for power_values in network_power_per_location_type_A.values():
        network_power_values += power_values.to_list()

    for power_values in network_power_per_location_type_B.values():
        network_power_values += power_values.to_list()

    max_power_scale: float = cook.reference_scale(
        network_power_values, digit_shift=1
    )[1]

    network_figure_A: Figure = get_network_locations_figure(
        network_power_per_location_type=network_power_per_location_type_A,
        location_types_colors=location_types_colors,
        metrics_text_color=metrics_text_color,
        max_power_scale=max_power_scale,
    )
    network_figure_B: Figure = get_network_locations_figure(
        network_power_per_location_type=network_power_per_location_type_B,
        location_types_colors=location_types_colors,
        metrics_text_color=metrics_text_color,
        max_power_scale=max_power_scale,
    )

    with network_A:
        st.pyplot(fig=network_figure_A)
        plt.close(network_figure_A)

    with network_B:
        st.pyplot(fig=network_figure_B)
        plt.close(network_figure_B)

    power_from_network_W_A: pl.Series = (
        statistics_A.pool_average_hourly_power_from_network_kW
    ) * 1_000
    power_from_network_W_B: pl.Series = (
        statistics_B.pool_average_hourly_power_from_network_kW
    ) * 1_000

    color_A_name: str = 'TNO_action_blue'
    color_B_name: str = 'TNO_action_orange'

    color_A: tuple[float, float, float] = cook.get_rgb_from_name(
        color_name=color_A_name, color_definitions=general_definitions.colors
    )
    color_B: tuple[float, float, float] = cook.get_rgb_from_name(
        color_name=color_B_name, color_definitions=general_definitions.colors
    )
    power_from_network_W_A_per_location: dict[str, pl.Series] = (
        statistics_A.pool_average_hourly_power_from_network_kW_per_location_type  # noqa:E501
    )

    power_from_network_W_B_per_location: dict[str, pl.Series] = (
        statistics_B.pool_average_hourly_power_from_network_kW_per_location_type  # noqa:E501
    )

    network_power_figures: dict[str, Figure] = {
        location_type_for_power: get_network_power_figure(
            location_type=location_type_for_power,
            power_from_network_W_A=(
                power_from_network_W_A_per_location[location_type_for_power]
            ),
            power_from_network_W_B=(
                power_from_network_W_B_per_location[location_type_for_power]
            ),
            color_A=color_A,
            color_B=color_B,
            metrics_text_color=metrics_text_color,
        )
        for location_type_for_power in location_types
    }
    network_power_figures['total'] = get_network_power_figure(
        location_type='total',
        power_from_network_W_A=power_from_network_W_A,
        power_from_network_W_B=power_from_network_W_B,
        color_A=color_A,
        color_B=color_B,
        metrics_text_color=metrics_text_color,
    )
    with plot_box_1:

        location_type_for_power: str = st.selectbox(
            'Location type',
            options=network_power_figures.keys(),
            index=len(location_types),
        )
        st.pyplot(network_power_figures[location_type_for_power])

        plt.close(network_power_figures[location_type_for_power])


def run_dashboard() -> None:
    app_path: Path = Path(__file__).resolve()
    subprocess.run(
        [sys.executable, '-m', 'streamlit', 'run', str(app_path)], check=True
    )


if __name__ == '__main__':

    make_dashboard()

    # Adjust km (including commute days, holiday, WE factors)
    # Demo cases show how things are related
    # slider selection in TOML
    # weekday commutre factir nd/or commute day probabilities
    # Session data (start, duration, kWh needed)
    # step(user) computation
    # power requested and power allocated (or queue?)
    # Does power requested increase?

    # slider defaults in TOML
    # slider trigger button
    # powere per location type! filter street
    # required kWH and obtained
    # based on trafo ID and line id
    # and a queueu of available powers
    # first comes in
    # You will be allowed if there is space
    # Alllow queuing (waiting --> tolerance (e.g. leave queue
    # if 25% of the session time is done)
    # ) queueu

    # add more sliders
