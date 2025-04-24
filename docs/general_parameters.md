# Purpose
The purpose of the ChaProEV.toml file is to set parameters
that are common for all your scenarios.
This page describes the various parameters.

# variants
The variants section of the configuration file sets parameters
to create scenario [variants](variants.md) (see that page for
details).
1.  **use_variants"** Setting the use_variants parameters to true creates variants,
while setting it to false skips variant creation althogether.
2. **csv_version:** Setting the csv_version to true parameters makes you use csv files
to define your variants (in a folder within the variants folder: this
folder needs to have the same name as your case). Setting it to false makes you use a toml file in the variants folder (case_name.toml).
3. **use_years_in_profiles:** This is used to create different variants per year when doing 
[car home own driveway and street parking splits](car_home_own_driveway_splits.md)




# parallel_processing
This parallel processing section of the configuration file sets parameters to manage the [parallel processing/multiprocessing](multiprocessing.md) of the model (which reduces the model run time, see link for details).
[parallel_processing]
1. **set_amount_of_processes:** set this as false if you want the amount of parallel processes to be determined by the model (via the [multiprocessing standard library of Python](https://docs.python.org/3/library/multiprocessing.html)). Set this to true if you want to set the amount of processes yourself.
2. **amount_for_scenarios:** If you put true in set_amount_of_processes, provide a number of parallel processes here to run scenarios in parallel.
3. **amount_for_pickle_saves:** If you put true in set_amount_of_processes, provide a number of parallel processes here to save the pickle output saves to other formats in parallel (see [writing module](writing.md) for details).

# interim_files
This concerns parameters for saving intermediary results to files.
1. **pickle:** Set this to true to save interim results to pickle files.
Set this to false not to do this.
2. **consumption_tables_frequencies:** Provide a list of consumption
tables frequencies (see [consumption module](consumption.md)). The default is the following list ['hourly', 'daily', 'weekly', 'monthly', 'yearly']
**save_consumption_table:**  Provide a list of booleans (true or false) to save a given frequency to file (this list needs to have the same length as the above list): true save a file for that frequency and false does not.




