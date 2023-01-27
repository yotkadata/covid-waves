import includes.prepare as prep
import includes.plot as plot
import includes.misc as misc


def main():
    # Get configuration information
    conf = misc.conf_defaults()

    # Update data if requested
    if conf['update_data']:

        # Import data
        covid_raw = prep.import_data()

        # Clean the imported data
        covid_clean = prep.clean_data(covid_raw)

        # Transform the data
        covid_calc, covid_calc_weekly = prep.transform_data(covid_clean)

        # Export data
        prep.export_data(covid_calc)
        prep.export_data(covid_calc_weekly, filename_suffix='-weekly', xls=True)

    # Start performance measures
    conf = misc.conf_performance(conf)

    # Import data if mode is 'image' or 'html'
    if conf['mode'] in ['image', 'html']:

        # Import COVID-19 data from CSV
        df, df_raw = plot.import_covid_data()

        # Export maps as images if selected mode is 'image'
        if conf['mode'] == 'image':
            conf['dates_processed'] = plot.plot_images(df, df_raw, conf['filepath_dt'])

        # Create HTML animation if selected mode is HTML
        if conf['mode'] == 'html':
            conf['dates_processed'] = plot.plot_html(df, df_raw)

    # If selected, create animation from files in manually defined directory
    if conf['mode'] == 'stitch':

        # Prepare file list
        image_files = plot.animation_prepare_list()

        # Create animation
        plot.stitch_animation(image_files, filepath_dt=conf['filepath_dt'])

    # Display statistics of script running time
    misc.performance_show()


if __name__ == "__main__":

    main()
