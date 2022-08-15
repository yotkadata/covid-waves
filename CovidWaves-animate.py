import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
import json
import imageio
import pathlib
import glob
import time

#
# Define some variables for the script
#

set_dates = False  # Use date_start and date_end to limit the dataset?
date_start = '2022-01-01'  # Start date if 'set_dates' is True
date_end = '2022-05-01'  # End date if 'set_dates' is True

mode = 'png'  # html, png or stitch (manual_path)
resolution = '10M'  # Resolution for the map: 01M, 03M, 10M, 60M
metric = 'moving14d_pop'  # Metric to use: moving7d_pop, moving14d_pop, cumulated_pop, cases_pop_weekly, moving4w_pop
metric_desc = {  # Descriptions for the different metrics
    'moving7d_pop': 'Moving 7 day average of detected cases per million by NUTS region',
    'moving14d_pop': 'Moving 14 day average of detected cases per million by NUTS region',
    'cumulated_pop': 'Cumulated detected cases per million by NUTS region',
    'cases_pop_weekly': 'Weekly detected cases per million by NUTS region',
    'moving4w_pop': 'Moving 4 week average of detected weekly cases per million by NUTS region',
}

animation = True  # Create animation? True or False (just for mode 'png')
manual_path = '/home/jan/DataViz/Projekte/CovidWaves/export/png/20220814-143236/'  # Path for manual
animation_fps = 14  # Frames per second
animation_loops = 1  # Number of loops (0=loop indefinitely)

height = 800  # Height of the images/animation
width = 1000  # Width of the images/animation
colorscale = 'dataset'  # Set colorscale based on 'sample' or whole 'dataset'
coloraxis = False  # Show color axis? True or False

# white-bg, open-street-map, carto-positron, carto-darkmatter, stamen-terrain, stamen-toner, stamen-watercolor
basemap = 'white-bg'

##

# Set variables to calculate script running time
start = time.time()  # Start time to calculate script running time
dates_processed = 0  # Create empty list for calculation


#
# Define functions
#

# Calculate quintiles for the colorscale
def calc_quintiles(df, column):
    # Steps to be used as break points
    steps = [0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.99, 1]
    breaks = {}

    for step in range(len(steps)):
        breaks[steps[step]] = (df[column].quantile(steps[step]) / df[column].max()).round(3)

    return breaks


# Stitch images to get an animation
def stitch_animation(image_files, path, params='', fps=animation_fps):
    print("Starting to stitch images together for an animation.")

    images = []
    image_count = 0

    # Loop through image files and add them to 'images'
    for file_name in image_files:
        images.append(imageio.v2.imread(file_name))
        image_count += 1

    print("Done. Added", image_count, "images.")

    print("Create animation.")

    # Join parameters to be added to file name
    try:
        iter(params)
        file_params = '-' + '-'.join(params)
    except TypeError:
        print("{} is not iterable".format(params))
        file_params = ''

    # Create path and file name for animation
    gif_path = str(path) + '/animation' + file_params + '-fps' + str(fps) + '.gif'

    # Create animation
    imageio.mimsave(gif_path, images, fps=fps, loop=animation_loops)

    print("Animation saved to", gif_path)


##

#
# Define custom template for Plotly output
#

custom_template = {
    'layout': go.Layout(
        font={
            'family': 'Lato',
            'size': 12,
            'color': '#1f1f1f',
        },
        title={
            'font': {
                'family': 'Lato',
                'size': 24,
                'color': '#1f1f1f',
            },
        },
    )
}

##

#
# Import GeoJson files
#

print("\nImporting geo data.")

# Get geo data for NUTS regions (level 3)
file_name = 'data/NUTS_RG_' + resolution + '_2016_4326.geojson'
geo_nuts_level3 = json.load(open(file_name, 'r'))

# Get geo data for countries
file_name = 'data/CNTR_RG_' + resolution + '_2016_4326.geojson'
geo_countries = json.load(open(file_name, 'r'))

print("Done.")

##

#
# Import Covid19 data from CSV
#

print("\nStarting import of CSV file.")

# Define string to be added to fór weekly metrics
append = '-weekly' if metric in ['cases_pop_weekly', 'moving4w_pop'] else ''

