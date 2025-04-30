# Purpose
The purpose of the ChaProEV.toml file is to set parameters
that are common for all your scenarios.
This page describes the various parameters.
You can use the navigation bar on the left to go directly to a group
of parameters (or a given parameter).
This mostly contains general parameters that should not change too much from case to case. As such, you can take the version provided in the repository (and possibly modify one or two things).

## variants
The variants section of the configuration file sets parameters
to create scenario [variants](variants.md) (see that page for
details).

### use_variants 
Setting the use_variants parameters to true creates variants,
while setting it to false skips variant creation althogether.

### csv_version 

Setting the csv_version to true parameters makes you use csv files
to define your variants (in a folder within the variants folder: this
folder needs to have the same name as your case). Setting it to false makes you use a toml file in the variants folder (case_name.toml).

### use_years_in_profiles

This is used to create different variants per year when doing 
[car home own driveway and street parking splits](profiles.md#home-type-split)




## parallel_processing
This parallel processing section of the configuration file sets parameters to manage the [parallel processing/multiprocessing](multiprocessing.md) of the model (which reduces the model run time, see link for details).

### set_amount_of_processes 

Set this as false if you want the amount of parallel processes to be determined by the model (via the [multiprocessing standard library of Python](https://docs.python.org/3/library/multiprocessing.html)). Set this to true if you want to set the amount of processes yourself.

### amount_for_scenarios

If you put true in set_amount_of_processes, provide a number of parallel processes here to run scenarios in parallel.

### amount_for_pickle_saves 
If you put true in set_amount_of_processes, provide a number of parallel processes here to save the pickle output saves to other formats in parallel (see [writing module](writing.md) for details).

## interim_files
This concerns parameters for saving intermediary results to files.

### pickle
Set this to true to save interim results to pickle files.
Set this to false not to do this.
### consumption_tables_frequencies
 Provide a list of consumption
tables frequencies (see [consumption module](consumption.md)). The default is the following list ['hourly', 'daily', 'weekly', 'monthly', 'yearly']
### save_consumption_table
Provide a list of booleans (true or false) to save a given frequency to file (this list needs to have the same length as the above list): true save a file for that frequency and false does not.




## profile_dataframe
These are the headers that appear in output dataframes.

### headers
This one is for profiles (at one-vehicle scale).
### fleet_headers
This one is for the fleet-level dataframes.
### do_fleet_tables
Set this to true to create fleet-level tables.
### fleet_file_name
The file name (has to be a csv inside the input/your_case folder)
containing the fleet characteristics.
See [here](input.md#fleets) for details about this file.

## sessions_dataframe
This is to create the session dataframes.
### properties
Those are the quantities we want to put in the session dataframes.
### dataframe_headers
Those are the headers of the session dataframes at the day level.
### run_dataframe_headers
Those are the headers of the session dataframes for the whole run.
### display_dataframe_headers
These are the headers of the display/final output dataframe headers at vehicle level.
### display_dataframe_index
These give the index of the display/final output dataframe headers.
### fleet_display_dataframe_headers
These are the headers of the display/final output dataframe headers at fleet
level.
## plots
This contains parameters for output plots (colors, styles, sizes, etc.).
### vehicle_temperature_efficiency
This set of parameters is for the [range-temperature](weather.md#range-and-temperature) plot.
#### style
This is a string with one of the [available Matplotlib styles](https://matplotlib.org/stable/gallery/style_sheets/style_sheets_reference.html).
#### source_data_folder
Folder where the data to plot is.
#### source_data_file 
File containg the data to plot.
#### fit_color 
The color name of fit line.
#### fit_line_size
The size of the fir line.
#### geotab_data_color
The color of the data points. 
#### geotab_data_size
The size of the data points.
#### title_size 
The size of the plot title.

## files
General file parameters.
### input_root
The name of the folder where your input data goes (it goes to a subfolder of this with the name of your case).
### output_root
The name of the folder where your output data goes (it goes to a subfolder of this with the name of your case).
### groupfile_root
This is for files that group data (such as (sqlite) databases or Excel workbooks) and will be the name of that grouping file.

### figures
Parameters for plots/figures.
#### dpi
Change this to change the resolution of the output figures.
#### outputs
Indicate  if you want to save your (Matplotlib) figures (true if you do, false if you don't) in various formats.


### dataframe_outputs
Indicate if you want to save your Pandas DataFrames in the
listed formats (put a true if you want to do so, false if you don't).
Clipboard saves to the local clipboard, not a file.

## maps
Parameters for making maps.
## map_data_folder
The folder where the map data is.
## area_data_file_name
The file containing map areas.
## general_exclusion_codes
Excluded map codes.
## border_data_file_prefix
The prefix of the border data file.
## border_data_file_suffix
The suffix of the border data file.
## points_data_file_prefix
The prefix of the points data file.
## points_data_file_suffix
The suffix of the points data file.
## country_code_header
The header we use for country codes.
## country_code_header_in_map_data
The country code header in tnhe source data.
## heat_bar_map
The heat bar map/scale we want to use for maps (is the name of a 
[color bar](#color_bars)).

## colors
Definitions of custom colors (with RGB values, from 0 to 255).
## color_bars
You can deine color bars here, by listing the colors they use (in order).


## unit_conversions
This contains various constants used for unit conversions,
such as the amount of Joules in a kiloWatt-hour.
Some are grouped (time conversions).
The times subpart also contains the codes for weekend day numbers
and the index of the first hour in the year (often 0,
but sometimes 1, as for the SPINE toolbox).
## numbers
This contains a threshold to avoid issues with float precision and exteremely small values that are actually zero.

## consumption
This contains settings (mostly headers and display names) related to
the [connusmption](consumption.md) tables.
### energy_carriers
A list of the energy carriers that come in the consumption table.
### consumption_table_name
The name of the consumption table.
### time_header
The header used for the time index in the consumption table.
### distance_header
The header used for the distance column in the consumption table.
### fleet_distance_header
The header used for the distance column in the fleet consumption table.
### energy_carriers_consumption_names
The headers for each emergy carrier in the consumption table. 
### fleet_energy_carriers_consumption_names
The headers for each emergy carrier in the fleet consumption table.

## home_type
These are parametrers related to the [home type split](profiles.md#home-type-split) (split for cars between cars with their own driveway and street parking).
### do_car_home_type_split
Set this to true to compute the split. Set it to false not to do it.
### percentages_file
The file name (has to be a csv inside the input/your_case folder)
containing the spli.
See [here](input.md#car-own-driveway-percentage) for details about this file.

### index_name
The index header in the source file.

### own_driveway_name
The header for the own driveway percentage. Also used for the output profile file names.
### on_street_name
The header for the street parking percentage. Used for the output profile file names.
### profiles_index
The index for the profile outputs.
### sessions_index
The index for the sessions outputs.
### sessions_values_columns
The columns of the sessions dataframes.

## sessions
Parameters used for the [sessions](profiles.md#sessions).
### produce
Set to true if you want to create  [sessions](profiles.md#sessions), to
false if you don't.

### generate_profiles
Set to true if you want to [generate profiles from sessions][scenarios_module.md#Generate-profiles-from-sessions], to false if you don't.
## standard_profiles

### produce
Set to true if you want to produce [standard charging profiles](profiles.md#standard-profiles), false if you don't.

## progress_bars
Parameters related to displaying progress bars.
### display_scenario_run
Set to true to show a progress bar for the computing of scenarios, false if you don't.
### scenario_run_description
Text to display for the scenarios progress bar.
### display_saving_pool_run
Set to true to show a progress bar for the saving of output files, false if you don't.
### saving_pool_run_description
Text to display for the output file saving progress bar.

## discharge
Parameters related to vehicle discharge.
### no_discharge_efficiency_output
Message to display if the discharge efficiencncy value is empty.
### no_charge_efficiency_output
Message to display if the charge efficiencncy value is empty.