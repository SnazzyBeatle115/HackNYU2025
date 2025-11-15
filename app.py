"""
Flask Web Application
Main entry point for the web application
"""
import os
from flask import Flask, render_template, request, jsonify, Blueprint
# from ml.model import predict

app = Flask(__name__)

# API blueprint: group API routes under `/api` prefix
api = Blueprint('api', __name__, url_prefix='/api')

# Configure the app
# In production, set these via environment variables
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')


@app.route('/')
def index():
    """Home page route"""
    return render_template('index.html')




@api.route('/predict', methods=['POST'])
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


@api.route('/text', methods=['POST'])
def process_text():
    """
    Handle text requests sent to /api/text
    Expects JSON payload with a `text` field.
    """
    payload = request.get_json(silent=True) or {}
    text = payload.get('text')

    if not text:
        return jsonify({
            'success': False,
            'error': "Missing required field 'text'."
        }), 400

    # Replace the response below with real logic when ready.
    return jsonify({
        'success': True,
        'message': 'Text processed successfully.',
        'length': len(text),
        'metadata': payload.get('metadata', {})
    })


@api.route('/voice', methods=['POST'])
def process_voice():
    """
    Handle voice uploads sent to /api/voice
    Expects multipart/form-data with an `audio` file.
    """
    audio_file = request.files.get('audio')

    if audio_file is None or audio_file.filename == '':
        return jsonify({
            'success': False,
            'error': "Missing audio file in 'audio' form field."
        }), 400

    # Placeholder response – integrate with voice model or storage later.
    return jsonify({
        'success': True,
        'message': 'Voice data received.',
        'filename': audio_file.filename
    })


@app.route('/about')
def about():
    """About page route"""
    return render_template('about.html')


# Register API blueprint so `/api` routes are available
app.register_blueprint(api)


if __name__ == '__main__':
    # Debug mode should only be enabled in development
    # In production, use a proper WSGI server like gunicorn
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
