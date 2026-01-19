# Water Demand Forecast App

A mobile-first web application for predicting 10-day water demand in Pearland, TX.  
Built for **Civitas Engineering Group**.

## Project Structure

```
├── backend/           # FastAPI backend (deploy to Railway)
│   ├── main.py
│   ├── requirements.txt
│   ├── Procfile
│   └── model/         # ML model files
└── frontend/          # React frontend (deploy to Vercel)
    ├── src/
    ├── public/
    └── package.json
```

## Deployment Instructions

### Step 1: Deploy Backend to Railway

1. Create a new project on Railway
2. Connect your GitHub repo
3. Select the `backend` folder as root directory
4. Railway will auto-detect Python and deploy
5. Copy your deployment URL (e.g., `https://xxx.up.railway.app`)

### Step 2: Deploy Frontend to Vercel

1. Create a new project on Vercel
2. Connect your GitHub repo
3. Set root directory to `frontend`
4. Add environment variable:
   - `REACT_APP_API_URL` = your Railway backend URL
5. Deploy

## Model Performance

- **R² Score**: 0.94
- **MAPE**: 3.29%
- **Training Data**: 2019-2022 Pearland water production

## Tech Stack

- **Backend**: FastAPI, scikit-learn, pandas
- **Frontend**: React
- **ML Model**: Gradient Boosting Regressor

---

© 2025 Civitas Engineering Group
