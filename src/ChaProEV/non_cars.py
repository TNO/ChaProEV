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


# have active and inactive chaging
# active only if battry drops below a given level and up to a given level
#  (only max power)
# inactive up to full level (can hacve strategy)

# consumption then battery track
# two locs: underway and depot/overnight, each with connectivity and power
# hours at depot (maybe per day type)
# use hour in day in car module

# and does not include vheicle name --> stop program (option to switch it off)


def get_run_kilometrage(
    scenario: ty.Dict, general_parameters: ty.Dict
) -> float:
    '''
    Gets the kilometrage over the whole run.
    '''

    yearly_kilometrage: float = scenario['vehicle']['yearly_kilometrage']
    run_duration_years: float = run_time.get_run_duration(
        scenario, general_parameters
    )[1]

    run_kilometrage: float = yearly_kilometrage * run_duration_years

    return run_kilometrage


def get_empty_run_driven_kilometers_dataframe(
    scenario: ty.Dict,
) -> pd.DataFrame:
    '''
    Makes the empty DataFrame where we get kilometers driven per time tag
    '''

    run_driven_kilometers: pd.DataFrame = run_time.get_time_stamped_dataframe(
        scenario, locations_as_columns=False
    )

    kilometers_driven_headers: ty.List[str] = scenario['mobility_module'][
        'kilometers_driven_headers'
    ]

    run_driven_kilometers[kilometers_driven_headers] = np.empty(
        (len(run_driven_kilometers.index), len(kilometers_driven_headers))
    )

    run_driven_kilometers[kilometers_driven_headers] = np.nan

    return run_driven_kilometers


def get_time_proportions(
    run_driven_kilometers: pd.DataFrame, scenario: ty.Dict
) -> pd.DataFrame:
    '''
    This gets the time proportions (driving, at base, idle while en route)
    in the run driven kilometers DataFrame
    '''
    day_types: ty.List[str] = scenario['mobility_module']['day_types']

    percent_time_at_base_per_day_type: ty.Dict[str, ty.List[float]] = scenario[
        'mobility_module'
    ]['percent_time_at_base']

    percent_driving_when_not_at_base_per_day_type: ty.Dict[
        str, ty.List[float]
    ] = scenario['mobility_module']['percent_driving_when_not_at_base']

    percent_time_driving_per_day_type: ty.Dict[str, ty.List[float]] = {}
    percent_time_idle_en_route_per_day_type: ty.Dict[str, ty.List[float]] = {}

    for day_type in day_types:
        percent_time_driving_per_day_type[day_type] = [
            (1 - this_hour_percent_time_at_base_per_day_type)
            * this_hour_percent_driving_when_not_at_base_per_day_type
            for (
                this_hour_percent_time_at_base_per_day_type,
                this_hour_percent_driving_when_not_at_base_per_day_type,
            ) in zip(
                percent_time_at_base_per_day_type[day_type],
                percent_driving_when_not_at_base_per_day_type[day_type],
            )
        ]

        percent_time_idle_en_route_per_day_type[day_type] = [
            (1 - this_hour_percent_time_at_base_per_day_type)
            * (1 - this_hour_percent_driving_when_not_at_base_per_day_type)
            for (
                this_hour_percent_time_at_base_per_day_type,
                this_hour_percent_driving_when_not_at_base_per_day_type,
            ) in zip(
                percent_time_at_base_per_day_type[day_type],
                percent_driving_when_not_at_base_per_day_type[day_type],
            )
        ]

    for day_type in day_types:
        for hour_index_from_day_start, (
            time_driving,
            time_at_base,
            time_idle,
        ) in enumerate(
            zip(
                percent_time_driving_per_day_type[day_type],
                percent_time_at_base_per_day_type[day_type],
                percent_time_idle_en_route_per_day_type[day_type],
            )
        ):
            run_driven_kilometers.loc[
                (run_driven_kilometers['Day Type'] == day_type)
                & (
                    run_driven_kilometers['Hour index from day start']
                    == hour_index_from_day_start
                ),
                'Proportion driving',
            ] = time_driving

            run_driven_kilometers.loc[
                (run_driven_kilometers['Day Type'] == day_type)
                & (
                    run_driven_kilometers['Hour index from day start']
                    == hour_index_from_day_start
                ),
                'Proportion at base',
            ] = time_at_base

            run_driven_kilometers.loc[
                (run_driven_kilometers['Day Type'] == day_type)
                & (
                    run_driven_kilometers['Hour index from day start']
                    == hour_index_from_day_start
                ),
                'Proportion idle en route',
            ] = time_idle

    run_time_driving: float = run_driven_kilometers['Proportion driving'].sum()
    run_driven_kilometers['Proportion of run time driving'] = (
        run_driven_kilometers['Proportion driving'] / run_time_driving
    )
    return run_driven_kilometers


def compute_run_driven_kilometers(
    run_driven_kilometers: pd.DataFrame, general_parameters: ty.Dict
) -> pd.DataFrame:
    '''
    Adds the driven kilometers per time tag
    '''
    run_kilometrage: float = get_run_kilometrage(scenario, general_parameters)

    run_driven_kilometers['Driven kilometers (km)'] = (
        run_kilometrage
        * run_driven_kilometers['Proportion of run time driving']
    )

    return run_driven_kilometers


def get_run_driven_kilometers(
    scenario: ty.Dict, case_name: str, general_parameters: ty.Dict
) -> pd.DataFrame:
    '''
    This gets a DataFrame with kilometers driven per time tag.
    '''
    run_driven_kilometers: pd.DataFrame = (
        get_empty_run_driven_kilometers_dataframe(scenario)
    )
    run_driven_kilometers = get_time_proportions(
        run_driven_kilometers, scenario
    )
    run_driven_kilometers = compute_run_driven_kilometers(
        run_driven_kilometers, general_parameters
    )

    scenario_name: str = scenario['scenario_name']

    file_parameters: ty.Dict = general_parameters['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'

    run_driven_kilometers.to_pickle(
        f'{output_folder}/{scenario_name}_run_driven_kilometers.pkl'
    )

    return run_driven_kilometers


if __name__ == '__main__':
    print('Not currently in use')
    exit()
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: ty.Dict = cook.parameters_from_TOML(
        general_parameters_file_name
    )
    case_name = 'local_impact_BEVs'
    test_scenario_name: str = 'baseline'
    scenario_file_name: str = (
        f'scenarios/{case_name}/{test_scenario_name}.toml'
    )
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)
    scenario['scenario_name'] = test_scenario_name

    run_driven_kilometers = get_run_driven_kilometers(
        scenario, case_name, general_parameters
    )

    print(run_driven_kilometers)
    # Normal charge when act=0
    # or within the time driving
    # or bool for charging during active?
    # track charge and discharge
    # energy for next leg (is it relevant?)
