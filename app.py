import os
import io
import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from scipy.optimize import minimize
from sklearn.ensemble import RandomForestRegressor
import joblib

# ReportLab imports for PDF Spec Sheet Generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. PAGE CONFIG & SESSION STATE SETUP
# ==========================================
st.set_page_config(
    page_title="BioMatX AI - Circular Economy Platform",
    page_icon="🧪",
    layout="wide"
)

# Initialize Session State Variables
if "user_plan" not in st.session_state:
    st.session_state["user_plan"] = "free"  # Options: 'free', 'researcher', 'enterprise'

if "daily_predictions" not in st.session_state:
    st.session_state["daily_predictions"] = 0

if "last_prediction_date" not in st.session_state:
    st.session_state["last_prediction_date"] = datetime.date.today()

# Daily Quota Reset Logic (Resets at Midnight WAT)
today = datetime.date.today()
if st.session_state["last_prediction_date"] < today:
    st.session_state["daily_predictions"] = 0
    st.session_state["last_prediction_date"] = today


# ==========================================
# 2. ML MODEL LOADING & OPTIMIZER ENGINES
# ==========================================
MODEL_PATH = "models/bioplastic_rf_v1.pkl"

@st.cache_resource
def load_or_train_model():
    """
    Checks if a saved model exists on disk.
    If yes, loads it via joblib. If no, trains a baseline model and saves it.
    """
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            return model
        except Exception:
            pass  # Fall back to training if loading fails

    # Synthetic baseline training data fallback
    np.random.seed(42)
    N = 1000
    
    # Features: [Glycerin %, Water %, Citric Acid %, Chitosan %]
    glycerin = np.random.uniform(5, 40, N)
    water = np.random.uniform(10, 50, N)
    citric_acid = np.random.uniform(0.5, 5.0, N)
    chitosan = np.random.uniform(0.0, 3.0, N)
    
    X = np.column_stack([glycerin, water, citric_acid, chitosan])
    
    # Physics relationship simulation
    tensile = 50.0 - (glycerin * 0.9) - (water * 0.4) + (citric_acid * 2.5) + (chitosan * 3.1) + np.random.normal(0, 1, N)
    elasticity = 2.0 + (glycerin * 2.2) + (water * 0.3) - (citric_acid * 0.8) + np.random.normal(0, 1, N)
    water_abs = 15.0 + (water * 0.8) - (glycerin * 0.1) - (citric_acid * 1.5) - (chitosan * 2.0) + np.random.normal(0, 1, N)
    
    y = np.column_stack([
        np.clip(tensile, 1.0, 100.0),
        np.clip(elasticity, 1.0, 150.0),
        np.clip(water_abs, 1.0, 90.0)
    ])
    
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    
    # Save model locally for persistence
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    
    return model

model = load_or_train_model()

def run_inverse_optimizer(target_tensile, target_elasticity, target_water_abs):
    """Calculates required additive ratios based on target mechanical properties."""
    def objective(x):
        preds = model.predict([x])[0]
        err = (preds[0] - target_tensile)**2 + (preds[1] - target_elasticity)**2 + (preds[2] - target_water_abs)**2
        return err

    bounds = [(5, 40), (10, 50), (0.5, 5.0), (0.0, 3.0)]
    initial_guess = [20.0, 30.0, 2.0, 1.0]
    
    res = minimize(objective, initial_guess, method='L-BFGS-B', bounds=bounds)
    opt_ratios = res.x
    predicted_outputs = model.predict([opt_ratios])[0]
    
    return {
        "glycerin": round(opt_ratios[0], 2),
        "water": round(opt_ratios[1], 2),
        "citric_acid": round(opt_ratios[2], 2),
        "chitosan": round(opt_ratios[3], 2),
        "achieved_tensile": round(predicted_outputs[0], 2),
        "achieved_elasticity": round(predicted_outputs[1], 2),
        "achieved_water_abs": round(predicted_outputs[2], 2)
    }


