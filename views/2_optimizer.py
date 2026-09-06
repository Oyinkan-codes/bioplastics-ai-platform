import joblib
import numpy as np
import streamlit as st
from scipy.optimize import minimize

st.set_page_config(page_title="Inverse Recipe Optimizer", page_icon="🎯", layout="wide")

st.title("🎯 Inverse Recipe Optimizer")
st.markdown("Set target physical performance attributes, and the solver will output the exact chemical ratios required.")

user_plan = st.session_state.get("user_plan", "free")

if user_plan == "free":
    st.error("🔒 The Inverse Optimizer is a paid feature. Upgrade to the Researcher Plan ($12) or Enterprise Plan ($38.99) to unlock.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Target Material Properties")
    target_tensile = st.number_input("Target Tensile Strength (MPa)", 10.0, 60.0, 35.0)
    target_elasticity = st.number_input("Target Elongation (%)", 10.0, 100.0, 45.0)
    target_water_abs = st.number_input("Target Water Absorption (%)", 5.0, 50.0, 20.0)

model = joblib.load("models/bioplastic_rf_v1.pkl")

def loss_function(weights):
    pred = model.predict([weights])[0]
    error = (pred[0] - target_tensile)**2 + (pred[1] - target_elasticity)**2 + (pred[2] - target_water_abs)**2
    return error

with col2:
    st.subheader("Optimal Formulation Results")
    if st.button("🚀 Run Optimization Solver", type="primary"):
        bounds = [(5.0, 40.0), (10.0, 50.0), (0.5, 5.0), (0.0, 3.0)]
        initial_guess = [20.0, 30.0, 2.0, 1.0]
        
        res = minimize(loss_function, initial_guess, method="L-BFGS-B", bounds=bounds)
        opt_g, opt_w, opt_ca, opt_ch = res.x
        
        st.success("Formulation Successfully Optimized!")
        st.write(f"• **Glycerin:** {opt_g:.2f} g")
        st.write(f"• **Water Solvent:** {opt_w:.2f} g")
        st.write(f"• **Citric Acid:** {opt_ca:.2f} g")
        st.write(f"• **Chitosan:** {opt_ch:.2f} g")
