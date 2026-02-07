import React, { useState, useEffect } from 'react';

// Civitas brand colors extracted from logo
const COLORS = {
  primary: '#4A0E78',
  primaryLight: '#6B1FA3', 
  primaryDark: '#2D0849',
  accent: '#F5A623',
  success: '#22C55E',
  warning: '#EAB308',
  danger: '#EF4444',
  white: '#FFFFFF',
  gray100: '#F8F9FA',
  gray200: '#E9ECEF',
  gray300: '#DEE2E6',
  gray600: '#6C757D',
  gray800: '#343A40',
};

// API Configuration - Uses environment variable in production
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Civitas Logo Component - Using official Civitas logo image
const CivitasLogo = () => (
  <div style={logoStyles.container}>
    <img
      src={`${process.env.PUBLIC_URL}/Civitas_New Logo.png`}
      alt="Civitas Engineering Group"
      style={logoStyles.image}
      onError={(e) => {
        // Fallback if logo file is not found
        e.target.style.display = 'none';
        e.target.parentElement.innerHTML = `
          <div style="display: flex; flex-direction: column; align-items: flex-start;">
            <svg width="95" height="36" viewBox="0 0 95 36" fill="none">
              <path d="M18 14 Q47.5 2 77 14" stroke="white" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
              <text x="47.5" y="28" text-anchor="middle" fill="white" font-family="Arial, Helvetica, sans-serif" font-size="17" font-weight="bold" letter-spacing="2.5">CIVITAS</text>
            </svg>
            <span style="color: rgba(255,255,255,0.65); font-size: 7px; letter-spacing: 1.8px; margin-top: 1px; margin-left: 8px; font-family: Arial, Helvetica, sans-serif;">ENGINEERING GROUP</span>
          </div>
        `;
      }}
    />
  </div>
);

const logoStyles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
  },
  image: {
    height: '50px',
    width: 'auto',
    objectFit: 'contain',
    filter: 'brightness(0) invert(1)', // Makes purple logo appear white
  },
};

// Get demand level and color
const getDemandLevel = (demand) => {
  if (demand < 14) return { level: 'Low', color: COLORS.success, bg: 'rgba(34, 197, 94, 0.15)' };
  if (demand >= 14 && demand < 18) return { level: 'Moderate', color: COLORS.warning, bg: 'rgba(234, 179, 8, 0.15)' };
  return { level: 'High', color: COLORS.danger, bg: 'rgba(239, 68, 68, 0.15)' };
};

// Hourly demand data generator
const generateHourlyData = (dailyDemand) => {
  // Typical residential water usage pattern percentages
  const hourlyPattern = [
    0.020, 0.015, 0.012, 0.010, 0.012, 0.025,  // 12am-5am (low overnight)
    0.045, 0.065, 0.070, 0.060,                 // 6am-9am (morning peak)
    0.050, 0.048, 0.052, 0.048, 0.045, 0.048,  // 10am-3pm (midday)
    0.055, 0.065, 0.070, 0.062,                 // 4pm-7pm (evening peak)
    0.052, 0.042, 0.035, 0.027                  // 8pm-11pm (declining)
  ];
  
  return hourlyPattern.map((pct, hour) => ({
    hour,
    value: dailyDemand * pct * 24, // Convert to hourly rate
    label: hour % 6 === 0 ? `${hour === 0 ? '12' : hour > 12 ? hour - 12 : hour}${hour < 12 ? 'AM' : 'PM'}` : '',
  }));
};

