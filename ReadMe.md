# CovidWaves
_A data visualisation project by Jan Kühn, August 2022_

## What is this about?

After more than two years of living with the pandemic of the new Corona virus Sars-CoV2 one thing we know for sure is that **the virus spreads in waves**. But how do those waves spread across a continent – in this case Europe – that has many countries and even more policies to deal with the threat of this new pathogen? I used data to try to answer that question. The result is an animation of detected Covid19 cases throughout the time period from February 2020 to June 2022.

## About the data

For Covid19 cases, I used data of the (great!) [**COVID19-European-Regional-Tracker**](https://github.com/asjadnaqvi/COVID19-European-Regional-Tracker). It's a project that collected data from many different sources and adapted them to Eurostat's geographic [**NUTS regions**](https://ec.europa.eu/eurostat/web/nuts/background) (the so called "Nomenclature of territorial units for statistics" (NUTS)).

## About the script(s)

After import, the Python script `CovidWaves-update-data.py` cleans the Covid19 data removing some extreme outliers and values below zero (both due to data corrections) and correcting some [erroneous dates](https://github.com/asjadnaqvi/COVID19-European-Regional-Tracker/issues/1) (years 2222 and 2121). It then adds missing dates for each NUTS region and interpolates missing values between known data points. In a last step before the export, different metrics are calculated both for daily data and for weekly aggregated data.

The second script `CovidWaves-animate.py` creates an animation of the data using Plotly Choropleth Mapbox and GeoJson files provided by Eurostat. The script allows to define different characteristics of the animation like time frame, metrics, speed (frames per second), map details etc.

## Use of colors

Defining **colors and break points** for this dataset is rather challenging, because the magnitude of detected cases varies a lot both over time and geographically. For that reason, analyzing the data I chose to use red as the 'medium' color and dark purple as the maxim. The break points are **quantiles** at 20%, 40%, 60%, 80%, 90%, 95%, and 99%. 

That way, during the **first waves** of the pandemic in 2020, maximum numbers are reaching the **red area** while **later on** (especially with much more contagious variants like Omikron) maximums are **dark purple to black**. This allows for differentiation both in the first and in later waves. 