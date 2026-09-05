import os
import io
import datetime
import joblib
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

MODEL_PATH = "models/bioplastic_rf_v1.pkl"

@st.cache_resource
def load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

model = load_model()

def generate_pdf_spec_sheet(data_dict):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1b4332"))
    
    story.append(Paragraph("BioMatX Intelligence - Technical Data Sheet (TDS)", title_style))
    story.append(Spacer(1, 15))
    
    table_data = [
        ["Parameter", "Target Specification", "Predicted Output Value"],
        ["Base Polymer", data_dict.get("base_polymer"), data_dict.get("base_polymer")],
        ["Tensile Strength", f"{data_dict.get('tensile')} MPa", f"{data_dict.get('tensile')} MPa"],
        ["Elasticity", f"{data_dict.get('elasticity')} %", f"{data_dict.get('elasticity')} %"],
        ["Water Absorption", f"{data_dict.get('water_abs')} %", f"{data_dict.get('water_abs')} %"],
        ["Glycerin", "-", f"{data_dict.get('glycerin')}%"],
        ["Water", "-", f"{data_dict.get('water')}%"],
        ["Citric Acid", "-", f"{data_dict.get('citric_acid')}%"],
        ["Chitosan", "-", f"{data_dict.get('chitosan')}%"]
    ]
    
    t = Table(table_data, colWidths=[180, 150, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2d6a4f")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#d3d3d3")),
    ]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

st.header("1. Forward Mechanical Property Predictor")
st.markdown("Adjust input raw material ratios to calculate predicted physical outputs.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    base_mat = st.selectbox("Base Biopolymer", ["Cassava Starch", "Sugarcane Bagasse", "Corn Starch"])
with c2:
    gly_in = st.slider("Glycerin Plasticizer (%)", 5.0, 40.0, 20.0)
with c3:
    wat_in = st.slider("Water Content (%)", 10.0, 50.0, 30.0)
with c4:
    cit_in = st.slider("Citric Acid Crosslinker (%)", 0.5, 5.0, 2.0)

chitos_in = st.slider("Chitosan Additive (%)", 0.0, 3.0, 1.0)

if st.button("Run Forward Prediction", type="primary"):
    plan = st.session_state.get("user_plan", "free")
    count = st.session_state.get("daily_predictions", 0)

    if plan == "free" and count >= 3:
        st.error("🚫 Daily free prediction limit reached (3/3). Upgrade to continue.")
    else:
        if plan == "free":
            st.session_state["daily_predictions"] += 1

        if model:
            preds = model.predict([[gly_in, wat_in, cit_in, chitos_in]])[0]
            tensile, elasticity, water_abs = round(float(preds[0]), 2), round(float(preds[1]), 2), round(float(preds[2]), 2)
            
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Tensile Strength", f"{tensile} MPa")
            m2.metric("Elasticity", f"{elasticity} %")
            m3.metric("Water Absorption", f"{water_abs} %")

            if plan != "free":
                spec_data = {
                    "base_polymer": base_mat,
                    "tensile": tensile,
                    "elasticity": elasticity,
                    "water_abs": water_abs,
                    "glycerin": gly_in,
                    "water": wat_in,
                    "citric_acid": cit_in,
                    "chitosan": chitos_in
                }
                pdf_bytes = generate_pdf_spec_sheet(spec_data)
                st.download_button("📄 Download TDS Spec Sheet (PDF)", pdf_bytes, file_name="BioMatX_Spec.pdf", mime="application/pdf")
