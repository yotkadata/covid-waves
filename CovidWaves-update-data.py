#
# Import necessary libraries
#

import pandas as pd


##

#
# Define some variables for the script
#

limit_dates = False         # Limit the dates to be included? True/False
date_start = '2020-11-01'   # Start date in case of True
date_end = '2020-11-30'     # End date in case of True

refresh_source = False      # Download data to refresh? True/False

##

#
# Get Covid19 data
#

print("Get Covid19 data.")

# COVID19-European-Regional-Tracker
# https://github.com/asjadnaqvi/COVID19-European-Regional-Tracker

if refresh_source:

    import requests

    remote_url = 'https://raw.githubusercontent.com/asjadnaqvi/COVID19-European-Regional-Tracker/master/04_master' \
                 '/csv_nuts/EUROPE_COVID19_master.csv '
    local_file = 'data/european-regional-tracker.csv'

    # Make http request for remote file data
    data = requests.get(remote_url)

    # Save file data to local copy
    with open(local_file, 'wb') as file:
        file.write(data.content)


# Import CSV with Covid19 data
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

##

#
# If selected above, reduce the dataset to selected time frame
#

if limit_dates:
    covid_raw = covid_raw[(covid_raw['date'] >= date_start) & (covid_raw['date'] <= date_end)]

##

#
# Do some cleaning
#

print("\nDo some cleaning.")

# Make a copy of the dataframe
covid_clean = covid_raw.copy()

##

# Remove rows with negative values
print("\nRemove rows with negative values.")

length_before = len(covid_clean)
covid_clean = covid_clean[covid_clean['cases'] >= 0]
length_after = len(covid_clean)

print(f"\nRemoved {length_before - length_after} rows with values below 0."
      f"\n{length_after} rows left.")

##

# Correct some dates from the years 2121 and 2222
# https://stackoverflow.com/a/50674062/381821

print("\nCorrect some dates.")

# Define years to be corrected
error_years = {2121: 2021, 2222: 2022}

# Loop through years to be corrected
for y in error_years:
    covid_clean['date'] = (covid_clean['date']
                           .apply(lambda x: x.replace(year=x.year - (y - error_years[y])) if x.year == y else x))

print("Done.")

##

# Remove outliers in each NUTS id group as there are many because of data corrections

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

##

# Sort dataframe
covid_clean = covid_clean.sort_values(['nuts_id', 'date'])

print("\nCleaning done.")

##

#
# Do some calculations
#

print("\nDo some calculations.")

# Make a copy of the dataframe
covid_calc = covid_clean.copy()

# Add missing dates for each nuts_id group
# From https://stackoverflow.com/a/62690665

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


# Fill missing values in 'static' columns (first forwards, than backwards)

print("\nFill missing values in 'static' columns.")

# Columns te be filled
fill = ['country', 'nuts_id', 'nuts_name', 'population']

# Loop through the columns and fill them
for fill_col in fill:
    covid_calc[fill_col] = covid_calc.groupby('nuts_id')[fill_col].ffill().bfill()

print("Done.")


# Interpolate missing values in 'dynamic' columns
# From https://stackoverflow.com/a/58844499

print("\nInterpolate missing values in 'dynamic' columns.")

# Columns to be interpolated
interpolate = ['cases']

# Loop through columns and interpolate missing values
for fill_col in interpolate:
    covid_calc[fill_col] = covid_calc.groupby('nuts_id')\
        .apply(lambda x: x[[fill_col]].interpolate(method='linear', limit_area='inside'))

print("Done.")


# Calculate cases in relation to population for each NUTS ID

print("\nCalculate cases in relation to population.")

# Calculation
covid_calc['cases_pop'] = covid_calc['cases'] / covid_calc['population'] * 10000

print("Done.")


# "Fork" weekly aggregates before further calculations
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


# Calculate 7 and 14 day rolling average for each NUTS ID

print("\nCalculate 7/14 day rolling average for each NUTS ID.")

covid_calc['moving7d_pop'] = (covid_calc.groupby('nuts_id')['cases_pop']
                              .transform(lambda x: x.rolling(7, 1).mean().round(2)))

covid_calc['moving14d_pop'] = (covid_calc.groupby('nuts_id')['cases_pop']
                               .transform(lambda x: x.rolling(14, 1).mean().round(2)))

print("Done.")


# Calculate 4 week rolling average for aggregated weekly data

print("\nCalculate 4 week rolling average for each NUTS ID (weekly data).")

covid_calc_weekly['moving4w_pop'] = (covid_calc_weekly.groupby('nuts_id')['cases_pop_w']
                                     .transform(lambda x: x.rolling(4, 1).mean().round(2)))

print("Done.")


# Calculate cumulated cases per population for each NUTS ID

print("\nCalculate cumulated cases per population for each NUTS ID.")

covid_calc['cumulated_pop'] = covid_calc.groupby('nuts_id')['cases_pop'].transform(pd.Series.cumsum)
covid_calc_weekly['cumulated_pop_w'] = covid_calc_weekly.groupby('nuts_id')['cases_pop_w'].transform(pd.Series.cumsum)

print("Done.")


# Fill still missing values with a constant for 'no data available'

print("\nFill still missing values with a constant for 'no data available'")

# Daily data: Define columns to be filled
no_data = ['cases', 'cases_pop', 'moving7d_pop', 'moving14d_pop', 'cumulated_pop']

# Loop through columns and fill them
for fill_col in no_data:
    covid_calc[fill_col] = covid_calc[fill_col].fillna(value=-1)

# Weekly data: Define columns to be filled
no_data = ['cases_w', 'cases_pop_w', 'moving4w_pop', 'cumulated_pop_w']

# Loop through columns and fill them
for fill_col in no_data:
    covid_calc_weekly[fill_col] = covid_calc_weekly[fill_col].fillna(value=-1)

print("Done.")

print("\nCalculations done.")

##

#
# Export dataframe to CSV file
#

print("\nStart export.")

# Define string to be added to file name if data is limited to certain time frame
limit = ('_' + str(date_start) + '_' + str(date_end)) if limit_dates else ''

# Define file name and export daily data to CSV
file = 'data/covid-waves-data-clean' + limit + '.csv'
covid_calc.to_csv(file)
print("File saved as", file)

# Define file name and export weekly data to CSV
file = 'data/covid-waves-data-clean-weekly' + limit + '.csv'
covid_calc_weekly.to_csv(file)
print("File saved as", file)

# Define file name and export weekly data to Excel file
file = 'data/covid-waves-data-clean-weekly' + limit + '.xlsx'
with pd.ExcelWriter(file) as writer:
    covid_calc_weekly.to_excel(writer, sheet_name='Data')
print("File saved as", file)
