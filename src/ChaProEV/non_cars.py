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

# total_km
# per hour: active % (<- per day type)
# do it over whole year --> hourly driven km --> hourly consumption
# have active and inactive chaging
# active only if battry drops below a given level and up to a given level
#  (only max power)
# inactive up to full level (can hacve strategy)


# Need kilometrage
# day_start_hour (might be different pewr vehicle type)
# activity levels per day type
# put these on whole run
# get kilometers of whole run
# divide --> kms per hour slot


def get_run_driven_kilometers(scenario: ty.Dict) -> pd.DataFrame:
    run_driven_kilometers: pd.DataFrame = run_time.get_time_stamped_dataframe(
        scenario, locations_as_columns=False
    )
    run_driven_kilometers['Driven kilometers (km)'] = np.empty(
        len(run_driven_kilometers.index)
    )
    run_driven_kilometers['Driven kilometers (km)'] = np.nan

    return run_driven_kilometers


if __name__ == '__main__':
    scenario_file_name: str = 'scenarios/baseline.toml'
    scenario: ty.Dict = cook.parameters_from_TOML(scenario_file_name)

    run_driven_kilometers = get_run_driven_kilometers(scenario)
    print(run_driven_kilometers)
