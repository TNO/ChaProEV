'''
Author:Omar Usmai (Omar.Usmani@TNO.nl).
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
15. **dataframes_from_query_list:**This returns a list of dataframes,
    each obtained from a query in the list
16. **from_grib_to_dataframe:**
This function takes a grib file and converts it to a DataFrame.
17. **sql_query_generator:** This function returns an sql query string that
    can be used (for example) in Panda's read_sql.
18. **database_tables_columns:** Returns a dictionary with the tables of a
    database as keys and their columns as values.
'''

import os
import datetime
import math
import sqlite3
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


import numpy as np
import openpyxl
import pandas as pd
import matplotlib
import xarray as xr


def check_if_folder_exists(folder_to_check):
    '''
    Checks if a folder exists. If it does not, it creates it.
    This way, users can setup a new (sub-)folder in the configuration file
    without having to ensure that it already exits or create it.
    '''

    # We check if the output folder exists.
    if not os.path.exists(folder_to_check):
        # If it doesn't, we create it
        os.makedirs(folder_to_check)


def parameters_from_TOML(parameters_file_name):
    '''
    Reads a TOML parameters file name and returns a parameters
    dictionary.
    '''

    with open(parameters_file_name, mode='rb') as parameters_file:
        parameters = tomllib.load(parameters_file)

    return parameters


def reference_scale(number_list: 'list[float]', digit_shift: int = 0):
    '''
    This function takes a list of numbers an returns a scale
    (lower and upper boundary) they are in.
    The digit shift parameter tells us on which digit we need to
    focus. The default is 0, so the upper boundary of 53.57 will be 60
    by default, but 54 if the digit shift is 1 (thus focussing on the 3 part).
    This can for example be useful to determine the plotting area of a dataset
    (x-axis boundaries).
    '''

    number_list_boundaries = [min(number_list), max(number_list)]
    boundary_powers_of_ten = [
        int(math.log10(number))-digit_shift
        # The first term gives us the power of ten of the highest digit,
        # which we shift with the digit_shift parameter
        for number in number_list_boundaries]

    dividers = [math.pow(10, power) for power in boundary_powers_of_ten]

    if dividers[0] == 0:
        lower_scale = 0
    else:
        lower_scale = (
            math.floor((number_list_boundaries[0])/dividers[0])
            * dividers[0])

    if dividers[1] == 0:
        upper_scale = 0
    else:
        upper_scale = (
            math.ceil((number_list_boundaries[1])/dividers[1])
            * dividers[1])

    return [lower_scale, upper_scale]


def dataframe_from_Excel_table_name(table_name, Excel_file):
    '''
    This function looks up a given table name in an Excel file
    and returns a DataFrame containing the values of that table.
    Note that if the name does not exist (or is spelled wrongly (it's
    case-sensitive), the function will crash).
    '''

    source_workbook = openpyxl.load_workbook(Excel_file)

    # We need to look up the worksheet
    # table_worksheet = ''
    for worksheet in source_workbook.worksheets:
        if table_name in worksheet.tables:
            table_worksheet = worksheet

    table = table_worksheet.tables[table_name]
    table_range = table_worksheet[table.ref]

    table_entries = [
        [cell_entry.value for cell_entry in row_entry]
        for row_entry in table_range
    ]

    table_headers = table_entries[0]
    table_values = table_entries[1:]

    # We need to go thhrough a dictionary, as passing the values directly
    # leads to duplicates with no index, for some reason
    table_dictionary = {}
    for header_index, header in enumerate(table_headers):
        values_for_header = [
            table_row[header_index] for table_row in table_values]
        table_dictionary[header] = values_for_header

    table_dataframe = pd.DataFrame.from_dict(table_dictionary)

    return table_dataframe


