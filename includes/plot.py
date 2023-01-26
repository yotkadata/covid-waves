import datetime as dt

import imageio.v3 as iio
import plotly.graph_objects as go
from PIL import Image
from settings import conf  # Import configuration defined in settings.py


#
# Function to define custom template for Plotly output
#
def custom_template(factor=1):

    custom_template = {
        'layout': go.Layout(
            font={
                'family': 'Lato',
                'size': 12*factor,
                'color': '#1f1f1f',
            },
            title={
                'font': {
                    'family': 'Lato',
                    'size': 24*factor,
                    'color': '#1f1f1f',
                },
            },
        )
    }

    return custom_template


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
            breaks_q[steps[step]] = base * round(df_q[column_q].quantile(steps[step]) / base)
        # Round to twice the base for very high values
        if breaks_q[steps[step]] >= 10 * base:
            breaks_q[steps[step]] = (2 * base) * round(df_q[column_q].quantile(steps[step]) / (2 * base))

        # Normalize to values between 0 and 1 if selected
        if normalized:
            breaks_q[steps[step]] = (breaks_q[steps[step]] / df_q[column_q].max()).round(3)

    return breaks_q


#
# Function to stitch images to get an animation
#
def stitch_animation(file_list, anim_path, animation_format=conf['animation_format'],
                     fps=conf['animation_fps'], loop=conf['animation_loops'],
                     filepath_dt=None, params=None):
    if params is None:
        params = []

    # If global datetime is not set, use current for folder names etc.
    if filepath_dt is None:
        filepath_dt = dt.datetime.now()

    print("\nStarting to stitch images together for an animation.")

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
    anim_path = str(anim_path) + '/' + \
                str(filepath_dt.strftime('%Y%m%d-%H%M%S')) + \
                '-anim' + file_params + \
                '-fps' + str(fps) + \
                '.' + animation_format

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
        img.save(anim_path, save_all=True, append_images=images[1:], duration=fps_to_duration, loop=loop,
                 optimize=False, disposal=2, lossless=True)

    print("Animation saved to", anim_path)
