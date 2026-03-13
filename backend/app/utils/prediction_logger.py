"""
Prediction logging utilities for tracking historical forecasts.

This module provides functionality to log daily water demand predictions
and retrieve recent prediction history for accuracy verification.
"""

import csv
import os
from datetime import datetime
from pathlib import Path

# Prediction log file path
LOG_FILE = Path("data/prediction_history.csv")


def initialize_log():
    """Create prediction log file if it doesn't exist."""
    LOG_FILE.parent.mkdir(exist_ok=True)

    if not LOG_FILE.exists():
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp',
                'prediction_date',
                'predicted_demand',
                'confidence_lower',
                'confidence_upper',
                'demand_level'
            ])


def log_prediction(prediction_date, predicted_demand, confidence_lower, confidence_upper, demand_level):
    """
    Log a prediction to the CSV file.

    Args:
        prediction_date: Date for which the prediction was made (ISO format)
        predicted_demand: Predicted water demand in MGD
        confidence_lower: Lower bound of 80% confidence interval
        confidence_upper: Upper bound of 80% confidence interval
        demand_level: Classification (LOW, MODERATE, HIGH)
    """
    initialize_log()

    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            prediction_date,
            predicted_demand,
            confidence_lower,
            confidence_upper,
            demand_level
        ])


def get_recent_predictions(days=5):
    """
    Get the most recent N days of predictions.

    Args:
        days: Number of recent days to retrieve (default: 5)

    Returns:
        List of dictionaries containing prediction data, sorted by date descending
    """
    initialize_log()

    predictions = []

    with open(LOG_FILE, 'r') as f:
        reader = csv.DictReader(f)
        all_predictions = list(reader)

    # Group by prediction_date, keep only the most recent prediction for each date
    date_predictions = {}
    for pred in all_predictions:
        pred_date = pred['prediction_date']
        if pred_date not in date_predictions or pred['timestamp'] > date_predictions[pred_date]['timestamp']:
            date_predictions[pred_date] = pred

    # Sort by date descending and take last N days
    sorted_predictions = sorted(
        date_predictions.values(),
        key=lambda x: x['prediction_date'],
        reverse=True
    )

    # Return up to N days (might be less if we don't have 5 days yet)
    return sorted_predictions[:days]
