"""
ML Utilities
Helper functions for data preprocessing and feature engineering
"""
import numpy as np


def preprocess_data(data):
    """
    Preprocess raw data for model input
    
    Args:
        data: Raw input data
        
    Returns:
        Preprocessed data ready for model
    """
    # Placeholder for preprocessing logic
    # Example: normalize, scale, encode categorical variables, etc.
    return data


def extract_features(data):
    """
    Extract features from raw data
    
    Args:
        data: Raw input data
        
    Returns:
        Extracted features
    """
    # Placeholder for feature extraction
    features = []
    
    # Example feature extraction logic
    if isinstance(data, dict):
        features = [data.get(key, 0) for key in sorted(data.keys())]
    
    return features


def normalize_data(data, mean=None, std=None):
    """
    Normalize data using z-score normalization
    
    Args:
        data: Input data
        mean: Mean for normalization (if None, computed from data)
        std: Standard deviation for normalization (if None, computed from data)
        
    Returns:
        Normalized data
    """
    data_array = np.array(data)
    
    if mean is None:
        mean = np.mean(data_array)
    if std is None:
        std = np.std(data_array)
    
    if std == 0:
        return data_array
    
    return (data_array - mean) / std


def split_dataset(X, y, test_size=0.2, random_state=42):
    """
    Split dataset into training and testing sets
    
    Args:
        X: Features
        y: Labels
        test_size: Proportion of dataset to include in test split
        random_state: Random seed for reproducibility
        
    Returns:
        X_train, X_test, y_train, y_test
    """
    # Placeholder - in production, use sklearn.model_selection.train_test_split
    np.random.seed(random_state)
    
    n_samples = len(X)
    n_test = int(n_samples * test_size)
    
    indices = np.random.permutation(n_samples)
    test_indices = indices[:n_test]
    train_indices = indices[n_test:]
    
    X_array = np.array(X)
    y_array = np.array(y)
    
    return (X_array[train_indices], X_array[test_indices],
            y_array[train_indices], y_array[test_indices])
