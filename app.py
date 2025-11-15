"""
Flask Web Application
Main entry point for the web application
"""
import os
from flask import Flask, render_template, request, jsonify
from ml.model import predict

app = Flask(__name__)

# Configure the app
# In production, set these via environment variables
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')


@app.route('/')
def index():
    """Home page route"""
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def make_prediction():
    """
    API endpoint for making predictions using the ML model
    Expects JSON input with data to predict
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get prediction from ML model
        result = predict(data)
        
        return jsonify({
            'success': True,
            'prediction': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/about')
def about():
    """About page route"""
    return render_template('about.html')


if __name__ == '__main__':
    # Debug mode should only be enabled in development
    # In production, use a proper WSGI server like gunicorn
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
