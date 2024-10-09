import os
import typing as ty

import pandas as pd
import toml
from ETS_CookBook import ETS_CookBook as cook


def make_variants(case_name: str, csv_version: bool = True) -> None:

    if csv_version:
        make_csv_variants(case_name)
    else:
        make_toml_variants(case_name)


def make_csv_variants(case_name: str) -> None:
    '''
    This uses a csv, with commas as separators.
    If you want to put a list as a value, do it as such:
    "[1, 2.5, 5]" 
    (with the quotes: note that this is not necessary in Excel, where you can
    just put the list with brackets without the quotes)
    '''

    variant_files_folder: str = f'variants/{case_name}/'
    variant_files: ty.List[str] = os.listdir(variant_files_folder)
    for variant_file in variant_files:

        reference_scenario_name: str = variant_file.split('.')[0]

        reference_scenario: ty.Dict = cook.parameters_from_TOML(
            f'scenarios/{case_name}/{reference_scenario_name}.toml'
        )

        variant_data: pd.DataFrame = pd.read_csv(
            f'{variant_files_folder}/{variant_file}'
        ).set_index('Variant name')

        variant_names: ty.List[str] = list(variant_data.index)

        for variant_name in variant_names:

            variant_scenario: ty.Dict = reference_scenario.copy()

            for quantity_string in variant_data.columns:

                variant_name_list = quantity_string.split('.')
                variant_value = variant_data.loc[variant_name][quantity_string]

                if isinstance(variant_value, float):
                    variant_value = float(variant_value)
                elif variant_value.startswith('['):
                    variant_value = variant_value.replace('[', '')
                    variant_value = variant_value.replace(']', '')
                    variant_value = variant_value.split(',')
                    variant_value = [
                        float(value_item) for value_item in variant_value
                    ]

                cook.set_nested_value(
                    variant_scenario, variant_name_list, variant_value
                )

            with open(
                f'scenarios/{case_name}/{variant_name}.toml',
                'w',
                encoding='utf-8',
            ) as file_to_write:
                toml.dump(variant_scenario, file_to_write)


def make_toml_variants(case_name: str) -> None:
    variant_configuration: ty.Dict = cook.parameters_from_TOML(
        f'variants/{case_name}.toml'
    )

    for reference_scenario_name in variant_configuration[
        'reference_scenarios'
    ]:
        reference_scenario: ty.Dict = cook.parameters_from_TOML(
            f'scenarios/{case_name}/{reference_scenario_name}.toml'
        )

        variant_names: ty.List[str] = variant_configuration[
            'reference_scenarios'
        ][reference_scenario_name]['variants']

        variant_scenarios: ty.Dict[str, ty.Dict] = {}
        for variant_name in variant_names:
            variant_scenarios[variant_name] = reference_scenario.copy()

        modified_parameters: ty.Dict = variant_configuration[
            'reference_scenarios'
        ][reference_scenario_name]['modified_parameters']

        modified_parameters_names: ty.List[ty.List[str]] = []

        for modified_parameter in modified_parameters:
            this_modification_names: ty.List[str] = [modified_parameter]
            next_step_in_modification = modified_parameters[modified_parameter]
            next_level: str = list(next_step_in_modification.keys())[0]
            while next_level not in variant_names:

                this_modification_names.append(next_level)
                next_step_in_modification = next_step_in_modification[
                    next_level
                ]
                next_level = list(next_step_in_modification.keys())[0]

            modified_parameters_names.append(this_modification_names)

        for modified_parameter_names in modified_parameters_names:
            for variant_name in variant_names:
                variant_scenario = variant_scenarios[variant_name]

                variant_nested_keys: ty.List[str] = (
                    modified_parameter_names + [variant_name]
                )
                modified_value = cook.get_nested_value(
                    modified_parameters, variant_nested_keys
                )
                cook.set_nested_value(
                    variant_scenario, modified_parameter_names, modified_value
                )

        for variant_name in variant_names:
            with open(
                f'scenarios/{case_name}/{variant_name}.toml',
                'w',
                encoding='utf-8',
            ) as file_to_write:
                toml.dump(variant_scenarios[variant_name], file_to_write)


if __name__ == '__main__':
    case_name = 'Mopo'
    csv_version = True
    make_variants(case_name, csv_version)
