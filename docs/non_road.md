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
the database from Eurostat. See [the documentation about parameters for more details](###Eurostat).

## Configuration (non-roal.toml)


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