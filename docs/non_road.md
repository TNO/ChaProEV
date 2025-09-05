# Non-road Profiles

This module computes demand profiles for non-road modes of transport.




## Module

### get_non_road_data
This is the main function of this module. It runs all the functions of this module.


### get_Eurostat_balances
This function gets the energy balances from Eurostat via
the [Eurostat Python Package](https://pypi.org/project/eurostat/).
This function runs a function from the Eurostat package to
get a table, by using the right table code and saving the
obatined dataframe. This only runs if the user decides to fetch
the database from Eurostat. See [the documentation about parameters for more details](#eurostat).


### process_Eurostat_dataframe
Processes the DataFrame fetched from Eurostat into a DataFrame for the years
modes, energy carriers we want.

The function runs through each mode (defined [here](#modes)) and gets its
values from the Eurostat table obatined [here](#get_Eurostat_balances) through
the [get_mode_Eurostat_values function](#get_mode_Eurostat_values).
The function also sets [the index](#demand_index) and sorts it. 

The function also saves the resulting historical data.



### get_mode_Eurostat_values
This function get historical data from the Eurostat DataFrame for a
given mode.
We need to translate the energy carrier into [SIEC codes](#get_siec_code)
and back into [carrier names](#get_name_from_siec_code).



### get_siec_code
Gets the
[SIEC (Standard international energy product classification code)](https://dd.eionet.europa.eu/vocabulary/eurostat/siec/view), for an energy carrier using a [translation_file](#code_file).

### get_name_from_siec_code
Gets the name of an energy carrier from its 
[SIEC (Standard international energy product classification code)](https://dd.eionet.europa.eu/vocabulary/eurostat/siec/view), using a [translation_file](#code_file).


## Configuration (non-roal.toml)

#### historical_dataframe_name
The name of the historical data DataFrame.

#### demand_dataframe_name
The name of the DataFrame that conatins all th edemand data (historical
and projected)

#### source_folder
The folder that contains source/input data for a given
case (so it is under that case name's subfolder).
The case name subfolder contains the [scenarios per mode and year](#scenarios)

#### output_folder
The folder where the output files go (in a case name subfolder).

#### demand_index
Those are the columns we use for the index of the historical demand
DataFrame.

#### demand_header
This is the name of the header/column of the historical demand DataFrame

#### histtorical_year
The year for which we extract the Eurostat data

### modes
For each mode, you need to provide its code and the
energy carriers it uses.
Follow the structure of existing elements (see example below), by copying it
and replacing the name (in this case international-maritime-bunkers)
by the name of your mode and by using the right code and energy carriers.
```toml
[modes.international-maritime-bunkers]
code = 'INTMARB'
energy_carriers = [
    'Natural gas',
    'Motor gasoline (excluding biofuel portion)',
    'Kerosene-type jet fuel (excluding biofuel portion)',
    'Gas oil and diesel oil (excluding biofuel portion)',
    'Fuel oil',
    'Lubricants',
    'Other oil products n.e.c.',
    'Blended biodiesels',
    'Pure biodiesels',
    'Other liquid biofuels'

]
```


### Eurostat
These are parameters for getting data from the Eurostat API,
using the [Eurostat Python Package](https://pypi.org/project/eurostat/)
#### fetch
A boolean to tell the model if it needs to fetch the data from Eurostat.
Set it to true if you don't have the data yet or if you want to refresh it.
Set it to false if you want to run with already fetch data (for exmaple if 
you ant to run offline, or if you just got the data).
#### table_code
The table code for complete energy balances is 'nrg_bal_c'.
Other codes can be obtained with eurostat.get_toc_df().
See [Eurostat Python Package](https://pypi.org/project/eurostat/)
for details.

#### table_name
The name you want to use to save your DataFrame and that you will be using for
retrieving the Eurostat data.

#### index_headers
The headers/columns to use as an index (used in the 
[function getting values per mode][#get_mode_eurostat_values]).
#### unit_to_use
The unit to use for the Eurostat data

### Energy_carriers
#### code_file
The location of the file used to translate 
[SIEC (Standard international energy product classification codes)](https://dd.eionet.europa.eu/vocabulary/eurostat/siec/view).
#### code_column
The name of the column conmtaining the SIEC codes
#### name_column
The name of the column conatining energy carriers/products names.
#### status_column
The column containing the status of that code (if it is still in use , 'it is 'valid').


## Scenarios