def dataframe_to_Excel(dataframe_to_append, Excel_workbook, my_sheet):
    '''
    This function takes a DataFrame and puts it into a new sheet in
    an Excel workbook. If the sheet already exists, it will replace it.
    If the Excel workbook does not exist, the function creates it.
    '''

    if not os.path.isfile(Excel_workbook):
        new_workbook = openpyxl.Workbook()
        new_workbook.save(Excel_workbook)

    with pd.ExcelWriter(
            Excel_workbook, mode='a', engine='openpyxl',
            if_sheet_exists='replace') as writer:

        dataframe_to_append.to_excel(
            writer, sheet_name=my_sheet
        )


def get_extra_colors(parameters_file_name):
    '''
    This function gets the user-defined extra colors from a file.
    This file contains the names of the colors, and their RGB values
    (from 0 to 255). The function returns a DataFrame with
    color names as index, and their RGB codes (between 0 and 1)
    as values.
    '''
    parameters = parameters_from_TOML(parameters_file_name)
    colors = parameters['colors']

    extra_colors = pd.DataFrame(columns=['R', 'G', 'B'])
    for color in colors:
        extra_colors.loc[color] = colors[color]
    extra_colors = extra_colors/255

    return extra_colors


def get_rgb_from_name(color_name, parameters_file_name):
    '''
    This function takes a color name and returns its RGB values (0 to 1).
    If the color name is in the extra colors, then, we use
    the values given.
    If it is a matplotlib color, then we use the matplotlib function.
    '''
    extra_colors = get_extra_colors(parameters_file_name)

    if color_name in extra_colors.index.values:
        return extra_colors.loc[color_name].values
    else:
        return matplotlib.colors.to_rgb(color_name)


def rgb_color_list(color_names, parameters_file_name):
    '''
    Gets a list of RGB codes for a list of color names.
    '''
    rgb_codes = [
        get_rgb_from_name(color_name, parameters_file_name)
        for color_name in color_names
    ]

    return rgb_codes


def register_color_bars(parameters_file_name):
    '''
    This function reads the user-defined color bars in a parameter file
    (names for the bars, and a list of the colors they contain, with the
    first being at the bottom of the bar, and the last at the top, and the
    others in between). It then creates the color bars and stores them
    in the list of available color maps.
    '''

    parameters = parameters_from_TOML(parameters_file_name)
    color_bars = parameters['color_bars']

    # This dictionary stores the dictionaries for each color bar
    color_bar_dictionary = {}
    # These colors are the three base keys of each bar color dictionary
    # Each dictionary contains a tuple of tuples for each base colors
    # Each of these sub-tuples cotains a step (between 0 and 1),
    # and a tone of the basic color in question (red, green, or blue)
    # This is repeated. The second value can be different
    # if cretaing discontinuities.
    # See https://matplotlib.org/stable/gallery/color/custom_cmap.html
    # for details
    base_colors_for_color_bar = ['red', 'green', 'blue']

    # We fill the color bar dictionary
    for color_bar in color_bars:
        # We read the color list
        color_bar_colors = color_bars[color_bar]
        # We set the color steps, based on the color list
        color_steps = np.linspace(0, 1, len(color_bar_colors))

        color_bar_dictionary[color_bar] = {}
        for base_color_index, base_color in enumerate(
                base_colors_for_color_bar):
            # We create a list of entries for that base color
            # It is a list so that we can append,
            # but we will need to convert it to a tuple
            base_color_entries = []
            for color_bar_index, (color_step, color_bar_color) in enumerate(
                    zip(color_steps, color_bar_colors)):
                # We get the ton by getting the RGB values of the
                # color bar color and taking the corresponding base index
                color_bar_color_tone = get_rgb_from_name(
                    color_bar_color, parameters_file_name)[
                    base_color_index]

                base_color_entries.append(
                    # The subtuples consist of the color step
                    (
                        color_step,
                        # And the tone of the base color
                        # for the color corresponding
                        # to the step
                        color_bar_color_tone,
                        # This iis repeated for continuous schemes
                        # See
                        # https://matplotlib.org/stable/gallery/color/custom_cmap.html
                        # for details
                        color_bar_color_tone
                    )
                )
            # We now convert the list to a tuple and put it into
            # the dictionary
            color_bar_dictionary[color_bar][base_color] = tuple(
                base_color_entries)

    # We now add the color bars to the color maps

    for color_bar in color_bars:
        color_bar_to_register = matplotlib.colors.LinearSegmentedColormap(
            color_bar, color_bar_dictionary[color_bar])

        if color_bar_to_register.name not in matplotlib.pyplot.colormaps():
            matplotlib.colormaps.register(color_bar_to_register)


