
import pandas as pd


import cookbook as cook


def get_trip_probabilities_per_day_type(parameters_file_name):
    parameters = cook.parameters_from_TOML(parameters_file_name)
    trip_list = list(parameters['trips'].keys())
    mobility_module_parameters = parameters['mobility_module']
    day_types = mobility_module_parameters['day_types']
    trip_probabilities_per_day_type = pd.DataFrame(
        columns = day_types, index = trip_list
    )
    return trip_probabilities_per_day_type

if __name__ == '__main__':
    parameters_file_name = 'scenarios/baseline.toml'
    trip_probabilities_per_day_type = get_trip_probabilities_per_day_type(
        parameters_file_name
    )

    print(trip_probabilities_per_day_type)