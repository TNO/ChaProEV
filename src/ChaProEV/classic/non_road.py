'''
Functions for non-road transport modes
'''

import datetime
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


def get_Eurostat_balances(
    non_road_parameters: box.Box, case_name: str
) -> None:
    '''
    This function gets the energy balances from Eurostat via
    the [Eurostat Python Package](https://pypi.org/project/eurostat/).
    '''

    Eurostat_parameters: box.Box = non_road_parameters.Eurostat

    if Eurostat_parameters.fetch:
        Eurostat_balances_dataframe: pd.DataFrame = pd.DataFrame(
            eurostat.get_data_df(Eurostat_parameters.table_code)
        )

        output_folder: str = f'{non_road_parameters.output_folder}/{case_name}'

        cook.save_dataframe(
            dataframe=Eurostat_balances_dataframe,
            dataframe_name=Eurostat_parameters.table_name,
            groupfile_name=case_name,
            output_folder=output_folder,
            dataframe_formats=non_road_parameters.files.dataframe_outputs,
        )


def get_reference_year_data(
    non_road_parameters: box.Box,
) -> pd.DataFrame:
    '''
    Processes the DataFrame fetched from Eurostat into a DataFrame for the
    refrence year, modes, energy carriers we want.
    '''
    eurostat_table_name: str = non_road_parameters.Eurostat.table_name
    database_folder: str = f'{non_road_parameters.output_folder}/{case_name}'
    database_file: str = f'{database_folder}/{case_name}.sqlite3'

    eurostat_dataframe: pd.DataFrame = cook.read_table_from_database(
        eurostat_table_name, database_file
    ).set_index(non_road_parameters.Eurostat.index_headers)

    reference_values: pd.DataFrame = pd.DataFrame()

    modes: list[str] = list(non_road_parameters.modes.keys())

    for mode in modes:
        mode_reference_values: pd.DataFrame = get_mode_reference_values(
            mode, non_road_parameters, eurostat_dataframe
        ).reset_index()
        reference_values = pd.concat(
            [reference_values, mode_reference_values], ignore_index=False
        )
    reference_values = reference_values.set_index(
        non_road_parameters.demand_index
    ).sort_index()

    output_folder: str = f'{non_road_parameters.output_folder}/{case_name}'

    cook.save_dataframe(
        dataframe=reference_values,
        dataframe_name=non_road_parameters.historical_dataframe_name,
        groupfile_name=case_name,
        output_folder=output_folder,
        dataframe_formats=non_road_parameters.files.dataframe_outputs,
    )

    return reference_values


def get_mode_reference_values(
    mode: str, non_road_parameters: box.Box, eurostat_dataframe: pd.DataFrame
) -> pd.DataFrame:
    '''
    This function get reference historical data from the Eurostat DataFrame
    for a given mode.
    '''

    mode_parameters: box.Box = non_road_parameters.modes[mode]
    mode_code: str = mode_parameters.code
    mode_energy_carriers: list[str] = mode_parameters.energy_carriers
    mode_energy_carrier_codes: list[str] = [
        get_siec_code(energy_carrier, non_road_parameters.Energy_carriers)
        for energy_carrier in mode_energy_carriers
    ]

    mode_reference_values: pd.DataFrame = (
        eurostat_dataframe.loc[
            mode_code,
            mode_energy_carrier_codes,
            non_road_parameters.Eurostat.unit_to_use,  # type: ignore
        ][  # type: ignore
            str(non_road_parameters.reference_historical_year)
        ]  # type: ignore
        / 1000  # because we want to use PJs and the data is in TJ
    )

    mode_reference_values = mode_reference_values.reset_index()

    mode_reference_values['unit'] = 'PJ'

    mode_reference_values['siec'] = [
        get_name_from_siec_code(siec_code, non_road_parameters.Energy_carriers)
        for siec_code in mode_reference_values['siec']
    ]

    mode_reference_values = mode_reference_values.rename(
        columns={
            'siec': 'Energy carrier',
            r'geo\TIME_PERIOD': 'Country Code',
            # str(
            #     non_road_parameters.reference_historical_year
            # ): non_road_parameters.demand_header[0],
        }
    )

    # mode_historical_values['Year'] = non_road_parameters.historical_year
    mode_reference_values['Mode'] = mode

    mode_reference_values = pd.DataFrame(
        mode_reference_values.set_index(non_road_parameters.demand_index)[
            str(non_road_parameters.reference_historical_year)
        ]
    )

    return mode_reference_values


