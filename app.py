"""
Flask Web Application
Main entry point for the web application
"""
import os
import base64
import time
import secrets
import subprocess
import sys
import atexit
from flask import Flask, render_template, request, jsonify, Blueprint

# Try to import flask_cors for CORS support
try:
    from flask_cors import CORS
    cors_available = True
except ImportError:
    cors_available = False
    print("Warning: flask-cors not available. CORS may cause issues.")

# Safe fallback for predict if ML model module isn't present
try:
    from ml.model import predict
except Exception:
    def predict(data):
        return {
            'warning': 'ml.model.predict not available; using fallback stub',
            'received_type': data.get('input_type') if isinstance(data, dict) else str(type(data)),
            'summary': str(data)[:200]
        }

app = Flask(__name__)

# Enable CORS if available
if cors_available:
    CORS(app)

# API blueprint: group API routes under `/api` prefix
api = Blueprint('api', __name__, url_prefix='/api')

# Directory to temporarily save uploads for debugging
TMP_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'tmp_uploads')
os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)

# ML server URL (used to forward images). Can be overridden with env var ML_SERVER_URL
ML_SERVER_URL = os.environ.get('ML_SERVER_URL', 'http://localhost:8081')

import json
import urllib.request

# Prefer `requests` if available for simpler multipart uploads; fall back to urllib
try:
    import requests
except Exception:
    requests = None


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
def forward_to_ml(payload, endpoint='/detectscreen', timeout=60):
    """Forward the base64 image in `payload['data']` (or encode `file_bytes`) to
    the ML server endpoint as JSON {"image": "<base64>"} and return the parsed
    JSON response. This follows the `image` key convention used in the test
    utility example.
    """
    url = ML_SERVER_URL.rstrip('/') + endpoint

    # Build base64 string from payload
    b64 = None
    if payload is None:
        return {'error': 'no_payload'}
    if payload.get('data') is not None:
        b64 = payload.get('data')
        if isinstance(b64, str) and b64.startswith('data:'):
            b64 = b64.split(',', 1)[1]
    elif payload.get('file_bytes') is not None:
        b64 = base64.b64encode(payload.get('file_bytes')).decode()

    if not b64:
        return {'error': 'no_image_data'}

    data = {'image': b64}

    # Debug print concise info
    try:
        preview = b64[:120] + '...' if len(b64) > 120 else b64
        print(f"Forwarding to ML {url} image_length={len(b64)} preview={preview}")
    except Exception:
        print(f"Forwarding to ML {url} (payload present)")

    try:
        if requests:
            resp = requests.post(url, json=data, timeout=timeout)
            try:
                return resp.json()
            except Exception:
                return {'error': 'invalid_json_response', 'text': resp.text, 'status': resp.status_code}
        else:
            body = json.dumps(data).encode()
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
    except Exception as e:
        return {'error': str(e)}

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
            # Accept full data URL or raw base64 string; store raw base64 in payload
            if isinstance(b64, str) and b64.startswith('data:'):
                b64 = b64.split(',', 1)[1]
            payload = {'input_type': 'screen', 'data': b64}

        # Save temporary copy for debugging
        saved = save_temp_file(payload)

        # Forward to ML server's /detectscreen endpoint
        ml_resp = forward_to_ml(payload, endpoint='/detectscreen')

        # If ML server returned an error, return the error
        if isinstance(ml_resp, dict) and ml_resp.get('error'):
            # Log ML server error body to console for debugging
            try:
                print("ML server error:", ml_resp.get('error'))
                if ml_resp.get('body'):
                    print("ML server error body:", ml_resp.get('body'))
            except Exception:
                pass
            resp = ml_resp.copy()
        else:
            # ML returned a successful JSON response — return it directly so
            # the client gets fields like text_extracted, activity_detected, etc.
            if isinstance(ml_resp, dict):
                resp = ml_resp.copy()
            else:
                resp = {'ml_response': ml_resp}

        if saved:
            resp['saved_path'] = saved

        return jsonify(resp)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/camera', methods=['POST'])
