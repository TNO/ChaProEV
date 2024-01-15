'''
This module creates consumption tables
'''
import pandas as pd

from ETS_CookBook import ETS_CookBook as cook


def create_consumption_tables(parameters):
    '''
    Creates the consumption tables
    '''
    case_name = parameters['case_name']
    scenario = parameters['scenario']
    groupfile_root = parameters['files']['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    output_folder = parameters['files']['output_folder']
    groupfile_root = parameters['files']['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    output_folder = parameters['files']['output_folder']
    vehicle_parameters = parameters['vehicle']
    kilometers_column_for_consumption = (
        vehicle_parameters['kilometers_column_for_consumption']
    )
    use_weighted = vehicle_parameters['use_weighted']
    if use_weighted:
        kilometers_source_column = (
            f'{kilometers_column_for_consumption} weighted kilometers'
        )
    else:
        kilometers_source_column = (
            f'{kilometers_column_for_consumption} kilometers'
        )
    consumption_matrix = pd.DataFrame(
        cook.read_table_from_database(
            f'{scenario}_run_mobility_matrix',
            f'{output_folder}/{groupfile_name}.sqlite3'
        )
    )

    consumption_matrix['Time tag'] = pd.to_datetime(
        consumption_matrix['Time tag'])

    # We create a consumption matrix
    consumption_matrix = pd.DataFrame(
        consumption_matrix
        .set_index(['From', 'To', 'Time tag'])
        [kilometers_source_column]
    ).rename(columns={kilometers_source_column: 'Kilometers'})

    vehicle_base_consumptions_per_km = (
        vehicle_parameters['base_consumption_per_km']
    )
    for energy_carrier in vehicle_base_consumptions_per_km:
        carrier_name = energy_carrier.split('_')[0]
        unit = energy_carrier.split('_')[1]
        base_consumption_per_km = (
            vehicle_base_consumptions_per_km[energy_carrier]
        )
        consumption_matrix[f'{carrier_name} consumption {unit}'] = (
            consumption_matrix['Kilometers'].values * base_consumption_per_km
        )

    # We create a consumption table
    consumption_table = consumption_matrix.groupby(['Time tag']).sum()

    # We also create versions grouped by different time units
    daily_consumption_table = consumption_table.resample('D').sum()
    weekly_consumption_table = consumption_table.resample('W').sum()

    weekly_consumption_table.index = [
        f'Week {time_tag.isocalendar().week}, {time_tag.isocalendar().year}'
        for time_tag in weekly_consumption_table.index
    ]

    weekly_consumption_table.index.name = 'Week number'
    monthly_consumption_table = consumption_table.resample('M').sum()
    monthly_consumption_table.index = [
        f'{time_tag.strftime("%B")} {time_tag.year}'
        for time_tag in monthly_consumption_table.index
    ]
    monthly_consumption_table.index.name = 'Month'
    yearly_consumption_table = consumption_table.resample('Y').sum()
    yearly_consumption_table.index = [
        f'{time_tag.year}'
        for time_tag in yearly_consumption_table.index
    ]
    yearly_consumption_table.index.name = 'Year'

    cook.save_dataframe(
        consumption_matrix, f'{scenario}_consumption_matrix',
        groupfile_name, output_folder, parameters
    )
    cook.save_dataframe(
        consumption_table, f'{scenario}_consumption_table',
        groupfile_name, output_folder, parameters
    )
    cook.save_dataframe(
        daily_consumption_table, f'{scenario}_daily_consumption_table',
        groupfile_name, output_folder, parameters
    )
    cook.save_dataframe(
        weekly_consumption_table, f'{scenario}_weekly_consumption_table',
        groupfile_name, output_folder, parameters
    )
    cook.save_dataframe(
        monthly_consumption_table, f'{scenario}_monthly_consumption_table',
        groupfile_name, output_folder, parameters
    )
    cook.save_dataframe(
        yearly_consumption_table, f'{scenario}_yearly_consumption_table',
        groupfile_name, output_folder, parameters
    )


if __name__ == '__main__':

    parameters_file_name = 'scenarios/baseline.toml'
    parameters = cook.parameters_from_TOML(parameters_file_name)
    create_consumption_tables(parameters)
