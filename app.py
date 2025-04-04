from flask import Flask, request, jsonify, send_file
from pytrials.client import ClinicalTrials
import pandas as pd
import plotly.express as px
import pycountry
import io
from mangum import Mangum  # For AWS Lambda compatibility

app = Flask(__name__)

# Function to extract country from location string
def extract_country_from_list(location_string):
    if pd.isna(location_string):
        return None
    for country in pycountry.countries:
        if country.name in location_string or country.alpha_2 in location_string:
            return country.name
    return None

# Function to get clinical trials data
def get_clinical_trials(search_terms, target_fields, max_no_studies=1000):
    ct = ClinicalTrials()
    try:
        clinical_trials = ct.get_study_fields(
            search_expr=search_terms,
            fields=target_fields,
            max_studies=max_no_studies,
            fmt="csv"
        )
        if not clinical_trials or len(clinical_trials) < 2:
            return None
        return clinical_trials
    except Exception as e:
        print(f"Error fetching clinical trials data: {e}")
        return None

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request, JSON expected"}), 400

    search_terms = data.get('search_terms', '')
    date_field = data.get('date_field', 'Start Date')
    start_date_from = data.get('start_date_from')
    start_date_to = data.get('start_date_to')
    pc_date_from = data.get('pc_date_from')
    pc_date_to = data.get('pc_date_to')
    
    target_fields = ['NCT Number', 'Study Title', 'Study URL', 'Locations', 'Start Date', 'Primary Completion Date']
    trials_data = get_clinical_trials(search_terms, target_fields)
    if trials_data is None:
        return jsonify({"error": "No clinical trials data found."})
    
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
    
    # Generate choropleth map
    country_counts = df_filtered['Country'].value_counts().reset_index()
    country_counts.columns = ['Country', 'Count']
    
    if df_filtered.empty:
        return jsonify({'table_data': table_data, 'graph_html': '<p>No data available for visualization.</p>'})
    
    fig = px.choropleth(
        country_counts, 
        locations='Country', 
        locationmode='country names', 
        color='Count',
        hover_name='Country',
        hover_data=['Count'],
        color_continuous_scale='Viridis',
        title=f"Distribution of Clinical Trials by Country for {search_terms}"
    )
    
    graph_html = fig.to_html(full_html=False)
    
    return jsonify({'table_data': table_data, 'graph_html': graph_html})

@app.route('/download', methods=['GET'])
def download():
    search_terms = request.args.get('search_terms')
    if not search_terms:
        return jsonify({"error": "Missing search_terms parameter"}), 400

    target_fields = ['NCT Number', 'Study Title', 'Study URL', 'Locations', 'Start Date', 'Primary Completion Date']
    trials_data = get_clinical_trials(search_terms, target_fields)
    if trials_data is None:
        return jsonify({"error": "No data available for download."})
    
    df = pd.DataFrame(trials_data[1:], columns=trials_data[0])
    df['Country'] = df['Locations'].apply(lambda x: extract_country_from_list(str(x)))
    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df['Primary Completion Date'] = pd.to_datetime(df['Primary Completion Date'], errors='coerce')
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Clinical Trials')
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name="clinical_trials.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# AWS Lambda Handler for Netlify Function
handler = Mangum(app)

# Optional for local testing
if __name__ == '__main__':
    app.run(debug=True)
