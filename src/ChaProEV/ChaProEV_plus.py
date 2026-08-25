from dataclasses import dataclass
from datetime import date, datetime, timedelta, time
from pathlib import Path

import numpy as np
import polars as pl
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print


try:
    import define_plus  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import define_plus  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


try:
    import mobility_plus  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import mobility_plus  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again



try:
    import charging_plus  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import charging_plus  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again




if __name__ == '__main__':
    scenario_path: Path = Path('scenarios/plus/test.toml')
    scenario: Box = cook.parameters_from_TOML(scenario_path)

    for _ in range(1):
        (
            time_ranges,
            run_trips,
            base_trips,
            locations,
            random_generator,
        ) = define_plus.define_user(scenario=scenario)

        mobility_matrix: pl.DataFrame = mobility_plus.compute_mobility_matrix(
            time_ranges=time_ranges,
            run_trips=run_trips,
            base_trips=base_trips,
            scenario=scenario,
        )

        charging_dataframe, charging_averages = charging_plus.compute_charging(
            mobility_matrix=mobility_matrix,
            locations=locations,
            scenario=scenario,
            random_generator=random_generator,
        )
        # print(charging_dataframe)
        print(charging_dataframe['Power to vehicle (kW)'].sum() / 60)
        with pl.Config(tbl_rows=26):
            print(charging_averages)
        # input()