// Beautiful SVG Area Chart Component
const HourlyDemandChart = ({ dailyDemand, color }) => {
  const data = generateHourlyData(dailyDemand);
  const maxValue = Math.max(...data.map(d => d.value));
  const minValue = Math.min(...data.map(d => d.value));
  
  // Chart dimensions
  const width = 320;
  const height = 140;
  const padding = { top: 20, right: 15, bottom: 35, left: 45 }; // Increased left padding for Y-axis
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  
  // Scale functions
  const xScale = (index) => padding.left + (index / 23) * chartWidth;
  const yScale = (value) => padding.top + chartHeight - ((value - minValue * 0.8) / (maxValue - minValue * 0.8)) * chartHeight;
  
  // Generate smooth curve path using cardinal spline
  const generateSmoothPath = (points, closed = false) => {
    if (points.length < 2) return '';
    
    const tension = 0.3;
    let path = `M ${points[0].x} ${points[0].y}`;
    
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i === 0 ? i : i - 1];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = points[i + 2 >= points.length ? i + 1 : i + 2];
      
      const cp1x = p1.x + (p2.x - p0.x) * tension;
      const cp1y = p1.y + (p2.y - p0.y) * tension;
      const cp2x = p2.x - (p3.x - p1.x) * tension;
      const cp2y = p2.y - (p3.y - p1.y) * tension;
      
      path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
    }
    
    if (closed) {
      path += ` L ${points[points.length - 1].x} ${height - padding.bottom}`;
      path += ` L ${points[0].x} ${height - padding.bottom}`;
      path += ' Z';
    }
    
    return path;
  };
  
  // Create points array
  const points = data.map((d, i) => ({
    x: xScale(i),
    y: yScale(d.value),
  }));
  
  // Find peak hours for highlighting
  const morningPeakStart = 6;
  const morningPeakEnd = 9;
  const eveningPeakStart = 17;
  const eveningPeakEnd = 20;
  
  // Gradient ID
  const gradientId = `areaGradient-${color.replace('#', '')}`;
  
  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: width }}>
        <defs>
          {/* Area gradient */}
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.4" />
            <stop offset="100%" stopColor={color} stopOpacity="0.05" />
          </linearGradient>
          
          {/* Glow filter for the line */}
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Y-axis */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={height - padding.bottom}
          stroke={COLORS.gray300}
          strokeWidth="2"
        />

        {/* Y-axis ticks and labels */}
        {(() => {
          const yMax = Math.ceil(maxValue / 5) * 5; // Round up to nearest 5
          const yMin = 0;
          const tickCount = 6; // 0, 5, 10, 15, 20, 25 (or scaled appropriately)
          const ticks = [];
          for (let i = 0; i <= tickCount; i++) {
            const value = yMin + (yMax - yMin) * (i / tickCount);
            const y = padding.top + chartHeight - (value / yMax) * chartHeight;
            ticks.push(
              <g key={i}>
                <line
                  x1={padding.left - 4}
                  y1={y}
                  x2={padding.left}
                  y2={y}
                  stroke={COLORS.gray300}
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={y}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fill={COLORS.gray600}
                  fontSize="9"
                  fontWeight="500"
                >
                  {value.toFixed(0)}
                </text>
              </g>
            );
          }
          return ticks;
        })()}

        {/* Y-axis label (rotated) */}
        <text
          x={12}
          y={padding.top + chartHeight / 2}
          textAnchor="middle"
          fill={COLORS.gray600}
          fontSize="10"
          fontWeight="600"
          transform={`rotate(-90, 12, ${padding.top + chartHeight / 2})`}
        >
          Water Demand (MGD)
        </text>

        {/* Background grid lines */}
        {[0.25, 0.5, 0.75].map((pct, i) => (
          <line
            key={i}
            x1={padding.left}
            y1={padding.top + chartHeight * pct}
            x2={width - padding.right}
            y2={padding.top + chartHeight * pct}
            stroke={COLORS.gray200}
            strokeWidth="1"
            strokeDasharray="4,4"
          />
        ))}
        
        {/* Peak hour highlighting */}
        <rect
          x={xScale(morningPeakStart)}
          y={padding.top}
          width={xScale(morningPeakEnd) - xScale(morningPeakStart)}
          height={chartHeight}
          fill={color}
          opacity="0.08"
          rx="4"
        />
        <rect
          x={xScale(eveningPeakStart)}
          y={padding.top}
          width={xScale(eveningPeakEnd) - xScale(eveningPeakStart)}
          height={chartHeight}
          fill={color}
          opacity="0.08"
          rx="4"
        />
        
        {/* Area fill */}
        <path
          d={generateSmoothPath(points, true)}
          fill={`url(#${gradientId})`}
        />
        
        {/* Main line */}
        <path
          d={generateSmoothPath(points)}
          fill="none"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#glow)"
        />
        
        {/* Peak indicators */}
        {[7, 18].map((peakHour) => {
          const peakPoint = points[peakHour];
          const peakValue = data[peakHour].value;
          return (
            <g key={peakHour}>
              <circle
                cx={peakPoint.x}
                cy={peakPoint.y}
                r="5"
                fill={COLORS.white}
                stroke={color}
                strokeWidth="2.5"
              />
              <text
                x={peakPoint.x}
                y={peakPoint.y - 10}
                textAnchor="middle"
                fill={color}
                fontSize="9"
                fontWeight="600"
              >
                {peakValue.toFixed(1)}
              </text>
            </g>
          );
        })}
        
        {/* X-axis labels */}
        {data.map((d, i) => (
          d.label && (
            <text
              key={i}
              x={xScale(i)}
              y={height - padding.bottom + 18}
              textAnchor="middle"
              fill={COLORS.gray600}
              fontSize="10"
              fontWeight="500"
            >
              {d.label}
            </text>
          )
        ))}
        
        {/* Axis line */}
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          stroke={COLORS.gray300}
          strokeWidth="1"
        />
      </svg>
      
      {/* Legend */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: '24px',
        marginTop: '12px',
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{
            width: '12px',
            height: '12px',
            borderRadius: '3px',
            backgroundColor: color,
            opacity: 0.2,
          }} />
          <span style={{ fontSize: '11px', color: COLORS.gray600 }}>Peak Hours</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: COLORS.white,
            border: `2px solid ${color}`,
          }} />
          <span style={{ fontSize: '11px', color: COLORS.gray600 }}>Peak Demand</span>
        </div>
      </div>
    </div>
  );
};

