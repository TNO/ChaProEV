'''
Author: Omar Usmani (Omar.Usmani@TNO.nl)
This module contains functions related to weather data and factors.
It contains the following functions:
1. **download_cds_weather_quantity:**
Downloads CDS ERA-5 weather data for a given quantity in a given area.
'''


import cdsapi


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


if __name__ == '__main__':

    quantity = '2m_temperature'
    year = 2020
    month = '05'
    days = ['08']
    hours = ['08', '09']
    area = [52.0, 52.1, 4.2, 4.4]
    download_folder = 'input'
    download_cds_weather_quantity(
        quantity, year, month, days, hours, area, download_folder)