# ==========================================
# 3. PDF SPEC SHEET GENERATOR
# ==========================================
def generate_pdf_spec_sheet(data_dict):
    """Generates a downloadable PDF Spec Sheet using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1b4332"))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Heading3'], fontSize=12, textColor=colors.HexColor("#2d6a4f"))
    
    # Header
    story.append(Paragraph("BioMatX Intelligence - Technical Data Sheet (TDS)", title_style))
    story.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S WAT')}", subtitle_style))
    story.append(Spacer(1, 15))
    
    # Spec Table
    table_data = [
        ["Parameter", "Target Value", "Optimized / Predicted Output"],
        ["Base Polymer", data_dict.get("base_polymer", "Cassava Starch"), data_dict.get("base_polymer", "Cassava Starch")],
        ["Tensile Strength (MPa)", f"{data_dict.get('target_tensile', 'N/A')}", f"{data_dict.get('achieved_tensile')} MPa"],
        ["Elasticity / Elongation (%)", f"{data_dict.get('target_elasticity', 'N/A')}", f"{data_dict.get('achieved_elasticity')} %"],
        ["Water Absorption 24hr (%)", f"{data_dict.get('target_water', 'N/A')}", f"{data_dict.get('achieved_water')} %"],
        ["Glycerin Plasticizer Ratio", "-", f"{data_dict.get('glycerin')}%"],
        ["Water Content", "-", f"{data_dict.get('water')}%"],
        ["Citric Acid Cross-linker", "-", f"{data_dict.get('citric_acid')}%"],
        ["Chitosan Additive", "-", f"{data_dict.get('chitosan')}%"]
    ]
    
    t = Table(table_data, colWidths=[200, 150, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2d6a4f")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8f9fa")),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#d3d3d3")),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Paragraph("<i>Disclaimer: Formulations are generated via predictive machine learning models. Physical lab verification recommended before production.</i>", styles['Italic']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


# ==========================================
# 4. SIDEBAR - USER PLAN & QUOTA CONTROLLER
# ==========================================
st.sidebar.title("🌿 BioMatX Platform")
st.sidebar.markdown(f"**Current Plan:** `{st.session_state['user_plan'].upper()}`")

# Quota Tracker
if st.session_state["user_plan"] == "free":
    quota_left = max(0, 3 - st.session_state["daily_predictions"])
    st.sidebar.progress((3 - quota_left) / 3)
    st.sidebar.caption(f"Daily Free Quota Remaining: **{quota_left} / 3 predictions**")
    if quota_left == 0:
        st.sidebar.error("⚠️ Daily quota exhausted. Upgrade to unlock unlimited runs.")
else:
    st.sidebar.success("⚡ Unlimited Premium Access Active")

st.sidebar.markdown("---")
st.sidebar.subheader("Simulate Account Tier:")
plan_choice = st.sidebar.radio("Active Tier:", ["Free ($0/mo)", "Researcher ($12/mo)", "Enterprise ($38.99/mo)"])
if plan_choice.startswith("Free"):
    st.session_state["user_plan"] = "free"
elif plan_choice.startswith("Researcher"):
    st.session_state["user_plan"] = "researcher"
else:
    st.session_state["user_plan"] = "enterprise"


# ==========================================
# 5. MAIN APPLICATION TABS
# ==========================================
st.title("🧪 AI Bioplastic Formulation & Optimization Engine")
st.caption("Predict mechanical properties, optimize raw material input ratios, and generate specification sheets.")

tab1, tab2, tab3 = st.tabs(["🔮 Predictive Modeler", "🎯 Inverse Recipe Optimizer", "📊 Interactive 3D Surfaces"])


# ------------------------------------------
# TAB 1: PREDICTIVE MODELER
# ------------------------------------------
with tab1:
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
        # Check Daily Quota for Free Users
        if st.session_state["user_plan"] == "free" and st.session_state["daily_predictions"] >= 3:
            st.error("🚫 Daily free prediction limit reached (3/3). Please upgrade to the Researcher plan ($12/mo) to continue.")
        else:
            if st.session_state["user_plan"] == "free":
                st.session_state["daily_predictions"] += 1
            
            # Perform Prediction
            preds = model.predict([[gly_in, wat_in, cit_in, chitos_in]])[0]
            tensile, elasticity, water_abs = round(preds[0], 2), round(preds[1], 2), round(preds[2], 2)
            
            st.markdown("---")
            st.subheader("Predicted Mechanical Properties")
            m1, m2, m3 = st.columns(3)
            m1.metric("Tensile Strength", f"{tensile} MPa")
            m2.metric("Elasticity (Elongation)", f"{elasticity} %")
            m3.metric("Water Absorption (24h)", f"{water_abs} %")
            
            st.markdown("---")
            st.subheader("Additive Ratios & Formulation Spec")
            
            # CONVERSION TRIGGER (TEASE & BLOCK)
            if st.session_state["user_plan"] == "free":
                st.warning("🔒 Exact cross-linker optimization and commercial spec downloads are locked on the Free Tier.")
                
                # Blurred Mockup CSS
                st.markdown(
                    """
                    <div style="background-color: #212529; color: #f8f9fa; padding: 20px; border-radius: 10px; filter: blur(5px); opacity: 0.5; user-select: none;">
                        <p><strong>Optimized Curing Temperature:</strong> 87.5°C</p>
                        <p><strong>Recommended Mixing Shear Rate:</strong> 450 RPM</p>
                        <p><strong>Exact Polymer-to-Plasticizer Ratio:</strong> 1 : 0.34</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                st.info("💡 **Upgrade to Researcher ($12/mo)** to unlock exact formulation metrics and PDF TDS downloads.")
            else:
                st.success("✅ Full Technical Specification Unlocked")
                spec_data = {
                    "base_polymer": base_mat,
                    "target_tensile": f"{tensile} MPa",
                    "target_elasticity": f"{elasticity} %",
                    "target_water": f"{water_abs} %",
                    "achieved_tensile": tensile,
                    "achieved_elasticity": elasticity,
                    "achieved_water": water_abs,
                    "glycerin": gly_in,
                    "water": wat_in,
                    "citric_acid": cit_in,
                    "chitosan": chitos_in
                }
                st.json(spec_data)
                
                # PDF Download Button
                pdf_bytes = generate_pdf_spec_sheet(spec_data)
                st.download_button(
                    label="📄 Download Technical Data Sheet (PDF)",
                    data=pdf_bytes,
                    file_name=f"BioMatX_Spec_{base_mat.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )


# ------------------------------------------
# TAB 2: INVERSE RECIPE OPTIMIZER
# ------------------------------------------
with tab2:
    st.header("2. Inverse Recipe Optimizer")
    st.markdown("Input your target mechanical performance requirements, and the AI will calculate the exact required material formulation.")
    
    if st.session_state["user_plan"] == "free":
        st.warning("🔒 **Inverse Recipe Optimization is a Paid Feature.** Upgrade to Researcher ($12/mo) or Enterprise ($38.99/mo) to use this tool.")
        st.image("https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=800&q=80", caption="Lock in target properties to output precise chemical ratios.")
    else:
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            target_t = st.number_input("Target Tensile Strength (MPa)", 5.0, 80.0, 35.0)
        with col_t2:
            target_e = st.number_input("Target Elasticity (%)", 10.0, 120.0, 45.0)
        with col_t3:
            target_w = st.number_input("Target Max Water Abs. (%)", 5.0, 60.0, 20.0)
            
        if st.button("Calculate Optimized Recipe", type="primary"):
            results = run_inverse_optimizer(target_t, target_e, target_w)
            
            st.success("🎯 Optimal Formulation Found!")
            
            res_c1, res_c2 = st.columns(2)
            with res_c1:
                st.subheader("Required Input Ingredients")
                st.write(f"• **Glycerin Plasticizer:** {results['glycerin']}%")
                st.write(f"• **Water Content:** {results['water']}%")
                st.write(f"• **Citric Acid Cross-linker:** {results['citric_acid']}%")
                st.write(f"• **Chitosan Additive:** {results['chitosan']}%")
            
            with res_c2:
                st.subheader("Predicted Output Match")
                st.write(f"• **Tensile Achieved:** {results['achieved_tensile']} MPa (Target: {target_t})")
                st.write(f"• **Elasticity Achieved:** {results['achieved_elasticity']}% (Target: {target_e})")
                st.write(f"• **Water Abs. Achieved:** {results['achieved_water_abs']}% (Target: {target_w})")


# ------------------------------------------
# TAB 3: INTERACTIVE 3D SURFACES
# ------------------------------------------
with tab3:
    st.header("3. Polymer Interaction Surfaces")
    st.markdown("Explore 3D interaction dynamics between Plasticizers (Glycerin) and Water Content on Tensile Strength.")
    
    # Generate Meshgrid for Surface Plot
    g_range = np.linspace(5, 40, 30)
    w_range = np.linspace(10, 50, 30)
    G, W = np.meshgrid(g_range, w_range)
    
    # Static values for citric acid and chitosan
    C_static = 2.0
    Ch_static = 1.0
    
    # Flatten grid for model prediction
    grid_inputs = np.column_stack([G.ravel(), W.ravel(), np.full(G.size, C_static), np.full(G.size, Ch_static)])
    grid_preds = model.predict(grid_inputs)
    Z_tensile = grid_preds[:, 0].reshape(G.shape)
    
    # Plotly 3D Surface Figure
    fig = go.Figure(data=[go.Surface(z=Z_tensile, x=G, y=W, colorscale='Viridis')])
    fig.update_layout(
        title="3D Tensile Strength Surface (MPa)",
        scene=dict(
            xaxis_title="Glycerin (%)",
            yaxis_title="Water Content (%)",
            zaxis_title="Tensile Strength (MPa)"
        ),
        autosize=True,
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    st.plotly_chart(fig, use_container_width=True)
