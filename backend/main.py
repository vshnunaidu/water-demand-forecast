"""
Water Demand Forecast API
Backend service for the Civitas Water Demand Forecast App
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import httpx
import joblib
import numpy as np
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.utils.prediction_logger import log_prediction, get_recent_predictions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Water Demand Forecast API",
    description="API for predicting water demand in Pearland, TX",
    version="1.0.0"
)

# Initialize scheduler for daily prediction logging
scheduler = AsyncIOScheduler()

CENTRAL_TIMEZONE = timezone(timedelta(hours=-6))

FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_DIR = Path(__file__).parent / "model"

try:
    model = joblib.load(MODEL_DIR / "water_forecast_gb_model.pkl")
    scaler = joblib.load(MODEL_DIR / "feature_scaler.pkl")
    feature_columns = joblib.load(MODEL_DIR / "feature_columns.pkl")
    residual_std = joblib.load(MODEL_DIR / "residual_std.pkl")
    historical_data = pd.read_csv(MODEL_DIR / "pearland_merged_data.csv")
    historical_data['Date'] = pd.to_datetime(historical_data['Date'])
    MODEL_LOADED = True
    logger.info("Model and artifacts loaded successfully")
except Exception as e:
    MODEL_LOADED = False
    logger.warning(f"Could not load model artifacts: {e}")
    logger.info("Running in demo mode with simulated predictions")

PEARLAND_LAT = 29.5636
PEARLAND_LON = -95.2861


# Response models
class WeatherData(BaseModel):
    date: str
    temp_mean: float
    temp_max: float
    temp_min: float
    precipitation: float
    condition: str
    icon: str


class DayForecast(BaseModel):
    date: str
    day_name: str
    day_number: int
    month: str
    is_today: bool
    demand: float
    lower_bound: float
    upper_bound: float
    demand_level: str
    demand_color: str
    weather: WeatherData
    vs_average: float
    factors: dict


class ForecastResponse(BaseModel):
    forecasts: List[DayForecast]
    last_updated: str
    model_accuracy: dict


def get_weather_condition(temp_max: float, precipitation: float) -> tuple:
    """
    Determine weather condition and icon based on temperature and precipitation.

    Args:
        temp_max: Maximum temperature in Fahrenheit
        precipitation: Precipitation amount in inches

    Returns:
        Tuple of (condition_string, icon_emoji)
    """
    if precipitation > 0.1:
        if precipitation > 0.5:
            return "Rainy", "🌧️"
        return "Showers", "🌦️"
    elif temp_max > 85:
        return "Hot", "☀️"
    elif temp_max > 75:
        return "Warm", "☀️"
    elif temp_max > 65:
        return "Mild", "⛅"
    elif temp_max > 50:
        return "Cool", "☁️"
    else:
        return "Cold", "❄️"


def get_demand_level(demand: float) -> tuple:
    """
    Classify water demand level and assign color.

    Args:
        demand: Predicted water demand in MGD

    Returns:
        Tuple of (level_string, color_hex)
    """
    if demand < 12:
        return "Low", "#22C55E"
    elif demand < 16:
        return "Moderate", "#EAB308"
    else:
        return "High", "#EF4444"


async def fetch_weather_for_date(target_date: datetime) -> dict:
    """
    Fetch weather data for a specific date (historical or forecast).

    Args:
        target_date: The date to get weather for

    Returns:
        Dictionary with temperature and precipitation data for that date
    """
    url = "https://api.open-meteo.com/v1/forecast"
    date_str = target_date.strftime('%Y-%m-%d')

    params = {
        "latitude": PEARLAND_LAT,
        "longitude": PEARLAND_LON,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/Chicago",
        "start_date": date_str,
        "end_date": date_str
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            daily = data.get("daily", {})
            if not daily.get("time"):
                logger.warning(f"No weather data for {date_str}, using fallback")
                return None

            t_max = daily["temperature_2m_max"][0] if daily["temperature_2m_max"][0] is not None else 70
            t_min = daily["temperature_2m_min"][0] if daily["temperature_2m_min"][0] is not None else 55
            p = daily["precipitation_sum"][0] if daily["precipitation_sum"][0] is not None else 0
            condition, icon = get_weather_condition(t_max, p)

            return {
                "date": date_str,
                "temp_max": round(t_max, 1),
                "temp_min": round(t_min, 1),
                "temp_mean": round((t_max + t_min) / 2, 1),
                "precipitation": round(p, 2),
                "condition": condition,
                "icon": icon
            }
        except Exception as e:
            logger.error(f"Error fetching weather for {date_str}: {e}")
            return None


async def fetch_weather_forecast() -> List[dict]:
    """
    Fetch 10-day weather forecast from Open-Meteo API.

    Returns:
        List of dictionaries containing daily weather data including temperature,
        precipitation, and weather conditions. Falls back to simulated data if API fails.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": PEARLAND_LAT,
        "longitude": PEARLAND_LON,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/Chicago",
        "forecast_days": 10
    }
    
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Fetching weather for Pearland ({PEARLAND_LAT}, {PEARLAND_LON})")
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            daily = data.get("daily", {})
            dates = daily.get("time", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])

            if not dates:
                logger.warning("No dates returned from API, using fallback")
                return generate_simulated_weather()
            
            weather_data = []
            for i in range(len(dates)):
                t_max = temp_max[i] if i < len(temp_max) and temp_max[i] is not None else 70
                t_min = temp_min[i] if i < len(temp_min) and temp_min[i] is not None else 55
                p = precip[i] if i < len(precip) and precip[i] is not None else 0
                condition, icon = get_weather_condition(t_max, p)
                
                weather_data.append({
                    "date": dates[i],
                    "temp_max": round(t_max, 1),
                    "temp_min": round(t_min, 1),
                    "temp_mean": round((t_max + t_min) / 2, 1),
                    "precipitation": round(p, 2),
                    "condition": condition,
                    "icon": icon
                })
            
            logger.info(f"Successfully fetched weather: {weather_data[0]['date']} - {weather_data[0]['temp_max']}°F")
            return weather_data

        except httpx.TimeoutException:
            logger.warning("Weather API timeout, using fallback")
            return generate_simulated_weather()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Weather API returned {e.response.status_code}, using fallback")
            return generate_simulated_weather()
        except Exception as e:
            logger.error(f"Error fetching weather: {type(e).__name__}: {e}")
            return generate_simulated_weather()