def get_season(time_stamp):
    '''
    This function takes a datetime timestamp and tells us in which season
    it is.
    '''
    # We take the date of the timestamp to avoid issues
    # during the transitions (where the timestamp would be
    # larger than the previous season's end, which is at midnight)
    date = datetime.datetime(
        time_stamp.year, time_stamp.month, time_stamp.day, 0, 0
    )
    seasons = [
            (
                'winter',
                (
                    datetime.datetime(date.year, 1, 1),
                    datetime.datetime(date.year, 3, 20)
                )
            ),
            (
                'spring',
                (
                    datetime.datetime(date.year, 3, 21),
                    datetime.datetime(date.year, 6, 20)
                )
            ),
            (
                'summer',
                (
                    datetime.datetime(date.year, 6, 21),
                    datetime.datetime(date.year, 9, 22)
                )
            ),
            (
                'fall',
                (
                    datetime.datetime(date.year, 9, 23),
                    datetime.datetime(date.year, 12, 20)
                )
            ),
            (
                'winter',
                (
                    datetime.datetime(date.year, 12, 21),
                    datetime.datetime(date.year, 12, 31)
                )
            )
    ]
    for season, (start, end) in seasons:

        if start <= date <= end:
            return season


def save_figure(figure, figure_name, output_folder, parameters_file_name):
    '''
    This function saves a Matplolib figure to a number of
    file formats and an output folder that are all specified in a
    TOML parameters file (under a [files.figures_outputs] heading).
    '''

    check_if_folder_exists(output_folder)
    parameters = parameters_from_TOML(parameters_file_name)
    file_parameters = parameters['files']
    figure_parameters = file_parameters['figures']
    dpi_to_use = figure_parameters['dpi']
    outputs = figure_parameters['outputs']

    for file_type in outputs:
        if outputs[file_type]:
            figure.savefig(
                f'{output_folder}/{figure_name}.{file_type}',
                dpi=dpi_to_use
            )


