# HackNYU2025 - Flask ML Web App

A Flask-based web application with integrated machine learning capabilities. This project features a clean separation of concerns with a dedicated ML folder for all machine learning-related code.

## Project Structure

```
HackNYU2025/
├── app.py                  # Main Flask application entry point
├── templates/              # HTML templates (Jinja2)
│   ├── base.html          # Base template with navigation
│   ├── index.html         # Home page with ML prediction form
│   └── about.html         # About page
├── static/                 # Static files (CSS, JS, images)
│   ├── css/
│   │   └── style.css      # Main stylesheet
│   ├── js/
│   │   └── main.js        # JavaScript utilities
│   └── images/            # Image assets
├── ml/                     # Machine Learning module
│   ├── __init__.py        # Package initialization
│   ├── model.py           # ML model implementation
│   └── utils.py           # ML utilities (preprocessing, feature engineering)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Features

- **Flask Framework**: Lightweight and powerful Python web framework
- **ML Integration**: Separate ML folder with modular machine learning implementation
- **RESTful API**: Clean API endpoints for making predictions
- **Responsive Design**: Modern, mobile-friendly user interface
- **Modular Structure**: Easy to extend and maintain

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/SnazzyBeatle115/HackNYU2025.git
   cd HackNYU2025
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** (optional)
   ```bash
   cp .env.example .env
   # Edit .env and set your SECRET_KEY and other configuration
   ```

## Usage

1. **Run the Flask application**
   ```bash
   python app.py
   ```
   
   By default, the app runs in debug mode. To disable debug mode:
   ```bash
   export FLASK_DEBUG=False
   python app.py
   ```

2. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`
   - Try the ML prediction feature on the home page
   - Explore the about page for more information

## API Endpoints

- `GET /` - Home page with ML prediction form
- `GET /about` - About page with project information
- `POST /predict` - API endpoint for making predictions
  - Request body (JSON): `{"value": <number>}`
  - Response: `{"success": true, "prediction": <result>}`

## ML Module

The `ml/` folder contains all machine learning-related code:

- **model.py**: Contains the `MLModel` class with methods for training, prediction, and model persistence
- **utils.py**: Utility functions for data preprocessing, feature extraction, and dataset splitting

### Using the ML Module

```python
from ml.model import predict, get_model

# Make a prediction
result = predict({"value": 42})

# Access the model directly
model = get_model()
model.train(X_train, y_train)
```

## Customization

### Adding Your Own ML Model

1. Replace the placeholder logic in `ml/model.py` with your actual model
2. Install required ML libraries (uncomment in `requirements.txt`)
3. Update the prediction logic to use your trained model

Example with scikit-learn:
```python
from sklearn.ensemble import RandomForestClassifier

class MLModel:
    def __init__(self):
        self.model = RandomForestClassifier()
    
    def train(self, X_train, y_train):
        self.model.fit(X_train, y_train)
    
    def predict_single(self, data):
        features = extract_features(data)
        return self.model.predict([features])[0]
```

### Adding New Routes

Add new routes in `app.py`:
```python
@app.route('/new-route')
def new_route():
    return render_template('new_template.html')
```

## Development

- **Debug mode**: The app runs in debug mode by default for development. Set `FLASK_DEBUG=False` in production.
- **Secret key**: Set a secure `SECRET_KEY` environment variable in production.
- **Port**: Default port is 5000, can be changed in `app.py`.

## Security Notes

⚠️ **Important for Production:**
1. Set `FLASK_DEBUG=False` to disable debug mode
2. Use a strong, random `SECRET_KEY` (not the default)
3. Use a production WSGI server like gunicorn instead of the built-in Flask server
4. Never commit `.env` files with secrets to version control

## Technologies Used

- **Flask** - Web framework
- **NumPy** - Numerical computing
- **HTML/CSS/JavaScript** - Frontend
- **Jinja2** - Template engine (comes with Flask)

## Contributing

This project was built for HackNYU2025. Feel free to fork and customize for your own needs!

## License

MIT License - feel free to use this project as a starting point for your own applications.