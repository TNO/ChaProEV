'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This module contains functions related to weather data and factors.
The weather data is pulled from the CDS (Climate Data Store) ERA-5 weather
data from the Copernicus institute
(https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land?tab=form).
This data contains many quantities (such as temperature, precipitation,
or solar radiation) at an hourly level (starting in 1950) for the whole
world, at a one-decimal resolution for latitudes and longitudes.
Note that the data sometimes has trailing digits, but the resolution
still seems to be to the first decimal. This is the reason why we round the
coordinate values in our processing functions.
It contains the following functions:
1. **download_cds_weather_quantity:**
Downloads CDS ERA-5 weather data for a given quantity in a given area.
2. **download_all_cds_weather_data:**
Downloads all the necessary CDS weather data.
3. **make_weather_dataframe:** This function makes a weather DataFrame
into one we can use by
removing empty data and processing data into forms useful for the model.
4. **write_weather_database:** This function writes the weather database.
5. **get_hourly_values:** This function takes a Dataframe for a
given weather quantity. If this is a cumulative quantity, it adds hourly
values to it.
6. **get_all_hourly_values:** This functions adds hourly values to
cumulative quantities in the weather database.
7. **get_EV_tool_data:**: This gets the temperature efficiency data from the
     EV tool made by geotab.
    https://www.geotab.com/CMS-GeneralFiles-production/NA/EV/EVTOOL.html
8. **temperature_efficiency_factor:**This function returns the temperature
efficiency factor that corrects the baseline vehicle efficiency.
9. **plot_temperature_efficiency:** Plots the temperature efficiency
correction factor (source data versus interpolation)of electric vehicles.
10. **get_scenario_location_weather_quantity:** Returns a chosen weather
    quantity for a given location and a given runtime.
11. **get_scenario_weather_data:** Fetches the weather data and efficiency
    factors and puts it into a table that is saved to files/databases.
12. **solar_efficiency_factor:*** This gives us the efficiency factor of solar
     panels (i.e. how much of the solar radiation is converted into
     electricity).
    THIS IS A PLACEHOLDER FUNCTION
13. **setup_weather:** This runs all the functions necessary to get the
    scenario weather factors for a given case.
14. **get_location_weather_quantity:** Returns the value of a chosen
    weather quantity for a given location and time tag.
