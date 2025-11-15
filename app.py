"""
Flask Web Application
Main entry point for the web application
"""
from flask import Flask, render_template, request, jsonify
from ml.model import predict

app = Flask(__name__)

# Configure the app
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production


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
    app.run(debug=True, host='0.0.0.0', port=5000)
