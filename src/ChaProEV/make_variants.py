import typing as ty

import toml
from ETS_CookBook import ETS_CookBook as cook


def make_variants(scenario_name: str) -> None:
    variant_configuration: ty.Dict = cook.parameters_from_TOML(
        f'variants/{scenario_name}.toml'
    )

    for reference_scenario_name in variant_configuration[
        'reference_scenarios'
    ]:
        reference_scenario: ty.Dict = cook.parameters_from_TOML(
            f'scenarios/{scenario_name}/{reference_scenario_name}.toml'
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
                f'scenarios/{scenario_name}/{variant_name}.toml',
                'w',
                encoding='utf-8',
            ) as file_to_write:
                toml.dump(variant_scenarios[variant_name], file_to_write)


if __name__ == '__main__':
    case_name = 'Mopo'
    make_variants(case_name)
