#
# Define some variables for the script
#

conf = {
    'set_dates': False,  # Use date_start and date_end to limit the dataset?
    'date_start': '2022-01-01',  # Start date if 'set_dates' is True
    'date_end': '2022-02-01',  # End date if 'set_dates' is True

    'mode': 'image',  # image, html, or stitch (manual_path)
    'image_format': 'png',  # png or webp
    'resolution': '10M',  # Resolution for the map: 01M, 03M, 10M, 60M
    'metric': 'moving14d_pop',  # Metric to use: see metric_desc
    'metric_desc': {  # Descriptions for the different metrics
        'cases_pop': 'Daily detected cases per million by NUTS region',
        'moving7d_pop': 'Moving 7 day average of detected cases per million by NUTS region',
        'moving14d_pop': 'Moving 14 day average of detected cases per million by NUTS region',
        'cumulated_pop': 'Cumulated detected cases per million by NUTS region',
        'cases_pop_weekly': 'Weekly detected cases per million by NUTS region',
        'moving4w_pop': 'Moving 4 week average of detected weekly cases per million by NUTS region',
    },

    'animation': True,  # Create animation? True or False (just for mode 'image')
    'animation_format': 'webp',  # File format of the animation (gif or webp). gif only works with png.
    'manual_path': '',  # Path for manual
    'animation_fps': 7,  # Frames per second
    'animation_loops': 1,  # Number of loops (0=loop indefinitely)

    'height': 800,  # Height of the images/animation
    'width': 1000,  # Width of the images/animation
    'colorscale': 'dataset',  # Set colorscale based on 'sample' or whole 'dataset'
    'coloraxis': False,  # Show color axis? True or False
    'legend': True,  # Show legend based on calculated break points? True or False

    # white-bg, open-street-map, carto-positron, carto-darkmatter, stamen-terrain, stamen-toner, stamen-watercolor
    'basemap': 'white-bg',
}