// Fallback data generator when API is unavailable
const generateFallbackForecast = () => {
  const today = new Date();
  const forecasts = [];
  
  const weatherPatterns = [
    { icon: '☀️', condition: 'Sunny', temp_max: 72, temp_min: 58, precipitation: 0 },
    { icon: '⛅', condition: 'Partly Cloudy', temp_max: 68, temp_min: 55, precipitation: 0 },
    { icon: '☁️', condition: 'Cloudy', temp_max: 65, temp_min: 52, precipitation: 0 },
    { icon: '🌧️', condition: 'Rainy', temp_max: 62, temp_min: 50, precipitation: 0.3 },
    { icon: '☀️', condition: 'Sunny', temp_max: 75, temp_min: 60, precipitation: 0 },
    { icon: '☀️', condition: 'Hot', temp_max: 85, temp_min: 68, precipitation: 0 },
    { icon: '⛅', condition: 'Warm', temp_max: 78, temp_min: 62, precipitation: 0 },
    { icon: '🌧️', condition: 'Showers', temp_max: 64, temp_min: 52, precipitation: 0.2 },
    { icon: '☀️', condition: 'Clear', temp_max: 70, temp_min: 55, precipitation: 0 },
    { icon: '⛅', condition: 'Mild', temp_max: 72, temp_min: 58, precipitation: 0 },
  ];

  for (let i = 0; i < 10; i++) {
    const date = new Date(today);
    date.setDate(date.getDate() + i);
    const weather = weatherPatterns[i];
    
    let baseDemand = 12 + (weather.temp_max - 65) * 0.15;
    if (weather.precipitation > 0.1) baseDemand *= 0.85;
    if (date.getDay() === 0 || date.getDay() === 6) baseDemand *= 1.05;
    
    const demand = Math.round(baseDemand * 100) / 100;
    const { level, color } = getDemandLevel(demand);
    
    forecasts.push({
      date: date.toISOString().split('T')[0],
      day_name: i === 0 ? 'TODAY' : date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase(),
      day_number: date.getDate(),
      month: date.toLocaleDateString('en-US', { month: 'short' }),
      is_today: i === 0,
      demand,
      lower_bound: Math.round((demand - 1.2) * 100) / 100,
      upper_bound: Math.round((demand + 1.2) * 100) / 100,
      demand_level: level,
      demand_color: color,
      weather: {
        ...weather,
        temp_mean: (weather.temp_max + weather.temp_min) / 2,
      },
      vs_average: Math.round((demand / 13.9 - 1) * 100),
      factors: {
        temperature: weather.temp_max > 75 ? 'high' : weather.temp_max < 65 ? 'low' : 'moderate',
        precipitation: weather.precipitation > 0.05 ? 'yes' : 'no',
        day_type: date.getDay() === 0 || date.getDay() === 6 ? 'weekend' : 'weekday',
      },
    });
  }
  
  return { forecasts, last_updated: new Date().toISOString(), model_accuracy: { model_type: 'Demo Mode' } };
};

