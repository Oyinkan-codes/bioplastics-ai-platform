import datetime
import streamlit as st
import joblib
import numpy as np
import os

# Base Model Loader
MODEL_PATH = "models/bioplastic_rf_v1.pkl"

@st.cache_resource
def load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

model = load_model()

st.header("1. Forward Mechanical Property Predictor")
st.markdown("Adjust input raw material ratios to calculate predicted physical outputs.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    base_mat = st.selectbox("Base Biopolymer", ["Cassava Starch", "Sugarcane Bagasse", "Corn Starch", "Palm Kernel Ash Composite"])
with c2:
    gly_in = st.slider("Glycerin Plasticizer (%)", 5.0, 40.0, 20.0)
with c3:
    wat_in = st.slider("Water Content (%)", 10.0, 50.0, 30.0)
with c4:
    cit_in = st.slider("Citric Acid Crosslinker (%)", 0.5, 5.0, 2.0)

chitos_in = st.slider("Chitosan Additive (%)", 0.0, 3.0, 1.0)

if st.button("Run Forward Prediction", type="primary"):
    user_plan = st.session_state.get("user_plan", "free")
    daily_predictions = st.session_state.get("daily_predictions", 0)

    if user_plan == "free" and daily_predictions >= 3:
        st.error("🚫 Daily free prediction limit reached (3/3). Upgrade to the Researcher plan ($12/mo) to continue.")
    else:
        if user_plan == "free":
            st.session_state["daily_predictions"] += 1
        
        if model:
            preds = model.predict([[gly_in, wat_in, cit_in, chitos_in]])[0]
            tensile, elasticity, water_abs = round(float(preds[0]), 2), round(float(preds[1]), 2), round(float(preds[2]), 2)
            
            st.markdown("---")
            st.subheader("Predicted Mechanical Properties")
            m1, m2, m3 = st.columns(3)
            m1.metric("Tensile Strength", f"{tensile} MPa")
            m2.metric("Elasticity (Elongation)", f"{elasticity} %")
            m3.metric("Water Absorption (24h)", f"{water_abs} %")
            
            if user_plan == "free":
                st.warning("🔒 Exact cross-linker optimization and commercial spec downloads are locked on the Free Tier.")
            else:
                st.success("✅ Full Technical Specification Unlocked")
