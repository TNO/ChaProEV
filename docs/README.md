Test
## More

## Even more

## **List of relevant files and modules**

### **ChaProEV.py**
 Where you run the model

### **scenarios folder**
This folder contains scenario configuration files. There is one per scenario,
containing all necessary parameters to run the scenatio. To add a scenario,
copy one of the existing files and add/remove/modify parasmeters paramters as
required, including the first parameter, which is the scenario name,
which should be the same as the file name (it might work with another name,
but this is not tested and there is no reason to have different names for the
same scenario).
These scenario files contain the following sections:
- **unit_conversions:** Parameters to convert units
- **files:** File-related parameters (folders, output type choices, etc.)
- **colors:** Color-related parameters(defining new ones, as well as color bars)
- **time:** Time-related parameters and constants needed in formulas
- **run:** Parameters related to the run, such as timing, and elements such
as locations, vehicles, legs, trips, etc.
- **weather:** Parameters related to the weather, such as elements to define
what we want to download from various sources, where we store weather data,
how we process it, 
or how we want to label quantititis
- **plots:** Parameters for plots (colors, sizes, etc.)





### **define.py:**
This module defines and declares classes for the different objects 
that define the system (the parameters/defintions come from a parameters file),
namely:
1. **Legs:** Legs are point-to-point vehicle movements (i.e. movements where
    the vehicle goes from a start location and ends/stops at an end location).
2. **Vehicles:** Each vehicle type (or subtype) is defined in this class.


### **weather.py**
This module contains functions related to weather data and factors.
The weather data is pulled from the [CDS (Climate Data Store) ERA-5 weather
data from the Copernicus institute](https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land?tab=form).
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
4. **write_weather_database"** This function writes the weather database.
5. **get_hourly_values:** This function takes a Dataframe for a 
given weather quantity. If this is a cumulative quantity, it adds hourly 
values to it.
6. **get_all_hourly_values:** This functions adds hourly values to
cumulative quantities in the weather database.
7. **get_EV_tool_data:**: This gets the temperature efficiency data from the
EV tool made by 
[geotab](https://www.geotab.com/CMS-GeneralFiles-production/NA/EV/EVTOOL.html).
8. **temperature_efficiency_factor:**This function returns the temperature
efficiency factor that corrects the baseline vehicle efficiency.
9. **plot_temperature_efficiency:** Plots the temperature efficiency 
correction factor (source data versus interpolation)of electric vehicles.
10. **get_run_location_weather_quantity:** Returns a chosen weather quantity
    for a given location and a given runtime.
11. **get_run_weather_data:** Fetches the weather data and efficiency factors
    and puts it into a table that is saved to files/databases.
12. **solar_efficiency_factor:*** This gives us the efficiency factor of solar
     panels (i.e. how much of the solar radiation is converted into
     electricity).
    THIS IS A PLACEHOLDER FUNCTION
13. **setup_weather:** This runs all the functions necessary to get the run
    weather factors for a given case.
14. **get_location_weather_quantity:** Returns the value a a chosen
    weather quantity for a given location and time tag.


### **run_time.py:**
This module defines time structures.

It contains the following functions:
1. **get_time_range:** This function returns the time range of the run, and the
    associated hour numbers, based on values found in the
    parameters file.
2. **get_time_stamped_dataframe:** This function creates a DataFrame with the
timestamps of the run as index (and hour numbers as a column).
3. **get_day_type:** Tells us the date type of a given time_tag.
4. **add_day_type_to_time_stamped_dataframe:** Adds a column with the date type
to a time-stamped_dataframe

### **writing.py:**
This contains functions related to writting outputs.
It contains the following functions:
1. **write_scenario_parameters:** This function writes the scenario parameters
    to the output files (either as separate files, or as tables/sheets
    in groupfiles.)
### **mobility.py:**
This module computes the various functions related to mobility.
It contains the following functions:
1. **get_trip_probabilities_per_day_type:** This function computes the trip
probabilities per day type.

#### Temperature efficiency
This function returns the temperature efficiency factor that corrects
the baseline vehicle efficiency. It uses a data file (extracted from
EV tool made by 
[geotab](https://www.geotab.com/CMS-GeneralFiles-production/NA/EV/EVTOOL.html).

[This information](https://www.geotab.com/blog/ev-range/) is
based on 5.2 million trips by 4200 vehicles.
The degree 6 polynomial fit is:

$$
C(T)=0.7078+0.01751\cdot T+0.0001611\cdot T^2-1.036\cdot 10^{-5}\cdot T^3
-3.581\cdot 10^{-7}\cdot T^4+1.746\cdot 10^{-9}\cdot T^5
+1.07\cdot10^{-10}\cdot T^6
$$

where T is the ambient temparture (in the weather data, it's the temperature
at 2 meters), and C is the efficiency correction factor.

Plotting the fit verus the data shows that thisi a great fit:
<center>
<img src=Vehicle_Temperature_correction_factor.svg>
</center>