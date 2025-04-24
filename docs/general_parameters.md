# Purpose
The purpose of the ChaProEV.toml file is to set parameters
that are common for all your scenarios.
This page describes the various parameters.
You can use the navigation bar on the left to go directly to a group
of parameters (or a given parameter).

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
[car home own driveway and street parking splits](car_home_own_driveway_splits.md)




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

### headers
### fleet_headers
### do_fleet_tables
### fleet_file_name

## sessions_dataframe

### properties
### dataframe_headers
### run_dataframe_headers
### display_dataframe_headers
### display_dataframe_index
### fleet_display_dataframe_headers

## plots
### vehicle_temperature_efficiency
#### style
#### source_data_folder
#### source_data_file 
#### fit_color 
#### fit_line_size
#### geotab_data_color 
#### geotab_data_size
#### title_size 

## files
### input_root
### output_root
### groupfile_root

### figures
#### dpi
#### outputs

### dataframe_outputs


## maps
## map_data_folder
## area_data_file_name
## general_exclusion_codes
## border_data_file_prefix
## border_data_file_suffix
## points_data_file_prefix
## points_data_file_suffix
## country_code_header
## country_code_header_in_map_data
## heat_bar_map

## colors

## color_bars

## unit_conversions

## numbers

## consumption
### energy_carriers
### consumption_table_name
### time_header
### distance_header
### fleet_distance_header
### energy_carriers_consumption_names
### fleet_energy_carriers_consumption_names


## home_type
### do_car_home_type_split
### percentages_file
### index_name
### own_driveway_name
### on_street_name
### profiles_index
### sessions_index
### sessions_values_columns

## sessions
### produce
### generate_profiles
## standard_profiles
### produce

## progress_bars
### display_scenario_run
### scenario_run_description
### display_saving_pool_run
### saving_pool_run_description

## discharge
### no_discharge_efficiency_output
### no_charge_efficiency_output
