#
# Import necessary libraries
#

import pandas as pd
from settings import conf  # Import configuration defined in settings.py
import requests


#
# Function to get COVID-19 data
#

def import_data():

    print("Get COVID-19 data. This may take a while.")

    # If settings say so, refresh the data source
    if not conf['refresh_source']:
        print("Skipping external refresh of the data. (To change this, adjust 'refresh_source' setting.)")
    else:
        import_refresh_source()

    print("Start data import.")

    # Import CSV with COVID-19 data
    covid_raw = pd.read_csv('data/european-regional-tracker.csv',
                            sep=';',
                            decimal='.',
                            parse_dates=['date'],
                            usecols=['country', 'nuts_id', 'nuts_name', 'date', 'population', 'cases_daily'],
                            header=0,
                            )

    # Set column names
    covid_raw.columns = ['country', 'nuts_id', 'nuts_name', 'date', 'population', 'cases']

    print("Import done.")

    #
    # If selected above, reduce the dataset to selected time frame
    #

    if conf['limit_dates']:
        print(f"Reducing dataset to timframe between {conf['data_start']} and {conf['data_end']}")
        covid_raw = covid_raw[(covid_raw['date'] >= conf['data_start']) & (covid_raw['date'] <= conf['data_end'])]
        print("Done.")

    return covid_raw


#
# Function to refresh COVID-19 data from source
#

def import_refresh_source():

    print("Refresh data from GitHub: Start download.")

    # COVID19-European-Regional-Tracker
    # https://github.com/asjadnaqvi/COVID19-European-Regional-Tracker
    remote_url = 'https://raw.githubusercontent.com/asjadnaqvi/COVID19-European-Regional-Tracker/master/04_master' \
                 '/csv_nuts/EUROPE_COVID19_master.csv'
    local_file = 'data/european-regional-tracker.csv'

    # Make http request for remote file data
    data = requests.get(remote_url)

    # Save file data to local copy
    with open(local_file, 'wb') as file:
        file.write(data.content)

    print(f"Done. File saved as {local_file}")


#
# Function to clean data after import
#

def clean_data(covid_raw):

    print("\nDo some cleaning.")

    # Make a copy of the dataframe
    covid_clean = covid_raw.copy()

    # Remove negative values
    covid_clean = clean_remove_neg(covid_clean)

    # Remove NUTS regions irrelevant to the map
    covid_clean = clean_remove_nuts(covid_clean)

    # Remove outliers in each NUTS id group
    covid_clean = clean_outliers(covid_clean)

    # Sort dataframe
    covid_clean = covid_clean.sort_values(['nuts_id', 'date'])

    print("\nCleaning done.")

    return covid_clean


#
# Function to remove negative values
#

def clean_remove_neg(covid_clean):

    # Remove rows with negative values
    print("\nRemove rows with negative values.")

    length_before = len(covid_clean)
    covid_clean = covid_clean[covid_clean['cases'] >= 0]
    length_after = len(covid_clean)

    print(f"\nRemoved {length_before - length_after} rows with values below 0."
          f"\n{length_after} rows left.")

    return covid_clean


#
# Function to remove NUTS regions irrelevant to the map
#

def clean_remove_nuts(covid_clean):

    print("\nRemove NUTS regions irrelevant to the map.")

    # Mostly oversea territories
    remove_nuts = ['ES707', 'ES709', 'PT300', 'FRY10', 'FRY20', 'FRY30', 'FRY40', 'FRY50']
    covid_clean = covid_clean[~covid_clean['nuts_id'].isin(remove_nuts)]

    print(f"Removed {len(remove_nuts)} NUTS regions, leaving {len(covid_clean)} rows.")

    return covid_clean


#
# Function to remove outliers in each NUTS id group
#

def clean_outliers(covid_clean):

    print("\nRemove extreme outliers for each NUTS group.")

    df_out = covid_clean.copy()

    # Calculate cases per population and exclude values below zero
    df_out['cases_pop'] = df_out['cases'] / df_out['population'] * 10000
    df_out = df_out[df_out['cases_pop'] >= 0]

    # Define outliers in a new column
    # (1) First create a new column grouping by NUTS and working on cases_pop.
    # (2) Then calculate the difference of each days' value to the mean of a rolling window of 45 days before and after
    #     that date. That way we get outliers in that timeframe.
    # (3) Lastly exclude all rows whose calculated value is more than five times the standard deviation for that
    #     timeframe, i.e. we only catch extreme outliers.
    df_out['is_outlier'] = df_out.groupby('nuts_id')['cases_pop'] \
        .transform(lambda x: (x - x.rolling(120, min_periods=15, center=True).mean()).abs()
                             > 5 * x.rolling(120, min_periods=15, center=True).std())

    # Include only outlier rows with more than 100 cases per million population
    df_out = df_out[df_out['is_outlier'] & (df_out['cases_pop'] >= 100)]

    covid_clean = covid_clean[~covid_clean.index.isin(df_out.index)]

    print(f"Removed {len(df_out)} extreme outliers leaving {len(covid_clean)} rows.")

    return covid_clean


