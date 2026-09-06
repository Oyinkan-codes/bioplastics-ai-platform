import io
import joblib
import numpy as np
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Predictive Modeler", page_icon="🔮", layout="wide")

st.title("🔮 Predictive Formulation Modeler")
st.markdown("Select agricultural/industrial waste feedstocks and configure formulation ratios to predict physical properties.")

user_plan = st.session_state.get("user_plan", "free")

# Tier Access Rules
if user_plan == "free" and st.session_state.get("daily_predictions", 0) >= 5:
    st.warning("⚠️ Daily free limit reached (5/5). Upgrade to Researcher ($12/mo) or Enterprise ($38.99/mo) for unlimited predictions.")
    st.stop()

# Inputs
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("1. Feedstock & Additives")
    
    feedstock = st.selectbox(
        "Agricultural Waste Feedstock Source",
        ["Cassava Starch Waste", "Brewery Spent Grain", "Palm Kernel Ash Composite", "Citrus Peel Fiber"] 
        if user_plan != "free" else ["Standard Corn Starch (Base)"]
    )
    
    glycerin = st.slider("Glycerin / Plasticizer (g)", 5.0, 40.0, 20.0)
    water = st.slider("Water Solvent (g)", 10.0, 50.0, 30.0)
    citric_acid = st.slider("Citric Acid Cross-Linker (g)", 0.5, 5.0, 2.0)
    chitosan = st.slider("Chitosan Reinforcement (g)", 0.0, 3.0, 1.0)

# Prediction Logic
model = joblib.load("models/bioplastic_rf_v1.pkl")
X_input = np.array([[glycerin, water, citric_acid, chitosan]])
preds = model.predict(X_input)[0]

tensile_str, elasticity, water_abs = preds[0], preds[1], preds[2]

with col_right:
    st.subheader("2. Predicted Material Properties")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Tensile Strength", f"{tensile_str:.2f} MPa")
    m2.metric("Elongation / Elasticity", f"{elasticity:.2f} %")
    m3.metric("Water Absorption Rate", f"{water_abs:.2f} %")

    st.markdown("---")
    st.subheader("3. Technical Data Sheet (TDS) Export")

    def generate_tds_pdf(feedstock, glycerin, water, citric_acid, chitosan, tensile, elasticity, water_abs):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(100, 730, "BioMatX AI - Technical Data Sheet (TDS)")
        c.setFont("Helvetica", 10)
        c.drawString(100, 715, f"Material Feedstock: {feedstock}")
        c.line(100, 705, 500, 705)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 680, "Formulation Ratios:")
        c.setFont("Helvetica", 10)
        c.drawString(120, 660, f"• Glycerin: {glycerin} g")
        c.drawString(120, 645, f"• Water Solvent: {water} g")
        c.drawString(120, 630, f"• Citric Acid: {citric_acid} g")
        c.drawString(120, 615, f"• Chitosan: {chitosan} g")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 580, "Predicted Physical Properties:")
        c.setFont("Helvetica", 10)
        c.drawString(120, 560, f"• Tensile Strength: {tensile:.2f} MPa")
        c.drawString(120, 545, f"• Elongation at Break: {elasticity:.2f} %")
        c.drawString(120, 530, f"• Water Absorption (24h): {water_abs:.2f} %")

        c.setFont("Helvetica-Oblique", 9)
        c.drawString(100, 480, "Generated via BioMatX DeepTech ML Platform for UK B2B Licensing & Compliance.")
        c.save()
        buffer.seek(0)
        return buffer

    if user_plan in ["researcher", "enterprise"]:
        pdf_bytes = generate_tds_pdf(feedstock, glycerin, water, citric_acid, chitosan, tensile_str, elasticity, water_abs)
        st.download_button(
            label="📄 Download Official TDS PDF",
            data=pdf_bytes,
            file_name=f"BioMatX_TDS_{feedstock.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("🔒 TDS PDF Export is locked on the Free plan. Upgrade to Researcher ($12) or Enterprise ($38.99) to export.")

st.session_state["daily_predictions"] += 1
