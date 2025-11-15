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

def forward_to_ml(payload, endpoint, timeout=10):
    """Forward payload to the ML API server endpoint and return parsed JSON response.

    - If payload contains `file_bytes`, attempt a multipart/form-data upload (requests preferred).
    - Otherwise send JSON (base64 string under `screen` key).
    """
    url = ML_SERVER_URL.rstrip('/') + endpoint
    try:
        # Build base64 image string from either raw bytes or provided data
        if payload.get('file_bytes') is not None:
            b64 = base64.b64encode(payload['file_bytes']).decode()
        else:
            b64 = payload.get('data')
            if isinstance(b64, str) and b64.startswith('data:'):
                b64 = b64.split(',', 1)[1]

        if not b64:
            return {'error': 'no_image_data'}

        data = {'image': b64}

        # Debug: print concise payload info before forwarding to ML server
        try:
            preview = b64[:120] + '...' if isinstance(b64, str) and len(b64) > 120 else b64
            print(f"Forwarding to ML {url} with payload image length={len(b64)} preview={preview}")
        except Exception:
            print(f"Forwarding to ML {url} (payload present, preview suppressed)")

        if requests:
            resp = requests.post(url, json=data, timeout=timeout)
            try:
                body = resp.json()
            except Exception:
                body = {'text': resp.text}
            if resp.status_code >= 400:
                return {'error': f'{resp.status_code} {resp.reason}', 'body': body}
            return body
        else:
            data_bytes = json.dumps(data).encode()
            req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
    except Exception as e:
        return {'error': str(e)}

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