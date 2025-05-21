'''
Functions for non-road transport modes
'''

import datetime
import os
import typing as ty
from itertools import repeat
from multiprocessing import Pool

import box
import eurostat
import numpy as np
import pandas as pd
from ETS_CookBook import ETS_CookBook as cook
from rich import print
from tqdm.rich import tqdm


def get_run_demand(
    scenario_name: str, case_name: str, general_parameters: box.Box
) -> float:

    scenario_elements_list: list[str] = scenario_name.split('_')

    country_code: str = scenario_elements_list[0]
    mode: str = scenario_elements_list[1]
    year: int = general_parameters.historical_year
    carrier: str = scenario_elements_list[3]

    demand_index: str = general_parameters.demand_index
    demand_header: str = general_parameters.demand_header

    source_table: str = general_parameters.demand_dataframe_name
    database_folder: str = f'{general_parameters.output_folder}/{case_name}'
    database_file: str = f'{database_folder}/{case_name}.sqlite3'

    demand_values: pd.DataFrame = cook.read_table_from_database(
        source_table, database_file
    ).set_index(demand_index)

    run_demand: float = demand_values.loc[country_code, mode, year, carrier][
        demand_header
    ][0]

    return run_demand


def get_run_demand2(
    scenario_name: str, case_name: str, general_parameters: box.Box
) -> float:

    scenario_elements_list: list[str] = scenario_name.split('_')

    country_code: str = scenario_elements_list[0]
    mode: str = scenario_elements_list[1]
    year: int = int(scenario_elements_list[2])
    carrier: str = scenario_elements_list[3]

    source_folder: str = general_parameters.source_folder
    demand_file: str = general_parameters.demand_file
    demand_index: str = general_parameters.demand_index
    demand_header: str = general_parameters.demand_header

    scenario_demand_elements: pd.DataFrame = pd.read_csv(
        f'{source_folder}/{case_name}/{demand_file}'
    ).set_index(demand_index)

    run_demand: float = scenario_demand_elements.loc[
        country_code, mode, year, carrier
    ][demand_header][0]

    return run_demand


def get_profile_weights(
    scenario: box.Box, run_range=pd.DatetimeIndex
) -> pd.Series:

    weight_factors: np.ndarray = np.ones(len(run_range))

    for modified_instance, modification_factor in zip(
        scenario.modified_instances, scenario.modification_factors
    ):
        weight_factors[modified_instance] *= modification_factor

    recurring_modifications_starts: list[int] = (
        scenario.recurring_modifications_starts
    )
    recurring_modifications: list[float] = scenario.recurring_modifications
    recurrences_steps: list[int] = scenario.recurrences_steps
    amounts_of_recurrences: list[int] = scenario.amounts_of_recurrences

    for (
        recurring_start,
        recurring_modification,
        recurrence_step,
        amount_of_recurrences,
    ) in zip(
        recurring_modifications_starts,
        recurring_modifications,
        recurrences_steps,
        amounts_of_recurrences,
    ):
        recurring: bool = True
        run_index: int = recurring_start
        elapsed_recurrences: int = 0
        while recurring:
            weight_factors[run_index] *= recurring_modification
            elapsed_recurrences += 1

            run_index += recurrence_step
            recurring = run_index < len(run_range)
            if amount_of_recurrences > 0:
                recurring = elapsed_recurrences > amount_of_recurrences

    weight_factors /= sum(weight_factors)

    run_profile_weights: pd.Series = pd.Series(
        weight_factors, index=run_range, name=scenario.name
    )
    return run_profile_weights


