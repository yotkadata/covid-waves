import datetime as dt
import time
from settings import conf  # Import configuration defined in settings.py
from includes import prepare as prep
from includes import plot


#
# Update data if requested
#

if conf['update_data']:

    # Import data
    covid_raw = prep.import_data()

    # Clean the imported data
    covid_clean = prep.clean_data(covid_raw)

    # Transform the data
    covid_calc, covid_calc_weekly = prep.transform_data(covid_clean)

    # Export data
    prep.export_data(covid_calc, filename='covid-waves-data-clean', xls=False)
    prep.export_data(covid_calc_weekly, filename='covid-waves-data-clean-weekly', xls=True)

#
# Set variables to calculate script running time and other tasks
#

performance = {
    'start': time.time(),  # Start time to calculate script running time
    'dates_processed': 0,  # Create empty variable for calculation
    'duration_total': 0,  # Create empty variable for calculation
}

# Current datetime to be used for folder names etc.
filepath_dt = dt.datetime.now()

# Calculate height in case it is set to 'auto'
if conf['height'] == 'auto':
    conf['height'] = conf['width'] * conf['height_scale']

# Calculate factor for resizing, based on the default width of 1000px or height of 800px
default = 1000 if conf['zoom_adapt'] == 'width' else 800
factor = conf[conf['zoom_adapt']] / default

# Import GeoJson files
if conf['mode'] != 'stitch':
    geo_nuts_level3, geo_countries = plot.import_geojson()

# Import COVID-19 data from CSV
if conf['mode'] != 'stitch':
    df, df_raw = plot.import_covid_data()

# Export maps as images if selected mode is 'image'
if conf['mode'] == 'image':
    plot.plot_images(df, df_raw, filepath_dt, performance, factor)
    # TODO: Better solution for performance, factor

# Create HTML animation if selected mode is HTML
if conf['mode'] == 'html':
    plot.plot_html(df, df_raw, performance, factor)
    # TODO: Better solution for performance, factor

# If selected, create animation from files in manually defined directory
if conf['mode'] == 'stitch':
    # Prepare file list
    image_files = plot.animation_prepare_list()

    # Create animation
    plot.stitch_animation(image_files, filepath_dt=filepath_dt)


#
# Display statistics of script running time
#

# Subtract start time from end time
total_time = time.time() - performance['start']

print(f"\nScript running time: {round(total_time, 2)} seconds ({round(total_time / 60, 2)} minutes)")

if performance['dates_processed']:
    print(f"{performance['dates_processed']} days have been processed. "
          f"That's {round(total_time / performance['dates_processed'], 2)} seconds per day.")
