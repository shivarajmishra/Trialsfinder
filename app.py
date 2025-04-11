from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import plotly.express as px
import pycountry
import io
import csv
import requests
from urllib.parse import quote_plus

# Increase CSV field size limit to avoid the field size limit error
csv.field_size_limit(10 * 1024 * 1024)  # Set to 10MB, adjust as needed

app = Flask(__name__)

# Function to extract country from location string
def extract_country_from_list(location_string):
    if pd.isna(location_string):
        return None
    country_list = [country.name for country in pycountry.countries]
    for country in country_list:
        if country in location_string:
            return country
    return None

# Function to get clinical trials data using the URL-based method
def fetch_clinical_trials_data(search_terms, target_fields, max_no_studies=50000):
    # Encode the search term and fields into the URL format
    search_cond = quote_plus(search_terms)
    field_str = "%2C".join([quote_plus(f) for f in target_fields])
    
    # Construct the URL to fetch the data
    url = (
        f"https://clinicaltrials.gov/api/int/studies/download"
        f"?format=csv&cond={search_cond}"
        f"&aggFilters=&sort=%40relevance&fields={field_str}"
    )
    
    print(f"Fetching clinical trials data from: {url}")
    
    # Fetch the data from the URL
    response = requests.get(url)
    
    # Read the CSV response into a DataFrame
    df = pd.read_csv(io.StringIO(response.text))
    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    search_terms = data.get('search_terms')
    date_field = data.get('date_field')
    start_date_from = data.get('start_date_from')
    start_date_to = data.get('start_date_to')
    pc_date_from = data.get('pc_date_from')
    pc_date_to = data.get('pc_date_to')
    
    target_fields = ['NCT Number', 'Study Title', 'Study URL', 'Locations', 'Start Date', 'Primary Completion Date']
    df = fetch_clinical_trials_data(search_terms, target_fields)
    
    # Extract Country
    df['Country'] = df['Locations'].apply(lambda x: extract_country_from_list(str(x)))
    
    # Convert date fields to datetime (Coerce invalid dates to NaT)
    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df['Primary Completion Date'] = pd.to_datetime(df['Primary Completion Date'], errors='coerce')
    
    # Remove rows with NaT (invalid date values)
    df = df.dropna(subset=['Start Date', 'Primary Completion Date'])
    
    # Apply date filters
    if start_date_from:
        df = df[df['Start Date'] >= pd.to_datetime(start_date_from)]
    if start_date_to:
        df = df[df['Start Date'] <= pd.to_datetime(start_date_to)]
    if pc_date_from:
        df = df[df['Primary Completion Date'] >= pd.to_datetime(pc_date_from)]
    if pc_date_to:
        df = df[df['Primary Completion Date'] <= pd.to_datetime(pc_date_to)]
    
    # Remove rows where Country is NaN
    df_filtered = df.dropna(subset=['Country'])
    
    # Convert filtered data to JSON for response
    table_data = df_filtered[['NCT Number', 'Study Title', 'Country', date_field]].to_dict(orient='records')
    
    # Generate a Plotly choropleth map for the distribution of trials by country
    country_counts = df_filtered['Country'].value_counts().reset_index()
    country_counts.columns = ['Country', 'Count']
    
    # Create the choropleth map
    fig = px.choropleth(country_counts, 
                        locations='Country', 
                        locationmode='country names', 
                        color='Count',
                        hover_name='Country',
                        hover_data=['Count'],
                        color_continuous_scale='Viridis',  # You can choose a different color scale
                        title=f"Distribution of Clinical Trials by Country for {search_terms}")
    
    fig.update_layout(
    geo=dict(
        projection_type="natural earth",
        showland=True,
        landcolor="white",
    ),
    title=f"Distribution of Clinical Trials by Country for {search_terms}",
    title_font=dict(size=24, family="Arial", weight="bold"),  # Increase size and make title bold
    width=1200,  # Set width of the figure
    height=800,  # Set height of the figure
)
    graph_html = fig.to_html(full_html=False)
    
    return jsonify({'table_data': table_data, 'graph_html': graph_html})

@app.route('/download', methods=['GET'])
def download():
    # Retrieve the clinical trial data from the previous search
    search_terms = request.args.get('search_terms')
    date_field = request.args.get('date_field')
    
    # Fetch the data and process it again
    target_fields = ['NCT Number', 'Study Title', 'Study URL', 'Locations', 'Start Date', 'Primary Completion Date']
    df = fetch_clinical_trials_data(search_terms, target_fields)
    
    # Extract Country
    df['Country'] = df['Locations'].apply(lambda x: extract_country_from_list(str(x)))
    
    # Convert date fields to datetime (Coerce invalid dates to NaT)
    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df['Primary Completion Date'] = pd.to_datetime(df['Primary Completion Date'], errors='coerce')
    
    # Prepare the data for downloading
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Clinical Trials')
    output.seek(0)
    
    # Send the file as a response for download
    return send_file(output, as_attachment=True, download_name="clinical_trials.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == '__main__':
    app.run(debug=True)
