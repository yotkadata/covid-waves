import datetime as dt
import json
import pathlib
import time

import imageio.v3 as iio
import pandas as pd
import PIL.Image as Image
import plotly.express as px
import plotly.graph_objects as go

import includes.misc as misc
from settings import conf  # Import configuration defined in settings.py


#
# Function to define custom template for Plotly output
#
def custom_template():

    factor = misc.calc_factor()

    template = {
        'layout': go.Layout(
            font={
                'family': 'Lato',
                'size': 12 * factor,
                'color': '#1f1f1f',
            },
            title={
                'font': {
                    'family': 'Lato',
                    'size': 24 * factor,
                    'color': '#1f1f1f',
                },
            },
        )
    }

    return template


#
# Function to calculate quintiles for the colorscale
#
def calc_quantiles(df_q, column_q, normalized=True, base=5):
    # Steps to be used as break points
    steps = [0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.99, 1]
    breaks_q = {}

    for step in range(len(steps)):
        # Calculate quantiles based on the steps defined above
        breaks_q[steps[step]] = df_q[column_q].quantile(steps[step])

        # Round to next integer for low values (method from https://stackoverflow.com/a/2272174)
        if breaks_q[steps[step]] < (1.5 * base):
            breaks_q[steps[step]] = round(df_q[column_q].quantile(steps[step]))
        # Round to next base for higher values
        if (1.5 * base) <= breaks_q[steps[step]] < (10 * base):
            breaks_q[steps[step]] = base * round(
                df_q[column_q].quantile(steps[step]) / base
            )
        # Round to twice the base for very high values
        if breaks_q[steps[step]] >= 10 * base:
            breaks_q[steps[step]] = (2 * base) * round(
                df_q[column_q].quantile(steps[step]) / (2 * base)
            )

        # Normalize to values between 0 and 1 if selected
        if normalized:
            breaks_q[steps[step]] = (
                breaks_q[steps[step]] / df_q[column_q].max()
            ).round(3)

    return breaks_q


#
# Function to import GeoJson files
#
def import_geojson():

    print("\nImporting geo data.")

    # Get geo data for NUTS regions (level 3)
    file_name = 'data/NUTS_RG_' + conf['resolution'] + '_2016_4326.geojson'
    geo_nuts_level3 = json.load(open(file_name, 'r'))

    # Get geo data for countries
    file_name = 'data/CNTR_RG_' + conf['resolution'] + '_2016_4326.geojson'
    geo_countries = json.load(open(file_name, 'r'))

    print("Done.")

    return geo_nuts_level3, geo_countries


#
# Function to import COVID-19 data from CSV
#
def import_covid_data():

    print("\nStarting import of CSV file.")

    # Define string to be added to fór weekly metrics
    append = (
        '-weekly'
        if conf['metric'] in ['cases_pop_weekly', 'moving4w_pop', 'moving8w_pop']
        else ''
    )

    # Define file name to be imported
    file = 'data/covid-waves-data-clean' + append + '.csv'

    # Import CSV
    df_raw = pd.read_csv(
        file,
        parse_dates=['date'],
        usecols=['country', 'nuts_id', 'nuts_name', 'date', conf['metric']],
        header=0,
    )

    print("File imported:", file)

    df = df_raw.copy()

    # If set, reduce data set to requested time frame
    if conf['set_dates']:
        df = df[(df['date'] >= conf['date_start']) & (df['date'] <= conf['date_end'])]

    return df, df_raw


