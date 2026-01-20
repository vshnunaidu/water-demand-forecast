"""
Water Demand Forecast API
Backend service for the Civitas Water Demand Forecast App
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import joblib
import httpx
from pathlib import Path
import os

# Initialize FastAPI app
app = FastAPI(
    title="Water Demand Forecast API",
    description="API for predicting water demand in Pearland, TX",
    version="1.0.0"
)

# Timezone for Pearland, TX (Central Time)
# CST = UTC-6, CDT = UTC-5 (we'll use -6 for consistency, or calculate dynamically)
CENTRAL_TIMEZONE = timezone(timedelta(hours=-6))

# Enable CORS for frontend access
# Update this with your Vercel domain after deployment
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will be updated to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model and artifacts
MODEL_DIR = Path(__file__).parent / "model"

try:
    model = joblib.load(MODEL_DIR / "water_forecast_gb_model.pkl")
    scaler = joblib.load(MODEL_DIR / "feature_scaler.pkl")
    feature_columns = joblib.load(MODEL_DIR / "feature_columns.pkl")
    residual_std = joblib.load(MODEL_DIR / "residual_std.pkl")
    historical_data = pd.read_csv(MODEL_DIR / "pearland_merged_data.csv")
    historical_data['Date'] = pd.to_datetime(historical_data['Date'])
    MODEL_LOADED = True
    print("✓ Model and artifacts loaded successfully")
except Exception as e:
    MODEL_LOADED = False
    print(f"⚠ Warning: Could not load model artifacts: {e}")
    print("  Running in demo mode with simulated predictions")

# Pearland, TX coordinates (City Center)
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
    """Determine weather condition and icon based on temperature and precipitation."""
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
    """Get demand level classification and color."""
    if demand < 12:
        return "Low", "#22C55E"
    elif demand < 16:
        return "Moderate", "#EAB308"
    else:
        return "High", "#EF4444"


async def fetch_weather_forecast() -> List[dict]:
    """Fetch 10-day weather forecast from Open-Meteo API."""
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
            print(f"Fetching weather for Pearland ({PEARLAND_LAT}, {PEARLAND_LON})...")
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])
            
            if not dates:
                print("Warning: No dates returned from API, using fallback")
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
            
            print(f"✓ Successfully fetched weather: {weather_data[0]['date']} - {weather_data[0]['temp_max']}°F")
            return weather_data
            
        except httpx.TimeoutException:
            print("Error: Weather API timeout, using fallback")
            return generate_simulated_weather()
        except httpx.HTTPStatusError as e:
            print(f"Error: Weather API returned {e.response.status_code}, using fallback")
            return generate_simulated_weather()
        except Exception as e:
            print(f"Error fetching weather: {type(e).__name__}: {e}")
            return generate_simulated_weather()


def generate_simulated_weather() -> List[dict]:
    """Generate simulated weather data when API is unavailable.
    Based on typical January weather in Pearland, TX.
    """
    today = datetime.now(CENTRAL_TIMEZONE)
    weather_data = []
    
    # Realistic January patterns for Pearland, TX
    # Typical highs: 55-65°F, Lows: 35-50°F
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
    
    print("⚠ Using simulated weather data (API unavailable)")
    return weather_data


def prepare_features(weather_data: List[dict], historical_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare feature dataframe for model prediction."""
    pred_rows = []
    
    for i, weather in enumerate(weather_data):
        date = datetime.strptime(weather["date"], "%Y-%m-%d")
        if date < today:
            continue
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
    """Generate water demand predictions using the trained model."""
    
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
        print(f"Error in prediction: {e}")
        return generate_simulated_predictions(weather_data)


def generate_simulated_predictions(weather_data: List[dict]) -> List[dict]:
    """Generate simulated predictions when model is unavailable."""
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


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Water Demand Forecast API",
        "model_loaded": MODEL_LOADED
    }


@app.get("/api/forecast", response_model=ForecastResponse)
async def get_forecast():
    """Get 10-day water demand forecast."""
    
    weather_data = await fetch_weather_forecast()
    predictions = generate_predictions(weather_data)
    
    # Use Central Time for Pearland, TX (not UTC!)
    today = datetime.now(CENTRAL_TIMEZONE).date()
    forecasts = []
    
    for i, (weather, prediction) in enumerate(zip(weather_data, predictions)):
        date = datetime.strptime(weather["date"], "%Y-%m-%d").date()
        
        # Skip past dates - only include today and future
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
    """Detailed health check."""
    return {
        "status": "healthy",
        "model_loaded": MODEL_LOADED,
        "timestamp": datetime.now(CENTRAL_TIMEZONE).isoformat(),
        "features_count": len(feature_columns) if MODEL_LOADED else 0
    }
