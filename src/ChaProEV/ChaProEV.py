'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This is where you run the model
'''

import typing as ty
from itertools import repeat
from multiprocessing import Pool

import tqdm
from box import Box
from ETS_CookBook import ETS_CookBook as cook

try:
    import writing  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import writing  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


try:
    import make_variants  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import make_variants  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


try:
    import profiles  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import profiles  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again

try:
    import scenarios_module  # type: ignore

    # We need to ignore the type because mypy has its own search path for
    # imports and does not resolve imports exactly as Python does and it
    # isn't able to find the module.
    # https://stackoverflow.com/questions/68695851/mypy-cannot-find-implementation-or-library-stub-for-module
except ModuleNotFoundError:
    from ChaProEV import scenarios_module  # type: ignore
# So that it works both as a standalone (1st) and as a package (2nd)
# We need to add to type: ignore thing to avoid MypY thinking
# we are importing again


@cook.function_timer
def run_ChaProEV(case_name: str) -> None:
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: Box = Box(
        cook.parameters_from_TOML(general_parameters_file_name)
    )
    output_root: str = general_parameters.files.output_root
    cook.check_if_folder_exists(f'{output_root}/{case_name}')
    variant_parameters: Box = general_parameters.variants
    use_variants: bool = variant_parameters.use_variants
    if use_variants:
        csv_version: bool = variant_parameters.csv_version
        make_variants.make_variants(case_name, csv_version)

    scenarios: list[Box] = scenarios_module.load_scenarios(case_name)

    set_amount_of_processes: bool = (
        general_parameters.parallel_processing.set_amount_of_processes
    )
    if set_amount_of_processes:
        amount_of_parallel_processes: int | None = None
    else:
        amount_of_parallel_processes = (
            general_parameters.parallel_processing.amount_for_scenarios
        )

    pool_inputs: ty.Iterator[tuple[Box, str, Box]] | ty.Any = zip(
        scenarios, repeat(case_name), repeat(general_parameters)
    )
    # the ty.Any alternative is there because transforming it with the
    # progress bar makes mypy think it change is type
    progress_bars_parameters: Box = general_parameters.progress_bars
    display_scenario_run: bool = progress_bars_parameters.display_scenario_run
    scenario_run_description: str = (
        progress_bars_parameters.scenario_run_description
    )
    if display_scenario_run:
        pool_inputs = tqdm.tqdm(
            pool_inputs,
            desc=scenario_run_description,
            total=len(scenarios),
        )

    with Pool(amount_of_parallel_processes) as scenarios_pool:
        scenarios_pool.starmap(scenarios_module.run_scenario, pool_inputs)

    do_car_home_type_split: bool = (
        general_parameters.home_type.do_car_home_type_split
    )
    if do_car_home_type_split:
        profiles.car_home_parking(case_name, general_parameters)

    writing.extra_end_outputs(case_name, general_parameters)


if __name__ == '__main__':
    # This is a case name, which is the grouping of all your scenarios.
    # This is principally used to label your output files.
    case_name = 'Mopo'

    run_ChaProEV(case_name)

    # print('Add sessions into next day')
    # print('Iterate through sessions and send remainder to next session')
    # print('Compute session first pass')
    # print('Do a second compute with passthrough')
    # print('Convert session-basec charge to profile')
    # print('Have parameter that shifts within a session?')
    # print('Do kilometers/consumption split for sessions?')
    # print('Do effetive session end andthen a match between the approaches')
    # print('Make profile DF (with all) from sessions version')
    # print('Make fleet version')
    # print('Compare profiles')
    # Add actual stop time (if using full power)
    # Then infer profiles
    # DO this in a sperate DF that will be used to compare
    # COnnectivity: does the groupneed to be smaller?
    # Also somehow include legs from before that did not charge because
    # of connectivity
    # Base profile is spread according to partial arrivals.