def camera_input():
    """Accept camera input (image file or JSON/base64) and forward to ML model."""
    try:
        # multipart/form-data upload with field 'file'
        if request.files and 'file' in request.files:
            f = request.files['file']
            content = f.read()
            payload = {'input_type': 'camera', 'filename': f.filename, 'file_bytes': content}
        else:
            data = request.get_json(silent=True) or {}
            b64 = data.get('camera') or data.get('data')
            if not b64:
                return jsonify({'success': False, 'error': 'No camera data provided'}), 400
            # Accept full data URL or raw base64 string; store raw base64 in payload
            if isinstance(b64, str) and b64.startswith('data:'):
                b64 = b64.split(',', 1)[1]
            payload = {'input_type': 'camera', 'data': b64}

        # Save temporary copy for debugging
        saved = save_temp_file(payload)

        # Forward to ML server's /detectcamera endpoint
        ml_resp = forward_to_ml(payload, endpoint='/detectcamera')

        # If ML server returned an error, return the error
        if isinstance(ml_resp, dict) and ml_resp.get('error'):
            # Log ML server error body to console for debugging
            try:
                print("ML server error:", ml_resp.get('error'))
                if ml_resp.get('body'):
                    print("ML server error body:", ml_resp.get('body'))
            except Exception:
                pass
            resp = ml_resp.copy()
        else:
            # ML returned a successful JSON response — return it directly so
            # the client gets fields like text_extracted, activity_detected, etc.
            if isinstance(ml_resp, dict):
                resp = ml_resp.copy()
            else:
                resp = {'ml_response': ml_resp}

        if saved:
            resp['saved_path'] = saved

        return jsonify(resp)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def forward_text_to_ml(message, endpoint='/chat', timeout=60):
    """Forward a text message to the ML server endpoint as JSON {"message": "<text>"}
    and return the parsed JSON response.
    """
    url = ML_SERVER_URL.rstrip('/') + endpoint
    
    if not message or not message.strip():
        return {'error': 'empty_message'}
    
    data = {'message': message.strip()}
    
    print(f"Forwarding text to ML {url} message_length={len(message)}")
    
    try:
        if requests:
            resp = requests.post(url, json=data, timeout=timeout)
            try:
                return resp.json()
            except Exception:
                return {'error': 'invalid_json_response', 'text': resp.text, 'status': resp.status_code}
        else:
            body = json.dumps(data).encode()
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
    except Exception as e:
        return {'error': str(e)}


@api.route('/text', methods=['POST'])
def process_text():
    """
    Handle text requests sent to /api/text
    Expects JSON payload with a `text` field.
    Forwards to ML server's /chat endpoint.
    """
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text') or data.get('message')
        
        if not text:
            return jsonify({
                'success': False,
                'error': "Missing required field 'text' or 'message'."
            }), 400

        print(f"Processing text: {text}")
        
        # Forward to ML server's /chat endpoint
        ml_resp = forward_text_to_ml(text, endpoint='/chat')
        
        # Log the full ML response for debugging
        print(f"ML server response: {ml_resp}")
        
        # If ML server returned an error, return the error
        if isinstance(ml_resp, dict) and ml_resp.get('error'):
            try:
                print("ML server error:", ml_resp.get('error'))
            except Exception:
                pass
            return jsonify(ml_resp), 500
        
        # ML returned a successful JSON response — return it directly
        if isinstance(ml_resp, dict):
            resp = ml_resp.copy()
        else:
            resp = {'ml_response': ml_resp}
        
        # Log the response being sent to frontend
        print(f"Sending to frontend: {resp}")
        
        return jsonify(resp)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def forward_audio_to_ml(audio_base64, audio_format='audio/webm', endpoint='/voice', timeout=60):
    """Forward base64 audio to the ML server endpoint as JSON {"audio": "<base64>"} 
    and return the parsed JSON response.
    """
    url = ML_SERVER_URL.rstrip('/') + endpoint
    
    if not audio_base64:
        return {'error': 'no_audio_data'}
    
    data = {
        'audio': audio_base64,
        'format': audio_format
    }
    
    print(f"Forwarding audio to ML {url} format={audio_format} audio_length={len(audio_base64)}")
    
    try:
        if requests:
            resp = requests.post(url, json=data, timeout=timeout)
            try:
                return resp.json()
            except Exception:
                return {'error': 'invalid_json_response', 'text': resp.text, 'status': resp.status_code}
        else:
            body = json.dumps(data).encode()
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
    except Exception as e:
        return {'error': str(e)}


