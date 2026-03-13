# Pearland Water Demand Forecast - Backend

FastAPI backend service for daily water demand forecasting using machine learning.

## Overview

This service provides water demand predictions for Pearland, TX using a Gradient Boosting Regressor model trained on 2019-2025 historical data. The model achieves ~94% R² accuracy and provides 10-day forecasts with 80% confidence intervals.

## Features

- **10-Day Forecasting**: Daily water demand predictions in Million Gallons per Day (MGD)
- **Weather Integration**: Real-time weather data from Open-Meteo API
- **Prediction Logging**: Automatic tracking of daily predictions for accuracy verification
- **Confidence Intervals**: 80% confidence bounds for each prediction
- **Demand Classification**: Low/Moderate/High demand levels based on thresholds

## Setup

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure model artifacts are in the `model/` directory:
   - `water_forecast_gb_model.pkl`
   - `feature_scaler.pkl`
   - `feature_columns.pkl`
   - `residual_std.pkl`
   - `pearland_merged_data.csv`

3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### `GET /api/forecast`
Get 10-day water demand forecast with weather data.

**Response:**
```json
{
  "forecasts": [
    {
      "date": "2025-01-20",
      "demand": 13.5,
      "lower_bound": 12.3,
      "upper_bound": 14.7,
      "demand_level": "Moderate",
      "weather": { ... }
    }
  ],
  "last_updated": "2025-01-20T10:30:00-06:00",
  "model_accuracy": {
    "r_squared": 0.94,
    "confidence_interval": "80%"
  }
}
```

### `GET /api/recent-predictions`
Get last 5 days of prediction history for accuracy verification.

**Response:**
```json
{
  "predictions": [
    {
      "date": "2025-01-19",
      "predicted_demand": 14.2,
      "confidence_lower": 13.0,
      "confidence_upper": 15.4,
      "demand_level": "MODERATE"
    }
  ],
  "count": 5
}
```

### `GET /api/health`
Health check endpoint with model status.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "timestamp": "2025-01-20T10:30:00-06:00",
  "features_count": 26
}
```

## Model Details

- **Algorithm**: Gradient Boosting Regressor
- **Training Period**: 2019-2025
- **Accuracy**: R² = 0.94, MAPE = 3.29%
- **Features**: 26 engineered features including:
  - Temperature (mean, max, min)
  - Precipitation
  - Day of week, month, seasonality
  - Historical production lags and rolling averages

## Demand Level Thresholds

- **Low**: < 14 MGD
- **Moderate**: 14-18 MGD
- **High**: > 18 MGD

## Prediction Logging

All predictions are automatically logged to `data/prediction_history.csv` for accuracy verification. The log stores:
- Timestamp of prediction
- Prediction date
- Predicted demand and confidence bounds
- Demand level classification

## Deployment

### Railway/Heroku

The service is configured for deployment with:
- `Procfile`: Specifies the web server command
- `railway.json`: Railway-specific configuration

### Environment Variables

- `FRONTEND_URL`: CORS allowed origin (default: "*")

## Development

### Project Structure

```
backend/
├── app/
│   └── utils/
│       └── prediction_logger.py  # Prediction logging utilities
├── model/                         # ML model artifacts
├── data/                          # Prediction history logs
├── main.py                        # FastAPI application
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

### Adding New Features

1. Add feature engineering in `prepare_features()`
2. Update model artifacts after retraining
3. Ensure feature columns match trained model

## Troubleshooting

**Model not loading:**
- Verify all `.pkl` files are in `model/` directory
- Check file permissions
- Server will fall back to simulated predictions

**Weather API failures:**
- Service gracefully falls back to simulated weather data
- Check internet connectivity
- Verify Open-Meteo API availability

## License

© 2025 Civitas Engineering Group
