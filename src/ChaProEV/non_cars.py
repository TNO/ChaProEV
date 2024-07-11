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


def get_run_kilometrage(scenario: ty.Dict) -> float:
    '''
    Gets the kilometrage over the whole run.
    '''

    yearly_kilometrage: float = scenario['vehicle']['yearly_kilometrage']
    run_duration_years: float = run_time.get_run_duration(scenario)[1]

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


def get_time_driving(
    run_driven_kilometers: pd.DataFrame, scenario: ty.Dict
) -> pd.DataFrame:
    '''
    This gets the time driving (%) in the run driven kilometers DataFrame
    '''
    day_types: ty.List[str] = scenario['mobility_module']['day_types']
    percent_time_driving_per_day_type: ty.Dict[str, ty.List[float]] = scenario[
        'mobility_module'
    ]['percent_time_driving']

    for day_type in day_types:
        for hour_index_from_day_start, time_driving in enumerate(
            percent_time_driving_per_day_type[day_type]
        ):
            run_driven_kilometers.loc[
                (run_driven_kilometers['Day Type'] == day_type)
                & (
                    run_driven_kilometers['Hour index from day start']
                    == hour_index_from_day_start
                ),
                'Time driving (%)',
            ] = time_driving
    run_time_driving: float = run_driven_kilometers['Time driving (%)'].sum()
    run_driven_kilometers['Percentage of run time driving (%)'] = (
        run_driven_kilometers['Time driving (%)'] / run_time_driving
    )
    return run_driven_kilometers


def compute_run_driven_kilometers(
    run_driven_kilometers: pd.DataFrame,
) -> pd.DataFrame:
    '''
    Adds the driven kilometers per time tag
    '''
    run_kilometrage: float = get_run_kilometrage(scenario)

    run_driven_kilometers['Driven kilometers (km)'] = (
        run_kilometrage
        * run_driven_kilometers['Percentage of run time driving (%)']
    )

    return run_driven_kilometers


def get_run_driven_kilometers(
    scenario: ty.Dict, case_name: str
) -> pd.DataFrame:
    '''
    This gets a DataFrame with kilometers driven per time tag.
    '''
    run_driven_kilometers: pd.DataFrame = (
        get_empty_run_driven_kilometers_dataframe(scenario)
    )
    run_driven_kilometers = get_time_driving(run_driven_kilometers, scenario)
    run_driven_kilometers = compute_run_driven_kilometers(
        run_driven_kilometers
    )

    scenario_name: str = scenario['scenario']

    file_parameters: ty.Dict = scenario['files']
    output_folder: str = f'{file_parameters["output_root"]}/{case_name}'
    groupfile_root: str = file_parameters['groupfile_root']
    groupfile_name: str = f'{groupfile_root}_{case_name}'

    cook.save_dataframe(
        run_driven_kilometers,
        f'{scenario_name}_tun_driven_kilometers',
        groupfile_name,
        output_folder,
        scenario,
    )

    return run_driven_kilometers


if __name__ == '__main__':
    case_name = 'local_impact_BEVs'
    scenario_file_name: str = f'scenarios/{case_name}/baseline.toml'
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)

    run_driven_kilometers = get_run_driven_kilometers(scenario, case_name)

    print(run_driven_kilometers)
    # Normal charge when act=0
    # or within the time driving
    # or bool for charging during active?