# Define file name to be imported
file = 'data/covid-waves-data-clean' + append + '.csv'

# Import CSV
df_raw = pd.read_csv(file,
                     parse_dates=['date'],
                     usecols=['country', 'nuts_id', 'nuts_name', 'date', metric],
                     header=0,
                     )

print("File imported:", file)

# Create a copy of the dataframe to work with
df = df_raw.copy()

##

#
# If set, reduce data set to requested time frame
#

if set_dates:
    df = df[(df['date'] >= date_start) & (df['date'] <= date_end)]

##

#
# Export maps as PNGs if selected mode is PNG
#

if mode == 'png':

    # Create folder
    path = 'export/png/' + str(dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
    export_path = pathlib.Path(path)
    export_path.mkdir(parents=True, exist_ok=True)

    image_files = []

    # Calculate quintiles for the colorscale using whole or reduced dataframe
    df_breaks = df if colorscale == 'sample' else df_raw
    breaks = calc_quintiles(df_breaks, metric)

    print("\nStart plotting.")

    # Get all unique dates and sort them
    dates = df['date'].sort_values().unique()

    # Get min and max dates of the whole dataset
    first_date = df_raw['date'].min()
    last_date = df_raw['date'].max()

    for date in dates:

        # Set variable to track performance
        duration_start = time.time()

        # Convert date to Pandas datetime
        date = pd.to_datetime(date)

        # Check if this is the last iteration
        last_run = True if (len(dates) > 1 and date == dates.max()) else False

        # Create a new dataframe containing just the rows for the current date
        df_plot = df[df['date'] == date]

        # Calculate position of the date
        total_seconds = (last_date - first_date).total_seconds()
        now_seconds = (date - first_date).total_seconds()
        date_position = 1 - (now_seconds / total_seconds)

        # Start plotting
        fig = go.Figure(go.Choroplethmapbox(
            geojson=geo_nuts_level3,
            locations=df_plot['nuts_id'],
            z=df_plot[metric],
            zmin=0,
            zmax=df_breaks[metric].max(),
            colorscale=[
                [0, '#ccc'],
                [breaks[0.2], '#FFF304'],  # Cadmium Yellow
                [breaks[0.4], '#FFAC00'],  # Chrome Yellow
                [breaks[0.6], '#FF4654'],  # Sunburnt Cyclops
                [breaks[0.8], '#E71827'],  # Pigment Red
                [breaks[0.9], '#C064E0'],
                [breaks[0.95], '#9C51B6'],  # Purple Plum
                [breaks[0.99], '#733381'],  # Maximum Purple
                [1, '#000000']
            ],
        ))

        fig.update_layout(
            autosize=False,
            height=height,
            width=width,
            mapbox={
                'center': {'lat': 57.245936, 'lon': 9.274491},  # Set center coordinates of the map
                'style': basemap,
                'zoom': 3,
                'layers': [
                    {
                        'name': 'country_borders',  # Add country borders as thin lines
                        'source': geo_countries,
                        'type': 'line',
                        'color': '#ccc',
                        'opacity': 0.3,
                        'line': {'width': 1}
                    },
                ],
            },
            margin={'r': 3, 't': 3, 'l': 3, 'b': 3},
            template=custom_template,
            title_text='<b>COVID19 waves in Europe</b><br />'
                       '<sup>' + metric_desc[metric] + '</sup>',
            title_x=0.01,
            title_y=0.96,
            coloraxis_colorbar=dict(title=''),
            annotations=[
                dict(
                    xref='paper',
                    yref='paper',
                    x=0.01,
                    y=0,
                    showarrow=False,
                    text='<b>Data:</b> COVID19-European-Regional-Tracker, <b>Graph:</b> Jan Kühn',
                ),
                dict(
                    xref='paper',
                    yref='paper',
                    x=0.99,
                    y=date_position,
                    showarrow=False,
                    text='<b>' + str(date.strftime('%d.%m.%Y')) + '</b>',
                    font={
                        'size': 24,
                    },
                ),
            ]
        )

        # Add attribution to the last frame
        if last_run:
            fig.add_annotation(
                dict(
                    font=dict(
                        size=24,
                    ),
                    x=0.01,
                    y=0.5,
                    showarrow=False,
                    text='<b>By Jan Kühn</b><br /><sup>https://yotka.org | @derjaku</sup>',
                    xanchor='left',
                    xref='paper',
                    yref='paper',
                    align='left',
                )
            )

        fig.update_traces(
            marker_line_width=0,  # Width of the NUTS borders
            showscale=coloraxis,
        )

        # Define file path and name
        file = str(export_path) + '/' + \
               date.strftime('%Y-%m-%d') + '-' + \
               resolution + '-' + \
               metric + \
               '.png'

        # Write map to PNG file
        fig.write_image(file, width=width, height=height)

        # Append image to variable for animation
        image_files.append(file)

        # Count dates processed and duration
        dates_processed += 1
        duration_end = time.time()

        print("Output saved to", file,
              "(duration:", str(round(duration_end - duration_start, 1)), "seconds)",
              dates_processed, "of", len(dates), "(", round(dates_processed / len(dates) * 100, 2), "% )")

    print("All images saved.")

##

#
# Create HTML animation if selected mode is HTML
#

if mode == 'html':
    print("\nConvert date to string for slider")

    # Convert date to string for the slider
    df['date_str'] = df['date'].apply(lambda x: str(x)[0:10])

    # Calculate quintiles for the colorscale using whole or reduced dataframe
    df_breaks = df if colorscale == 'sample' else df_raw
    breaks = calc_quintiles(df_breaks, metric)

    print("\nStart plotting.")

    # Define variable for script statistics
    dates_processed = len(df['date'].unique())

    # Get min and max dates of the whole dataset
    first_date = df_raw['date'].min()
    last_date = df_raw['date'].max()

    # Start plotting
    fig = px.choropleth_mapbox(
        df,
        locations='nuts_id',
        geojson=geo_nuts_level3,
        color=metric,
        range_color=[0, df_breaks[metric].max()],
        color_continuous_scale=[
            [0, '#ccc'],
            [breaks[0.2], '#FFF304'],  # Cadmium Yellow
            [breaks[0.4], '#FFAC00'],  # Chrome Yellow
            [breaks[0.6], '#FF4654'],  # Sunburnt Cyclops
            [breaks[0.8], '#E71827'],  # Pigment Red
            [breaks[0.9], '#C064E0'],
            [breaks[0.95], '#9C51B6'],  # Purple Plum
            [breaks[0.99], '#733381'],  # Maximum Purple
            [1, '#000000']
        ],
        mapbox_style=basemap,
        center={'lat': 57.245936, 'lon': 9.274491},
        zoom=3,
        template=custom_template,
        animation_frame='date_str',
        animation_group='nuts_id',
        width=width,
        height=height,
    )

    fig.update_layout(
        title_text='<b>COVID19 waves in Europe</b><br />'
                   '<sup>' + metric_desc[metric] + '</sup>',
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
                text='<b>Data:</b> COVID19-European-Regional-Tracker, <b>Graph:</b> Jan Kühn',
            ),
        ]
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
# Create GIF file with animation
#

if animation and mode == 'png':
    stitch_animation(image_files, export_path, params=[resolution, metric])

##

#
# If selected, create animation from files in manually defined directory
#

if mode == 'stitch':
    # Create folder
    path = 'export/png/' + str(dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
    export_path = pathlib.Path(path)
    export_path.mkdir(parents=True, exist_ok=True)

    # Define path to look for PNG files
    search_path = manual_path + '/*.png'
    image_files = glob.glob(search_path)

    # Sort files
    image_files.sort()

    # Create animation
    stitch_animation(image_files, path)

##

#
# Display statistics of script running time
#

# Grab currrent Ttime after running the script
end = time.time()

# Subtract start time from end time
total_time = end - start

print("Script running time: " + str(round(total_time, 2)) + " seconds (" + str(
    round(total_time / 60, 2)) + " minutes)")

if dates_processed:
    print(dates_processed, "days have been processed. That's", round(total_time / dates_processed, 2),
          "seconds per day.")