def generate_simulated_weather() -> List[dict]:
    """
    Generate simulated weather data when API is unavailable.

    Returns:
        List of 10 days of simulated weather based on typical Pearland, TX patterns
    """
    today = datetime.now(CENTRAL_TIMEZONE)
    weather_data = []

    patterns = [
        (58, 35, 0.0, "Cool", "☁️"),
        (68, 45, 0.0, "Mild", "⛅"),
        (62, 42, 0.0, "Cool", "☁️"),
        (55, 38, 0.1, "Showers", "🌦️"),
        (58, 33, 0.0, "Cool", "☁️"),
        (66, 39, 0.0, "Mild", "⛅"),
        (70, 48, 0.0, "Mild", "☀️"),
        (65, 45, 0.2, "Showers", "🌧️"),
        (55, 40, 0.0, "Cool", "☁️"),
        (60, 42, 0.0, "Cool", "⛅"),
    ]
    
    for i, (t_max, t_min, precip, condition, icon) in enumerate(patterns):
        date = today + timedelta(days=i)
        weather_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "temp_max": t_max,
            "temp_min": t_min,
            "temp_mean": (t_max + t_min) / 2,
            "precipitation": precip,
            "condition": condition,
            "icon": icon
        })
    
    logger.warning("Using simulated weather data (API unavailable)")
    return weather_data