def get_siec_code(energy_carier: str, carrier_parameters: box.Box) -> str:
    code_file: str = carrier_parameters.code_file
    code_data: pd.DataFrame = pd.read_csv(code_file)
    code_data = code_data.loc[
        code_data[carrier_parameters.status_column] == 'valid'
    ]

    codes: list[str] = list(code_data[carrier_parameters.code_column])
    carriers: list[str] = list(code_data[carrier_parameters.name_column])
    carrier_dict: dict[str, str] = dict(zip(carriers, codes))

    carrier_code: str = carrier_dict[energy_carier]

    return carrier_code


def get_name_from_siec_code(
    siec_code: str, carrier_parameters: box.Box
) -> str:
    code_file: str = carrier_parameters.code_file
    code_data: pd.DataFrame = pd.read_csv(code_file)
    code_data = code_data.loc[
        code_data[carrier_parameters.status_column] == 'valid'
    ]

    codes: list[str] = list(code_data[carrier_parameters.code_column])
    carriers: list[str] = list(code_data[carrier_parameters.name_column])
    code_dict: dict[str, str] = dict(zip(codes, carriers))

    carrier_name: str = code_dict[siec_code]

    return carrier_name


def get_future_demand_values(
    reference_historical_values: pd.DataFrame,
    non_road_parameters: box.Box,
    case_name: str,
) -> pd.DataFrame:
    '''
    Gets the demand for future years.
    '''

    growth_factors: pd.DataFrame = pd.read_csv(
        f'{non_road_parameters.source_folder}/{case_name}/'
        f'{non_road_parameters.growth_factors_file}'
    ).set_index(non_road_parameters.growth_factors_index)

    future_demand_values: pd.DataFrame = pd.DataFrame(
        index=reference_historical_values.index, columns=growth_factors.columns
    )

    for year_label in growth_factors.columns:
        future_demand_values[year_label] = (
            growth_factors[year_label]
            * reference_historical_values[
                str(non_road_parameters.reference_historical_year)
            ]
        )

    output_folder: str = f'{non_road_parameters.output_folder}/{case_name}'

    cook.save_dataframe(
        dataframe=future_demand_values,
        dataframe_name=non_road_parameters.demand_dataframe_name,
        groupfile_name=case_name,
        output_folder=output_folder,
        dataframe_formats=non_road_parameters.files.dataframe_outputs,
    )

    return future_demand_values


def get_profile_weights(
    scenario: tuple[list[str], str],
    non_road_parameters: box.Box,
    run_range=pd.DatetimeIndex,
) -> pd.Series:
    mode: str = scenario[0][1]
    mode_scenario: box.Box = non_road_parameters.modes[mode]
    weight_factors: np.ndarray = np.ones(run_range.size)  # type: ignore

    for modified_instance, modification_factor in zip(
        mode_scenario.modified_instances, mode_scenario.modification_factors
    ):
        weight_factors[modified_instance] *= modification_factor

    recurring_modifications_starts: list[
        int
    ] = mode_scenario.recurring_modifications_starts
    recurring_modifications: list[
        float
    ] = mode_scenario.recurring_modifications
    recurrences_steps: list[int] = mode_scenario.recurrences_steps
    amounts_of_recurrences: list[int] = mode_scenario.amounts_of_recurrences

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
            recurring = run_index < run_range.size  # type: ignore
            if amount_of_recurrences > 0:
                recurring = elapsed_recurrences > amount_of_recurrences

    weight_factors /= sum(weight_factors)

    scenario_name: str = ' '.join(scenario[0]) + '_' + scenario[1]
    run_profile_weights: pd.Series = pd.Series(
        weight_factors, index=run_range, name=scenario_name  # type: ignore
    )  # type: ignore
    return run_profile_weights


# @cook.function_timer
def get_profile(
    scenario: tuple[list[str], str],
    future_yearly_demand_values: pd.DataFrame,
    non_road_parameters: box.Box,
    run_range: pd.DatetimeIndex,
) -> tuple[str, pd.DataFrame]:
    scenario_name: str = (
        ' '.join(scenario[0]) + '_' + scenario[1] + '_Demand (PJ)'
    )

    run_demand: float = future_yearly_demand_values.loc[
        scenario
    ]  # type: ignore

    run_profile_weights: pd.Series = get_profile_weights(
        scenario, non_road_parameters, run_range  # type: ignore
    )
    run_demand_profile: pd.Series = pd.Series(
        run_demand * run_profile_weights, index=run_range, name=scenario_name
    )
    run_demand_dataframe: pd.DataFrame = pd.DataFrame(run_demand_profile)
    return scenario_name, run_demand_dataframe


