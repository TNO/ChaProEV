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

    non_road_parametrs_file: str = 'non_road.toml'
    non_road_parameters: box.Box = box.Box(
        cook.parameters_from_TOML(non_road_parametrs_file)
    )
    run_demand: float = 1000
    run_start: datetime.datetime = datetime.datetime(2018, 1, 1, 0)
    run_end: datetime.datetime = datetime.datetime(2018, 1, 1, 0)
    frequency: str = 'w'
    profile_name: str = 'NL_air_2050'
    profile_parameters: box.Box = non_road_parameters[profile_name]

    run_demand_profile: pd.Series = get_profile(
        run_demand, run_start, run_end, frequency, profile_parameters
    )

    print(run_demand_profile)