def prepare_features(weather_data: List[dict], historical_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare feature dataframe for model prediction.

    Args:
        weather_data: List of weather forecast dictionaries
        historical_df: Historical water production data

    Returns:
        DataFrame with engineered features for model input
    """
    pred_rows = []

    for i, weather in enumerate(weather_data):
        date = datetime.strptime(weather["date"], "%Y-%m-%d")
        row = {
            "Date": date,
            "temp_mean": weather["temp_mean"],
            "temp_max": weather["temp_max"],
            "temp_min": weather["temp_min"],
            "precip_total": weather["precipitation"],
            "day_of_week": date.weekday(),
            "month": date.month,
            "is_weekend": 1 if date.weekday() >= 5 else 0,
        }
        pred_rows.append(row)
    
    pred_df = pd.DataFrame(pred_rows)
    
    avg_production = historical_df['Production_MG'].mean()
    recent_avg = historical_df['Production_MG'].tail(7).mean()
    recent_std = historical_df['Production_MG'].tail(14).std()
    
    pred_df['prod_lag1'] = recent_avg
    pred_df['prod_lag2'] = recent_avg
    pred_df['prod_lag3'] = recent_avg
    pred_df['prod_lag7'] = recent_avg
    pred_df['prod_lag14'] = avg_production
    pred_df['prod_lag30'] = avg_production
    
    pred_df['prod_rolling_mean_3'] = recent_avg
    pred_df['prod_rolling_mean_7'] = recent_avg
    pred_df['prod_rolling_mean_14'] = avg_production
    pred_df['prod_rolling_mean_30'] = avg_production
    pred_df['prod_rolling_std_7'] = recent_std
    pred_df['prod_rolling_std_14'] = recent_std
    
    pred_df['temp_rolling_mean_7'] = pred_df['temp_max'].rolling(7, min_periods=1).mean()
    pred_df['temp_rolling_mean_14'] = pred_df['temp_max'].rolling(14, min_periods=1).mean()
    
    pred_df['temp_rolling_mean_7'] = pred_df['temp_rolling_mean_7'].fillna(pred_df['temp_max'])
    pred_df['temp_rolling_mean_14'] = pred_df['temp_rolling_mean_14'].fillna(pred_df['temp_max'])
    
    pred_df['day_sin'] = np.sin(2 * np.pi * pred_df['Date'].dt.dayofyear / 365)
    pred_df['day_cos'] = np.cos(2 * np.pi * pred_df['Date'].dt.dayofyear / 365)
    pred_df['dow_sin'] = np.sin(2 * np.pi * pred_df['day_of_week'] / 7)
    pred_df['dow_cos'] = np.cos(2 * np.pi * pred_df['day_of_week'] / 7)
    
    return pred_df


def generate_predictions(weather_data: List[dict]) -> List[dict]:
    """
    Generate water demand predictions using the trained model.

    Args:
        weather_data: List of weather forecast dictionaries

    Returns:
        List of prediction dictionaries with demand, bounds, and comparison to average
    """
    if not MODEL_LOADED:
        return generate_simulated_predictions(weather_data)
    
    try:
        pred_df = prepare_features(weather_data, historical_data)
        X = pred_df[feature_columns]
        X_scaled = scaler.transform(X)
        predictions = model.predict(X_scaled)
        
        results = []
        avg_production = historical_data['Production_MG'].mean()
        
        for i, (pred, weather) in enumerate(zip(predictions, weather_data)):
            pred = max(4.0, min(40.0, pred))
            lower = pred - 1.28 * residual_std
            upper = pred + 1.28 * residual_std
            vs_avg = round((pred / avg_production - 1) * 100)
            
            results.append({
                "demand": round(pred, 2),
                "lower_bound": round(max(0, lower), 2),
                "upper_bound": round(upper, 2),
                "vs_average": vs_avg
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error in prediction: {e}")
        return generate_simulated_predictions(weather_data)


def generate_simulated_predictions(weather_data: List[dict]) -> List[dict]:
    """
    Generate simulated predictions when model is unavailable.

    Args:
        weather_data: List of weather forecast dictionaries

    Returns:
        List of simulated prediction dictionaries
    """
    results = []
    avg_production = 13.9

    for weather in weather_data:
        date = datetime.strptime(weather["date"], "%Y-%m-%d")

        base_demand = 12.5
        temp_effect = (weather["temp_max"] - 65) * 0.12
        precip_effect = -2.0 if weather["precipitation"] > 0.1 else 0
        weekend_effect = 0.5 if date.weekday() >= 5 else 0

        demand = base_demand + temp_effect + precip_effect + weekend_effect
        demand = max(8.0, min(25.0, demand))

        lower = demand - 1.5
        upper = demand + 1.5
        vs_avg = round((demand / avg_production - 1) * 100)

        results.append({
            "demand": round(demand, 2),
            "lower_bound": round(max(0, lower), 2),
            "upper_bound": round(upper, 2),
            "vs_average": vs_avg
        })

    return results


async def generate_prediction_for_date(date_str: str) -> dict:
    """
    Generate a water demand prediction for a specific past date.

    Args:
        date_str: Date in ISO format (YYYY-MM-DD)

    Returns:
        Dictionary with prediction, confidence intervals, and demand level
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")

        # Get weather data for that specific date
        weather_data = await fetch_weather_for_date(target_date)

        if not weather_data:
            # Fallback to simulated weather if API fails
            logger.warning(f"Using simulated weather for {date_str}")
            weather_data = {
                "date": date_str,
                "temp_max": 70,
                "temp_min": 55,
                "temp_mean": 62.5,
                "precipitation": 0.0,
                "condition": "Mild",
                "icon": "⛅"
            }

        # Generate prediction using the model
        if MODEL_LOADED:
            try:
                pred_df = prepare_features([weather_data], historical_data)
                X = pred_df[feature_columns]
                X_scaled = scaler.transform(X)
                predicted_demand = model.predict(X_scaled)[0]

                # Apply bounds
                predicted_demand = max(4.0, min(40.0, predicted_demand))

                # Calculate confidence intervals
                confidence_lower = predicted_demand - 1.28 * residual_std
                confidence_upper = predicted_demand + 1.28 * residual_std

            except Exception as e:
                logger.error(f"Model prediction failed for {date_str}: {e}")
                # Fall back to simulated prediction
                predicted_demand = generate_simulated_predictions([weather_data])[0]["demand"]
                confidence_lower = predicted_demand - 1.5
                confidence_upper = predicted_demand + 1.5
        else:
            # Use simulated prediction
            simulated = generate_simulated_predictions([weather_data])[0]
            predicted_demand = simulated["demand"]
            confidence_lower = simulated["lower_bound"]
            confidence_upper = simulated["upper_bound"]

        # Determine demand level
        demand_level, _ = get_demand_level(predicted_demand)

        return {
            "date": date_str,
            "predicted_demand": float(round(predicted_demand, 2)),
            "confidence_lower": float(round(max(0, confidence_lower), 2)),
            "confidence_upper": float(round(confidence_upper, 2)),
            "demand_level": demand_level.upper()
        }

    except Exception as e:
        logger.error(f"Error generating prediction for {date_str}: {e}")
        # Return a fallback prediction if generation fails
        return {
            "date": date_str,
            "predicted_demand": 0.0,
            "confidence_lower": 0.0,
            "confidence_upper": 0.0,
            "demand_level": "UNKNOWN"
        }


async def log_daily_prediction():
    """
    Scheduled task to automatically log today's prediction at midnight.

    This runs daily at 12:01 AM Central Time to ensure we have a prediction
    logged for each day, regardless of whether the application is accessed.
    """
    try:
        today = datetime.now(CENTRAL_TIMEZONE).date()
        date_str = today.isoformat()

        logger.info(f"Running scheduled prediction logging for {date_str}")

        # Fetch weather data for today
        weather_data = await fetch_weather_for_date(datetime.combine(today, datetime.min.time()))

        if not weather_data:
            logger.warning(f"Could not fetch weather for {date_str}, using fallback")
            weather_data = {
                "date": date_str,
                "temp_max": 70,
                "temp_min": 55,
                "temp_mean": 62.5,
                "precipitation": 0.0,
                "condition": "Mild",
                "icon": "⛅"
            }

        # Generate prediction
        if MODEL_LOADED:
            try:
                pred_df = prepare_features([weather_data], historical_data)
                X = pred_df[feature_columns]
                X_scaled = scaler.transform(X)
                predicted_demand = model.predict(X_scaled)[0]
                predicted_demand = max(4.0, min(40.0, predicted_demand))

                confidence_lower = predicted_demand - 1.28 * residual_std
                confidence_upper = predicted_demand + 1.28 * residual_std
            except Exception as e:
                logger.error(f"Model prediction failed in scheduled task: {e}")
                simulated = generate_simulated_predictions([weather_data])[0]
                predicted_demand = simulated["demand"]
                confidence_lower = simulated["lower_bound"]
                confidence_upper = simulated["upper_bound"]
        else:
            simulated = generate_simulated_predictions([weather_data])[0]
            predicted_demand = simulated["demand"]
            confidence_lower = simulated["lower_bound"]
            confidence_upper = simulated["upper_bound"]

        # Determine demand level
        demand_level, _ = get_demand_level(predicted_demand)

        # Log the prediction
        log_prediction(
            prediction_date=date_str,
            predicted_demand=round(predicted_demand, 2),
            confidence_lower=round(max(0, confidence_lower), 2),
            confidence_upper=round(confidence_upper, 2),
            demand_level=demand_level
        )

        logger.info(f"Successfully logged scheduled prediction for {date_str}: {predicted_demand:.2f} MGD")

    except Exception as e:
        logger.error(f"Error in scheduled prediction logging: {e}")


@app.on_event("startup")
async def startup_event():
    """
    Initialize scheduler when the application starts.

    Sets up daily prediction logging at 12:01 AM Central Time.
    """
    # Schedule daily prediction logging at 12:01 AM Central Time
    scheduler.add_job(
        log_daily_prediction,
        trigger=CronTrigger(hour=0, minute=1, timezone="America/Chicago"),
        id="daily_prediction_log",
        name="Log daily water demand prediction",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started - daily prediction logging enabled at 12:01 AM CT")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Gracefully shutdown the scheduler when the application stops.
    """
    scheduler.shutdown()
    logger.info("Scheduler shutdown complete")


@app.get("/")
async def root():
    """
    Root health check endpoint.

    Returns:
        Dict containing service status and model availability
    """
    return {
        "status": "online",
        "service": "Water Demand Forecast API",
        "model_loaded": MODEL_LOADED
    }


@app.get("/api/forecast", response_model=ForecastResponse)
async def get_forecast():
    """
    Generate 10-day water demand forecast for Pearland, TX.

    Returns:
        ForecastResponse containing daily forecasts with weather data and demand predictions
    """
    weather_data = await fetch_weather_forecast()
    predictions = generate_predictions(weather_data)

    today = datetime.now(CENTRAL_TIMEZONE).date()
    forecasts = []
    today_forecast = None

    for i, (weather, prediction) in enumerate(zip(weather_data, predictions)):
        date = datetime.strptime(weather["date"], "%Y-%m-%d").date()

        if date < today:
            continue

        is_today = date == today

        demand_level, demand_color = get_demand_level(prediction["demand"])

        factors = {
            "temperature": "high" if weather["temp_max"] > 75 else ("low" if weather["temp_max"] < 60 else "moderate"),
            "precipitation": "yes" if weather["precipitation"] > 0.05 else "no",
            "day_type": "weekend" if date.weekday() >= 5 else "weekday"
        }

        forecast = DayForecast(
            date=weather["date"],
            day_name="TODAY" if is_today else datetime.strptime(weather["date"], "%Y-%m-%d").strftime("%a").upper(),
            day_number=date.day,
            month=datetime.strptime(weather["date"], "%Y-%m-%d").strftime("%b"),
            is_today=is_today,
            demand=prediction["demand"],
            lower_bound=prediction["lower_bound"],
            upper_bound=prediction["upper_bound"],
            demand_level=demand_level,
            demand_color=demand_color,
            weather=WeatherData(
                date=weather["date"],
                temp_mean=weather["temp_mean"],
                temp_max=weather["temp_max"],
                temp_min=weather["temp_min"],
                precipitation=weather["precipitation"],
                condition=weather["condition"],
                icon=weather["icon"]
            ),
            vs_average=prediction["vs_average"],
            factors=factors
        )
        forecasts.append(forecast)

        if is_today:
            today_forecast = forecast

    # Log today's prediction for historical tracking
    if today_forecast:
        try:
            log_prediction(
                prediction_date=today_forecast.date,
                predicted_demand=today_forecast.demand,
                confidence_lower=today_forecast.lower_bound,
                confidence_upper=today_forecast.upper_bound,
                demand_level=today_forecast.demand_level
            )
            logger.info(f"Logged prediction for {today_forecast.date}: {today_forecast.demand} MGD")
        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")

    return ForecastResponse(
        forecasts=forecasts,
        last_updated=datetime.now(CENTRAL_TIMEZONE).isoformat(),
        model_accuracy={
            "r_squared": 0.94 if MODEL_LOADED else None,
            "mape_percent": 3.29 if MODEL_LOADED else None,
            "confidence_interval": "80%",
            "model_type": "Gradient Boosting" if MODEL_LOADED else "Simulated"
        }
    )


@app.get("/api/health")
async def health_check():
    """
    Detailed health check endpoint.

    Returns:
        Dict containing service health status and model information
    """
    return {
        "status": "healthy",
        "model_loaded": MODEL_LOADED,
        "timestamp": datetime.now(CENTRAL_TIMEZONE).isoformat(),
        "features_count": len(feature_columns) if MODEL_LOADED else 0
    }


@app.get("/api/recent-predictions")
async def get_recent_predictions_endpoint():
    """
    Get the last 5 days of predictions, auto-generating any missing days.

    This endpoint returns a complete 5-day prediction history by:
    1. Identifying the last 5 calendar days (yesterday through 5 days ago)
    2. Using logged predictions when available
    3. Auto-generating predictions for any missing days using historical weather data

    Returns:
        Dict containing list of 5 consecutive daily predictions with dates, demands, and confidence intervals
    """
    try:
        # Get the last 5 calendar days (excluding today, going back from yesterday)
        today = datetime.now(CENTRAL_TIMEZONE).date()
        last_5_days = [(today - timedelta(days=i)).isoformat() for i in range(1, 6)]

        # Get any existing logged predictions
        existing_predictions = get_recent_predictions(days=5)
        existing_dict = {pred['prediction_date']: pred for pred in existing_predictions}

        # Build complete 5-day list
        complete_predictions = []

        for date_str in last_5_days:
            if date_str in existing_dict:
                # Use existing logged prediction
                pred = existing_dict[date_str]
                complete_predictions.append({
                    "date": pred['prediction_date'],
                    "predicted_demand": float(pred['predicted_demand']),
                    "confidence_lower": float(pred['confidence_lower']),
                    "confidence_upper": float(pred['confidence_upper']),
                    "demand_level": pred['demand_level']
                })
                logger.info(f"Using logged prediction for {date_str}")
            else:
                # Generate prediction for this missing day
                logger.info(f"Auto-generating prediction for missing day: {date_str}")
                prediction = await generate_prediction_for_date(date_str)
                complete_predictions.append(prediction)

        return {
            "predictions": complete_predictions,
            "count": len(complete_predictions)
        }

    except Exception as e:
        logger.error(f"Error getting recent predictions: {e}")
        return {
            "predictions": [],
            "count": 0
        }


@app.post("/api/trigger-daily-log")
async def trigger_daily_log():
    """
    Manual trigger for daily prediction logging (for testing purposes).

    This endpoint allows you to manually trigger the daily prediction logging
    function without waiting for the scheduled time (12:01 AM).

    Returns:
        Dict containing status of the logging operation
    """
    try:
        await log_daily_prediction()
        return {
            "status": "success",
            "message": "Daily prediction logged successfully",
            "timestamp": datetime.now(CENTRAL_TIMEZONE).isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering daily log: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(CENTRAL_TIMEZONE).isoformat()
        }