#
# Function to do calculations to transform the data
#

def transform_data(covid_clean):
    print("\nDo some calculations.")

    # Make a copy of the dataframe
    covid_calc = covid_clean.copy()

    # Function to add missing dates for each nuts_id group
    covid_calc = transform_missing_dates(covid_calc)

    # Fill missing values in 'static' columns
    covid_calc = transform_fill_missing(covid_calc)

    # Interpolate missing values in 'dynamic' columns
    covid_calc = transform_interpolate(covid_calc)

    # Calculate cases in relation to population for each NUTS ID
    covid_calc = transform_calc_pop(covid_calc)

    # "Fork" weekly aggregates before further calculations
    covid_calc_weekly = transform_fork_weekly(covid_calc)

    # Calculate 7-, 14-, and 28-day moving average for each NUTS ID
    covid_calc = transform_moving_avg(covid_calc, period='daily')
    covid_calc_weekly = transform_moving_avg(covid_calc_weekly, period='weekly')

    # Calculate cumulated cases per population for each NUTS ID
    covid_calc = transform_cumulated(covid_calc, period='daily')
    covid_calc_weekly = transform_cumulated(covid_calc_weekly, period='weekly')

    # Fill still missing values with a constant for 'no data available'
    covid_calc = transform_fill_no_data(covid_calc, period='daily')
    covid_calc_weekly = transform_fill_no_data(covid_calc_weekly, period='weekly')

    print("\nCalculations done.")

    return covid_calc, covid_calc_weekly


#
# Function to add missing dates for each nuts_id group
# From https://stackoverflow.com/a/62690665
#

def transform_missing_dates(covid_calc):

    print("\nAdd missing dates for each nuts_id group.")

    # Get min and max values for dates in the whole dataset
    date_min = covid_calc['date'].min()
    date_max = covid_calc['date'].max()

    # Fill in missing dates for each group
    covid_calc = (covid_calc.set_index('date')
                  .groupby('nuts_id')
                  .apply(lambda x: x.reindex(pd.date_range(date_min, date_max, freq='D', name='date')))
                  .drop('nuts_id', axis=1)
                  )

    # Reset index
    covid_calc = covid_calc.reset_index()

    print("Done.")

    return covid_calc


#
# Function to fill missing values in 'static' columns
# (first forwards, than backwards)
#

def transform_fill_missing(covid_calc):

    print("\nFill missing values in 'static' columns.")

    # Columns te be filled
    fill = ['country', 'nuts_id', 'nuts_name', 'population']

    # Loop through the columns and fill them
    for fill_col in fill:
        covid_calc[fill_col] = covid_calc.groupby('nuts_id')[fill_col].ffill().bfill()

    print("Done.")

    return covid_calc


#
# Function to interpolate missing values in 'dynamic' columns
# From https://stackoverflow.com/a/58844499
#

def transform_interpolate(covid_calc):

    print("\nInterpolate missing values in 'dynamic' columns.")

    # Columns to be interpolated
    interpolate = ['cases']

    # Loop through columns and interpolate missing values
    for fill_col in interpolate:
        covid_calc[fill_col] = covid_calc.groupby('nuts_id') \
            .apply(lambda x: x[[fill_col]].interpolate(method='linear', limit_area='inside'))

    print("Done.")

    return covid_calc


#
# Function to calculate cases in relation to population for each NUTS ID
#
def transform_calc_pop(covid_calc):

    print("\nCalculate cases in relation to population.")

    # Calculation
    covid_calc['cases_pop'] = covid_calc['cases'] / covid_calc['population'] * 10000

    print("Done.")

    return covid_calc


#
# Function to "fork" weekly aggregates before further calculations
#
def transform_fork_weekly(covid_calc):

    print("\n'Fork' weekly aggregates before further calculations")

    # Group by nuts_id and aggregate by week
    covid_calc_weekly = (covid_calc
                         .groupby(['nuts_id', pd.Grouper(key='date', freq='W-MON'), 'country', 'nuts_name'])[
                             ['cases', 'cases_pop']]
                         .sum()
                         .reset_index()
                         .sort_values('date')
                         )

    # Rename columns in weekly data
    covid_calc_weekly = covid_calc_weekly.rename(columns={'cases': 'cases_w', 'cases_pop': 'cases_pop_w'})

    print("Done.")

    return covid_calc_weekly