#
# Function to export maps as images if selected mode is 'image'
#
def plot_images(df, df_raw, filepath_dt):

    # Get GeoJSON data
    geo_nuts_level3, geo_countries = import_geojson()

    # Create folder
    export_path = pathlib.Path(
        'export/image/' + str(filepath_dt.strftime('%Y%m%d-%H%M%S'))
    )
    export_path.mkdir(parents=True, exist_ok=True)

    image_files = []

    # Calculate quintiles for the conf['colorscale'] using whole or reduced dataframe
    df_breaks = df if conf['colorscale'] == 'sample' else df_raw
    breaks = calc_quantiles(df_breaks, conf['metric'], normalized=True)

    # Get resize factor
    factor = misc.calc_factor()

    # Get zoom factor for the map
    zoom = misc.calc_zoom()

    print("\nStart plotting.\n")

    # Get all unique dates and sort them
    dates = df['date'].sort_values().unique()

    # Get min and max dates of the whole dataset
    first_date = df_raw['date'].min()
    last_date = df_raw['date'].max()

    # Create a new dataframe containing just the rows for the first date and sort it
    df_plot = df[df['date'] == dates[0]].sort_values(['nuts_id', 'date'])

    # Start plotting constructing the map used for all images
    fig = go.Figure(
        go.Choroplethmapbox(
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
                [1, conf['colors'][8]],
            ],
        )
    )

    fig.update_layout(
        height=conf['height'],
        width=conf['width'],
        xaxis_autorange=False,
        yaxis_autorange=False,
        mapbox={
            # Set center coordinates of the map
            'center': {
                'lat': 57.245936,
                'lon': 9.274491,
            },
            'style': conf['basemap'],
            'zoom': zoom,
            # Add country borders as thin lines
            'layers': [
                {
                    'name': 'country_borders',
                    'source': geo_countries,
                    'type': 'line',
                    'color': '#ccc',
                    'opacity': 0.3,
                    'line': {'width': factor},
                },
            ],
        },
        margin={'r': 3, 't': 3, 'l': 3, 'b': 3},
        template=custom_template(),
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
        ],
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

        i = 0

        # Create shapes
        for color in conf['colors']:
            # https://plotly.com/python/reference/layout/shapes/
            fig.add_shape(
                go.layout.Shape(
                    type='rect',
                    fillcolor=color,
                    xref='paper',
                    yref='paper',
                    x0=left,
                    y0=top - i * height,
                    x1=left - width,
                    y1=top - (i + 1) * height,
                    line=dict(width=0),
                )
            )
            i += 1

        # Create annotations using not normalized break points
        breaks_legend = calc_quantiles(df_breaks, conf['metric'], normalized=False)

        i = 0

        for step in breaks_legend:
            text = 'No data' if breaks_legend[step] == -1 else breaks_legend[step]

            # https://plotly.com/python/reference/layout/annotations/
            fig.add_annotation(
                dict(
                    xref='paper',
                    yref='paper',
                    yanchor='middle',
                    xanchor='right',
                    x=left - width - 0.005,
                    y=center - i * height,
                    showarrow=False,
                    text=text,
                )
            )
            i += 1

    print("Created basic map for all images.")

    # Set variables to calculate time left
    duration_total = 0
    dates_processed = 0

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
                        'size': 24 * factor,
                    },
                ),
            )

        # Update annotation for all other loop runs
        if date != dates[0]:

            # Calculate date of the day before current date (day one week ago for weekly metrics)
            time_diff = (
                7
                if conf['metric']
                in ['cases_pop_weekly', 'moving4w_pop', 'moving8w_pop']
                else 1
            )
            selector = (pd.to_datetime(date) - dt.timedelta(days=time_diff)).strftime(
                '%d.%m.%Y'
            )

            # Update annotation showing current date
            fig.update_annotations(
                # Select the right annotation to update
                selector={'text': '<b>' + selector + '</b>'},
                text='<b>' + str(date.strftime('%d.%m.%Y')) + '</b>',
                y=date_position,
            )

        # Update colors of the map ('z') with those of the current date
        fig['data'][0]['z'] = df_plot[conf['metric']]

        # Add attribution to the last frame
        if last_run:
            fig.add_annotation(
                dict(
                    font=dict(size=24 * factor),
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
        file = (
            f"{export_path}/{date.strftime('%Y-%m-%d')}-"
            f"{conf['resolution']}-{conf['metric']}-{conf['width']}px.{conf['image_format']}"
        )

        # Write map to image file
        fig.write_image(file, width=conf['width'], height=conf['height'], scale=1)

        # Append image to variable for animation
        image_files.append(file)

        # Count dates processed and duration
        dates_processed += 1
        duration = time.time() - time_start
        duration_total = duration_total + duration
        duration_left = (duration_total / dates_processed) * (
            len(dates) - dates_processed
        )

        print(
            f"Output saved to {file} (duration: {round(duration, 1)} seconds) "
            f"{dates_processed} of {len(dates)} "
            f"({round(dates_processed / len(dates) * 100, 2)}%) "
            f"left: ~{dt.timedelta(seconds=round(duration_left, 0))}"
        )

    print("\nAll images saved.")

    # Create animation
    if conf['animation']:
        stitch_animation(
            image_files,
            filepath_dt=filepath_dt,
            params=[conf['resolution'], conf['metric'], str(conf['width']) + 'px'],
        )

    return dates_processed


#
# Function to prepare list of existing files for animation
#
def animation_prepare_list(searchpath=conf['manual_path']):

    # Define path to look for image files
    image_files = list(pathlib.Path(searchpath).glob('*.*'))

    # Sort files
    image_files.sort()

    return image_files


#
# Function to stitch images to get an animation
#
def stitch_animation(
    file_list,
    animation_format=conf['animation_format'],
    fps=conf['animation_fps'],
    loop=conf['animation_loops'],
    filepath_dt=None,
    params=None,
):

    print("\nStarting to stitch images together for an animation.")

    if params is None:
        params = []

    # If global datetime is not set, use current for folder names etc.
    if filepath_dt is None:
        filepath_dt = dt.datetime.now()

    # Create folder
    anim_path = pathlib.Path('export/animation/')
    anim_path.mkdir(parents=True, exist_ok=True)

    # Force webp format in case images are in webp
    if conf['animation_format'] == 'gif':
        if pathlib.Path(file_list[0]).suffix == '.webp':
            animation_format = 'webp'
            print("NOTICE: Animation format set to webp because images are in webp.")

    # Join parameters to be added to file name
    try:
        iter(params)
        file_params = '-' + '-'.join(params)
    except TypeError:
        print("{} is not iterable".format(params))
        file_params = ''

    # Create path and file name for animation
    anim_path = (
        str(anim_path)
        + '/'
        + str(filepath_dt.strftime('%Y%m%d-%H%M%S'))
        + '-anim'
        + file_params
        + '-fps'
        + str(fps)
        + '.'
        + animation_format
    )

    images = []
    image_count = 0

    if animation_format == 'gif':
        # Loop through image files and add them to 'images'
        for anim_file_name in file_list:
            images.append(iio.imread(anim_file_name))
            image_count += 1

        print("Done. Added", image_count, "images.")

        print("Create animation.")

        # Create animation
        iio.imwrite(anim_path, images, fps=fps, loop=loop)

    if animation_format == 'webp':
        # Loop through image files and add them to 'images'
        for img in file_list:
            images.append(Image.open(img))
            image_count += 1

        # Separate the first image to later append the rest
        img = images[0]

        # Calculate duration based on the frame rate
        fps_to_duration = int(round(1 / fps * 1000, 0))

        # Create animation
        img.save(
            anim_path,
            save_all=True,
            append_images=images[1:],
            duration=fps_to_duration,
            loop=loop,
            optimize=False,
            disposal=2,
            lossless=True,
        )

    print("Animation saved to", anim_path)


#
# Function to create HTML animation (EXPERIMENTAL)
#
def plot_html(df, df_raw):

    print("\nConvert date to string for slider")

    # Convert date to string for the slider
    df['date_str'] = df['date'].apply(lambda x: str(x)[0:10])

    # Calculate quintiles for the colorscale using whole or reduced dataframe
    df_breaks = df if conf['colorscale'] == 'sample' else df_raw
    breaks = calc_quantiles(df_breaks, conf['metric'])

    # Get zoom factor for the map
    zoom = misc.calc_zoom()

    print("\nStart plotting.")

    # Define variable for script statistics
    dates_processed = len(df['date'].unique())

    # Get GeoJSON data
    geo_nuts_level3, geo_countries = import_geojson()

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
            [1, conf['colors'][8]],
        ],
        mapbox_style=conf['basemap'],
        center={'lat': 57.245936, 'lon': 9.274491},
        zoom=zoom,
        template=custom_template(),
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
            )
        ],
    )

    fig.update_traces(
        marker_line_width=0,
    )

    # Define path and file name for export
    file = 'export/html/' + dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '.html'

    # Save output as HTML
    fig.write_html(file)

    print("Output saved to", file)

    return dates_processed