// Main App Component
export default function WaterDemandForecastApp() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDay, setSelectedDay] = useState(null);
  const [showDetail, setShowDetail] = useState(false);

  const fetchForecast = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/forecast`);
      if (!response.ok) throw new Error('API unavailable');
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      console.log('Using fallback data:', err.message);
      setData(generateFallbackForecast());
      setError('Using demo data - backend not connected');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecast();
    const interval = setInterval(fetchForecast, 6 * 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleDayClick = (forecast) => {
    setSelectedDay(forecast);
    setShowDetail(true);
  };

  const handleBack = () => {
    setShowDetail(false);
    setTimeout(() => setSelectedDay(null), 300);
  };

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.loadingSpinner} />
        <p style={styles.loadingText}>Loading forecast...</p>
      </div>
    );
  }

  const forecasts = data?.forecasts || [];
  // Find the forecast marked as today, or fall back to first item
  const todayForecast = forecasts.find(f => f.is_today) || forecasts[0];
  const todayLevel = todayForecast ? getDemandLevel(todayForecast.demand) : null;

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <CivitasLogo />
          <div style={styles.headerTitle}>
            <h1 style={styles.appTitle}>City of Pearland</h1>
            <p style={styles.appSubtitle}>Daily Water Demand Forecast</p>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div style={styles.errorBanner}>
          <span style={styles.errorText}>{error}</span>
        </div>
      )}

      {/* Main Content */}
      <main style={styles.main}>
        {!showDetail ? (
          <>
            {/* Today's Forecast Card */}
            {todayForecast && (
              <div 
                style={styles.todayCard}
                onClick={() => handleDayClick(todayForecast)}
              >
                <div style={styles.todayHeader}>
                  <span style={styles.todayLabel}>TODAY</span>
                  <span style={styles.todayDate}>
                    {(() => {
                      // Parse date parts manually to avoid timezone issues
                      const [year, month, day] = todayForecast.date.split('-').map(Number);
                      const date = new Date(year, month - 1, day); // month is 0-indexed
                      return date.toLocaleDateString('en-US', { 
                        weekday: 'long', 
                        month: 'long', 
                        day: 'numeric' 
                      });
                    })()}
                  </span>
                </div>
                
                <div style={styles.todayContent}>
                  <div style={styles.weatherInfo}>
                    <span style={styles.weatherLabel}>Max Temp</span>
                    <span style={styles.weatherTemp}>{Math.round(todayForecast.weather.temp_max)}°F</span>
                    <span style={styles.weatherIcon}>{todayForecast.weather.icon}</span>
                  </div>
                  
                  <div style={styles.demandDisplay}>
                    <div
                      style={{
                        ...styles.demandIndicator,
                        backgroundColor: todayLevel.bg,
                        borderColor: todayLevel.color,
                      }}
                    >
                      <span style={{...styles.demandDot, backgroundColor: todayLevel.color}} />
                    </div>
                    <div style={styles.demandValue}>
                      <span style={styles.demandNumber}>{todayForecast.demand.toFixed(1)}</span>
                      <span style={styles.demandUnit}>MGD</span>
                    </div>
                    <span style={styles.demandSubtext}>Million Gallons per Day Expected</span>
                  </div>
                </div>
                
                <div style={styles.todayFooter}>
                  <span style={styles.tapHint}>Tap for detailed breakdown →</span>
                </div>
              </div>
            )}

            {/* 10-Day Forecast */}
            <div style={styles.forecastSection}>
              <h2 style={styles.sectionTitle}>10-Day Forecast</h2>
              <div style={styles.forecastScroll}>
                {forecasts.map((forecast, index) => {
                  const level = getDemandLevel(forecast.demand);
                  return (
                    <div
                      key={index}
                      style={{
                        ...styles.forecastCard,
                        ...(forecast.is_today ? styles.forecastCardToday : {}),
                      }}
                      onClick={() => handleDayClick(forecast)}
                    >
                      <span style={{
                        ...styles.forecastDay,
                        color: forecast.is_today ? 'rgba(255,255,255,0.9)' : COLORS.gray600
                      }}>
                        {forecast.day_name}
                      </span>
                      <span style={{
                        ...styles.forecastDate,
                        color: forecast.is_today ? COLORS.white : COLORS.gray800
                      }}>
                        {forecast.day_number}
                      </span>
                      <span style={styles.forecastWeather}>{forecast.weather.icon}</span>
                      <span style={{
                        ...styles.forecastTemp,
                        color: forecast.is_today ? 'rgba(255,255,255,0.8)' : COLORS.gray600
                      }}>
                        {Math.round(forecast.weather.temp_max)}°
                      </span>
                      <div style={{
                        ...styles.forecastDemandDot, 
                        backgroundColor: level.color,
                        boxShadow: forecast.is_today ? `0 0 8px ${level.color}` : 'none'
                      }} />
                      <span style={{
                        ...styles.forecastDemand,
                        color: forecast.is_today ? COLORS.white : COLORS.gray800
                      }}>
                        {forecast.demand.toFixed(1)}
                      </span>
                      <span style={{
                        ...styles.forecastDemandUnit,
                        color: forecast.is_today ? 'rgba(255,255,255,0.7)' : COLORS.gray600
                      }}>
                        MGD
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Legend */}
            <div style={styles.legend}>
              <div style={styles.legendItem}>
                <div style={{...styles.legendDot, backgroundColor: COLORS.success}} />
                <span style={styles.legendText}>Low (&lt;14 MGD)</span>
              </div>
              <div style={styles.legendItem}>
                <div style={{...styles.legendDot, backgroundColor: COLORS.warning}} />
                <span style={styles.legendText}>Moderate (14-18 MGD)</span>
              </div>
              <div style={styles.legendItem}>
                <div style={{...styles.legendDot, backgroundColor: COLORS.danger}} />
                <span style={styles.legendText}>High (&gt;18 MGD)</span>
              </div>
            </div>

            {/* Model Info & Last Updated */}
            <div style={styles.updateInfo}>
              <span style={styles.updateText}>
                Last updated: {data?.last_updated 
                  ? new Date(data.last_updated).toLocaleTimeString('en-US', { 
                      hour: 'numeric', 
                      minute: '2-digit',
                      hour12: true 
                    })
                  : 'Unknown'}
              </span>
              {data?.model_accuracy?.r_squared && (
                <span style={styles.modelInfo}>
                  Model accuracy: {(data.model_accuracy.r_squared * 100).toFixed(0)}% R²
                </span>
              )}
              <span style={styles.updateNote}>Updates every 6 hours</span>
            </div>

            {/* Refresh Button */}
            <button style={styles.refreshButton} onClick={fetchForecast}>
              ↻ Refresh Forecast
            </button>
          </>
        ) : selectedDay && (
          <DetailView 
            forecast={selectedDay} 
            onBack={handleBack}
          />
        )}
      </main>

      {/* Footer */}
      <footer style={styles.footer}>
        <span style={styles.footerText}>© 2025 Civitas Engineering Group • Pearland, TX</span>
      </footer>
    </div>
  );
}

// Detail View Component
function DetailView({ forecast, onBack }) {
  const level = getDemandLevel(forecast.demand);

  return (
    <div style={styles.detailContainer}>
      {/* Back Button */}
      <button style={styles.backButton} onClick={onBack}>
        ← Back to Forecast
      </button>

      {/* Date Header */}
      <div style={styles.detailHeader}>
        <h2 style={styles.detailDate}>
          {(() => {
            const [year, month, day] = forecast.date.split('-').map(Number);
            const date = new Date(year, month - 1, day);
            return date.toLocaleDateString('en-US', { 
              weekday: 'long', 
              month: 'long', 
              day: 'numeric' 
            });
          })()}
        </h2>
        <div style={styles.detailWeather}>
          <span style={styles.detailWeatherLabel}>Max Temp</span>
          <span style={styles.detailWeatherTemp}>{Math.round(forecast.weather.temp_max)}°F</span>
          <span style={styles.detailWeatherIcon}>{forecast.weather.icon}</span>
        </div>
      </div>

      {/* Main Demand Card */}
      <div style={{
        ...styles.detailDemandCard,
        borderLeftColor: level.color,
      }}>
        <div style={styles.detailDemandHeader}>
          <span style={styles.detailDemandLabel}>Expected Daily Demand (MGD)</span>
          <div style={{
            ...styles.detailLevelBadge,
            backgroundColor: level.bg,
            color: level.color,
          }}>
            {level.level}
          </div>
        </div>
        {/* Side-by-side layout: prediction LEFT, confidence interval RIGHT */}
        <div style={styles.forecastLayout}>
          <div style={styles.mainPrediction}>
            <div style={styles.detailDemandNumber}>{forecast.demand.toFixed(1)}</div>
            <div style={styles.detailDemandUnit}>Million Gallons</div>
          </div>
          <div style={styles.confidenceSection}>
            <div style={styles.detailRangeLabel}>Expected Range (80% confidence):</div>
            <div style={styles.detailRangeValue}>
              {forecast.lower_bound.toFixed(1)} – {forecast.upper_bound.toFixed(1)} MGD
            </div>
          </div>
        </div>
      </div>

      {/* Hourly Pattern Chart - NEW DESIGN */}
      <div style={styles.graphCard}>
        <div style={styles.graphHeader}>
          <div>
            <h3 style={styles.graphTitle}>Daily Demand Pattern</h3>
            <p style={styles.graphSubtitle}>Typical hourly distribution</p>
          </div>
          <div style={styles.graphBadge}>
            <span style={styles.graphBadgeText}>MGD</span>
          </div>
        </div>
        
        <HourlyDemandChart dailyDemand={forecast.demand} color={level.color} />
        
        <div style={styles.graphInsight}>
          <span style={styles.graphInsightIcon}>💡</span>
          <span style={styles.graphInsightText}>
            Morning peak (7AM): ~{(forecast.demand * 0.07 * 24).toFixed(1)} MGD •
            Evening peak (6PM): ~{(forecast.demand * 0.07 * 24).toFixed(1)} MGD
          </span>
        </div>
      </div>

      {/* Contributing Factors */}
      <div style={styles.factorsCard}>
        <h3 style={styles.factorsTitle}>Why {level.level} Demand Expected?</h3>
        <div style={styles.factorsList}>
          <div style={styles.factorItem}>
            <span style={styles.factorIcon}>🌡️</span>
            <div style={styles.factorContent}>
              <span style={styles.factorLabel}>Temperature</span>
              <span style={styles.factorValue}>
                {Math.round(forecast.weather.temp_max)}°F forecasted
                {forecast.factors.temperature === 'high' && ' — Hot weather increases irrigation & cooling demand'}
                {forecast.factors.temperature === 'low' && ' — Cooler temps reduce outdoor water usage'}
                {forecast.factors.temperature === 'moderate' && ' — Typical seasonal temperatures'}
              </span>
            </div>
          </div>
          <div style={styles.factorItem}>
            <span style={styles.factorIcon}>🌧️</span>
            <div style={styles.factorContent}>
              <span style={styles.factorLabel}>Precipitation</span>
              <span style={styles.factorValue}>
                {forecast.factors.precipitation === 'yes' 
                  ? `${forecast.weather.precipitation}" expected — Reduces lawn irrigation needs`
                  : 'No rain expected — Normal outdoor usage patterns'}
              </span>
            </div>
          </div>
          <div style={styles.factorItem}>
            <span style={styles.factorIcon}>📅</span>
            <div style={styles.factorContent}>
              <span style={styles.factorLabel}>Day of Week</span>
              <span style={styles.factorValue}>
                {forecast.factors.day_type === 'weekend' 
                  ? 'Weekend — Typically 5-10% higher residential usage (more people home)'
                  : 'Weekday — Standard commercial & residential patterns'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Comparison to Average */}
      <div style={styles.comparisonCard}>
        <div style={styles.comparisonContent}>
          <span style={styles.comparisonLabel}>Compared to Historical Average (2019-2025)</span>
          <span style={styles.comparisonAvg}>(13.9 MGD typical)</span>
        </div>
        <span style={{
          ...styles.comparisonValue,
          color: forecast.vs_average > 10 ? COLORS.danger 
               : forecast.vs_average < -10 ? COLORS.success 
               : COLORS.gray800
        }}>
          {forecast.vs_average > 0 ? '+' : ''}{forecast.vs_average}%
        </span>
      </div>

      {/* Model Info Card */}
      <div style={styles.modelInfoCard}>
        <span style={styles.modelInfoTitle}>About This Prediction</span>
        <span style={styles.modelInfoText}>
          Daily totals predicted by ML model trained on 4 years of Pearland data. 
          Hourly pattern is estimated based on typical municipal usage curves.
        </span>
      </div>
    </div>
  );
}

