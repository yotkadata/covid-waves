import datetime as dt
import math
import time

from settings import conf  # Import configuration defined in settings.py


#
# Function to get configuration defaults
#
def conf_defaults():

    # Calculate height in case it is set to 'auto'
    if conf['height'] == 'auto':
        conf['height'] = conf['width'] * conf['height_scale']

    return conf


#
# Function to set performance values
#
def conf_performance(conf):

    # Set variables to calculate script running time and other tasks
    conf['start_time'] = time.time()  # Start time to calculate script running time
    conf['dates_processed'] = 0  # Create empty variable for calculation

    # Current datetime to be used for folder names etc.
    conf['filepath_dt'] = dt.datetime.now()

    return conf


#
# Function to calculate factor for resizing
# Based on the default width of 1000px or height of 800px
#
def calc_factor():

    # Set default depending on setting
    default = 1000 if conf['zoom_adapt'] == 'width' else 800

    # Calculate factor
    factor = conf[conf['zoom_adapt']] / default

    return factor


#
# Calculate zoom factor for the map
#
def calc_zoom():

    # Get factor
    factor = calc_factor()

    # Mapbox zoom is based on a log scale where zoom = 3 is ideal for our map at 1000px.
    # So factor = 2 ^ (zoom - 3) and zoom = log(factor) / log(2) + 3
    zoom = math.log(factor) / math.log(2) + 3

    return zoom
