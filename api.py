# api.py
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import geopandas as gpd
import folium
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Create necessary folders
UPLOAD_FOLDER = 'uploads'
MAPS_FOLDER = 'generated_maps'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MAPS_FOLDER, exist_ok=True)

def generate_health_map(df):
    """Generate health map from dataframe"""
    # Create base map centered on mean coordinates
    m = folium.Map(
        location=[df['latitude'].mean(), df['longitude'].mean()],
        zoom_start=4
    )
    
    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df['longitude'], df['latitude'])
    )
    
    # Add choropleth layer
    folium.Choropleth(
        geo_data=gdf.__geo_interface__,
        data=df,
        columns=['region', 'health_metric'],
        key_on='feature.properties.region',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Health Metric'
    ).add_to(m)
    
    # Add markers with popups
    for idx, row in df.iterrows():
        popup_content = f"""
            Region: {row['region']}<br>
            Health Metric: {row['health_metric']}<br>
            Additional Info: {row.get('additional_info', 'N/A')}
        """
        
        folium.Marker(
            [row['latitude'], row['longitude']],
            popup=popup_content
        ).add_to(m)
    
    # Generate unique filename and save map
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'health_map_{timestamp}.html'
    filepath = os.path.join(MAPS_FOLDER, filename)
    m.save(filepath)
    
    return filename

@app.route('/')
def home():
    return "Welcome to the HealthMap Analyzer API! Use the /api/health , /api/generate-map ad /api/maps/<filename>  endpoints."


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/api/generate-map', methods=['POST'])
def create_map():
    """Generate health map from uploaded CSV data"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Read and validate CSV
        try:
            df = pd.read_csv(filepath)
            required_columns = ['latitude', 'longitude', 'region', 'health_metric']
            if not all(col in df.columns for col in required_columns):
                return jsonify({
                    'error': f'Missing required columns. Required: {required_columns}'
                }), 400
            
            # Generate map
            map_filename = generate_health_map(df)
            
            # Clean up uploaded file
            os.remove(filepath)
            
            # Return map URL
            return jsonify({
                'success': True,
                'map_url': f'/api/maps/{map_filename}'
            })
            
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/maps/<filename>')
def get_map(filename):
    """Retrieve generated map"""
    try:
        return send_file(
            os.path.join(MAPS_FOLDER, filename),
            mimetype='text/html'
        )
    except FileNotFoundError:
        return jsonify({'error': 'Map not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)