'''

import os
import sqlite3
import datetime

import numpy as np
import pandas as pd
import cdsapi
import requests
from bs4 import BeautifulSoup as bs
import matplotlib.pyplot as plt

from ETS_CookBook import ETS_CookBook as cook


def download_cds_weather_quantity(
      quantity, year, month, days, hours, area, download_folder):
    '''
    Downloads CDS (Climate Data Store) ERA-5 weather data for a given quantity
    in a given area (given by a list with:
    [latitude_min, latitude_max, longitude_min, longitude_max]).
    The days, months, hours numbers need two digits (so a leading zero is
    needed if the number only has one digit).
    Because of restrictions on the amount of data that can be downloaded at
    once (number of time points), we restrict this function to a given month
    (but hours and day can be all the hours and days in that month).
    To download data for a larger time span (say a year), you need
    to iterate.
    You only need to use this function at the start of your project,
    or if you change the general area you of the data you want to download
    (say, if you add locations in places for which you don't have data yet),
    or if you want to gather other quantities, or look at other years.
    '''
    quantity_download = cdsapi.Client()
    cook.check_if_folder_exists(download_folder)
    quantity_download.retrieve(
        'reanalysis-era5-land',
        {
            'variable': quantity,
            'year': year,
            'month': month,
            'day': days,
            'time': hours,
            'area': area,
            'format': 'grib'
        },
        f'{download_folder}/{quantity}_{year}_{month}.grib'
    )


def download_all_cds_weather_data(parameters):
    '''
    Downloads all the necessary CDS ERA-5 weather data.
    You only need to use this function at the start of your project,
    or if you change the general area you of the data you want to download
    (say, if you add locations in places for which you don't have data yet),
    or if you want to gather other quantities, or look at other years.
    '''

    time_parameters = parameters['time']
    HOURS_IN_A_DAY = time_parameters['HOURS_IN_A_DAY']
    MONTHS_IN_A_YEAR = time_parameters['MONTHS_IN_A_YEAR']
    MAX_DAYS_IN_A_MONTH = time_parameters['MAX_DAYS_IN_A_MONTH']
    source_data_parameters = parameters['weather']['source_data']
    start_year = source_data_parameters['start_year']
    end_year = source_data_parameters['end_year']

    years = [str(year) for year in range(start_year, end_year+1)]
    months = [
        f'{month_number:02d}' for month_number in range(1, MONTHS_IN_A_YEAR+1)
    ]
    days = [
        f'{day_number:02d}' for day_number in range(1, MAX_DAYS_IN_A_MONTH+1)]
    quantities = source_data_parameters['quantities']
    hours = [f'{hour_number:02d}:00' for hour_number in range(HOURS_IN_A_DAY)]
    latitude_min = source_data_parameters['latitude_min']
    latitude_max = source_data_parameters['latitude_max']
    longitude_min = source_data_parameters['longitude_min']
    longitude_max = source_data_parameters['longitude_max']
    raw_data_folder = source_data_parameters['raw_data_folder']
    area = [latitude_min, longitude_min, latitude_max, longitude_max]

    for quantity in quantities:
        for year in years:
            for month in months:
                print(quantity, year, month)
                download_cds_weather_quantity(
                    quantity, year, month, days, hours, area, raw_data_folder
                )


def make_weather_dataframe(
        raw_weather_dataframe, quantity, quantity_tag, quantity_name,
        parameters
        ):
    '''
    This function makes a weather DataFrame into one we can use by
    processing data into forms useful for the model.
    The processed DataFrame can then be added to the weather database.
    This weather database has an area given by latitude and longitude
    ranges. Note that these ranges correspond to the general region of the
    scenario, and thus can be different from the download range
    (which can be for example the whole of Europe) and from the scenario range
    (which corresponds to all locations in the scenario).
    Typically, you will want to have a large range for the downloaded data
    (which you would do only once), a medium range for the processed weather
    data (which would cover the range of locations in the scenarios you are
    planning to do in the mid-term), and scenario-specific locations (with
    their own latitudes and longitudes).
    '''

    weather_parameters = parameters['weather']['processed_data']
    latitude_min = weather_parameters['latitude_min']
    latitude_max = weather_parameters['latitude_max']
    longitude_min = weather_parameters['longitude_min']
    longitude_max = weather_parameters['longitude_max']
    coordinate_step = weather_parameters['coordinate_step']
    # We round the coordinates to the first decimal,
    # as this is the data resolution (but with trailing digits).
    # (See general module exaplanation).
    latitudes = [
        np.round(latitude, 1)
        for latitude in np.arange(
            latitude_min, latitude_max+coordinate_step, coordinate_step
        )
    ]
    longitudes = [
        np.round(longitude, 1)
        for longitude in np.arange(
            longitude_min, longitude_max+coordinate_step, coordinate_step
        )
    ]
    KELVIN_TO_CELSIUS = weather_parameters['KELVIN_TO_CELSIUS']

    temperature_quantities = weather_parameters['temperature_quantities']
    processed_index_tags = weather_parameters['processed_index_tags']

    # We slice the latitudes and longitudes
    # Note that we round the values to the first decimal,
    # as this is the data resolution (but with trailing digits).
    # (See general module exaplanation).
    raw_weather_dataframe = raw_weather_dataframe.loc[
        np.round(
            raw_weather_dataframe.index.get_level_values('latitude'),
            1
            ).isin(latitudes)
    ]

    raw_weather_dataframe = raw_weather_dataframe.loc[
        np.round(
            raw_weather_dataframe.index.get_level_values('longitude'),
            1
            ).isin(longitudes)
    ]

    # We process the time data into time tags (if needed)
    if 'valid_time' in raw_weather_dataframe.columns:
        weather_data_time_tags = raw_weather_dataframe['valid_time'].values
    else:
        raw_times = raw_weather_dataframe.index.get_level_values('time')
        raw_steps = raw_weather_dataframe.index.get_level_values('step')
        weather_data_time_tags = raw_times + raw_steps

    # We round the latitudes and longitudes (see above) and gather the values
    raw_latitudes = raw_weather_dataframe.index.get_level_values('latitude')
    raw_longitudes = raw_weather_dataframe.index.get_level_values('longitude')
    latitudes = np.round(raw_latitudes, 1)
    longitudes = np.round(raw_longitudes, 1)
    values = raw_weather_dataframe[quantity_tag].values

    if quantity in temperature_quantities:
        values = values + KELVIN_TO_CELSIUS

    # We can collect everyting into a processed dataframe
    processed_weather_dataframe = pd.DataFrame(
        values, columns=[quantity_name],
        index=[weather_data_time_tags, latitudes, longitudes]
    )

    processed_weather_dataframe.index.rename(
        processed_index_tags, inplace=True
        )

    return processed_weather_dataframe


def write_weather_database(parameters):
    '''
    This function writes the weather database.
    It iterates over desired quantities, processes
    the corresponding .grib source files into dataframes
    (including some processing), and writes them to a database.
    '''

    weather_parameters = parameters['weather']['processed_data']
    raw_data_folder = weather_parameters['raw_data_folder']
    processed_folder = weather_parameters['processed_folder']
    weather_database_file_name = (
        weather_parameters['weather_database_file_name']
    )
    quantities = weather_parameters['quantities']
    quantity_tags = weather_parameters['quantity_tags']
    quantity_processed_names = weather_parameters['quantity_processed_names']
    chunk_size = weather_parameters['chunk_size']
    cook.check_if_folder_exists(processed_folder)
    weather_database_file = f'{processed_folder}/{weather_database_file_name}'

    for quantity, quantity_tag, quantity_name in zip(
            quantities, quantity_tags, quantity_processed_names):
        # We create a new table for each quantity
        clear_table = True
        print(quantity)
        for file_name in os.listdir(raw_data_folder):
            if file_name.split('.')[-1] == 'grib':
                file_header = file_name.split('.')[0]
                if file_header[0:len(quantity)] == quantity:

                    source_file = f'{raw_data_folder}/{file_name}'
                    quantity_dataframe = cook.from_grib_to_dataframe(
                        source_file)
                    quantity_dataframe = quantity_dataframe.dropna(
                        subset=[quantity_tag]
                    )

                    processed_weather_dataframe = make_weather_dataframe(
                        quantity_dataframe, quantity, quantity_tag,
                        quantity_name, parameters
                    )
                    cook.put_dataframe_in_sql_in_chunks(
                        processed_weather_dataframe, weather_database_file,
                        quantity_name, chunk_size,
                        drop_existing_table=clear_table
                    )
                    # In following iteraions, we just want to
                    # append data to an existing table.
                    clear_table = False


def get_hourly_values(
        quantity_dataframe, quantity, quantity_name, parameters):
    '''
    This function takes a Dataframe for a give weather quantity.
    If this is a cumulative quantity, it adds hourly values to it.
    '''
    weather_parameters = parameters['weather']['processed_data']
    cumulative_quantities = weather_parameters['cumulative_quantities']

    latitudes = np.unique(
        quantity_dataframe.index.get_level_values('Latitude')
    )
    longitudes = np.unique(
        quantity_dataframe.index.get_level_values('Longitude')
    )

    if quantity in cumulative_quantities:
        quantity_dataframe[f'Shifted {quantity_name}'] = (
            [np.nan] * len(quantity_dataframe.index)
        )
        quantity_dataframe[f'Hourly {quantity_name}'] = (
         [np.nan] * len(quantity_dataframe.index)
        )
        # We need to do this for each latitude/longitude combination
        # We will take a slice and fill it with values
        # This will also update the main dataframe

        for latitude in latitudes:
            for longitude in longitudes:

                # We need to check if the latitude/longitude combination
                # has data
                if (latitude, longitude) in quantity_dataframe.index:

                    location_dataframe = quantity_dataframe.loc[
                        latitude, longitude
                    ]

                    cumulative_values = location_dataframe[
                        quantity_name].values
                    shifted_cumulative_values = np.roll(cumulative_values, -1)
                    location_dataframe.loc[:, f'Shifted {quantity_name}'] = (
                        shifted_cumulative_values
                    )

                    location_dataframe.loc[:, f'Hourly {quantity_name}'] = (
                        shifted_cumulative_values
                        - cumulative_values
                        * (location_dataframe.index.get_level_values(
                            'Timetag').hour != 0)
                        # At midnight, the shifted value is equal to the
                        # hourly value (it's the cumulative value
                        # of the time from 00.00  and 01.00).
                    )

                    # The data seems to have some issues
                    # where the cumulative values
                    # sometimes decrease (slightly), so we change these to zero
                    location_dataframe.loc[
                                location_dataframe[
                                    f'Hourly {quantity_name}'
                                ] < 0,
                                f'Hourly {quantity_name}'
                                ] = 0

                    # The last value needs to be set to zero,
                    # as it will be based on the first value
                    # (but needs to be based
                    # on the following year, which is not in the data)
                    location_dataframe.at[
                        location_dataframe.index.values[-1],
                        f'Hourly {quantity_name}'] = 0

    return quantity_dataframe


def get_all_hourly_values(parameters):
    '''
    This functions adds hourly values to cumulative quantities
    in the weather database.
    '''
    weather_parameters = parameters['weather']['processed_data']

    quantities = weather_parameters['quantities']
    cumulative_quantities = weather_parameters['cumulative_quantities']
    processed_index_tags = weather_parameters['processed_index_tags']
    processed_folder = weather_parameters['processed_folder']
    weather_database_file_name = (
        weather_parameters['weather_database_file_name']
    )
    weather_database = f'{processed_folder}/{weather_database_file_name}'
    quantity_names = weather_parameters['quantity_processed_names']
    chunk_size = weather_parameters['chunk_size']
    queries_for_cumulative_quantities = weather_parameters[
        'queries_for_cumulative_quantities'
    ]

    query_dictionary = dict(
        zip(cumulative_quantities, queries_for_cumulative_quantities)
    )

    for quantity, quantity_name in zip(quantities, quantity_names):
        if quantity in cumulative_quantities:

            with sqlite3.connect(weather_database) as sql_connection:
                sql_query = query_dictionary[quantity]
                quantity_dataframe = pd.read_sql(
                    sql_query, sql_connection
                )
                quantity_dataframe['Timetag'] = pd.to_datetime(
                    quantity_dataframe['Timetag']
                )
                quantity_dataframe = quantity_dataframe.set_index(
                    processed_index_tags
                )

            print('Avoid swap by arranging before? And explain/improve')
            quantity_dataframe = quantity_dataframe.swaplevel(0, 2)
            quantity_dataframe = quantity_dataframe.swaplevel(0, 1)
            quantity_dataframe = quantity_dataframe.sort_index()

            quantity_dataframe = get_hourly_values(
                quantity_dataframe, quantity,
                quantity_name, parameters
            )

            cook.put_dataframe_in_sql_in_chunks(
                quantity_dataframe, weather_database, quantity_name,
                chunk_size
            )


def get_EV_tool_data(parameters):
    '''
    This gets the temperature efficiency data from the EV tool made
    by geotab.
    https://www.geotab.com/CMS-GeneralFiles-production/NA/EV/EVTOOL.html
    '''

    file_parameters = parameters['files']

    EV_tool_parameters = parameters[
        'weather']['EV_tool']

    EV_tool_url = EV_tool_parameters['EV_tool_url']
    user_agent = EV_tool_parameters['user_agent']

    EV_tool_session = requests.Session()
    EV_tool_session.headers['User-Agent'] = user_agent
    EV_tool_html_content = EV_tool_session.get(EV_tool_url).content
    EV_tool_soup = bs(EV_tool_html_content, 'html.parser')

    EV_tool_scripts = []
    for script in EV_tool_soup.find_all('script'):
        EV_tool_scripts.append(script)

    efficiency_curve_script_index = EV_tool_parameters[
        'efficiency_curve_script_index'
    ]
    efficiency_curve_script = EV_tool_scripts[efficiency_curve_script_index]
    efficiency_curve_script_text = efficiency_curve_script.get_text()
    data_splitter = EV_tool_parameters['data_splitter']
    efficiency_curve_script_data = efficiency_curve_script_text.split(
        data_splitter
    )

    temperatures = []
    efficiency_factors = []

    for data_point in efficiency_curve_script_data:
        data_values = data_point.split(',')
        if len(data_values) > 1:
            # Some entries are not actual data entries and are empty
            temperature = float(
                data_values[0].strip(" '")
            )
            temperatures.append(temperature)
            raw_efficiency_factor = data_values[1].split(':')[1]
            efficiency_factor = float(
                raw_efficiency_factor.split("'")[1]
            )
            efficiency_factors.append(efficiency_factor)
    efficiency_factor_column_name = EV_tool_parameters[
        'efficiency_factor_column_name'
    ]
    temperature_efficiencies = pd.DataFrame(
        efficiency_factors, columns=[efficiency_factor_column_name],
        index=temperatures
    )

    temperature_efficiencies.index.name = 'Temperature (°C)'
    # This tag (the ° symbol, probably) creates issues with xml files
    # (and a warning with stata), so we need to remove the xml output
    # (or change things).
    file_name = EV_tool_parameters['file_name']
    groupfile_name = EV_tool_parameters['groupfile_name']
    folder = EV_tool_parameters['folder']
    cook.save_dataframe(
        temperature_efficiencies, file_name, groupfile_name, folder,
        parameters)


def temperature_efficiency_factor(temperature, parameters):
    '''
    This function returns the temperature efficiency factor that corrects
    the baseline vehicle efficiency. It uses a data file (extracted from
    here https://www.geotab.com/CMS-GeneralFiles-production/NA/EV/EVTOOL.html).
    It then uses a fitting function. This is done for the following reasons:
    1) We can go beyond the temperature range provided by the data
    2) A function works better than a data lookup for future uses
    3) Consistency between the temparatures in and out of data range.
    '''

    EV_tool_parameters = parameters[
        'weather']['EV_tool']

    vehicle_temperature_efficiencies_parameters = parameters[
        'weather']['vehicle_temperature_efficiencies']

    source_folder = vehicle_temperature_efficiencies_parameters['folder']
    source_file = vehicle_temperature_efficiencies_parameters['file_name']
    values_header = EV_tool_parameters[
        'efficiency_factor_column_name'
    ]
    fitting_polynomial_order = vehicle_temperature_efficiencies_parameters[
        'fitting_polynomial_order'
    ]

    temperature_efficiencies_data = pd.read_pickle(
        f'{source_folder}/{source_file}'
    )
    data_temperature_range = temperature_efficiencies_data.index
    data_efficiencies = temperature_efficiencies_data[values_header]
    fitting_function_coefficients = np.polyfit(
        data_temperature_range,
        data_efficiencies,
        fitting_polynomial_order
    )
    fitting_function = np.poly1d(fitting_function_coefficients)

    efficiency_factor = fitting_function(temperature)

    return (efficiency_factor)


def plot_temperature_efficiency(parameters):
    '''
    Plots the temperature efficiency correction factor
    (source data versus interpolation)
    of electric vehicles.
    '''

    EV_tool_parameters = parameters[
        'weather']['EV_tool']

    plot_colors = cook.get_extra_colors(parameters)

    plot_parameters = parameters['plots']['vehicle_temperature_efficiency']
    plot_style = plot_parameters['style']
    geotab_data_color = plot_colors.loc[plot_parameters['geotab_data_color']]
    geotab_data_size = plot_parameters['geotab_data_size']
    fit_color = plot_colors.loc[plot_parameters['fit_color']]
    fit_line_size = plot_parameters['fit_line_size']
    title_size = plot_parameters['title_size']
    plt.style.use(plot_style)
    source_data_folder = plot_parameters['source_data_folder']
    source_data_file = plot_parameters['source_data_file']
    source_data = pd.read_pickle(f'{source_data_folder}/{source_data_file}')
    temperatures = source_data.index.values
    values_header = EV_tool_parameters[
        'efficiency_factor_column_name'
    ]
    geotab_data_efficiencies = source_data[values_header].values
    fitted_efficiencies = temperature_efficiency_factor(
                            temperatures, parameters
                        )

    temeprature_efficiency_figure, temperature_efficiency_plot = (
        plt.subplots(1, 1)
    )
    temperature_efficiency_plot.plot(
        temperatures, geotab_data_efficiencies, label='geotab_data',
        marker='.', markersize=geotab_data_size, color=geotab_data_color,
        linestyle='none')
    temperature_efficiency_plot.plot(
        temperatures, fitted_efficiencies, label='fit',
        linewidth=fit_line_size, color=fit_color)
    temperature_efficiency_plot.legend()
    temperature_efficiency_plot.set_xlabel('Temperature (°C)')
    temperature_efficiency_plot.set_ylabel('Efficiency factor')
    temperature_efficiency_plot.set_title(
        'Temperature correction factor of range/efficiency of BEVs',
        fontsize=title_size)
    temperature_efficiency_plot.set_ylim(0, 1.05)
    temeprature_efficiency_figure.tight_layout()
    cook.save_figure(
        temeprature_efficiency_figure,
        'Vehicle_Temperature_correction_factor',
        source_data_folder, parameters
    )


def get_scenario_location_weather_quantity(
        location_latitude, location_longitude, run_start, run_end,
        source_table, weather_quantity, parameters):
    '''
    Returns a chosen weather quantity for a given location and a given
    runtime.
    The run_start and run_end inputs are datetime objects,
    source_table and weather_quantity sometimes have the same name,
    but not always (e.g. for hourly values of a cumulative quantity
    such as the solar radiation downwards)
    '''

    processed_data_parameters = parameters['weather']['processed_data']
    processed_folder = processed_data_parameters['processed_folder']
    weather_database_file_name = processed_data_parameters[
        'weather_database_file_name'
    ]
    weather_database_connection = sqlite3.connect(
        f'{processed_folder}/{weather_database_file_name}'
    )

    # We need to avoid issues with spaces in column names, so we need
    # nested double quotes
    source_table = f'"{source_table}"'
    weather_quantity = f'"{weather_quantity}"'
    run_start = f'"{run_start}"'
    run_end = f'"{run_end}"'

    list_columns_to_fetch = [
        'Latitude', 'Longitude', 'Timetag', weather_quantity
    ]
    # We need to convert this into a string for a query
    columns_to_fetch = ','.join(list_columns_to_fetch)

    query_filter_quantities = ['Latitude', 'Longitude', 'Timetag']
    query_filter_types = ['=', '=', 'between']
    query_filter_values = [
        location_latitude, location_longitude, [run_start, run_end]
    ]

    location_scenario_query = cook.read_query_generator(
        columns_to_fetch, source_table, query_filter_quantities,
        query_filter_types, query_filter_values
    )

    weather_values = pd.read_sql(
        location_scenario_query, weather_database_connection
    )

    # We don't need the latitude and longitude values in columns
    # (they are all the same and are our input)
    weather_values = weather_values.drop(columns=['Latitude', 'Longitude'])

    return weather_values


def get_scenario_weather_data(parameters):
    '''
    Fetches the weather data and efficiency factors and puts it into
    a table that is saved to files/databases.
    '''
    weather_dataframe = pd.DataFrame()

    scenario = parameters['scenario']
    case_name = parameters['case_name']

    weather_factors_table_root_name = parameters[
        'run']['weather_factors_table_root_name']
    weather_factors_table_name = (
        f'{scenario}_{weather_factors_table_root_name}'
    )

    file_parameters = parameters['files']
    output_folder = file_parameters['output_folder']
    groupfile_root = file_parameters['groupfile_root']
    groupfile_name = f'{groupfile_root}_{case_name}'

    weather_processed_data_parameters = parameters['weather']['processed_data']
    quantity_processed_names = weather_processed_data_parameters[
        'quantity_processed_names'
    ]

    cumulative_quantity_processed_names = weather_processed_data_parameters[
        'cumulative_quantity_processed_names'
    ]

    run_parameters = parameters['run']
    run_start = datetime.datetime(
        run_parameters['start']['year'],
        run_parameters['start']['month'],
        run_parameters['start']['day'],
        run_parameters['start']['hour'],
        run_parameters['start']['minute']
    )
    run_end = datetime.datetime(
        run_parameters['end']['year'],
        run_parameters['end']['month'],
        run_parameters['end']['day'],
        run_parameters['end']['hour'],
        run_parameters['end']['minute']
    )

    location_parameters = parameters['locations']

    for location in location_parameters:
        location_weather_dataframe = pd.DataFrame()
        location_first_quantity = True
        location_latitude = location_parameters[location]['latitude']
        location_longitude = location_parameters[location]['longitude']

        for quantity in quantity_processed_names:
            source_table = quantity
            if quantity in cumulative_quantity_processed_names:
                weather_quantity = f'Hourly {quantity}'
            else:
                weather_quantity = quantity

            weather_values = get_scenario_location_weather_quantity(
                location_latitude, location_longitude, run_start, run_end,
                source_table, weather_quantity, parameters
            )
            # weather_values['Location'] = [location]*len(weather_values.index)
            if location_first_quantity:
                location_weather_dataframe['Location'] = (
                    [location]*len(weather_values.index)
                )
                location_weather_dataframe['Timetag'] = (
                    weather_values['Timetag']
                )
                location_weather_dataframe = (
                    location_weather_dataframe.set_index(
                        ['Location', 'Timetag']
                    )
                )
                location_first_quantity = False

            location_weather_dataframe[weather_quantity] = (
                weather_values[weather_quantity].values
            )

        weather_dataframe = pd.concat(
            [weather_dataframe, location_weather_dataframe],
            ignore_index=False
        )

        weather_dataframe['Vehicle efficiency factor'] = (
            temperature_efficiency_factor(
                weather_dataframe['Temperature at 2 meters (°C)'].values,
                parameters
            )
        )

        JOULES_IN_A_KWH = parameters['unit_conversions']['JOULES_IN_A_KWH']
        weather_dataframe['Vehicle solar panels production (kWhe/m2)'] = (
            weather_dataframe[
                'Hourly Surface solar radiation downwards (J/m2)'
            ]
            * solar_panels_efficiency_factor(
                weather_dataframe['Temperature at 2 meters (°C)']
            )
            / JOULES_IN_A_KWH
        )

    cook.save_dataframe(
        weather_dataframe, weather_factors_table_name, groupfile_name,
        output_folder, parameters
    )

    return weather_dataframe


def solar_panels_efficiency_factor(temperature):
    '''
    This gives us the efficiency factor of solar panels (i.e. how
    much of the solar radiation is converted into electricity).
    THIS IS A PLACEHOLDER FUNCTION
    '''
    # THIS IS A PLACEHOLDER VALUE
    efficiency_factor = np.exp(-((temperature-25)**2)/(100))/3

    return efficiency_factor


def setup_weather(parameters):
    '''
    This runs all the functions necessary to get the scenario weather factors
    for a given case. Downloading CDS weather data
    (which is in principle only done once, but can be repeated if we add
    new years or new areas) is an option. The same holds for the EV tool
    temperature curve data.
    Creating the weather database is also optional (it should happen less
    often than updates related to scenarios, but more often than the above
    downloads).
    '''

    get_extra_downloads = parameters['run']['get_extra_downloads']
    download_weather_data = get_extra_downloads['download_weather_data']
    download_EV_tool_data = get_extra_downloads['download_EV_tool_data']
    make_weather_database = get_extra_downloads['make_weather_database']

    if download_weather_data:
        download_all_cds_weather_data(parameters)
    if download_EV_tool_data:
        get_EV_tool_data(parameters)
        plot_temperature_efficiency(parameters)
    if make_weather_database:
        try:
            write_weather_database(parameters)
        except FileNotFoundError:
            raise FileNotFoundError(
                'Data files for writing the weather database not found.'
                'You can download them by setting download_weather_data as'
                'true (lowercase is required by toml) under the'
                '[run.get_extra_downloads] in your scenario file.'
            )

        get_all_hourly_values(parameters)
    try:
        get_scenario_weather_data(parameters)
    except sqlite3.OperationalError:
        raise FileNotFoundError(
            'Weather database could not be opened, it may not exist.'
            'A possible solution is to create the weather database. '
            'To do so, set make_weather_database as true'
            '(lowercase is required by toml) under [run.get_extra_downloads]'
            'in your scenario file.'
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            'Vehicle Efficiency data not found.'
            'A possible solution is to set download_EV_tool_data as true'
            '(lowercase is required by toml) under [run.get_extra_downloads]'
            'in your scenario file.'
        )


def get_location_weather_quantity(
        location_latitude, location_longitude, timetag,
        source_table, weather_quantity, parameters):
    '''
    Returns the value a a chosen weather quantity for a given location and
    time tag.
    '''

    processed_data_parameters = parameters['weather']['processed_data']
    processed_folder = processed_data_parameters['processed_folder']
    weather_database_file_name = processed_data_parameters[
        'weather_database_file_name'
    ]
    weather_database_connection = sqlite3.connect(
        f'{processed_folder}/{weather_database_file_name}'
    )
    # We need to avoid issues with spaces in column names, so we need
    # nested double quotes
    source_table = f'"{source_table}"'
    weather_quantity = f'"{weather_quantity}"'
    timetag = f'"{timetag}"'

    list_columns_to_fetch = [
        'Latitude', 'Longitude', 'Timetag', weather_quantity
    ]
    # We need to convert this into a string for a query
    columns_to_fetch = ','.join(list_columns_to_fetch)

    query_filter_quantities = ['Latitude', 'Longitude', 'Timetag']
    query_filter_types = ['=', '=', '=']
    query_filter_values = [
        location_latitude, location_longitude, timetag
    ]

    scenario_query = cook.read_query_generator(
        columns_to_fetch, source_table, query_filter_quantities,
        query_filter_types, query_filter_values
    )

    weather_values = pd.read_sql(
        scenario_query, weather_database_connection
    )

    # The column does not contain double quotes and we need
    # the value (hence [0])
    value_of_weather_quantity = weather_values[weather_quantity.strip('"')][0]

    return value_of_weather_quantity


if __name__ == '__main__':


    parameters_file_name = f'scenarios/{scenario}.toml'
    parameters = cook.parameters_from_TOML(parameters_file_name)
    scenario = parameters['scenario']
    setup_weather(parameters)
    print(
        get_location_weather_quantity(
            52.0, 4.2, datetime.datetime(2020, 5, 8, 8, 0),
            'Temperature at 2 meters (°C)', 'Temperature at 2 meters (°C)',
            parameters
        )
    )
