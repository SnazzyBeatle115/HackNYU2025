"""
Flask Web Application
Main entry point for the web application
"""
import os
import base64
import time
import secrets
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

# Directory to temporarily save uploads for debugging
TMP_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'tmp_uploads')
os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)

def save_temp_file(payload):
    """Save bytes from payload to TMP_UPLOAD_DIR and return the saved path or None.

    payload can contain 'file_bytes' (raw bytes) or 'data' (base64 string or data URL).
    """
    try:
        file_bytes = payload.get('file_bytes')
        filename = payload.get('filename')
        input_type = payload.get('input_type', 'data')

        # If no raw bytes, try to decode base64 from 'data'
        if file_bytes is None and 'data' in payload:
            b64 = payload.get('data')
            if isinstance(b64, str) and b64.startswith('data:'):
                # strip data URL prefix
                b64 = b64.split(',', 1)[1]
            file_bytes = base64.b64decode(b64)

        if not file_bytes:
            return None

        # Choose extension
        ext = None
        if filename:
            _, ext = os.path.splitext(filename)
        if not ext:
            ext = '.jpg' if input_type == 'screen' else '.bin'

        ts = int(time.time() * 1000)
        token = secrets.token_hex(4)
        out_name = f"{input_type}_{ts}_{token}{ext}"
        out_path = os.path.join(TMP_UPLOAD_DIR, out_name)

        with open(out_path, 'wb') as fh:
            fh.write(file_bytes)

        return out_path
    except Exception:
        return None

# Configure the app
# In production, set these via environment variables
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')


@app.route('/')
def index():
    """Home page route"""
    return render_template('index.html')



def get_input_payload(input_type, json_key):
    """
    Helper to extract input payload from request, handling file uploads and JSON data.
    Returns (payload, error_response) where error_response is None if successful.
    """
    # Prefer file upload via multipart/form-data field named 'file'
    if request.files and 'file' in request.files:
        f = request.files['file']
        content = f.read()
        payload = {
            'input_type': input_type,
            'filename': f.filename,
            'file_bytes': content
        }
        return payload, None
    else:
        data = request.get_json()
        if not data or (json_key not in data and 'data' not in data):
            return None, jsonify({'error': f'No {input_type} provided'}), 400
        # Accept either the specific key or 'data' key in JSON
        payload = {'input_type': input_type, 'data': data.get(json_key) or data.get('data')}
        return payload, None

@api.route('/video', methods=['POST'])
def video_input():
    """Accept video input (file upload or JSON/base64) and forward to ML model."""
    try:
        payload, error_response = get_input_payload('video', 'video')
        if error_response:
            return error_response
        # Save temporary copy for debugging
        saved = save_temp_file(payload)

        result = predict(payload)
        return jsonify({'success': True, 'prediction': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route('/screen', methods=['POST'])
def screen_input():
    """Accept screen input (screenshot file or JSON/base64) and forward to ML model."""
    try:
        # multipart/form-data upload with field 'file'
        if request.files and 'file' in request.files:
            f = request.files['file']
            content = f.read()
            payload = {'input_type': 'screen', 'filename': f.filename, 'file_bytes': content}
        else:
            data = request.get_json(silent=True) or {}
            b64 = data.get('screen') or data.get('data')
            if not b64:
                return jsonify({'success': False, 'error': 'No screen data provided'}), 400
            # strip data URL prefix if present: "data:image/jpeg;base64,...."
            if isinstance(b64, str) and b64.startswith('data:'):
                b64 = b64.split(',', 1)[1]
            try:
                file_bytes = base64.b64decode(b64)
            except Exception:
                return jsonify({'success': False, 'error': 'Invalid base64 data'}), 400
            payload = {'input_type': 'screen', 'file_bytes': file_bytes}

        # Save temporary copy for debugging
        # saved = save_temp_file(payload)

        result = predict(payload)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