// Styles
const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: COLORS.gray100,
    fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    display: 'flex',
    flexDirection: 'column',
  },
  
  loadingContainer: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.gray100,
  },
  loadingSpinner: {
    width: '40px',
    height: '40px',
    border: `4px solid ${COLORS.gray200}`,
    borderTopColor: COLORS.primary,
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    marginTop: '16px',
    color: COLORS.gray600,
    fontSize: '14px',
  },
  
  header: {
    background: `linear-gradient(135deg, ${COLORS.primary} 0%, ${COLORS.primaryDark} 100%)`,
    padding: '20px 24px',
    boxShadow: '0 4px 20px rgba(74, 14, 120, 0.4)',
  },
  headerContent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    maxWidth: '600px',
    margin: '0 auto',
  },
  headerTitle: {
    textAlign: 'right',
  },
  appTitle: {
    color: COLORS.white,
    fontSize: '18px',
    fontWeight: '600',
    margin: 0,
    lineHeight: 1.2,
  },
  appSubtitle: {
    color: 'rgba(255,255,255,0.75)',
    fontSize: '12px',
    margin: '4px 0 0 0',
  },

  errorBanner: {
    backgroundColor: '#FEF3C7',
    padding: '8px 20px',
    textAlign: 'center',
  },
  errorText: {
    color: '#92400E',
    fontSize: '12px',
  },

  main: {
    flex: 1,
    padding: '20px',
    maxWidth: '600px',
    margin: '0 auto',
    width: '100%',
    boxSizing: 'border-box',
  },

  todayCard: {
    background: COLORS.white,
    borderRadius: '20px',
    padding: '24px',
    marginBottom: '24px',
    boxShadow: '0 8px 30px rgba(0,0,0,0.08)',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
  },
  todayHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  todayLabel: {
    background: `linear-gradient(135deg, ${COLORS.primary} 0%, ${COLORS.primaryLight} 100%)`,
    color: COLORS.white,
    fontSize: '11px',
    fontWeight: '700',
    padding: '6px 14px',
    borderRadius: '14px',
    letterSpacing: '1px',
  },
  todayDate: {
    color: COLORS.gray600,
    fontSize: '13px',
    fontWeight: '500',
  },
  todayContent: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  weatherInfo: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
  },
  weatherIcon: {
    fontSize: '52px',
  },
  weatherTemp: {
    fontSize: '20px',
    fontWeight: '700',
    color: COLORS.gray800,
  },
  weatherLabel: {
    fontSize: '12px',
    color: COLORS.gray600,
    fontWeight: '600',
  },
  demandDisplay: {
    textAlign: 'right',
  },
  demandIndicator: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 14px',
    borderRadius: '20px',
    border: '2px solid',
    marginBottom: '12px',
  },
  demandDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
  },
  demandLevelText: {
    fontSize: '13px',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  demandValue: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'flex-end',
    gap: '6px',
  },
  demandNumber: {
    fontSize: '48px',
    fontWeight: '800',
    color: COLORS.gray800,
    lineHeight: 1,
  },
  demandUnit: {
    fontSize: '20px',
    fontWeight: '600',
    color: COLORS.gray600,
  },
  demandSubtext: {
    fontSize: '12px',
    color: COLORS.gray600,
    marginTop: '4px',
    display: 'block',
  },
  todayFooter: {
    marginTop: '20px',
    paddingTop: '16px',
    borderTop: `1px solid ${COLORS.gray200}`,
    textAlign: 'center',
  },
  tapHint: {
    fontSize: '13px',
    color: COLORS.primary,
    fontWeight: '600',
  },

  forecastSection: {
    marginBottom: '24px',
  },
  sectionTitle: {
    fontSize: '17px',
    fontWeight: '700',
    color: COLORS.gray800,
    marginBottom: '14px',
    marginLeft: '4px',
  },
  forecastScroll: {
    display: 'flex',
    gap: '10px',
    overflowX: 'auto',
    paddingBottom: '8px',
    scrollSnapType: 'x mandatory',
    WebkitOverflowScrolling: 'touch',
  },
  forecastCard: {
    flex: '0 0 auto',
    width: '76px',
    background: COLORS.white,
    borderRadius: '16px',
    padding: '14px 10px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '6px',
    boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
    cursor: 'pointer',
    scrollSnapAlign: 'start',
    transition: 'transform 0.2s',
  },
  forecastCardToday: {
    background: `linear-gradient(180deg, ${COLORS.primaryLight} 0%, ${COLORS.primary} 100%)`,
    boxShadow: '0 4px 20px rgba(74, 14, 120, 0.3)',
  },
  forecastDay: {
    fontSize: '10px',
    fontWeight: '700',
    letterSpacing: '0.5px',
  },
  forecastDate: {
    fontSize: '18px',
    fontWeight: '800',
  },
  forecastWeather: {
    fontSize: '26px',
    margin: '4px 0',
  },
  forecastTemp: {
    fontSize: '13px',
    fontWeight: '600',
  },
  forecastDemandDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    marginTop: '6px',
  },
  forecastDemand: {
    fontSize: '16px',
    fontWeight: '800',
  },
  forecastDemandUnit: {
    fontSize: '10px',
    marginTop: '-4px',
    fontWeight: '500',
  },

  legend: {
    display: 'flex',
    justifyContent: 'center',
    gap: '20px',
    marginBottom: '20px',
    flexWrap: 'wrap',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  legendDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
  },
  legendText: {
    fontSize: '12px',
    color: COLORS.gray600,
    fontWeight: '500',
  },

  updateInfo: {
    textAlign: 'center',
    marginTop: '8px',
  },
  updateText: {
    display: 'block',
    fontSize: '12px',
    color: COLORS.gray600,
  },
  modelInfo: {
    display: 'block',
    fontSize: '11px',
    color: COLORS.primary,
    marginTop: '4px',
    fontWeight: '500',
  },
  updateNote: {
    display: 'block',
    fontSize: '10px',
    color: COLORS.gray600,
    marginTop: '2px',
  },

  refreshButton: {
    display: 'block',
    width: '100%',
    maxWidth: '200px',
    margin: '20px auto 0',
    padding: '12px 24px',
    backgroundColor: COLORS.white,
    border: `2px solid ${COLORS.primary}`,
    borderRadius: '12px',
    color: COLORS.primary,
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },

  footer: {
    background: COLORS.primaryDark,
    padding: '14px 20px',
    textAlign: 'center',
  },
  footerText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: '11px',
  },

  // Detail View Styles
  detailContainer: {
    animation: 'fadeIn 0.3s ease',
  },
  backButton: {
    background: 'none',
    border: 'none',
    color: COLORS.primary,
    fontSize: '15px',
    fontWeight: '600',
    padding: '8px 0',
    cursor: 'pointer',
    marginBottom: '16px',
  },
  detailHeader: {
    marginBottom: '24px',
  },
  detailDate: {
    fontSize: '24px',
    fontWeight: '800',
    color: COLORS.gray800,
    margin: '0 0 12px 0',
  },
  detailWeather: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  detailWeatherLabel: {
    fontSize: '13px',
    color: COLORS.gray600,
    fontWeight: '600',
    marginRight: '8px',
  },
  detailWeatherTemp: {
    fontSize: '20px',
    fontWeight: '700',
    color: COLORS.gray800,
    marginRight: '8px',
  },
  detailWeatherIcon: {
    fontSize: '32px',
  },
  detailDemandCard: {
    background: COLORS.white,
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '16px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
    borderLeft: '5px solid',
  },
  detailDemandHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  detailDemandLabel: {
    fontSize: '14px',
    color: COLORS.gray600,
    fontWeight: '600',
  },
  detailLevelBadge: {
    padding: '6px 12px',
    borderRadius: '14px',
    fontSize: '12px',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  // Side-by-side layout styles
  forecastLayout: {
    display: 'flex',
    alignItems: 'center',
    gap: '40px',
    marginTop: '16px',
  },
  mainPrediction: {
    flex: '0 0 auto',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
  },
  confidenceSection: {
    flex: 1,
    background: COLORS.white,
    padding: '20px',
    borderRadius: '12px',
    border: `2px solid ${COLORS.gray200}`,
  },
  detailDemandValue: {
    marginBottom: '16px',
  },
  detailDemandNumber: {
    fontSize: '56px',
    fontWeight: '800',
    color: COLORS.gray800,
    lineHeight: 1,
  },
  detailDemandUnit: {
    display: 'block',
    fontSize: '15px',
    color: COLORS.gray600,
    marginTop: '6px',
    fontWeight: '500',
  },
  detailRange: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    padding: '14px 18px',
    background: COLORS.gray100,
    borderRadius: '12px',
  },
  detailRangeLabel: {
    fontSize: '11px',
    color: COLORS.gray600,
    fontWeight: '500',
  },
  detailRangeValue: {
    fontSize: '15px',
    fontWeight: '700',
    color: COLORS.gray800,
  },

  // Graph Card - Updated
  graphCard: {
    background: COLORS.white,
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '16px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
  },
  graphHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '20px',
  },
  graphTitle: {
    fontSize: '16px',
    fontWeight: '700',
    color: COLORS.gray800,
    margin: 0,
  },
  graphSubtitle: {
    fontSize: '12px',
    color: COLORS.gray600,
    margin: '4px 0 0 0',
  },
  graphBadge: {
    backgroundColor: COLORS.gray100,
    padding: '6px 10px',
    borderRadius: '8px',
  },
  graphBadgeText: {
    fontSize: '10px',
    fontWeight: '600',
    color: COLORS.gray600,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  graphInsight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '16px',
    padding: '12px 16px',
    backgroundColor: COLORS.gray100,
    borderRadius: '10px',
  },
  graphInsightIcon: {
    fontSize: '16px',
  },
  graphInsightText: {
    fontSize: '11px',
    color: COLORS.gray600,
    lineHeight: 1.4,
  },

  // Factors Card
  factorsCard: {
    background: COLORS.white,
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '16px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
  },
  factorsTitle: {
    fontSize: '15px',
    fontWeight: '700',
    color: COLORS.gray800,
    margin: '0 0 20px 0',
  },
  factorsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
  },
  factorItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '14px',
  },
  factorIcon: {
    fontSize: '24px',
  },
  factorContent: {
    flex: 1,
  },
  factorLabel: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '700',
    color: COLORS.gray800,
    marginBottom: '4px',
  },
  factorValue: {
    display: 'block',
    fontSize: '13px',
    color: COLORS.gray600,
    lineHeight: 1.4,
  },

  comparisonCard: {
    background: COLORS.white,
    borderRadius: '16px',
    padding: '20px 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
    marginBottom: '16px',
  },
  comparisonContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  comparisonLabel: {
    fontSize: '14px',
    color: COLORS.gray800,
    fontWeight: '600',
  },
  comparisonAvg: {
    fontSize: '12px',
    color: COLORS.gray600,
  },
  comparisonValue: {
    fontSize: '28px',
    fontWeight: '800',
  },

  modelInfoCard: {
    background: COLORS.gray100,
    borderRadius: '12px',
    padding: '16px 20px',
    border: `1px solid ${COLORS.gray200}`,
  },
  modelInfoTitle: {
    display: 'block',
    fontSize: '12px',
    fontWeight: '700',
    color: COLORS.gray800,
    marginBottom: '8px',
  },
  modelInfoText: {
    display: 'block',
    fontSize: '11px',
    color: COLORS.gray600,
    lineHeight: 1.5,
  },
};

// Add keyframes for animations
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  
  * {
    -webkit-tap-highlight-color: transparent;
    box-sizing: border-box;
  }
  
  ::-webkit-scrollbar {
    height: 4px;
  }
  
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  
  ::-webkit-scrollbar-thumb {
    background: #DEE2E6;
    border-radius: 2px;
  }
  
  button:hover {
    transform: scale(1.02);
  }
  
  button:active {
    transform: scale(0.98);
  }
`;
document.head.appendChild(styleSheet);