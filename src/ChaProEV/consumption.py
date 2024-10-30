'''
This module creates consumption tables
'''

import typing as ty

import numpy as np
import pandas as pd
from ETS_CookBook import ETS_CookBook as cook


def create_consumption_tables(
    run_mobility_matrix: pd.DataFrame,
    scenario: ty.Dict,
    case_name: str,
    general_parameters: ty.Dict,
) -> None:
    '''
    Creates the consumption tables
    '''
    scenario_name: str = scenario['scenario_name']
    output_folder: str = (
        f'{general_parameters["files"]["output_root"]}/{case_name}'
    )
    vehicle_parameters: ty.Dict = scenario['vehicle']
    kilometers_column_for_consumption: str = vehicle_parameters[
        'kilometers_column_for_consumption'
    ]
    use_weighted: bool = vehicle_parameters['use_weighted']
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

    vehicle_base_consumptions_per_km: ty.Dict[str, float] = vehicle_parameters[
        'base_consumption_per_km'
    ]
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
    pickle_interim_files: bool = general_parameters['interim_files']['pickle']
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
        
    consumption_tables_frequencies: ty.List[str] = general_parameters[
        'interim_files'
    ]['consumption_tables_frequencies']
    save_consumption_table: ty.List[bool] = general_parameters[
        'interim_files'
    ]['save_consumption_table']
    is_consumption_table_saved: ty.Dict[str, bool] = dict(
        zip(consumption_tables_frequencies, save_consumption_table)
    )
    if is_consumption_table_saved['hourly']:
        consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_consumption_table.pkl'
        )
    if is_consumption_table_saved['daily']:
        daily_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_daily_consumption_table.pkl'
        )
    if is_consumption_table_saved['weekly']:
        weekly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_weekly_consumption_table.pkl'
        )
    if is_consumption_table_saved['monthly']:
        monthly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_monthly_consumption_table.pkl'
        )
    if is_consumption_table_saved['yearly']:
        yearly_consumption_table.to_pickle(
            f'{output_folder}/{scenario_name}_yearly_consumption_table.pkl'
        )


def get_energy_for_next_leg(
    next_leg_kilometers: pd.DataFrame,
    next_leg_kilometers_cumulative: pd.DataFrame,
    scenario: ty.Dict,
    case_name: str,
    general_parameters: ty.Dict,
) -> None:
    file_parameters: ty.Dict = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    scenario_name: str = scenario['scenario_name']

    vehicle_parameters: ty.Dict = scenario['vehicle']
    vehicle_base_consumptions_kWh_per_km: float = vehicle_parameters[
        'base_consumption_per_km'
    ]['electricity_kWh']
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
    pickle_interim_files: bool = general_parameters['interim_files']['pickle']
    if pickle_interim_files:
        energy_for_next_leg.to_pickle(
            f'{output_folder}/{scenario_name}_energy_for_next_leg.pkl'
        )
        energy_for_next_leg_cumulative.to_pickle(
            f'{output_folder}/{scenario_name}'
            '_energy_for_next_leg_cumulative.pkl'
        )


def get_consumption_data(
    run_mobility_matrix: pd.DataFrame,
    next_leg_kilometers: pd.DataFrame,
    next_leg_kilometers_cumulative: pd.DataFrame,
    scenario: ty.Dict,
    case_name: str,
    general_parameters: ty.Dict,
) -> None:
    create_consumption_tables(
        run_mobility_matrix, scenario, case_name, general_parameters
    )
    get_energy_for_next_leg(
        next_leg_kilometers,
        next_leg_kilometers_cumulative,
        scenario,
        case_name,
        general_parameters,
    )


if __name__ == '__main__':
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: ty.Dict = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    case_name = 'Mopo'
    scenario_name: str = 'XX_car'
    scenario_file_name: str = f'scenarios/{case_name}/{scenario_name}.toml'
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
    scenario['scenario_name'] = scenario_name
    output_folder: str = (
        f'{general_parameters["files"]["output_root"]}/{case_name}'
    )
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
    get_consumption_data(
        run_mobility_matrix,
        next_leg_kilometers,
        next_leg_kilometers_cumulative,
        scenario,
        case_name,
        general_parameters,
    )
