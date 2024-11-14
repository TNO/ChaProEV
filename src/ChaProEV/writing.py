'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This contains functions related to writting outputs.
It contains the following functions:
1. **write_scenario_parameters:** This function writes the scenario parameters
    to the output files (either as separate files, or as tables/sheets
    in groupfiles.)
'''

import datetime
import os
import typing as ty
from itertools import repeat
from multiprocessing import Pool

import pandas as pd
import tqdm
from box import Box
from ETS_CookBook import ETS_CookBook as cook


@cook.function_timer
def extra_end_outputs(case_name: str, general_parameters: Box) -> None:
    '''
    Saves the pickle files to other formats
    '''
    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'
    groupfile_root: str = general_parameters.files.groupfile_root
    groupfile_name: str = f'{groupfile_root}_{case_name}'
    output_files: ty.List[str] = os.listdir(output_folder)
    output_pickle_files: ty.List[str] = [
        output_file
        for output_file in output_files
        if output_file.split('.')[1] == 'pkl'
    ]
    tables_to_save: ty.List[pd.DataFrame] = [
        pd.DataFrame(  # Because some of these are Series
            pd.read_pickle(f'{output_root}/{case_name}/{output_pickle_file}')
        )
        for output_pickle_file in output_pickle_files
    ]

    output_table_names: ty.List[str] = [
        output_pickle_file.split('.')[0]
        for output_pickle_file in output_pickle_files
    ]

    set_amount_of_processes: bool = (
        general_parameters.parallel_processing.set_amount_of_processes
    )
    if set_amount_of_processes:
        number_of_parallel_processes: int | None = None
    else:
        number_of_parallel_processes = (
            general_parameters.parallel_processing.amount_for_pickle_saves
        )
    saving_pool_inputs: (
        ty.Iterator[ty.Tuple[pd.DataFrame, str, str, str, Box]] | ty.Any
    ) = zip(
        tables_to_save,
        output_table_names,
        repeat(groupfile_name),
        repeat(output_folder),
        repeat(general_parameters),
    )
    # the ty.Any alternative is there because transforming it with the
    # progress bar makes mypy think it change is type
    progress_bars_parameters: Box = general_parameters.progress_bars
    display_saving_pool_run: bool = (
        progress_bars_parameters.display_saving_pool_run
    )
    saving_pool_run_description: str = (
        progress_bars_parameters.saving_pool_run_description
    )
    if display_saving_pool_run:
        saving_pool_inputs = tqdm.tqdm(
            saving_pool_inputs,
            desc=saving_pool_run_description,
            total=len(tables_to_save),
        )
    with Pool(number_of_parallel_processes) as saving_pool:
        saving_pool.starmap(cook.save_dataframe, saving_pool_inputs)


def write_scenario_parameters(
    scenario: Box, case_name: str, general_parameters: Box
) -> None:
    '''
    This function writes the scenario parameters to the output files (either
    as separate files, or as tables/sheets in groupfiles.)
    '''
    scenario_parameter_categories: ty.List[str] = (
        scenario.scenario_parameter_categories
    )

    scenario_name: str = scenario.name
    # groupfile_root: str = scenario['files']['groupfile_root']
    # groupfile_name: str = f'{groupfile_root}_{case_name}'
    output_root: str = general_parameters.files.output_root
    output_folder: str = f'{output_root}/{case_name}'

    for parameter_category in scenario_parameter_categories:
        parameter_values = scenario[parameter_category]
        parameter_dataframe = pd.DataFrame(parameter_values)
        # Some types (such as lists) create issues with some file formats,
        # and we only need to show the values anyway, so we
        # convert the DataFrame contents to strings
        parameter_dataframe = parameter_dataframe.astype('str')
        parameter_dataframe_name: str = f'{scenario_name}_{parameter_category}'
        parameter_dataframe.to_pickle(
            f'{output_folder}/{parameter_dataframe_name}.pkl'
        )


if __name__ == '__main__':
    case_name = 'Mopo'
    # test_scenario_name: str = 'baseline'
    start_time: datetime.datetime = datetime.datetime.now()
    general_parameters_file_name: str = 'ChaProEV.toml'
    general_parameters: Box = Box(
        cook.parameters_from_TOML(general_parameters_file_name)
    )

    extra_end_outputs(case_name, general_parameters)
    print((datetime.datetime.now() - start_time).total_seconds())