def save_dataframe(
        dataframe, dataframe_name, groupfile_name,
        output_folder, parameters_file_name
        ):
    '''
    This function saves a pandas dataframe to a number of
    file formats and an output folder that are all specified in a
    TOML parameters file (under a [files.dataframe_outputs] heading).

    Note that for some file types, you might need to install additional
    libraries.

    Also note that some formats will be saved into a group file that
    can contain several other dataframes (for example sheets into an Excel
    workbook or tables into an SQL database). dataframe_name will be the
    file name if the file format does not use group files. If the format does
    use a group fiule, then dataframe_name will be used for the sub-elements
    (sheets, tables, for example), and groupfile_name will be used for
    the file name (you can of course use the same value for both), and will be
    unused if the file format does not use group files.


    Bug to fix: XML does not accet a number to start names (or
    various case variations of xml), which must currently
    be handled by the user (who must avoid these).
    Other bug: Removing non-alphanumeric characters in the index does not seem
    to work (for xml and stata)

    gbq and orc outputs are not currently supported, as gbq is not
    a local file format, but a cloud-based one and orc does not seem to work
    with pyarrow (at least in Windows).
    '''

    check_if_folder_exists(output_folder)
    parameters = parameters_from_TOML(parameters_file_name)
    file_parameters = parameters['files']
    dataframe_outputs = file_parameters['dataframe_outputs']

    file_types = [
        'csv', 'json', 'html', 'latex', 'xml', 'clipboard',
        'excel', 'hdf', 'feather', 'parquet',
        'stata', 'pickle', 'sql'
    ]
    # Note that pandas has a few more export formats that we skipped
    # orc is not supported in arrows (ar least on Windows)
    # https://stackoverflow.com/questions/58822095/no-module-named-pyarrow-orc
    # gbq is about Google cloud storage, not about local files
    # https://cloud.google.com/bigquery/docs/introduction
    # Note that clipboard does not produce a file,
    # but can still be used locally, so the function supports it.

    file_extensions = [
        'csv', 'json', 'html', 'tex', 'xml', '',
        'xlsx', 'h5', 'feather', 'parquet',
        'dta', 'pkl', 'sqlite3'
    ]

    # This determines if the dataframe is saved into its own file
    # or into a group file (such as a database or an Excel Workbook)
    is_groupfile_per_type = [
        False, False, False, False, False, False,
        True, True, False, False,
        False, False, True
    ]

    file_functions = []
    for file_type in file_types:
        # Some file formats require some extra processing, so
        # we need to forgo list compreshension and use
        # copies of the dataframe that we will modify

        dataframe_to_use = dataframe.copy()

        if file_type == 'feather':
            # feather does not support serializing
            #  <class 'pandas.core.indexes.base.Index'> for the index;
            #   you can .reset_index() to make the index into column(s)
            dataframe_to_use = dataframe_to_use.reset_index()

        if file_type in ['xml', 'stata']:
            # These file formats have issues with some characters
            # in column and index names
            # Note that for xml, the names cannot start with the letters xml
            # (with all case variations) and must start with a letter or
            # underscore (replacement of such issues is not implemented
            # at the moment, so the function will fail unless you correct
            # that in your data).
            # Note that stata also has issues with too lonmg names
            #  (>32 characters), but the to_stata function manages this on its
            # own (by cutting any excess characters). As such, this does
            # not need to be corrected here
            code_for_invalid_characters = '[^0-9a-zA-Z_.]'

            dataframe_to_use.columns = (
                dataframe_to_use.columns.str.replace(
                    code_for_invalid_characters,  '_', regex=True)
            )

            if dataframe_to_use.index.name:
                # We only need to do the replacements if the index
                # has a name. This causes issues if we try to replace
                # things if the index does not have a name
                dataframe_to_use.index.name = (
                    dataframe_to_use.index.name.replace(' ', '_'))
            elif dataframe_to_use.index.names:
                # MultiIndex has to be treated sepaartely
                if dataframe_to_use.index.names[0] is not None:
                    dataframe_to_use.index.names = [
                        old_name.replace(' ', '_')
                        for old_name in dataframe_to_use.index.names
                    ]

        function_name = f'to_{file_type}'

        if file_type == 'latex':
            # In future versions `DataFrame.to_latex` is expected to utilise
            #  the base implementation of `Styler.to_latex` for formatting
            # and rendering. The arguments signature may therefore change.
            # It is recommended instead to use `DataFrame.style.to_latex`
            # which also contains additional functionality.
            # function_name = f'Styler.to_{file_type}'
            file_functions.append(dataframe_to_use.style.to_latex)
        else:
            file_functions.append(getattr(dataframe_to_use, function_name))

    using_file_types = [
        dataframe_outputs[file_type] for file_type in file_types
    ]

    for (
        file_type, file_extension, file_function, using_file_type,
        is_groupfile
        ) in zip(
                file_types, file_extensions, file_functions, using_file_types,
                is_groupfile_per_type):

        if using_file_type:
            if is_groupfile:
                file_to_use = (
                    f'{output_folder}/{groupfile_name}.{file_extension}'
                )

                if file_type == 'hdf':
                    file_function(
                        file_to_use,
                        key=dataframe_name)
                elif file_type == 'excel':
                    # If we want to append a sheet to an Excel file
                    # instead of replacing the existing file, we need
                    # to use Excelwriter, but that gives an error if the
                    # file does not exist, so we need to check if the file
                    # exists
                    if os.path.exists(file_to_use):
                        writer_to_use = pd.ExcelWriter(
                            file_to_use, engine='openpyxl', mode='a',
                            if_sheet_exists='replace'
                            )
                        with writer_to_use:
                            file_function(
                                writer_to_use,
                                sheet_name=dataframe_name
                            )
                    else:
                        # If the file does not exist, we need to use the
                        # function, which is to_excel() with the file name,
                        # not with a writer
                        file_function(
                            file_to_use,
                            sheet_name=dataframe_name
                            )

                elif file_type == 'sql':
                    with sqlite3.connect(file_to_use) as sql_connection:
                        file_function(
                            dataframe_name,
                            con=sql_connection,
                            if_exists='replace'
                        )

            else:
                file_to_use = (
                    f'{output_folder}/{dataframe_name}.{file_extension}'
                )
                file_function(file_to_use)


