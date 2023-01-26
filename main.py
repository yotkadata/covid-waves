import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
import json
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


#
# Import GeoJson files
#

if conf['mode'] != 'stitch':
    print("\nImporting geo data.")

    # Get geo data for NUTS regions (level 3)
    file_name = 'data/NUTS_RG_' + conf['resolution'] + '_2016_4326.geojson'
    geo_nuts_level3 = json.load(open(file_name, 'r'))

    # Get geo data for countries
    file_name = 'data/CNTR_RG_' + conf['resolution'] + '_2016_4326.geojson'
    geo_countries = json.load(open(file_name, 'r'))

    print("Done.")

##

#
# Import COVID-19 data from CSV
#

if conf['mode'] != 'stitch':
    print("\nStarting import of CSV file.")

    # Define string to be added to fór weekly metrics
    append = '-weekly' if conf['metric'] in ['cases_pop_weekly', 'moving4w_pop', 'moving8w_pop'] else ''

    # Define file name to be imported
    file = 'data/covid-waves-data-clean' + append + '.csv'

    # Import CSV
    df_raw = pd.read_csv(file,
                         parse_dates=['date'],
                         usecols=['country', 'nuts_id', 'nuts_name', 'date', conf['metric']],
                         header=0,
                         )

    print("File imported:", file)

    # Create a copy of the dataframe to work with
    df = df_raw.copy()

##

#
# If set, reduce data set to requested time frame
#

if conf['mode'] != 'stitch' and conf['set_dates']:
    df = df[(df['date'] >= conf['date_start']) & (df['date'] <= conf['date_end'])]

##

#
# Export maps as images if selected mode is 'image'
#

if conf['mode'] == 'image':

    # Create folder
    export_path = pathlib.Path('export/image/' + str(filepath_dt.strftime('%Y%m%d-%H%M%S')))
    export_path.mkdir(parents=True, exist_ok=True)

    image_files = []

    # Calculate quintiles for the conf['colorscale'] using whole or reduced dataframe
    df_breaks = df if conf['colorscale'] == 'sample' else df_raw
    breaks = plot.calc_quantiles(df_breaks, conf['metric'], normalized=True)

    print("\nStart plotting.\n")

    # Get all unique dates and sort them
    dates = df['date'].sort_values().unique()

    # Get min and max dates of the whole dataset
    first_date = df_raw['date'].min()
    last_date = df_raw['date'].max()

    # Create a new dataframe containing just the rows for the first date and sort it
    df_plot = df[df['date'] == dates[0]].sort_values(['nuts_id', 'date'])

