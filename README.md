# **ChaProEV**




This repository contains the ChaProEV (Charging Profiles of Electric Vehicles)
model.

## Status
The ChaProEV model is under construction and not yet ready for use.
Please contact the authors below if you have questions or requests to get
model runs at some point.

## Authors and contact
Omar Usmani (Omar.Usmani@TNO.nl)


## Licence

ChaProEV is released under the Apache 2.0 licence.
All accompanying documentation and manual are released under the 
Creative Commons BY-SA 4.0 license.

## Libraries used and licensing

### Main libraries to install
1. [Python](https://www.python.org/) and its 
    [standard library](https://docs.python.org/3/library/) use the 
    [PSF licence](https://docs.python.org/3/license.html). ChaProEV uses the
    following modules:
     1. [math](https://docs.python.org/3/library/math.html)
     2. [datetime](https://docs.python.org/3/library/datetime.html)
     3. [os](https://docs.python.org/3/library/os.html)
     4. [tomlib](https://docs.python.org/3/library/tomllib.html)
     5. [sqlite3](https://docs.python.org/3/library/sqlite3.html)
2. [tomli](https://pypi.org/project/tomli/) uses the 
    [MIT license](https://opensource.org/license/mit/) (only when using Python <3.11)
3. [pandas](https://pandas.pydata.org/) uses the
    [BSD 3 license](https://github.com/pandas-dev/pandas/blob/main/LICENSE)
4. [numpy](https://numpy.org/) 
[uses the BSD 3 license](https://github.com/numpy/numpy/blob/main/LICENSE.txt)
5. [matplotlib](https://matplotlib.org/) 
    only uses BSD compatible code, and its 
[license](https://matplotlib.org/stable/devel/license.html#license-discussion)
    is based on the PSF license.
6. [openpyxl](https://pypi.org/project/openpyxl/) 
uses the [MIT license](https://opensource.org/license/mit/)
7.  [Jinja2](https://pypi.org/project/Jinja2/) uses a
 [BSD-3-Clause](https://pypi.org/project/Jinja2/) license
8. [PyArrow](https://arrow.apache.org/docs/python/index.html) uses the 
 [Apache 2.0 license](https://arrow.apache.org/docs/_modules/pyarrow.html)
9. [lxml](https://lxml.de/) is shipped under a [BSD license](https://lxml.de/)
10. [tables](https://www.pytables.org/) uses 
    a [BSD-3 clause license](https://github.com/PyTables/PyTables/blob/master/LICENSE.txt) 
    note that you need to
    install 'tables'  (i.e. use 'pip install tables') though the package 
    is sometimes referred to as pytables
11. [cdsapi](https://pypi.org/project/cdsapi/) uses the 
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
12. [requests](https://pypi.org/project/requests/) uses
the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
13. [ecmwflibs](https://pypi.org/project/ecmwflibs/) uses
the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) (See note below)
14. [xarray](https://pypi.org/project/xarray/) uses
the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) (See note below)
15. [cfgrib](https://pypi.org/project/cfgrib/) uses
the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) (See note below)
16. [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) uses 
the [MIT license](https://opensource.org/license/mit/) (it is imported with 
'bs4', which can also be used to install the library)

**Important note:**
You need to have ecmwflibs installed for the grib converter to work. Installing
xarray (and cfrgrib to have the right engine) is not enough!
See [here](https://github.com/ecmwf/eccodes-python/issues/54#issuecomment-925036724)

### Dependencies of installed libraries
These libraries are installed when the above libraries are installed.

1. [six](https://pypi.org/project/six/) 
uses the [MIT license](https://opensource.org/license/mit/)
2. [pytz](https://pypi.org/project/pytz/) 
uses the [MIT license](https://opensource.org/license/mit/)
3. [python-dateutil](https://pypi.org/project/python-dateutil/) uses
either the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) or the
[BSD 3-Clause](https://opensource.org/licenses/BSD-3-Clause) licenses, 
depending on the contribution.
4. [contourpy](https://pypi.org/project/contourpy/) uses the 
[BSD 3-Clause](https://opensource.org/licenses/BSD-3-Clause) license
5. [cycler](https://pypi.org/project/cycler/) uses 
a [BSD](https://opensource.org/license/bsd-1-clause/) license 
(version not specified)
6. [fontTools](https://pypi.org/project/fonttools/) 
uses the [MIT license](https://opensource.org/license/mit/)
7. [importlib-resources](https://pypi.org/project/importlib-resources/) 
(only in earlier Python versions)
uses the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license 
(actual version not specified).
8. [kiwisolver](https://pypi.org/project/kiwisolver/) a 
[BSD](https://opensource.org/license/bsd-1-clause/) license 
(version not specified)
9. [packaging](https://pypi.org/project/packaging/) uses  a 
[BSD](https://opensource.org/license/bsd-1-clause/) license 
(version not specified) and an 
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license 
(actual version not specified).
10. [Pillow](https://pypi.org/project/Pillow/) uses
[HPND (Historical Permission Notice and Disclaimer)](https://spdx.org/licenses/HPND.html)
11. [pyParsing](https://pypi.org/project/pyparsing/) 
uses the [MIT license](https://opensource.org/license/mit/)
12. [zipp](https://pypi.org/project/zipp/) (only in earlier Python versions)
uses the [MIT license](https://opensource.org/license/mit/)
13. [et-xmlfile](https://pypi.org/project/et-xmlfile/)
uses the [MIT license](https://opensource.org/license/mit/)
14. [MarkupSafe](https://pypi.org/project/MarkupSafe/) uses the 
[BSD 3-Clause](https://opensource.org/licenses/BSD-3-Clause) license
15. [blosc2](https://pypi.org/project/blosc2/) uses the 
[BSD 3-Clause](https://opensource.org/licenses/BSD-3-Clause) license
16. [Cython](https://pypi.org/project/Cython/) uses an 
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license 
(actual version not specified).
17. [MessagePack](https://pypi.org/project/msgpack/) uses an 
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
18. [numexpr](https://pypi.org/project/numexpr/) uses the 
[MIT license](https://opensource.org/license/mit/)
19. [py-cpuinfo](https://pypi.org/project/py-cpuinfo/)  uses the 
[MIT license](https://opensource.org/license/mit/)
20. [tzdata](https://pypi.org/project/tzdata/) uses
the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
21. [certifi](https://pypi.org/project/certifi/) uses the 
[Mozilla Public Licence 2.0](https://www.mozilla.org/en-US/MPL/2.0/)
22. [charset-normalizer](https://pypi.org/project/charset-normalizer/)
uses the [MIT license](https://opensource.org/license/mit/)
23. [colorama](https://pypi.org/project/colorama/) uses 
a [BSD](https://opensource.org/license/bsd-1-clause/) license 
(version not specified)
24. [idna](https://pypi.org/project/idna/) uses 
a [BSD](https://opensource.org/license/bsd-1-clause/) license 
(version not specified)
25. [tqdm](https://pypi.org/project/tqdm/) uses 
the [MIT license](https://opensource.org/license/mit/) and the
[Mozilla Public Licence 2.0](https://www.mozilla.org/en-US/MPL/2.0/)
26. [urllib3](https://pypi.org/project/urllib3/) uses 
the [MIT license](https://opensource.org/license/mit/)
27. [xarray](https://pypi.org/project/xarray/) uses an 
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
28. [soupsieve](https://pypi.org/project/soupsieve/) uses 
the [MIT license](https://opensource.org/license/mit/)

### Non-compulsory libraries
The following libraries are also in requirements.txt, but are not strictly
needed to run ChaProEV:
1. [pycodestyle](https://pypi.org/project/pycodestyle/) uses the
[MIT license](https://opensource.org/license/mit/) License (Expat license). 
This is used to check if the code follows
proper style guidelines

(See requirements.txt file for versions (corresponding to Python 3.11.1, which
is the version used for developping  and testing the model))

## **List of relevant files and modules**

### **ChaProEV.py**
 Where you run the model

### **ChaProEV.toml**
This file contains the model's parameters.
It contains the following sections:
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


### **cookbook.py**

This module is a cookbook with useful auxiliary functions.
It contains the following functions:

1. **check_if_folder_exists:** Checks if a folder exists.
    If it does not, it creates it.
2. **parameters_from_TOML:**  Reads a TOML parameters file name and returns
    a parameters dictionary.
3. **reference_scale:** This function takes a list of numbers an returns
    a scale (lower and upper boundary) they are in.
4. **dataframe_from_Excel_table_name:** This function looks up a given table
    name in an Excel file and returns a DataFrame containing the values of
    that table.
5. **dataframe_to_Excel:** This function takes a DataFrame and puts it into
    a new sheet in an Excel workbook.
6. **get_extra_colors:** This function gets the user-defined extra colors
    from a file.
7. **get_RGB_from_name:** This function takes a color name and returns
    its RGB values (0 to 1).
8. **rgb_color_list:** Gets a list of RGB codes for a list of color names.
9. **register_color_bars:** This function reads the user-defined color bars
    in a parameter file, creates them and makes them available.
10. **get_season:** This function takes a datetime timestamp and tells us
    in which season it is.
11. **save_figure:** Saves a Matplotlib figure to a number of file formats set
    by the user.
12. **save_dataframe:** Saves a pandas dataframe to a number of file formats
    set by the user.
13. **put_dataframe_in_sql_in_chunks:** This function takes a Dataframe and
    writes it into the table of an SQL database.
    It does so in chunks to avoid memory issues.
14. **query_list_from_file:** This returns a list of queries from an SQL file
15. **dataframes_from_query_list:** This returns a list of dataframes,
    each obtained from a query in the list
16. **from_grib_to_dataframe:**
This function takes a grib file and converts it to a DataFrame.
17. **sql_query_generator:** This function returns an sql query string that 
    can be used (for example) in Panda's read_sql.
18. **database_tables_columns:** Returns a dictionary with the tables of a
    database as keys and their columns as values.


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

## **Context, goals, and future developments**

### **Driver**
The primary driver for the publication and development of ChaProEv in this
repository is the participation in the Mopo project (funded from 
European Climate, 
Infrastructure and Environment Executive Agency under the European Union’s 
HORIZON Research and Innovation Actions under grant agreement N°101095998).

### **Goal**
The main goal of providing this repository is transparency regarding the 
assumptions and computations of the ChaProEV model.

### **Uses outside Mopo**

#### **Prior to Mopo**

1. [Afspraken maken: 
Van data tot 
informatie
Informatiebehoeften, datastandaarden en 
protocollen voor provinciale 
systeemstudies – Deel II technische 
rapportage. Nina Voulis, Joeri Vendrik, Reinier van der Veen, Alexander Wirtz, Michiel Haan, Charlotte von Meijenfeldt, 
Edwin Matthijssen, Sebastiaan Hers, Ewoud Werkman (CE Delft, TNO, Quintel), April 2021](https://www.topsectorenergie.nl/sites/default/files/uploads/CE_Delft_200227_Afspraken_maken_Van_data_tot_informatie_Deel%202.pdf) where a previous version of ChaProEV was used to provide charging profiles of electric vehicles at the province level (for the Dutch proivinces of North Holland and Limburg)

2. [Elektrisch rijden personenauto's & logistiek: Trends en impact op het elektriciteitssyteem. Hein de Wilde, Charlotte Smit, Omar Usmani, Sebastiaan Hers (TNO), Marieke Nauta (PBL), August 2022](https://publications.tno.nl/publication/34640002/AVDCKb/TNO-2022-P11511.pdf) where a previous version of ChaProEV was used to identify potential moments where charging electric cars could result in local (i.e. neighbourhood/transformer level) network issues and see if these issues could be solved.

3. [Verlagen van lokale impact laden elektrisch vervoer: De waarde en haalbarheid van potentiële oplossingen, Charlotte Smit, Hein de Wilde, Richard Westerga, Omar Usmani, Sebastiaan Hers, TNO M12721, December 2022](https://energy.nl/wp-content/uploads/kip-local-impact-ev-charging-final-1.2.pdf) where a previous version of ChaProEV was used to identify and quantify potential solutions to potential local (i.e. neighbourhood/transformer level) issues due to a possible large-scale adoption of electric cars (with illustrative examples for neighbourhoods in ihe cities of Amsterdam and Lelystad).

4. [TRADE-RES](https://traderes.eu/). A previous version of ChaProEV was used to generate reference charging profiles for a number of European countries, based on statistical differences per country



#### **After/during Mopo**


#### **Future**
The ChaProEV will be used in other projects that will be listed here, if deemed
relevant and apprpriate within the context of these projects.



## Acknowledgments
&nbsp;
<hr>
<center>
<table width=500px frame="none">
<tr>
<td valign="middle" width=100px>
<img src=eu-emblem-low-res.jpg alt="EU emblem" width=100%></td>
<td valign="middle">This project has received funding from European Climate, 
Infrastructure and Environment Executive Agency under the European Union’s 
HORIZON Research and Innovation Actions under grant agreement N°101095998.</td>
<tr>
</table>
</center>