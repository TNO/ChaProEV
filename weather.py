'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This module contains functions related to weather data and factors.
It contains the following functions:
1. **download_cds_weather_quantity:**
Downloads CDS ERA-5 weather data for a given quantity in a given area.
2. **download_all_cds_weather_data:**
Downloads all the necessary CDS weather data.
'''

import cdsapi

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


if __name__ == '__main__':

    parameters_file_name = 'ChaProEV.toml'
    grib_file = 'input/cds_weather_data/2m_temperature_2020_01.grib'
    output_dataframe = cook.from_grib_to_dataframe(grib_file)
    print(output_dataframe)