@api.route('/voice', methods=['POST'])
def process_voice():
    """
    Handle voice uploads sent to /api/voice
    Accepts either:
    1. JSON payload with 'audio' (base64 string) and optional 'format' field
    2. multipart/form-data with an 'audio' file (legacy support)
    Forwards to ML server's /voice endpoint.
    """
    try:
        # Always try JSON first (most common case)
        data = request.get_json(silent=True)
        
        if data and isinstance(data, dict) and 'audio' in data:
            # This is a JSON request with audio field
            audio_base64 = data.get('audio')
            audio_format = data.get('format', 'audio/webm')
            
            if not audio_base64:
                return jsonify({
                    'success': False,
                    'error': "Missing 'audio' field in request body."
                }), 400
            
            print(f"Received audio input (JSON): format={audio_format}, base64_length={len(audio_base64)}")
            
            # Forward to ML server's /voice endpoint
            ml_resp = forward_audio_to_ml(audio_base64, audio_format, endpoint='/voice')
            
            # If ML server returned an error, return the error
            if isinstance(ml_resp, dict) and ml_resp.get('error'):
                try:
                    print("ML server error:", ml_resp.get('error'))
                except Exception:
                    pass
                return jsonify(ml_resp), 500
            
            # ML returned a successful JSON response — return it directly
            if isinstance(ml_resp, dict):
                resp = ml_resp.copy()
            else:
                resp = {'ml_response': ml_resp}
            
            return jsonify(resp)
        
        # Fallback: Check for multipart/form-data
        elif request.files:
            audio_file = request.files.get('audio')
            
            if audio_file is None or audio_file.filename == '':
                return jsonify({
                    'success': False,
                    'error': "Missing audio file in 'audio' form field."
                }), 400
            
            # Read file and convert to base64
            audio_bytes = audio_file.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            audio_format = audio_file.content_type or 'audio/webm'
            
            print(f"Received audio input (multipart): format={audio_format}, base64_length={len(audio_base64)}")
            
            # Forward to ML server
            ml_resp = forward_audio_to_ml(audio_base64, audio_format, endpoint='/voice')
            
            if isinstance(ml_resp, dict) and ml_resp.get('error'):
                return jsonify(ml_resp), 500
            
            if isinstance(ml_resp, dict):
                resp = ml_resp.copy()
            else:
                resp = {'ml_response': ml_resp}
            
            return jsonify(resp)
        
        else:
            # Neither JSON nor multipart detected
            return jsonify({
                'success': False,
                'error': "Invalid request format. Expected JSON with 'audio' field or multipart/form-data with 'audio' file."
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/')
def index():
    """Home page route"""
    # Get capture intervals from environment variables (in milliseconds)
    # Default to 2000ms (2 seconds) if not set
    screen_capture_interval = int(os.environ.get('SCREEN_CAPTURE_INTERVAL', 2000))
    camera_capture_interval = int(os.environ.get('CAMERA_CAPTURE_INTERVAL', 2000))
    
    return render_template('index.html', 
                         screen_capture_interval=screen_capture_interval,
                         camera_capture_interval=camera_capture_interval)


@app.route('/about')
def about():
    """About page route"""
    return render_template('about.html')


@app.route('/farm')
def farm():
    """Farm page route"""
    return render_template('farm.html')


# Register API blueprint so `/api` routes are available
app.register_blueprint(api)


def start_ml_api_server(port: int | None = None):
    """Start the ML API server (`ml/api_server.py`) as a subprocess.

    The subprocess is registered to be cleaned up at program exit. When running
    Flask in debug mode the Werkzeug reloader spawns multiple processes; to
    avoid starting multiple ML servers we only start it in the real child
    process (when `WERKZEUG_RUN_MAIN` == 'true') or when not in debug mode.
    """
    ml_script = os.path.join(os.path.dirname(__file__), 'ml', 'api_server.py')
    if not os.path.exists(ml_script):
        print(f"ML API script not found: {ml_script}")
        return None

    args = [sys.executable, ml_script]
    if port:
        args += ['--port', str(port)]

    try:
        # Ensure the ML server subprocess does not enable the Flask/Werkzeug
        # debug reloader on Windows. The reloader uses file-descriptor based
        # socket passing which can fail with "not a socket" errors.
        env = os.environ.copy()
        env['FLASK_DEBUG'] = '0'

        proc = subprocess.Popen(args, cwd=os.path.dirname(__file__), env=env)

        def _cleanup():
            try:
                if proc.poll() is None:
                    proc.terminate()
                    time.sleep(0.5)
                    if proc.poll() is None:
                        proc.kill()
            except Exception:
                pass

        atexit.register(_cleanup)
        print(f"Started ML API server (pid={proc.pid}) using {ml_script}")
        return proc
    except Exception as e:
        print("Failed to start ML API server:", e)
        return None


if __name__ == '__main__':
    # Debug mode should only be enabled in development
    # In production, use a proper WSGI server like gunicorn
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    # Start the ML API server before launching Flask. Choose a different port
    # to avoid colliding with the Flask port. When running with the
    # Werkzeug reloader, the parent process spawns a child; we only want to
    # start the ML server in the child process (when WERKZEUG_RUN_MAIN == 'true')
    flask_port = 8080
    ml_port = 8081

    
    start_ml_api_server(port=ml_port)

    app.run(debug=debug_mode, host='0.0.0.0', port=flask_port)