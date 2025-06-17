# Clinical Trials Search App

This is a Flask-based web application that allows users to search for clinical trials using specified terms, date ranges, and view the results on an interactive map. The app is designed to be deployed as a serverless function on **Netlify**, leveraging the `serverless-wsgi` package.
Link https://trialsfinder.onrender.com/
![Alt text](https://github.com/shivarajmishra/Trialsfinder/blob/main/Trialsfinder.png)
## Features

- **Search Clinical Trials**: Users can enter search terms, select date ranges, and filter clinical trials based on their chosen criteria.
- **Map Visualization**: Displays the distribution of clinical trials across countries using Plotly's choropleth map.
- **Excel Export**: Option to download the filtered clinical trials data as an Excel file.
- **Responsive Design**: Built with Bootstrap to ensure a clean and responsive user interface.

## Requirements

- **Python** (v3.6+)
- **Flask** (v2.1.2)
- **Netlify Functions**
- **Plotly** (for map visualization)
- **Pandas** (for handling data)
- **pycountry** (for country name extraction)
- **serverless-wsgi** (to adapt the app for serverless deployment)

