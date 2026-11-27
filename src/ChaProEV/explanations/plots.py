from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle


def price_curve(
    battery_proportion: float | np.ndarray,
    stop_trigger: float,
    threshold_trigger: float,
) -> float | np.ndarray:
    return (stop_trigger - battery_proportion) / (
        battery_proportion - threshold_trigger
    )


def get_charge_trigger_figure(
    *, charge_trigger_settings: Box, colors: Box, file_settings: Box
) -> Figure:
    plt.style.use(charge_trigger_settings.style)

    charge_trigger_figure, charge_trigger_plot = plt.subplots(
        1,
        1,
        figsize=(
            charge_trigger_settings.figure_width,
            charge_trigger_settings.figure_height,
        ),
    )

    x_max: float = charge_trigger_settings.x_max
    y_max: float = charge_trigger_settings.y_max

    # Colors
    want_charge_color_name: str = charge_trigger_settings.want_charge_color
    want_charge_color: tuple[float, float, float] = cook.get_rgb_from_name(
        want_charge_color_name,
        color_definitions=colors,
    )

    not_want_charge_color_name: str = (
        charge_trigger_settings.not_want_charge_color
    )
    not_want_charge_color: tuple[float, float, float] = cook.get_rgb_from_name(
        not_want_charge_color_name,
        color_definitions=colors,
    )

    line_color_name: str = charge_trigger_settings.line_color
    line_color: tuple[float, float, float] = cook.get_rgb_from_name(
        line_color_name,
        color_definitions=colors,
    )

    inset_background_color_name: str = (
        charge_trigger_settings.inset_background_color
    )
    inset_background_color: tuple[float, float, float] = (
        cook.get_rgb_from_name(
            inset_background_color_name,
            color_definitions=colors,
        )
    )

    inset_want_charge_color_name: str = (
        charge_trigger_settings.inset_want_charge_color
    )
    inset_want_charge_color: tuple[float, float, float] = (
        cook.get_rgb_from_name(
            inset_want_charge_color_name,
            color_definitions=colors,
        )
    )

    inset_not_want_charge_color_name: str = (
        charge_trigger_settings.inset_not_want_charge_color
    )
    inset_not_want_charge_color: tuple[float, float, float] = (
        cook.get_rgb_from_name(
            inset_not_want_charge_color_name,
            color_definitions=colors,
        )
    )

    # Trigger values and curve
    charge_trigger: float = charge_trigger_settings.charge_trigger
    stop_trigger: float = charge_trigger_settings.stop_trigger

    midpoint: float = (stop_trigger + charge_trigger) / 2

    reference_price: float = float(
        price_curve(
            battery_proportion=midpoint,
            stop_trigger=stop_trigger,
            threshold_trigger=charge_trigger,
        )
    )

    curve_range: np.ndarray = np.linspace(
        start=stop_trigger,
        stop=charge_trigger,
        num=charge_trigger_settings.steps,
        endpoint=False,
    )

    curve_values: np.ndarray = np.asarray(
        price_curve(
            battery_proportion=curve_range,
            stop_trigger=stop_trigger,
            threshold_trigger=charge_trigger,
        ),
        dtype=float,
    )

    # Main plot
    charge_trigger_plot.set_xlabel(charge_trigger_settings.x_label)
    charge_trigger_plot.set_xticks(charge_trigger_settings.x_ticks)
    charge_trigger_plot.set_xticklabels(charge_trigger_settings.xtick_labels)
    charge_trigger_plot.set_xlim(0, x_max)

    charge_trigger_plot.set_ylabel(charge_trigger_settings.y_label)
    charge_trigger_plot.set_yticks(charge_trigger_settings.y_ticks)
    charge_trigger_plot.set_yticklabels(charge_trigger_settings.ytick_labels)
    charge_trigger_plot.set_ylim(0, y_max)

    charge_trigger_plot.fill_between(
        x=curve_range,
        y1=0,
        y2=curve_values,
        color=want_charge_color,
        label='Wants to charge',
    )

    charge_trigger_plot.fill_between(
        x=curve_range,
        y1=curve_values,
        y2=y_max,
        color=not_want_charge_color,
        label='Does not want to charge',
    )

    charge_trigger_plot.axvspan(
        0,
        charge_trigger,
        color=want_charge_color,
    )

    charge_trigger_plot.axvspan(
        stop_trigger,
        x_max,
        color=not_want_charge_color,
    )

    charge_trigger_plot.plot(
        curve_range,
        curve_values,
        color=line_color,
    )

    charge_trigger_plot.vlines(
        x=stop_trigger,
        ymin=0,
        ymax=y_max,
        colors=line_color,
        linestyles=':',
    )

    charge_trigger_plot.vlines(
        x=charge_trigger,
        ymin=0,
        ymax=y_max,
        colors=line_color,
        linestyles=':',
    )

    # Inset background/frame
    inset_bounds: list[float] = charge_trigger_settings.inset_bounds
    inset_margin: float = charge_trigger_settings.inset_margin

    inset_background = Rectangle(
        (
            inset_bounds[0] - inset_margin,
            inset_bounds[1] - inset_margin,
        ),
        inset_bounds[2] + 2 * inset_margin,
        inset_bounds[3] + 2 * inset_margin,
        transform=charge_trigger_plot.transAxes,
        facecolor=inset_background_color,
        edgecolor='none',
        zorder=9,
    )

    charge_trigger_plot.add_patch(inset_background)

    # Inset
    inset_plot = charge_trigger_plot.inset_axes(
        bounds=inset_bounds,
        zorder=10,
    )

    inset_y_max: float = charge_trigger_settings.inset_y_max

    inset_plot.set_xlim(
        charge_trigger_settings.inset_x_min,
        charge_trigger_settings.inset_x_max,
    )
    inset_plot.set_ylim(
        0,
        inset_y_max,
    )

    # Opaque custom background.
    inset_plot.set_facecolor(inset_background_color)
    inset_plot.patch.set_alpha(1.0)
    inset_plot.set_zorder(10)

    # The inset uses custom colors so that the opaque background remains
    # visibly distinct from the main plot.
    inset_plot.fill_between(
        x=curve_range,
        y1=0,
        y2=curve_values,
        color=inset_want_charge_color,
    )

    inset_plot.fill_between(
        x=curve_range,
        y1=curve_values,
        y2=inset_y_max,
        color=inset_not_want_charge_color,
    )

    inset_plot.axvspan(
        0,
        charge_trigger,
        color=inset_want_charge_color,
    )

    inset_plot.axvspan(
        stop_trigger,
        x_max,
        color=inset_not_want_charge_color,
    )

    # Curve
    inset_plot.plot(
        curve_range,
        curve_values,
        color=line_color,
    )

    # Reference price -> curve
    inset_plot.hlines(
        y=reference_price,
        xmin=charge_trigger_settings.inset_x_min,
        xmax=midpoint,
        colors=line_color,
        linestyles='--',
    )

    # Curve -> midpoint
    inset_plot.vlines(
        x=midpoint,
        ymin=0,
        ymax=reference_price,
        colors=line_color,
        linestyles='--',
    )

    # Trigger lines
    inset_plot.vlines(
        x=charge_trigger,
        ymin=0,
        ymax=inset_y_max,
        colors=line_color,
        linestyles=':',
    )

    inset_plot.vlines(
        x=stop_trigger,
        ymin=0,
        ymax=inset_y_max,
        colors=line_color,
        linestyles=':',
    )

    # Inset ticks
    inset_plot.set_xticks(
        [
            charge_trigger,
            midpoint,
            stop_trigger,
        ]
    )
    inset_plot.set_xticklabels(
        [
            'Charge trigger',
            'Midpoint',
            'Charge stop',
        ],
        fontsize=charge_trigger_settings.inset_fontsize,
    )

    inset_plot.set_yticks(
        [
            0,
            reference_price,
            inset_y_max,
        ]
    )
    inset_plot.set_yticklabels(
        [
            '0',
            'Reference price',
            f'{inset_y_max:g}',
        ],
        fontsize=charge_trigger_settings.inset_fontsize,
    )

    inset_plot.tick_params(
        axis='both',
        length=0,
    )

    # Inset border
    for spine in inset_plot.spines.values():
        spine.set_color(line_color)
        spine.set_linewidth(charge_trigger_settings.inset_border_width)

    # Legend and layout
    charge_trigger_plot.legend(loc=charge_trigger_settings.legend_location)

    charge_trigger_figure.tight_layout()
    cook.save_figure(
        figure=charge_trigger_figure,
        figure_name='want_charge',
        output_folder='docs',
        dpi_to_use=file_settings.figures.dpi,
        file_formats=file_settings.figures.outputs,
    )

    return charge_trigger_figure



def make_plots() -> None:
    settings_path: Path = Path('explanations.toml')
    settings: Box = cook.parameters_from_TOML(settings_path)
    plot_settings: Box = settings.plots
    file_settings: Box = settings.files

    colors: Box = settings.colors

    charge_trigger_settings: Box = plot_settings.charge_trigger

    charge_trigger_figure: Figure = get_charge_trigger_figure(
        charge_trigger_settings=charge_trigger_settings,
        colors=colors,
        file_settings=file_settings,
    )