##
    # Start plotting constructing the map used for all images
    fig = go.Figure(go.Choroplethmapbox(
        geojson=geo_nuts_level3,
        locations=df_plot['nuts_id'],
        z=df_plot[conf['metric']],
        zmin=0,
        zmax=df_breaks[conf['metric']].max(),
        colorscale=[
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
    ))

    fig.update_layout(
        height=conf['height'],
        width=conf['width'],
        xaxis_autorange=False,
        yaxis_autorange=False,
        mapbox={
            'center': {'lat': 57.245936, 'lon': 9.274491},  # Set center coordinates of the map
            'style': conf['basemap'],
            'zoom': zoom,
            'layers': [
                {
                    'name': 'country_borders',  # Add country borders as thin lines
                    'source': geo_countries,
                    'type': 'line',
                    'color': '#ccc',
                    'opacity': 0.3,
                    'line': {'width': 1 * factor}
                },
            ],
        },
        margin={'r': 3, 't': 3, 'l': 3, 'b': 3},
        template=plot.custom_template(factor),
        title_text='<b>COVID-19 waves in Europe</b><br />'
                   '<sup>' + conf['metric_desc'][conf['metric']] + '</sup>',
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
                text='<b>Data:</b> COVID19-European-Regional-Tracker/Eurostat, '
                     '<b>Graph:</b> Jan Kühn (https://yotka.org), '
                     '<b>License:</b> CC by-nc-sa 4.0',
            ),
        ]
    )

    fig.update_traces(
        marker_line_width=0,  # Width of the NUTS borders
        showscale=conf['coloraxis'],
    )

    # Add legend
    if conf['legend']:
        # Define position and size of the legend
        top = 0.99  # 0 = bottom / 1 = top
        left = 0.99  # 0 = left / 1 = right
        width = 0.01
        height = 0.04
        center = top - height / 2

        shapes = []
        i = 0

        # Create shapes
        for color in conf['colors']:
            # https://plotly.com/python/reference/layout/shapes/
            fig.add_shape(go.layout.Shape(
                type='rect',
                fillcolor=color,
                xref='paper',
                yref='paper',
                x0=left,
                y0=top - i * height,
                x1=left - width,
                y1=top - (i + 1) * height,
                line=dict(width=0),
            ))
            i += 1

        # Create annotations using not normalized break points
        breaks_legend = plot.calc_quantiles(df_breaks, conf['metric'], normalized=False)

        annotations = []
        i = 0

        for step in breaks_legend:
            text = 'No data' if breaks_legend[step] == -1 else breaks_legend[step]

            # https://plotly.com/python/reference/layout/annotations/
            fig.add_annotation(dict(
                xref='paper',
                yref='paper',
                yanchor='middle',
                xanchor='right',
                x=left - width - 0.005,
                y=center - i * height,
                showarrow=False,
                text=text,
            ))
            i += 1

    print("Created basic map for all images.")

    # Update the map for all dates and export the image
    for date in dates:

        # Set variable to track performance
        time_start = time.time()

        # Convert date to Pandas datetime
        date = pd.to_datetime(date)

        # Check if this is the last iteration
        last_run = True if (len(dates) > 1 and date == dates.max()) else False

        # Create a new dataframe containing just the rows for the current date and sort it as above
        # It is important to sort the same way as above to make sure the numbers match to the right NUTS
        df_plot = df[df['date'] == date].sort_values(['nuts_id', 'date'])

        # Calculate position of the date
        total_seconds = (last_date - first_date).total_seconds()
        now_seconds = (date - first_date).total_seconds()
        date_position = 0.9 * (1 - now_seconds / total_seconds * 0.9)

        # Add annotation with the current date in the first run of the loop
        if date == dates[0]:
            fig.add_annotation(
                dict(
                    xref='paper',
                    yref='paper',
                    yanchor='top',
                    xanchor='left',
                    x=0.01,
                    y=date_position,
                    showarrow=False,
                    text='<b>' + str(date.strftime('%d.%m.%Y')) + '</b>',
                    font={
                        'size': 24*factor,
                    },
                ),
            )

        # Update annotation for all other loop runs
        if date != dates[0]:

            # Calculate date of the day before current date (day one week ago for weekly metrics)
            time_diff = 7 if conf['metric'] in ['cases_pop_weekly', 'moving4w_pop', 'moving8w_pop'] else 1
            selector = (pd.to_datetime(date) - dt.timedelta(days=time_diff)).strftime('%d.%m.%Y')

            # Update annotation showing current date
            fig.update_annotations(
                selector={'text': '<b>' + selector + '</b>'},  # Select the right annotation to update
                text='<b>' + str(date.strftime('%d.%m.%Y')) + '</b>',
                y=date_position,
            )

        # Update colors of the map ('z') with those of the current date
        fig['data'][0]['z'] = df_plot[conf['metric']]

        # Add attribution to the last frame
        if last_run:
            fig.add_annotation(
                dict(
                    font=dict(
                        size=24*factor,
                    ),
                    x=0.99,
                    y=0.01,
                    showarrow=False,
                    text='<b>By Jan Kühn</b><br /><sup>https://yotka.org</sup>',
                    xanchor='right',
                    yanchor='bottom',
                    xref='paper',
                    yref='paper',
                    align='right',
                )
            )

        # Define file path and name
        file = str(export_path) + '/' + \
               date.strftime('%Y-%m-%d') + '-' + \
               conf['resolution'] + '-' + \
               conf['metric'] + '-' + \
               str(conf['width']) + 'px' + \
               '.' + conf['image_format']

        # Write map to image file
        fig.write_image(file, width=conf['width'], height=conf['height'], scale=1)

        # Append image to variable for animation
        image_files.append(file)

        # Count dates processed and duration
        performance['dates_processed'] += 1
        duration = time.time() - time_start
        performance['duration_total'] = performance['duration_total'] + duration
        duration_left = ((performance['duration_total'] / performance['dates_processed']) * (len(dates) - performance['dates_processed']))

        print(f"Output saved to {file} (duration: {round(duration, 1)} seconds) "
              f"{performance['dates_processed']} of {len(dates)} ({round(performance['dates_processed'] / len(dates) * 100, 2)}%) "
              f"left: ~{dt.timedelta(seconds=round(duration_left, 0))}")

    print("\nAll images saved.")

    #
    # Create animation
    #

    if conf['animation']:
        # Create folder
        export_path = pathlib.Path('export/animation/')
        export_path.mkdir(parents=True, exist_ok=True)

        plot.stitch_animation(image_files, export_path, filepath_dt=filepath_dt,
                         params=[conf['resolution'], conf['metric'], str(conf['width']) + 'px'])

##

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
