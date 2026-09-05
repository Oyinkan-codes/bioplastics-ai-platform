import os
import joblib
import numpy as np
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# Page Configuration
st.set_page_config(
    page_title="BioMatX AI Platform",
    page_icon="🌿",
    layout="wide"
)

# Auto-generate baseline model if not present
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "bioplastic_rf_v1.pkl")

def ensure_model_exists():
    if not os.path.exists(MODEL_PATH):
        os.makedirs(MODEL_DIR, exist_ok=True)
        np.random.seed(42)
        N = 500
        glycerin = np.random.uniform(5, 40, N)
        water = np.random.uniform(10, 50, N)
        citric_acid = np.random.uniform(0.5, 5.0, N)
        chitosan = np.random.uniform(0.0, 3.0, N)
        X = np.column_stack([glycerin, water, citric_acid, chitosan])
        
        tensile = 50.0 - (glycerin * 0.9) - (water * 0.4) + (citric_acid * 2.5) + (chitosan * 3.1) + np.random.normal(0, 1, N)
        elasticity = 2.0 + (glycerin * 2.2) + (water * 0.3) - (citric_acid * 0.8) + np.random.normal(0, 1, N)
        water_abs = 15.0 + (water * 0.8) - (glycerin * 0.1) - (citric_acid * 1.5) - (chitosan * 2.0) + np.random.normal(0, 1, N)
        y = np.column_stack([tensile, elasticity, water_abs])
        
        model = RandomForestRegressor(n_estimators=30, random_state=42)
        model.fit(X, y)
        joblib.dump(model, MODEL_PATH)

ensure_model_exists()

# Initialize Global Session State Variables
if "user_plan" not in st.session_state:
    st.session_state["user_plan"] = "free"

if "daily_predictions" not in st.session_state:
    st.session_state["daily_predictions"] = 0

# App Router Navigation Setup
p1 = st.Page("views/1_dashboard.py", title="Predictive Modeler", icon="🔮", default=True)
p2 = st.Page("views/2_optimizer.py", title="Inverse Recipe Optimizer", icon="🎯")
p3 = st.Page("views/3_surfaces.py", title="Interactive 3D Surfaces", icon="📊")
p4 = st.Page("views/4_upgrade.py", title="Upgrade Plan", icon="💳")

pg = st.navigation({
    "Core Features": [p1, p2, p3],
    "Billing & Account": [p4]
})

pg.run()
