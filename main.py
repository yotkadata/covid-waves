import plotly.express as px
import datetime as dt
import pathlib
import time
import math
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

# Calculate the zoom factor
# Mapbox zoom is based on a log scale where zoom = 3 is ideal for our map at 1000px.
# So factor = 2 ^ (zoom - 3) and zoom = log(factor) / log(2) + 3
zoom = math.log(factor) / math.log(2) + 3

# Import GeoJson files
if conf['mode'] != 'stitch':
    geo_nuts_level3, geo_countries = plot.import_geojson()

# Import COVID-19 data from CSV
if conf['mode'] != 'stitch':
    df, df_raw = plot.import_covid_data()

# Export maps as images if selected mode is 'image'
if conf['mode'] == 'image':
    plot.plot_images(df, df_raw, filepath_dt, performance, zoom, factor)
    # TODO: Better solution for performance, zoom, factor


#
# Create HTML animation if selected mode is HTML
#

if conf['mode'] == 'html':
    print("\nConvert date to string for slider")

    # Convert date to string for the slider
    df['date_str'] = df['date'].apply(lambda x: str(x)[0:10])

    # Calculate quintiles for the colorscale using whole or reduced dataframe
    df_breaks = df if conf['colorscale'] == 'sample' else df_raw
    breaks = plot.calc_quantiles(df_breaks, conf['metric'])

    print("\nStart plotting.")

    # Define variable for script statistics
    performance['dates_processed'] = len(df['date'].unique())

    # Get min and max dates of the whole dataset
    first_date = df_raw['date'].min()
    last_date = df_raw['date'].max()

    # Start plotting
    fig = px.choropleth_mapbox(
        df,
        locations='nuts_id',
        geojson=geo_nuts_level3,
        color=conf['metric'],
        range_color=[0, df_breaks[conf['metric']].max()],
        color_continuous_scale=[
            [0, conf['colors'][0]],
            [breaks[0.2], conf['colors'][1]],
            [breaks[0.4], conf['colors'][2]],
            [breaks[0.6], conf['colors'][3]],
            [breaks[0.8], conf['colors'][4]],
            [breaks[0.9], conf['colors'][5]],
            [breaks[0.95], conf['colors'][6]],
            [breaks[0.99], conf['colors'][7]],
            [1, conf['colors'][8]]
        ],
        mapbox_style=conf['basemap'],
        center={'lat': 57.245936, 'lon': 9.274491},
        zoom=zoom,
        template=plot.custom_template(factor),
        animation_frame='date_str',
        animation_group='nuts_id',
        width=conf['width'],
        height=conf['height'],
    )

    fig.update_layout(
        title_text='<b>COVID-19 waves in Europe</b><br />'
                   '<sup>' + conf['metric_desc'][conf['metric']] + '</sup>',
        title_x=0.01,
        title_y=0.96,
        margin={'r': 0, 't': 0, 'l': 0, 'b': 0},
        coloraxis_showscale=False,
        coloraxis_colorbar=dict(title=''),
        annotations=[
            dict(
                xref='paper',
                yref='paper',
                x=0.01,
                y=0,
                showarrow=False,
                text='<b>Data:</b> COVID19-European-Regional-Tracker/Eurostat, '
                     '<b>Graph:</b> Jan Kühn (https://yotka.org), '
                     '<b>License:</b> CC by-nc-sa 4.0',
            )]
    )

    fig.update_traces(
        marker_line_width=0,
    )

    # Define path and file name for export
    file = 'export/html/' + dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '.html'

    # Save output as HTML
    fig.write_html(file)

    print("Output saved to", file)

##

#
# If selected, create animation from files in manually defined directory
#

if conf['mode'] == 'stitch':
    # Create folder
    export_path = pathlib.Path('export/animation/')
    export_path.mkdir(parents=True, exist_ok=True)

    # Define path to look for image files
    search_path = conf['manual_path'] + '/*'
    image_files = list(pathlib.Path(conf['manual_path']).glob('*.*'))

    # Sort files
    image_files.sort()

    # Create animation
    plot.stitch_animation(image_files, export_path, filepath_dt=filepath_dt)

##

#
# Display statistics of script running time
#

# Subtract start time from end time
total_time = time.time() - performance['start']

print(f"\nScript running time: {round(total_time, 2)} seconds ({round(total_time / 60, 2)} minutes)")

if performance['dates_processed']:
    print(f"{performance['dates_processed']} days have been processed. "
          f"That's {round(total_time / performance['dates_processed'], 2)} seconds per day.")