def put_dataframe_in_sql_in_chunks(
        source_dataframe, sql_file, table_name, chunk_size,
        drop_existing_table=True):
    '''
    This function takes a Dataframe and writes it into the table
    of an SQL database. It does so in chunks to avoid memory issues.
    The parameter drop_existing table tells us if we want to
    dro/overwrite the table if it exists (it is True by default).
    If set to False, the data will be appended (if the table exists).
    '''

    # We first need the total data/index length of the Dataframe
    data_length = len(source_dataframe.index)

    # We initialise the chunk boundaries and the sql connection
    chunk_start = 0
    chunk_end = 0

    with sqlite3.connect(sql_file) as sql_connection:
        if drop_existing_table:
            table_action = 'replace'
        else:
            table_action = 'append'

        while chunk_end < data_length:

            chunk_end = min(chunk_start+chunk_size, data_length)
            # We select the corresponding chunk in the dataframe and
            # write it to the SQL database
            dataframe_chunk = source_dataframe.iloc[chunk_start:chunk_end]

            dataframe_chunk.to_sql(
                table_name, con=sql_connection, if_exists=table_action
            )

            chunk_start = chunk_end+1
            # Subsequent additions append in all cases
            table_action = 'append'


def query_list_from_file(sql_file):
    '''
    This returns a list of queries from an SQL file
    '''

    with open(sql_file) as script_file:
        sql_queries = script_file.read().split(';')

    sql_queries.remove('')
    return sql_queries


def dataframes_from_query_list(query_list, sql_connection):
    '''
    This returns a list of dataframes, each obtained from a query in the list
    '''
    dataframe_list = [
        pd.read_sql(sql_query, sql_connection) for sql_query in query_list
    ]

    return dataframe_list


def from_grib_to_dataframe(grib_file):
    '''
    This function takes a grib file and converts it to a DataFrame.
    **Important note:**
    You need to have ecmwflibs installed for the grib converter to work.
    Installing xarray (and cfrgrib to have the right engine) is not enough!
    See:
    https://github.com/ecmwf/eccodes-python/issues/54#issuecomment-925036724
    '''
    grib_engine = 'cfgrib'

    source_data = xr.load_dataset(grib_file, engine=grib_engine)
    source_dataframe = source_data.to_dataframe()

    return source_dataframe