@cook.function_timer
def get_profile(
    scenario: box.Box, case_name: str, general_parameters: box.Box
) -> tuple[str, pd.DataFrame]:

    run_demand: float = get_run_demand(
        scenario.name, case_name, general_parameters
    )
    run_start_parameters: box.Box = scenario.run_start
    run_start: datetime.datetime = datetime.datetime(
        run_start_parameters.year,
        run_start_parameters.month,
        run_start_parameters.day,
        run_start_parameters.hour,
    )
    run_end_parameters: box.Box = scenario.run_end
    run_end: datetime.datetime = datetime.datetime(
        run_end_parameters.year,
        run_end_parameters.month,
        run_end_parameters.day,
        run_end_parameters.hour,
    )
    frequency: str = scenario.frequency

    run_range: pd.DatetimeIndex = pd.date_range(
        start=run_start, end=run_end, freq=frequency, inclusive='left'
    )

    run_profile_weights: pd.Series = get_profile_weights(scenario, run_range)
    run_demand_profile: pd.Series = pd.Series(
        run_demand * run_profile_weights, index=run_range, name=scenario.name
    )
    run_demand_dataframe: pd.DataFrame = pd.DataFrame(run_demand_profile)
    return scenario.name, run_demand_dataframe


def load_scenarios(non_road_folder: str, case_name: str) -> list[box.Box]:
    scenario_folder_files: list[str] = os.listdir(
        f'{non_road_folder}/{case_name}'
    )
    scenario_files: list[str] = [
        scenario_folder_file
        for scenario_folder_file in scenario_folder_files
        if scenario_folder_file.split('.')[1] == 'toml'
    ]
    scenario_file_paths: list[str] = [
        f'{non_road_folder}/{case_name}/{scenario_file}'
        for scenario_file in scenario_files
    ]
    scenarios: list[box.Box] = [
        box.Box(cook.parameters_from_TOML(scenario_file_path))
        for scenario_file_path in scenario_file_paths
    ]
    for scenario, scenario_file in zip(scenarios, scenario_files):
        scenario.name = scenario_file.split('.')[0]
    return scenarios


@cook.function_timer
def get_non_road_profiles(
    case_name: str,
    demand_values: pd.DataFrame,
    non_road_parameters: box.Box,
) -> dict[str, pd.DataFrame]:

    set_amount_of_processes: bool = (
        non_road_parameters.parallel_processing.set_amount_of_processes
    )
    if set_amount_of_processes:
        amount_of_parallel_processes: int | None = None
    else:
        amount_of_parallel_processes = (
            non_road_parameters.parallel_processing.amount_of_processes
        )

    scenarios: list[box.Box] = load_scenarios(
        non_road_parameters.source_folder, case_name
    )

    pool_inputs: ty.Iterator[tuple[box.Box, str, box.Box]] | ty.Any = zip(
        scenarios, repeat(case_name), repeat(non_road_parameters)
    )
    # the ty.Any alternative is there because transforming it with the
    # progress bar makes mypy think it change is type

    progress_bars_parameters: box.Box = non_road_parameters.progress_bars

    display_scenario_run: bool = progress_bars_parameters.display_scenario_run
    scenario_run_description: str = (
        progress_bars_parameters.scenario_run_description
    )
    if display_scenario_run:
        pool_inputs = tqdm(
            pool_inputs,
            desc=scenario_run_description,
            total=len(scenarios),
        )

    with Pool(amount_of_parallel_processes) as scenarios_pool:
        output_profiles: dict[str, pd.DataFrame] = dict(
            scenarios_pool.starmap(get_profile, pool_inputs)
        )
    return output_profiles


def fetch_historical_value(
    country: str, mode: str, year: int, energy_carrier: str
) -> float:
    consumption: float = np.random.rand()
    return consumption


