import os
import joblib
import numpy as np
import streamlit as st
from scipy.optimize import minimize

MODEL_PATH = "models/bioplastic_rf_v1.pkl"

@st.cache_resource
def load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

model = load_model()

st.header("2. Inverse Recipe Optimizer")

user_plan = st.session_state.get("user_plan", "free")

if user_plan == "free":
    st.warning("🔒 **Inverse Recipe Optimization is a Paid Feature.** Upgrade to Researcher or Enterprise to unlock.")
else:
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        target_t = st.number_input("Target Tensile Strength (MPa)", 5.0, 80.0, 35.0)
    with col_t2:
        target_e = st.number_input("Target Elasticity (%)", 10.0, 120.0, 45.0)
    with col_t3:
        target_w = st.number_input("Target Max Water Abs. (%)", 5.0, 60.0, 20.0)

    if st.button("Calculate Optimized Recipe", type="primary"):
        def objective(x):
            preds = model.predict([x])[0]
            return (preds[0] - target_t)**2 + (preds[1] - target_e)**2 + (preds[2] - target_w)**2

        bounds = [(5.0, 40.0), (10.0, 50.0), (0.5, 5.0), (0.0, 3.0)]
        initial_guess = [20.0, 30.0, 2.0, 1.0]

        res = minimize(objective, initial_guess, method='L-BFGS-B', bounds=bounds)
        opt = res.x

        st.success("🎯 Optimal Formulation Calculated!")
        st.write(f"• **Glycerin Plasticizer:** {round(float(opt[0]), 2)}%")
        st.write(f"• **Water Content:** {round(float(opt[1]), 2)}%")
        st.write(f"• **Citric Acid Cross-linker:** {round(float(opt[2]), 2)}%")
        st.write(f"• **Chitosan Additive:** {round(float(opt[3]), 2)}%")
