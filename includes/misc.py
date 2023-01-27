import math

from settings import conf  # Import configuration defined in settings.py


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