@cook.function_timer
def get_non_road_profiles(
    future_yearly_demand_values: pd.DataFrame,
    case_name: str,
    non_road_parameters: box.Box,
) -> dict[str, pd.DataFrame]:
    demand_index_elements: pd.MultiIndex = (
        future_yearly_demand_values.index  # type: ignore
    )
    scenario_years: pd.Index = future_yearly_demand_values.columns

    scenarios: list[tuple[list[str], str]] = [
        (demand_index_element, scenario_year)
        for demand_index_element in demand_index_elements
        for scenario_year in scenario_years
    ]

    run_range_parameters: box.Box = non_road_parameters.run_range
    run_start: datetime.datetime = datetime.datetime(
        run_range_parameters.start.year,
        run_range_parameters.start.month,
        run_range_parameters.start.day,
        run_range_parameters.start.hour,
    )
    run_end: datetime.datetime = datetime.datetime(
        run_range_parameters.end.year,
        run_range_parameters.end.month,
        run_range_parameters.end.day,
        run_range_parameters.end.hour,
    )
    frequency: str = run_range_parameters.frequency

    run_range: pd.DatetimeIndex = pd.date_range(
        start=run_start, end=run_end, freq=frequency, inclusive='left'
    )

    set_amount_of_processes: bool = (
        non_road_parameters.parallel_processing.set_amount_of_processes
    )
    if set_amount_of_processes:
        amount_of_parallel_processes: int | None = (
            non_road_parameters.parallel_processing.amount_of_processes
        )
    else:
        amount_of_parallel_processes = None

    pool_inputs: (
        ty.Iterator[
            tuple[
                list[tuple[list[str], str]],
                pd.DataFrame,
                box.Box,
                pd.DatetimeIndex,
            ]
        ]
        | ty.Any
    ) = zip(
        scenarios,
        repeat(future_yearly_demand_values),
        repeat(non_road_parameters),
        repeat(run_range),
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


@cook.function_timer
def save_output_profiles(
    output_profiles: dict[str, pd.DataFrame],
    case_name: str,
    output_folder: str,
    non_road_parameters: box.Box,
) -> None:
    if non_road_parameters.parallel_processing.set_amount_of_processes:
        number_of_parallel_processes: int | None = (
            non_road_parameters.parallel_processing.amount_of_processes
        )
    else:
        number_of_parallel_processes = None

    saving_pool_inputs: (
        ty.Iterator[tuple[pd.DataFrame, str, str, str, box.Box]] | ty.Any
    ) = zip(
        output_profiles.values(),
        output_profiles.keys(),
        repeat(case_name),
        repeat(output_folder),
        repeat(non_road_parameters.files.dataframe_outputs),
    )
    # the ty.Any alternative is there because transforming it with the
    # progress bar makes mypy think it change is type

    progress_bars_parameters: box.Box = non_road_parameters.progress_bars
    display_saving_pool_run: bool = (
        progress_bars_parameters.display_saving_profiles
    )
    saving_pool_run_description: str = (
        progress_bars_parameters.saving_run_description
    )
    if display_saving_pool_run:
        saving_pool_inputs = tqdm(
            saving_pool_inputs,
            desc=saving_pool_run_description,
            total=len(output_profiles.keys()),
        )

    if non_road_parameters.parallel_processing.use_for_saving:
        with Pool(number_of_parallel_processes) as saving_pool:
            saving_pool.starmap(cook.save_dataframe, saving_pool_inputs)
    else:
        for output_profile in output_profiles:
            cook.save_dataframe(
                dataframe=output_profiles[output_profile],
                dataframe_name=output_profile,
                groupfile_name=case_name,
                output_folder=output_folder,
                dataframe_formats=non_road_parameters.files.dataframe_outputs,
            )


def get_non_road_data(case_name: str, non_road_parameters: box.Box) -> None:
    get_Eurostat_balances(non_road_parameters, case_name)

    reference_historical_values: pd.DataFrame = get_reference_year_data(
        non_road_parameters
    )
    # print(reference_historical_values)
    # reference_historical_values.to_csv('ref_val.csv')
    # exit()

    future_yearly_demand_values: pd.DataFrame = get_future_demand_values(
        reference_historical_values, non_road_parameters, case_name
    )

    output_profiles: dict[str, pd.DataFrame] = get_non_road_profiles(
        future_yearly_demand_values, case_name, non_road_parameters
    )

    country_codes: list[str] = []
    modes: list[str] = []
    years: list[int] = []
    carriers: list[str] = []
    for profile_name in output_profiles.keys():
        print(profile_name)

        if not profile_name.startswith('EU27'):
            country_code: str = profile_name.split(' ')[0]
            country_codes.append(country_code)
            year: int = int(profile_name.split('_')[1][:4])
            years.append(year)
            mode: str = profile_name.split(' ')[1]
            carrier: str = profile_name.split('_')[0][
                len(f'{country_code} {mode} ') :
            ]
            carriers.append(carrier)
            modes.append(mode)
            # print(f'{country_code=}, {mode=}, {year=}, {carrier=}')
            # if carrier == 'Electricity':
            #     modes.append(f'{mode}_{carrier}')
            # else:
            #     modes.append(mode)
    country_codes = sorted(list(set(country_codes)))
    modes = sorted(list(set(modes)))
    years = sorted(list(set(years)))
    carriers = sorted(list(set(carriers)))
    non_thermal_carriers: list[str] = ['Electricity']
    non_energetic_carriers: list[str] = ['Lubricants']
    profiles_grouped_by_carrier: dict[str, pd.Series] = {}
    country_year_profiles: dict[str, pd.DataFrame] = {}
    print(f'{country_codes=}')
    print(f'{modes=}')
    print(f'{years=}')
    print(f'{carriers=}')
    for country_code in country_codes:
        for year in years:
            this_country_year_profiles: pd.DataFrame = pd.DataFrame()
            for mode in modes:
                profiles_to_group_thermal: list[pd.Series] = []
                profiles_to_group_non_thermal: list[pd.Series] = []

                for carrier in carriers:
                    if carrier not in non_energetic_carriers:
                        profile_name_to_get: str = (
                            f'{country_code} {mode} {carrier}_{year}'
                            '_Demand (PJ)'
                        )

                        if profile_name_to_get in output_profiles.keys():
                            if carrier in non_thermal_carriers:
                                profiles_to_group_non_thermal.append(
                                    output_profiles[profile_name_to_get][
                                        profile_name_to_get
                                    ].fillna(0)
                                )
                            else:
                                # print(output_profiles[profile_name_to_get])
                                profiles_to_group_thermal.append(
                                    output_profiles[profile_name_to_get][
                                        profile_name_to_get
                                    ].fillna(0)
                                )
                                # print(
                                #     output_profiles[profile_name_to_get][
                                #         profile_name_to_get
                                #     ].fillna(0)
                                # )
                # print(mode)
                # if mode == 'domestic-navigation':
                #     exit()
                if len(profiles_to_group_non_thermal) > 0:
                    group_name: str = (
                        f'{country_code}_{mode}_non_thermal_PJ_{year}'
                    )
                    profiles_grouped_by_carrier[group_name] = pd.Series(
                        sum(profiles_to_group_non_thermal)
                    )
                    this_country_year_profiles[
                        f'{mode}_non_thermal_PJ'
                    ] = profiles_grouped_by_carrier[group_name]

                if len(profiles_to_group_thermal) > 0:
                    group_name = f'{country_code}_{mode}_thermal_PJ_{year}'
                    profiles_grouped_by_carrier[group_name] = pd.Series(
                        sum(profiles_to_group_thermal)
                    )
                    this_country_year_profiles[
                        f'{mode}_thermal_PJ'
                    ] = profiles_grouped_by_carrier[group_name]

            country_year_profiles[
                f'{country_code}_{year}'
            ] = this_country_year_profiles

    output_folder: str = f'{non_road_parameters.output_folder}/{case_name}'

    save_output_profiles(
        output_profiles, case_name, output_folder, non_road_parameters
    )

    carrier_group_output_folder: str = (
        f'{non_road_parameters.output_folder}/{case_name}/carrier_group'
    )
    save_output_profiles(
        profiles_grouped_by_carrier,
        case_name,
        carrier_group_output_folder,
        non_road_parameters,
    )

    country_year_output_folder: str = (
        f'{non_road_parameters.output_folder}/{case_name}/country_year'
    )
    save_output_profiles(
        country_year_profiles,
        case_name,
        country_year_output_folder,
        non_road_parameters,
    )


if __name__ == '__main__':
    case_name: str = 'Mopo'
    non_road_parameters_file: str = 'non-road.toml'

    non_road_parameters: box.Box = cook.parameters_from_TOML(
        non_road_parameters_file
    )
    get_non_road_data(case_name, non_road_parameters)

    print('Get growth')
    print('Get CH, UK, etc.')
    print('Check whihc historical year to use')
    print('SPread aross weeks in modes')
    print('Remove names from scenarios')
    print('Do growth in a function')
    print('First/last week inclusion issues')
    print('Zero-one shift explanation')
    print('Transport other/nec, pipelines?')
    print('NRMM: is that other/nec?')
    print('CH (and others?) missing')
    print('Tram/metro? nrg_d_traq')
    print('Scenarios now per mode, but could be differentiated per country')
    print('and/or year (or even carrier)')
    print('Parallelize saving?')

    # ENTSO-e for future
    # WLO?
    # Add proportionality cutoff for partial weeks (also for road????)
