from flask import Flask, render_template, request, jsonify, send_file
from pytrials.client import ClinicalTrials
import pandas as pd
import plotly.express as px
import pycountry
import io

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

# Function to get clinical trials data
def get_clinical_trials(search_terms, target_fields, max_no_studies=1000):
    ct = ClinicalTrials()
    clinical_trials = ct.get_study_fields(
        search_expr=search_terms,
        fields=target_fields,
        max_studies=max_no_studies,
        fmt="csv"
    )
    return clinical_trials

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
    trials_data = get_clinical_trials(search_terms, target_fields)
    df = pd.DataFrame(trials_data[1:], columns=trials_data[0])
    df['Country'] = df['Locations'].apply(lambda x: extract_country_from_list(str(x)))
    
    # Convert date fields to datetime
    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df['Primary Completion Date'] = pd.to_datetime(df['Primary Completion Date'], errors='coerce')
    
    # Apply date filters
    if start_date_from:
        df = df[df['Start Date'] >= pd.to_datetime(start_date_from)]
    if start_date_to:
        df = df[df['Start Date'] <= pd.to_datetime(start_date_to)]
    if pc_date_from:
        df = df[df['Primary Completion Date'] >= pd.to_datetime(pc_date_from)]
    if pc_date_to:
        df = df[df['Primary Completion Date'] <= pd.to_datetime(pc_date_to)]
    
    df_filtered = df.dropna(subset=['Country'])
    
    # Convert to JSON
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
    
    graph_html = fig.to_html(full_html=False)
    
    return jsonify({'table_data': table_data, 'graph_html': graph_html})

@app.route('/download', methods=['GET'])
def download():
    # Retrieve the clinical trial data from the previous search
    search_terms = request.args.get('search_terms')
    date_field = request.args.get('date_field')
    
    # Fetch the data and process it again
    target_fields = ['NCT Number', 'Study Title', 'Study URL', 'Locations', 'Start Date', 'Primary Completion Date']
    trials_data = get_clinical_trials(search_terms, target_fields)
    df = pd.DataFrame(trials_data[1:], columns=trials_data[0])
    df['Country'] = df['Locations'].apply(lambda x: extract_country_from_list(str(x)))
    
    # Convert date fields to datetime
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
