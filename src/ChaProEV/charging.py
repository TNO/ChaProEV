import datetime
import math
import typing as ty

import numpy as np
import pandas as pd
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


try:
    import define  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import define  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again

try:
    import mobility  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import mobility  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


def get_charging_framework(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> ty.Tuple[
    ty.Dict[str, pd.DataFrame],
    pd.DatetimeIndex,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.Series,
]:
    '''
    Produces the structures we want for the charging profiles
    '''

    run_range, run_hour_numbers = run_time.get_time_range(
        scenario, general_parameters
    )

    vehicle_parameters: ty.Dict = scenario['vehicle']
    vehicle_name: str = vehicle_parameters['name']
    location_parameters: ty.Dict[str, ty.Dict[str, float]] = scenario[
        'locations'
    ]
    location_names: ty.List[str] = [
        location_name
        for location_name in location_parameters
        if location_parameters[location_name]['vehicle'] == vehicle_name
    ]
    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict[str, str] = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    location_split_table_name: str = f'{scenario_name}_location_split'
    location_split: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{location_split_table_name}.pkl'
    )

    # We create a dictionary of various battery spaces that are available
    # at each charging location (i.e. percent of vehicles with
    # a given battery space per location) (locations are keys and
    # battery space dataframes are dictionary entries)
    battery_space: ty.Dict[str, pd.DataFrame] = {}
    for location_name in location_names:
        battery_space[location_name] = pd.DataFrame(
            run_range, columns=['Time Tag']
        )
        # battery_space[0] float(0)
        battery_space[location_name] = battery_space[location_name].set_index(
            ['Time Tag']
        )
        battery_space[location_name][float(0)] = float(0)

        battery_space[location_name].loc[run_range[0], 0] = location_split.loc[
            run_range[0]
        ][location_name]

    # We read the run's mobility matrix as well as specific elements of it
    run_mobility_matrix: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_run_mobility_matrix.pkl',
    ).astype(float)
    run_arrivals_impact: pd.Series = run_mobility_matrix[
        'Arrivals impact'
    ].copy()

    battery_space_shift_arrivals_impact: pd.DataFrame = pd.read_pickle(
        f'{output_folder}/{scenario_name}_'
        f'run_battery_space_shifts_departures_impact.pkl'
    )

    # We create the Dataframes for the charge drawn
    charge_drawn_by_vehicles: pd.DataFrame = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )
    charge_drawn_by_vehicles.index.name = 'Time Tag'
    charge_drawn_from_network = pd.DataFrame(
        np.zeros((len(run_range), len(location_names))),
        columns=location_names,
        index=run_range,
    )
    charge_drawn_from_network.index.name = 'Time Tag'

    return (
        battery_space,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        battery_space_shift_arrivals_impact,
        run_arrivals_impact,
    )


def get_charging_profile(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> ty.Tuple[ty.Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    '''
    This is the main function of the charging module.
    It produces the charging profile
    '''

    (
        battery_space,
        run_range,
        run_mobility_matrix,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
        battery_space_shift_arrivals_impact,
        run_arrivals_impact,
    ) = get_charging_framework(scenario, case_name, general_parameters)
    print(run_mobility_matrix)

    return battery_space, charge_drawn_by_vehicles, charge_drawn_from_network


if __name__ == '__main__':
    case_name = 'local_impact_BEVs'
    test_scenario_name: str = 'baseline'
    case_name = 'Mopo'
    test_scenario_name = 'XX_truck'
    scenario_file_name: str = (
        f'scenarios/{case_name}/{test_scenario_name}.toml'
    )
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
    scenario['scenario_name'] = test_scenario_name
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: ty.Dict = cook.parameters_from_TOML(
        general_parameters_file_name
    )

    start_: datetime.datetime = datetime.datetime.now()
    (
        battery_space,
        charge_drawn_by_vehicles,
        charge_drawn_from_network,
    ) = get_charging_profile(scenario, case_name, general_parameters)
    print((datetime.datetime.now() - start_).total_seconds())