#
# Function to Calculate 7-, 14-, and 28-day moving average for each NUTS ID
#
def transform_moving_avg(covid_calc, period='daily'):

    if period == 'daily':

        print("\nCalculate 7/14-day moving average for each NUTS ID.")

        covid_calc['moving7d_pop'] = (covid_calc.groupby('nuts_id')['cases_pop']
                                      .transform(lambda x: x.rolling(7, 1).mean().round(2)))

        covid_calc['moving14d_pop'] = (covid_calc.groupby('nuts_id')['cases_pop']
                                       .transform(lambda x: x.rolling(14, 1).mean().round(2)))

        covid_calc['moving28d_pop'] = (covid_calc.groupby('nuts_id')['cases_pop']
                                       .transform(lambda x: x.rolling(28, 1).mean().round(2)))

        print("Done.")

        return covid_calc

    if period == 'weekly':

        # Calculate 4- and 8-week moving average for aggregated weekly data
        print("\nCalculate 4- and 8-week moving average for each NUTS ID (weekly data).")

        covid_calc['moving4w_pop'] = (covid_calc.groupby('nuts_id')['cases_pop_w']
                                             .transform(lambda x: x.rolling(4, 2).mean().round(2)))
        covid_calc['moving8w_pop'] = (covid_calc.groupby('nuts_id')['cases_pop_w']
                                             .transform(lambda x: x.rolling(8, 4).mean().round(2)))

        print("Done.")

        return covid_calc


#
# Function to calculate cumulated cases per population for each NUTS ID
#
def transform_cumulated(covid_calc, period='daily'):

    print(f"\nCalculate cumulated cases per population for each NUTS ID. ({period} data)")

    if period == 'daily':

        covid_calc['cumulated_pop'] = covid_calc.groupby('nuts_id')['cases_pop'].transform(pd.Series.cumsum)

        # Forward fill cumulated values to the end
        covid_calc['cumulated_pop'] = covid_calc.groupby('nuts_id')['cumulated_pop'].ffill()

        print("Done.")

        return covid_calc

    if period == 'weekly':

        covid_calc['cumulated_pop_w'] = covid_calc.groupby('nuts_id')['cases_pop_w'].transform(
            pd.Series.cumsum)

        # Forward fill cumulated values to the end
        covid_calc['cumulated_pop_w'] = covid_calc.groupby('nuts_id')['cumulated_pop_w'].ffill()

        print("Done.")

        return covid_calc


#
# Function to fill still missing values with a constant for 'no data available'
#
def transform_fill_no_data(covid_calc, period='daily'):

    print(f"\nFill still missing values with a constant for 'no data available' ({period} data)")

    if period == 'daily':

        # Daily data: Define columns to be filled
        no_data = ['cases', 'cases_pop', 'moving7d_pop', 'moving14d_pop', 'moving28d_pop', 'cumulated_pop']

        # Loop through columns and fill them
        for fill_col in no_data:
            covid_calc[fill_col] = covid_calc[fill_col].fillna(value=-1)

        print("Done.")

        return covid_calc

    if period == 'weekly':

        # Weekly data: Define columns to be filled
        no_data = ['cases_w', 'cases_pop_w', 'moving4w_pop', 'moving8w_pop', 'cumulated_pop_w']

        # Loop through columns and fill them
        for fill_col in no_data:
            covid_calc[fill_col] = covid_calc[fill_col].fillna(value=-1)

        print("Done.")

        return covid_calc


#
# Function to export dataframes to CSV file
#
def export_data(covid_calc, filename='covid-waves-data-clean', xls=False):

    print("\nStart export.")

    # Define string to be added to file name if data is limited to certain time frame
    limit = ('_' + str(conf['data_start']) + '_' + str(conf['data_end'])) if conf['limit_dates'] else ''

    # Define file name and export data to CSV
    file = 'data/' + filename + limit + '.csv'
    covid_calc.to_csv(file)
    print("File saved as", file)

    if xls:

        # Define file name and export data to Excel file
        file = 'data/' + filename + limit + '.xlsx'
        with pd.ExcelWriter(file) as writer:
            covid_calc.to_excel(writer, sheet_name='Data')
        print("File saved as", file)
