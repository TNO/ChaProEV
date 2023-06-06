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
'''

import os
import sqlite3

import numpy as np
import pandas as pd
import cdsapi
import requests
from bs4 import BeautifulSoup as bs
import matplotlib.pyplot as plt

import cookbook as cook


def download_cds_weather_quantity(
      quantity, year, month, days, hours, area, download_folder):
    '''
    Downloads CDS (Climate Data Store) ERA-5 weather data for a given quantity
    in a given area (given by a list with:
    [latitude_min, latitude_max, longitude_min, longitude_max]).
    The days, months, hours numbers need two digits (so a trailing zero is
    needed if the number only has one digit).
    Because of restrictions on the amount of data that can be downloaded at
    once (number of time points), we restrictt this function to a given month
    (but hours and day can be all the hours and days in that month).
    To download data for a larger time span (say a year), you need
    to iterate.
    You only need to use this function at the start of your project,
    or if you change the general area you of the data you want to download
    (say, if you add locations in places for which you don't have data yet),
    or if you want to gather other quantities, or look at other years.
    '''
    quantity_download = cdsapi.Client()

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


def download_all_cds_weather_data(parameters_file_name):
    '''
    Downloads all the necessary CDS ERA-5 weather data.
    You only need to use this function at the start of your project,
    or if you change the general area you of the data you want to download
    (say, if you add locations in places for which you don't have data yet),
    or if you want to gather other quantities, or look at other years.
    '''

    parameters = cook.parameters_from_TOML(parameters_file_name)

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
        parameters_file_name
        ):
    '''
    This function makes a weather DataFrame into one we can use by
    processing data into forms useful for the model.
    The processed DataFrame can then be added to the weather database.
    This weather database has an area given by latitude and longitude
    ranges. Note that these ranges correspond to the general region of the run,
    and thus can be different from the download range
    (which can be for example the whole of Europe) and from the run range
    (which corresponds to all locations in the run).
    Typically, you will want to have a large range for the downlaoded data
    (which you would do only once), a medium range for the processed weather
    data (which would cover the range of locations in the runs you are
    planning to do in the mid-term), and run-specific locations (with
    their own latitudes and longitudes).
    '''

    parameters = cook.parameters_from_TOML(
        parameters_file_name)['weather']['processed_data']
    latitude_min = parameters['latitude_min']
    latitude_max = parameters['latitude_max']
    longitude_min = parameters['longitude_min']
    longitude_max = parameters['longitude_max']
    coordinate_step = parameters['coordinate_step']
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
    KELVIN_TO_CELSIUS = parameters['KELVIN_TO_CELSIUS']

    temperature_quantities = parameters['temperature_quantities']
    processed_index_tags = parameters['processed_index_tags']

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


def write_weather_database(parameters_file_name):
    '''
    This function writes the weather database.
    It iterates over desired quantities, processes
    the corresponding .grib source files into dataframes
    (including some processing), and writes them to a database.
    '''

    parameters = cook.parameters_from_TOML(
        parameters_file_name)['weather']['processed_data']
    raw_data_folder = parameters['raw_data_folder']
    processed_folder = parameters['processed_folder']
    weather_database_file_name = parameters['weather_database_file_name']
    quantities = parameters['quantities']
    quantity_tags = parameters['quantity_tags']
    quantity_processed_names = parameters['quantity_processed_names']
    chunk_size = parameters['chunk_size']
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
                    file_year = file_header[len(quantity):].split('_')[1]
                    file_month = file_header[len(quantity):].split('_')[2]

                    source_file = f'{raw_data_folder}/{file_name}'
                    quantity_dataframe = cook.from_grib_to_dataframe(
                        source_file)
                    quantity_dataframe = quantity_dataframe.dropna(
                        subset=[quantity_tag]
                    )

                    processed_weather_dataframe = make_weather_dataframe(
                        quantity_dataframe, quantity, quantity_tag,
                        quantity_name, parameters_file_name
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
        quantity_dataframe, quantity, quantity_name, parameters_file_name):
    '''
    This function takes a Dataframe for a give weather quantity.
    If this is a cumulative quantity, it adds hourly values to it.
    '''
    parameters = cook.parameters_from_TOML(
        parameters_file_name)['weather']['processed_data']
    cumulative_quantities = parameters['cumulative_quantities']

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


def get_all_hourly_values(parameters_file_name):
    '''
    This functions adds hourly values to cumulative quantities
    in the weather database.
    '''
    parameters = cook.parameters_from_TOML(
        parameters_file_name)['weather']['processed_data']

    quantities = parameters['quantities']
    cumulative_quantities = parameters['cumulative_quantities']
    processed_index_tags = parameters['processed_index_tags']
    processed_folder = parameters['processed_folder']
    weather_database_file_name = parameters['weather_database_file_name']
    weather_database = f'{processed_folder}/{weather_database_file_name}'
    quantity_names = parameters['quantity_processed_names']
    chunk_size = parameters['chunk_size']
    queries_for_cumulative_quantities = parameters[
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
                quantity_name, parameters_file_name
            )

            cook.put_dataframe_in_sql_in_chunks(
                quantity_dataframe, weather_database, quantity_name,
                chunk_size
            )


def get_EV_tool_data(parameters_file_name):
    '''
    This gets the temperature efficiency data from the EV tool made
    by geotab.
    https://www.geotab.com/CMS-GeneralFiles-production/NA/EV/EVTOOL.html
    '''
    parameters = cook.parameters_from_TOML(parameters_file_name)
    file_parameters = parameters['files']
    groupfile_name = file_parameters['groupfile_name']
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

    temperature_efficiencies = pd.DataFrame(
        efficiency_factors, columns=['Relative efficiency'],
        index=temperatures
    )

    temperature_efficiencies.index.name = 'Temperature (°C)'
    # This tag creates issues with xml files (and a warning with
    # stata), so we need to remove the xml output (or change things).
    file_name = EV_tool_parameters['file_name']
    folder = EV_tool_parameters['folder']
    cook.save_dataframe(
        temperature_efficiencies, file_name, groupfile_name, folder,
        parameters_file_name)


def temperature_efficiency_factor(temperature, parameters_file_name):
    '''
    This function returns the temperature efficiency factor that corrects
    the baseline vehicle efficiency. It uses a data file (extracted from
    here https://www.geotab.com/CMS-GeneralFiles-production/NA/EV/EVTOOL.html).
    It then uses a fitting function. This is done for the following reasons:
    1) We can go beyond the temperature range provided by the data
    2) A function works better than a data lookup for future uses
    3) Consistency between the temparatures in and out of data range.
    '''

    parameters = cook.parameters_from_TOML(parameters_file_name)
    temperature_efficiencies_parameters = parameters[
        'weather']['temperature_efficiencies']

    source_folder = temperature_efficiencies_parameters['folder']
    source_file = temperature_efficiencies_parameters['file_name']
    values_header = temperature_efficiencies_parameters['values_header']
    fitting_polynomial_order = temperature_efficiencies_parameters[
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


def plot_temperature_efficiency(parameters_file_name):
    '''
    Plots the temperature efficiency correction factor
    (source data versus interpolation)
    of electric vehicles.
    '''
    parameters = cook.parameters_from_TOML(parameters_file_name)

    plot_colors = cook.get_extra_colors(parameters_file_name)

    plot_parameters = parameters["plots"]['temperature_efficiency']
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
    geotab_data_efficiencies = source_data['Relative efficiency'].values
    fitted_efficiencies = temperature_efficiency_factor(
                            temperatures, parameters_file_name
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
        'Temperature_correction_factor',
        source_data_folder, parameters_file_name
    )


if __name__ == '__main__':

    parameters_file_name = 'ChaProEV.toml'
    parameters = cook.parameters_from_TOML(parameters_file_name)
    processed_data_parameters = parameters['weather']['processed_data']
    processed_folder = processed_data_parameters['processed_folder']
    weather_database_file_name = processed_data_parameters[
        'weather_database_file_name'
    ]
    weather_database_connection = sqlite3.connect(
        f'{processed_folder}/{weather_database_file_name}'
    )
    quantities_to_display_no_spaces = ['Timetag', 'Latitude', 'Longitude']
    quantities_to_display_spaces = [
        'Hourly Surface solar radiation downwards (J/m2)'
    ]
    quantities_to_display_spaces = [
        f'"{quantity}"' for quantity in quantities_to_display_spaces
    ]
    list_of_quantities_to_display = (
        quantities_to_display_no_spaces + quantities_to_display_spaces
    )
    quantities_to_display = ','.join(list_of_quantities_to_display)
    source_table = f'"Surface solar radiation downwards (J/m2)"'
    query_filter_quantities = [
        ('Latitude'), 'Timetag',
        '"Hourly Surface solar radiation downwards (J/m2)"'
    ]
    query_filter_types = ['in', 'between', '<>']
    query_filter_values = [
        [52.1, 52.0],
        ['"2020-05-08 00:00:00"', '"2020-06-26 16:00:00"'],
        0
    ]
    test_query = cook.sql_query_generator(
        quantities_to_display, source_table, query_filter_quantities,
        query_filter_types, query_filter_values)

    test_df = pd.read_sql(
        test_query, weather_database_connection
        ).set_index(['Latitude', 'Longitude', 'Timetag'])
    print(test_df)
