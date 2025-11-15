"""
Flask Web Application
Main entry point for the web application
"""
import os
from flask import Flask, render_template, request, jsonify, Blueprint

# Try to import the real ML predict function; fall back to a safe stub for dev
try:
    from ml.model import predict
except Exception:
    def predict(data):
        # Development fallback: return an echo-like response so endpoints remain usable
        return {
            'warning': 'ml.model.predict not available; using fallback stub',
            'received_type': data.get('input_type') if isinstance(data, dict) else str(type(data)),
            'summary': str(data)[:200]
        }

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





@api.route('/video', methods=['POST'])
def video_input():
    """Accept video input (file upload or JSON/base64) and forward to ML model."""
    try:
        # Prefer file upload via multipart/form-data field named 'file'
        if request.files and 'file' in request.files:
            f = request.files['file']
            content = f.read()
            payload = {
                'input_type': 'video',
                'filename': f.filename,
                'file_bytes': content
            }
        else:
            data = request.get_json()
            if not data or ('video' not in data and 'data' not in data):
                return jsonify({'error': 'No video provided'}), 400
            # Accept either `video` or `data` key in JSON
            payload = {'input_type': 'video', 'data': data.get('video') or data.get('data')}

        result = predict(payload)
        return jsonify({'success': True, 'prediction': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/screen', methods=['POST'])
def screen_input():
    """Accept screen input (screenshot file or JSON/base64) and forward to ML model."""
    try:
        # Support file upload via multipart/form-data field named 'file'
        if request.files and 'file' in request.files:
            f = request.files['file']
            content = f.read()
            payload = {
                'input_type': 'screen',
                'filename': f.filename,
                'file_bytes': content
            }
        else:
            data = request.get_json()
            if not data or ('screen' not in data and 'data' not in data):
                return jsonify({'error': 'No screen provided'}), 400
            payload = {'input_type': 'screen', 'data': data.get('screen') or data.get('data')}

        result = predict(payload)
        return jsonify({'success': True, 'prediction': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
