
import pandas as pd

from ETS_CookBook import ETS_CookBook as cook




if __name__ == '__main__':

    parameters_file_name = 'scenarios/baseline.toml'
    parameters = cook.parameters_from_TOML(parameters_file_name)
    case_name = parameters['case_name']
    scenario = parameters['scenario']
    groupfile_root = parameters['files']['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    output_folder = parameters['files']['output_folder']
    groupfile_root = parameters['files']['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'
    output_folder = parameters['files']['output_folder']
    parameters_file_name = f'scenarios/{scenario}.toml'
    vehicle_parameters = parameters['vehicle']
    kilometers_column_for_consumption = (
        vehicle_parameters['kilometers_column_for_consumption']
    )
    use_weighted= vehicle_parameters['use_weighted']
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
        ).set_index(['From', 'To', 'Time tag'])[kilometers_source_column]
    ).rename(columns={kilometers_source_column:'Kilometers'})
    print(consumption_matrix)
    print(sum(consumption_matrix['Kilometers']))