def sql_query_generator(
        quantities_to_display, source_table, query_filter_quantities,
        query_filter_types, query_filter_values):
    '''
    This function returns an sql query string that can be used
    (for example) in Panda's read_sql.
    The input parameters are:
    - quantities_to_display: A string list of table column names
    (as strings, in
    single quotes), separated by commas. If the user
    wants all columns displayed, then they should use a '*'. If one (or more)
    of the column names have spaces, then the user needs to use f strings and
    double quotes, as in the following example:
    quantity_1 = 'Time'
    quantity_2 =  'Surveyed Area'
    quantity_2_with_quotes = f'"quantity_2"'
    quantities_to_display = f'{quantity_1}, {quantity_2_with_quotes}'
    This latter variable is the input for the function
    - source table is the name of the source table. Note that it has a similar
    need if the name has spaces, so use:
    source_table = f'"My Table"'
    as an input
    - query_filter_quntities: A list of strings each representing a column
    name the user wants to filter. Again, names with spaces require
    f strings and double quotes, so add:
    f'"Surveyed Area"' to your list of filter names
    - query_filter_types: This list (that has to be the same length as the
    above liste of quantities)
    says which filter to use. Currently supported options are:
        - '='       (equal to)
        - '<'       (smaller than)
        - '>'       (larger than)
        - '!='      (not equal)
        - '<>'      (not equal)
        - '<='      (smalller or equal)
        - '>='      (larger or equal)
        - like      (matches/ searches for a pattern)
        - between   (between two  values)
        - in        (to select multiple values for one or several columns)
    - query_filter_values: The comparison values used for the filter.
    The three special cases are:
        1) Like: This needs to be a double quote string (since it will be
        nested into a single-quote string) with percentage signs,
        such as '"%2020-05-08%"' for timestamps for May 8th, 2020
        2) Between: Provide the two  values  into a
        list. If the values arte strings that contain spaces,
        you need nested quotes, such as:
        ['"2020-05-08 00:00:00"','"2020-06-26 16:00:00"']
        3) In provide the two tuple values into a list.,
        e.g: [(52.1,4.9),(52.0,5.1)]

    '''

    first_filter = True
    query_filter = ''
    for filter_quantity, filter_type, filter_value in zip(
        query_filter_quantities, query_filter_types, query_filter_values
    ):

        if first_filter:
            query_filter = f'where '
            first_filter = False
        else:
            query_filter = f'{query_filter} and'

        if filter_type.lower() == 'between':
            query_filter = (
                f'{query_filter} {filter_quantity} between {filter_value[0]} '
                f'and {filter_value[1]}'
            )
        elif filter_type.lower() == 'in':
            # We need the filter to be a string without (single) quotes
            # between brackets and the syntax and procedure are
            # different for tuples

            if type(filter_quantity) is tuple:

                tuple_content_string = ','.join(filter_quantity)
                filter_quantity = f'({tuple_content_string})'

                query_filter = (
                    f'{query_filter} {filter_quantity} in (values '
                    f'{filter_value[0]},{filter_value[1]})'
                )
            else:
                filter_value = [f'{my_value}' for my_value in filter_value]
                filter_value = ','.join(filter_value)
                query_filter = (
                    f'{query_filter} {filter_quantity} '
                    f'in ({filter_value})'
                )

        else:
            query_filter = (
                f'{query_filter} {filter_quantity} '
                f'{filter_type} {filter_value}'
            )

    output_query = (
        f'select {quantities_to_display} from {source_table} '
        f'{query_filter};'
    )

    return output_query


def database_tables_columns(database):
    '''
    Returns a dictionary with the tables of a database as keys and their
    columns as values.
    '''
    database_connection = sqlite3.connect(database)
    tables_query = 'select name from sqlite_master where type="table";'
    database_cursor = database_connection.cursor()
    database_cursor.execute(tables_query)
    database_tables = database_cursor.fetchall()
    tables_columns = {}
    for table in database_tables:
        table_name = table[0]
        # table_name = f'"{table[0]}"'
        table_cursor = database_connection.execute(
            f'select * from "{table_name}"'
        )
        tables_columns[table_name] = [
            description[0] for description in table_cursor.description
        ]

    return tables_columns


if __name__ == '__main__':

    parameters_file_name = 'YAL.toml'
