'''
This module creates consumption tables
'''

import pandas as pd
from ETS_CookBook import ETS_CookBook as cook


def create_consumption_tables(scenario):
    '''
    Creates the consumption tables
    '''
    case_name = scenario['case_name']
    scenario_name = scenario['scenario']
    groupfile_root = scenario['files']['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    output_folder = scenario['files']['output_folder']
    groupfile_root = scenario['files']['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    output_folder = scenario['files']['output_folder']
    vehicle_parameters = scenario['vehicle']
    kilometers_column_for_consumption = vehicle_parameters[
        'kilometers_column_for_consumption'
    ]
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
            f'{scenario_name}_run_mobility_matrix',
            f'{output_folder}/{groupfile_name}.sqlite3',
        )
    )

    consumption_matrix['Time Tag'] = pd.to_datetime(
        consumption_matrix['Time Tag']
    )

    # We create a consumption matrix
    consumption_matrix = pd.DataFrame(
        consumption_matrix.set_index(['From', 'To', 'Time Tag'])[
            kilometers_source_column
        ]
    ).rename(columns={kilometers_source_column: 'Kilometers'})

    vehicle_base_consumptions_per_km = vehicle_parameters[
        'base_consumption_per_km'
    ]
    for energy_carrier in vehicle_base_consumptions_per_km:
        carrier_name = energy_carrier.split('_')[0]
        unit = energy_carrier.split('_')[1]
        base_consumption_per_km = vehicle_base_consumptions_per_km[
            energy_carrier
        ]
        consumption_matrix[f'{carrier_name} consumption {unit}'] = (
            consumption_matrix['Kilometers'].values * base_consumption_per_km
        )

    # We create a consumption table
    consumption_table = consumption_matrix.groupby(['Time Tag']).sum()

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
        f'{time_tag.year}' for time_tag in yearly_consumption_table.index
    ]
    yearly_consumption_table.index.name = 'Year'

    cook.save_dataframe(
        consumption_matrix,
        f'{scenario_name}_consumption_matrix',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        consumption_table,
        f'{scenario_name}_consumption_table',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        daily_consumption_table,
        f'{scenario_name}_daily_consumption_table',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        weekly_consumption_table,
        f'{scenario_name}_weekly_consumption_table',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        monthly_consumption_table,
        f'{scenario_name}_monthly_consumption_table',
        groupfile_name,
        output_folder,
        scenario,
    )
    cook.save_dataframe(
        yearly_consumption_table,
        f'{scenario_name}_yearly_consumption_table',
        groupfile_name,
        output_folder,
        scenario,
    )


def get_energy_for_next_leg(scenario):
    file_parameters = scenario['files']
    output_folder = file_parameters['output_folder']
    groupfile_root = file_parameters['groupfile_root']
    scenario_name = scenario['scenario']
    case_name = scenario['case_name']
    next_leg_kilometers = cook.read_table_from_database(
        f'{scenario_name}_next_leg_kilometers',
        f'{output_folder}/{groupfile_root}_{case_name}.sqlite3',
    )
    next_leg_kilometers['Time Tag'] = pd.to_datetime(
        next_leg_kilometers['Time Tag']
    )
    next_leg_kilometers = next_leg_kilometers.set_index('Time Tag')
    next_leg_kilometers_cumulative = cook.read_table_from_database(
        f'{scenario_name}_next_leg_kilometers_cumulative',
        f'{output_folder}/{groupfile_root}_{case_name}.sqlite3',
    )
    next_leg_kilometers_cumulative['Time Tag'] = pd.to_datetime(
        next_leg_kilometers_cumulative['Time Tag']
    )
    next_leg_kilometers_cumulative = next_leg_kilometers_cumulative.set_index(
        'Time Tag'
    )

    vehicle_parameters = scenario['vehicle']
    vehicle_base_consumptions_kWh_per_km = vehicle_parameters[
        'base_consumption_per_km'
    ]['electricity_kWh']
    consumption = pd.Series(
        [vehicle_base_consumptions_kWh_per_km]
        * len(next_leg_kilometers.index),
        index=next_leg_kilometers.index,
    )
    energy_for_next_leg = next_leg_kilometers.mul(consumption, axis=0)
    cook.save_dataframe(
        energy_for_next_leg,
        f'{scenario_name}_energy_for_next_leg',
        f'{groupfile_root}_{case_name}',
        output_folder,
        scenario,
    )
    energy_for_next_leg_cumulative = next_leg_kilometers_cumulative.mul(
        consumption, axis=0
    )
    cook.save_dataframe(
        energy_for_next_leg_cumulative,
        f'{scenario_name}_energy_for_next_leg_cumulative',
        f'{groupfile_root}_{case_name}',
        output_folder,
        scenario,
    )


def get_consumption_data(scenario):
    create_consumption_tables(scenario)
    get_energy_for_next_leg(scenario)


if __name__ == '__main__':
    scenario_file_name = 'scenarios/baseline.toml'
    scenario = cook.parameters_from_TOML(scenario_file_name)
    get_consumption_data(scenario)
