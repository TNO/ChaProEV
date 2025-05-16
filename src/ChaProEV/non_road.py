'''
Functions for non-road transport modes
'''

import datetime
from itertools import repeat
from multiprocessing import Pool

import box
import pandas as pd
import tqdm
from ETS_CookBook import ETS_CookBook as cook
from rich import print


def get_profile(
    run_demand: float,
    run_start: datetime.datetime,
    run_end: datetime.datetime,
    frequency: str,
    profile_parameters: box.Box,
) -> pd.Series:

    run_demand_profile: pd.Series = pd.Series()

    return run_demand_profile


if __name__ == '__main__':

    case_name: str = 'Mopo'

    non_road_parametrs_file: str = f'non-road/{case_name}/non-road.toml'
    non_road_parameters: box.Box = box.Box(
        cook.parameters_from_TOML(non_road_parametrs_file)
    )
    run_demand: float = 1000

    profile_name: str = 'NL_air_2050'
    profile_parameters: box.Box = non_road_parameters[profile_name]

    run_start_parameters: box.Box = profile_parameters.run_start
    run_start: datetime.datetime = datetime.datetime(
        run_start_parameters.year,
        run_start_parameters.month,
        run_start_parameters.day,
        run_start_parameters.hour,
    )
    run_end_parameters: box.Box = profile_parameters.run_end
    run_end: datetime.datetime = datetime.datetime(
        run_end_parameters.year,
        run_end_parameters.month,
        run_end_parameters.day,
        run_end_parameters.hour,
    )
    frequency: str = profile_parameters.frequency

    run_demand_profile: pd.Series = get_profile(
        run_demand, run_start, run_end, frequency, profile_parameters
    )

    print(run_demand_profile)