def fetch_historical_values(
    general_parameters: box.Box,
) -> pd.DataFrame:

    year: int = general_parameters.historical_year
    countries: list[str] = general_parameters.countries
    country_codes: list[str] = general_parameters.country_codes
    energy_carriers: box.Box = general_parameters.mode_energy_carriers
    modes: list[str] = energy_carriers.keys()
    historical_values_index_tuples: list[tuple[str, str, int, str]] = [
        (
            country_code,
            mode,
            year,
            energy_carrier,
        )
        for country, country_code in zip(countries, country_codes)
        for mode in modes
        for energy_carrier in energy_carriers[mode]
    ]
    historical_values_index: pd.MultiIndex = pd.MultiIndex.from_tuples(
        historical_values_index_tuples
    )

    historical_values: pd.DataFrame = pd.DataFrame(
        columns=general_parameters.demand_header, index=historical_values_index
    )

    historical_values.index.names = general_parameters.demand_index
    for country, country_code in zip(countries, country_codes):
        for mode in modes:
            for energy_carrier in energy_carriers[mode]:
                historical_value: float = fetch_historical_value(
                    country, mode, year, energy_carrier
                )
                historical_values.loc[
                    (country_code, mode, year, energy_carrier),
                    general_parameters.demand_header,
                ] = historical_value

    output_folder: str = f'{general_parameters.output_folder}/{case_name}'

    historical_values = historical_values.sort_index()

    cook.save_dataframe(
        dataframe=historical_values,
        dataframe_name=general_parameters.historical_dataframe_name,
        groupfile_name=case_name,
        output_folder=output_folder,
        parameters=general_parameters,
    )

    return historical_values


def get_demand_values(
    historical_values: pd.DataFrame,
    non_road_parameters: box.Box,
    case_name: str,
) -> pd.DataFrame:

    demand_values: pd.DataFrame = historical_values.copy()

    scenarios: list[box.Box] = load_scenarios(
        non_road_parameters.source_folder, case_name
    )
    historical_year: int = non_road_parameters.historical_year

    for scenario in scenarios:
        country_code: str = scenario.name.split('_')[0]
        mode: str = scenario.name.split('_')[1]
        year: int = int(scenario.name.split('_')[2])
        energy_carrier: str = scenario.name.split('_')[3]

        historical_value: float = historical_values.loc[
            country_code, mode, historical_year, energy_carrier
        ][non_road_parameters.demand_header]

        scenario_value: float = scenario.growth * historical_value

        demand_values.loc[
            (country_code, mode, year, energy_carrier),
            non_road_parameters.demand_header,
        ] = scenario_value

    demand_values = demand_values.sort_index()
    output_folder: str = f'{non_road_parameters.output_folder}/{case_name}'

    cook.save_dataframe(
        dataframe=demand_values,
        dataframe_name=non_road_parameters.demand_dataframe_name,
        groupfile_name=case_name,
        output_folder=output_folder,
        parameters=non_road_parameters,
    )

    return demand_values


def get_Eurostat_balances(general_parameters: box.Box, case_name: str) -> None:

    Eurostat_balances_dataframe: pd.DataFrame = eurostat.get_data_df(
        general_parameters.Eurostat.table_code
    )

    output_folder: str = f'{general_parameters.output_folder}/{case_name}'

    cook.save_dataframe(
        dataframe=Eurostat_balances_dataframe,
        dataframe_name=general_parameters.Eurostat.table_name,
        groupfile_name=case_name,
        output_folder=output_folder,
        parameters=general_parameters,
    )


if __name__ == '__main__':

    case_name: str = 'Mopo'

    non_road_parametrs_file: str = 'non-road.toml'
    non_road_parameters: box.Box = box.Box(
        cook.parameters_from_TOML(non_road_parametrs_file)
    )
    if non_road_parameters.Eurostat.fetch:
        get_Eurostat_balances(non_road_parameters, case_name)

    historical_values: pd.DataFrame = fetch_historical_values(
        non_road_parameters
    )

    demand_values: pd.DataFrame = get_demand_values(
        historical_values, non_road_parameters, case_name
    )

    output_profiles: dict[str, pd.DataFrame] = get_non_road_profiles(
        case_name, demand_values, non_road_parameters
    )

    output_folder: str = f'{non_road_parameters.output_folder}/{case_name}'
    for output_profile in output_profiles:
        cook.save_dataframe(
            dataframe=output_profiles[output_profile],
            dataframe_name=output_profile,
            groupfile_name=case_name,
            output_folder=output_folder,
            parameters=non_road_parameters,
        )
    print('Do growth in a function')
    print('First/last week inclusion issues')
    print('Zero-one shift explanation')
    print('Connect to Eurostat API')
