'''
This module creates consumption tables
'''

import numpy as np
import pandas as pd
from box import Box
from ETS_CookBook import ETS_CookBook as cook

try:
    import run_time  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import run_time  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


def create_consumption_tables(
    run_mobility_matrix: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> pd.DataFrame:
    '''
    Creates the consumption tables
    '''
    scenario_name: str = scenario.name
    output_folder: str = f'{general_parameters.files.output_root}/{case_name}'
    vehicle_parameters: Box = scenario.vehicle
    kilometers_column_for_consumption: str = (
        vehicle_parameters.kilometers_column_for_consumption
    )

    use_weighted: bool = vehicle_parameters.use_weighted
    if use_weighted:
        kilometers_source_column: str = (
            f'{kilometers_column_for_consumption} weighted kilometers'
        )
    else:
        kilometers_source_column = (
            f'{kilometers_column_for_consumption} kilometers'
        )
    consumption_matrix: pd.DataFrame = run_mobility_matrix

    # We rearrange the matrix
    consumption_matrix = (
        pd.DataFrame(consumption_matrix[kilometers_source_column])
        .rename(columns={kilometers_source_column: 'Kilometers'})
        .astype(float)
    )

    vehicle_base_consumptions_per_km: Box = (
        vehicle_parameters.base_consumption_per_km
    )

    kilometers: np.ndarray = np.array(
        pd.Series(consumption_matrix['Kilometers']).values
    )

    for energy_carrier in vehicle_base_consumptions_per_km:
        carrier_name: str = energy_carrier.split('_')[0]
        unit: str = energy_carrier.split('_')[1]
        base_consumption_per_km: float = vehicle_base_consumptions_per_km[
            energy_carrier
        ]
        consumption_matrix[f'{carrier_name} consumption {unit}'] = (
            kilometers * base_consumption_per_km
        )

    # We create a consumption table
    consumption_table: pd.DataFrame = consumption_matrix.groupby(
        ['Time Tag']
    ).sum()

    display_range = run_time.get_time_range(scenario, general_parameters)[2]

    consumption_table = consumption_table.loc[display_range]

    # We also create versions grouped by different time units
    daily_consumption_table: pd.DataFrame = consumption_table.resample(
        'D'
    ).sum()
    weekly_consumption_table: pd.DataFrame = consumption_table.resample(
        'W'
    ).sum()

    weekly_consumption_table.index = pd.Index(
        [
            f'Week {time_tag.isocalendar().week}, '
            f'{time_tag.isocalendar().year}'
            for time_tag in weekly_consumption_table.index
        ]
    )

    weekly_consumption_table.index.name = 'Week number'
    monthly_consumption_table: pd.DataFrame = consumption_table.resample(
        'ME'
    ).sum()
    monthly_consumption_table.index = pd.Index(
        [
            f'{time_tag.strftime("%B")} {time_tag.year}'
            for time_tag in monthly_consumption_table.index
        ]
    )
    monthly_consumption_table.index.name = 'Month'
    yearly_consumption_table: pd.DataFrame = consumption_table.resample(
        'YE'
    ).sum()
    yearly_consumption_table.index = pd.Index(
        [f'{time_tag.year}' for time_tag in yearly_consumption_table.index]
    )
    yearly_consumption_table.index.name = 'Year'
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    if pickle_interim_files:
        consumption_matrix.to_pickle(
            f'{output_folder}/{scenario_name}_consumption_matrix.pkl'
        )
        consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_consumption_table.pkl'
        )
        daily_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_daily_consumption_table.pkl'
        )
        weekly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_weekly_consumption_table.pkl'
        )
        monthly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_monthly_consumption_table.pkl'
        )
        yearly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_yearly_consumption_table.pkl'
        )

    consumption_tables_frequencies: list[
        str
    ] = general_parameters.interim_files.consumption_tables_frequencies
    save_consumption_table: list[
        bool
    ] = general_parameters.interim_files.save_consumption_table
    is_consumption_table_saved: Box = Box(
        dict(zip(consumption_tables_frequencies, save_consumption_table))
    )
    if is_consumption_table_saved.hourly:
        consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_consumption_table.pkl'
        )
    if is_consumption_table_saved.daily:
        daily_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_daily_consumption_table.pkl'
        )
    if is_consumption_table_saved.weekly:
        weekly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_weekly_consumption_table.pkl'
        )
    if is_consumption_table_saved.monthly:
        monthly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_monthly_consumption_table.pkl'
        )
    if is_consumption_table_saved.yearly:
        yearly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_yearly_consumption_table.pkl'
        )
    return consumption_table


def get_energy_for_next_leg(
    next_leg_kilometers: pd.DataFrame,
    next_leg_kilometers_cumulative: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> None:
    file_parameters: Box = general_parameters.files
    output_folder: str = f'{file_parameters.output_root}/{case_name}'
    scenario_name: str = scenario.name

    vehicle_parameters: Box = scenario.vehicle
    vehicle_base_consumptions_kWh_per_km: float = (
        vehicle_parameters.base_consumption_per_km.electricity_kWh
    )
    consumption: pd.Series[float] = pd.Series(
        [vehicle_base_consumptions_kWh_per_km]
        * len(next_leg_kilometers.index),
        index=next_leg_kilometers.index,
    )
    energy_for_next_leg: pd.DataFrame = next_leg_kilometers.mul(
        consumption, axis=0
    )
    energy_for_next_leg_cumulative: pd.DataFrame = (
        next_leg_kilometers_cumulative.mul(consumption, axis=0)
    )
    pickle_interim_files: bool = general_parameters.interim_files.pickle
    if pickle_interim_files:
        energy_for_next_leg.to_pickle(
            f'{output_folder}/{scenario_name}_energy_for_next_leg.pkl'
        )
        energy_for_next_leg_cumulative.to_pickle(
            f'{output_folder}/{scenario_name}'
            '_energy_for_next_leg_cumulative.pkl'
        )


# @cook.function_timer
def get_consumption_data(
    run_mobility_matrix: pd.DataFrame,
    next_leg_kilometers: pd.DataFrame,
    next_leg_kilometers_cumulative: pd.DataFrame,
    scenario: Box,
    case_name: str,
    general_parameters: Box,
) -> pd.DataFrame:
    consumption_table = create_consumption_tables(
        run_mobility_matrix, scenario, case_name, general_parameters
    )
    get_energy_for_next_leg(
        next_leg_kilometers,
        next_leg_kilometers_cumulative,
        scenario,
        case_name,
        general_parameters,
    )
    return consumption_table


if __name__ == '__main__':
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: Box = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    case_name = 'Mopo'
    scenario_name: str = 'XX_car'
    scenario_file_name: str = f'scenarios/{case_name}/{scenario_name}.toml'
    scenario: Box = cook.parameters_from_TOML(scenario_file_name)
    scenario.name = scenario_name
    output_folder: str = f'{general_parameters.files.output_root}/{case_name}'
    run_mobility_matrix = pd.DataFrame(
        pd.read_pickle(
            f'{output_folder}/{scenario_name}_run_mobility_matrix.pkl',
        )
    )
    next_leg_kilometers: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_next_leg_kilometers.pkl',
    )
    next_leg_kilometers_cumulative: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_'
        'next_leg_kilometers_cumulative.pkl',
    )
    consumption_table: pd.DataFrame = get_consumption_data(
        run_mobility_matrix,
        next_leg_kilometers,
        next_leg_kilometers_cumulative,
        scenario,
        case_name,
        general_parameters,
    )
