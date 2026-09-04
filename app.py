import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker
from fpdf import FPDF

st.set_page_config(page_title="Bioplastics AI Platform", layout="wide")

# --- DATABASE SETUP ---
Base = declarative_base()

class Formulation(Base):
    __tablename__ = 'formulations'
    id = Column(Integer, primary_key=True)
    batch_code = Column(String)
    agar_percent = Column(Float)
    starch_percent = Column(Float)
    glycerin_percent = Column(Float)
    sorbitol_percent = Column(Float)
    water_percent = Column(Float)

class PropertyTest(Base):
    __tablename__ = 'property_tests'
    id = Column(Integer, primary_key=True)
    formulation_id = Column(Integer, ForeignKey('formulations.id'))
    tensile_strength_mpa = Column(Float)
    elastic_modulus_gpa = Column(Float)
    water_absorption_percent = Column(Float)

class ExportLog(Base):
    __tablename__ = 'export_logs'
    id = Column(Integer, primary_key=True)
    project_name = Column(String, default="Unnamed Project")
    timestamp = Column(DateTime, default=datetime.utcnow)
    tensile_strength = Column(Float)
    elastic_modulus = Column(Float)
    water_absorption = Column(Float)
    agar_percent = Column(Float)
    starch_percent = Column(Float)
    glycerin_percent = Column(Float)
    sorbitol_percent = Column(Float)
    water_percent = Column(Float)
    est_cost_per_kg = Column(Float, default=0.0)

engine = create_engine('sqlite:///bioplastics.db')

Base.metadata.create_all(engine)

def upgrade_db_schema():
    with engine.connect() as conn:
        for col in ['starch_percent', 'sorbitol_percent']:
            try:
                conn.execute(text(f"ALTER TABLE formulations ADD COLUMN {col} FLOAT DEFAULT 0.0;"))
                conn.commit()
            except Exception:
                pass
        for col in [('project_name', "VARCHAR DEFAULT 'Unnamed Project'"), ('est_cost_per_kg', 'FLOAT DEFAULT 0.0')]:
            try:
                conn.execute(text(f"ALTER TABLE export_logs ADD COLUMN {col[0]} {col[1]};"))
                conn.commit()
            except Exception:
                pass

upgrade_db_schema()

Session = sessionmaker(bind=engine)

def log_recipe_export(project_name, tensile, elastic, water_abs, recipe, cost_per_kg):
    session = Session()
    log_entry = ExportLog(
        project_name=project_name if project_name.strip() else "Batch-" + datetime.utcnow().strftime("%Y%m%d-%H%M"),
        tensile_strength=tensile,
        elastic_modulus=elastic,
        water_absorption=water_abs,
        agar_percent=recipe["Agar"],
        starch_percent=recipe["Starch"],
        glycerin_percent=recipe["Glycerin"],
        sorbitol_percent=recipe["Sorbitol"],
        water_percent=recipe["Water / Solvent"],
        est_cost_per_kg=cost_per_kg
    )
    session.add(log_entry)
    session.commit()
    session.close()

# --- MODEL TRAINING ---
@st.cache_resource
def load_and_train():
    session = Session()
    query = session.query(Formulation, PropertyTest).join(
        PropertyTest, Formulation.id == PropertyTest.formulation_id
    )
    
    data = []
    for form, test in query.all():
        data.append({
            'agar_percent': form.agar_percent or 0.0,
            'starch_percent': getattr(form, 'starch_percent', 0.0) or 0.0,
            'glycerin_percent': form.glycerin_percent or 0.0,
            'sorbitol_percent': getattr(form, 'sorbitol_percent', 0.0) or 0.0,
            'tensile_strength': test.tensile_strength_mpa,
            'elastic_modulus': test.elastic_modulus_gpa,
            'water_absorption': test.water_absorption_percent
        })
    session.close()
    
    df = pd.DataFrame(data)
    
    X = df[['tensile_strength', 'elastic_modulus', 'water_absorption']].values
    y = df[['agar_percent', 'starch_percent', 'glycerin_percent', 'sorbitol_percent']].values
    
    x_scaler = MinMaxScaler()
    y_scaler = MinMaxScaler()
    
    X_scaled = x_scaler.fit_transform(X)
    y_scaled = y_scaler.fit_transform(y)
    
    model = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
    model.fit(X_scaled, y_scaled)
    
    return model, x_scaler, y_scaler

model, x_scaler, y_scaler = load_and_train()

# --- PDF GENERATOR HELPER ---
def create_pdf_report(project_name, tensile, elastic, water_abs, recipe, cost_per_kg):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Bioplastics AI - Formulation Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Batch / Project Identifier: {project_name}", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "1. Target Mechanical Properties", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"  - Tensile Strength: {tensile:.2f} MPa", ln=True)
    pdf.cell(0, 6, f"  - Elastic Modulus: {elastic:.2f} GPa", ln=True)
    pdf.cell(0, 6, f"  - Water Absorption: {water_abs:.2f} %", ln=True)
    pdf.ln(8)
    
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "2. Predicted Chemical Recipe Ratios", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for component, val in recipe.items():
        pdf.cell(0, 6, f"  - {component}: {val:.2f}%", ln=True)
        
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "3. Estimated Economic Analysis", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"  - Estimated Raw Material Cost: ${cost_per_kg:.2f} / kg", ln=True)

    pdf.ln(12)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, "Note: Ratios are predicted using a multi-layer neural network.", ln=True)
    
    return bytes(pdf.output())

# --- APP LAYOUT ---
st.title("🌱 Bioplastics AI Formulation Platform")
st.write("Adjust target properties to generate optimal chemical formulation ratios, cost projections, and sensitivity analysis.")

# Sidebar Controls
st.sidebar.header("💵 Raw Material Unit Costs ($/kg)")
cost_agar = st.sidebar.number_input("Agar ($/kg)", value=25.0, step=1.0)
cost_starch = st.sidebar.number_input("Starch ($/kg)", value=1.5, step=0.1)
cost_glycerin = st.sidebar.number_input("Glycerin ($/kg)", value=2.0, step=0.1)
cost_sorbitol = st.sidebar.number_input("Sorbitol ($/kg)", value=2.5, step=0.1)
cost_water = st.sidebar.number_input("Water/Solvent ($/kg)", value=0.05, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Multi-Objective Trade-Off")

mode = st.sidebar.radio("Optimization Mode", ["Manual Target Sliders", "Constrained Pareto Optimizer"])

# Add Hard Constraint Controls
if mode == "Constrained Pareto Optimizer":
    st.sidebar.markdown("### 🛑 Hard Constraints")
    max_budget = st.sidebar.number_input("Max Budget ($/kg)", value=6.00, step=0.50, min_value=0.50)
    max_agar_limit = st.sidebar.slider("Max Allowed Agar (%)", 5.0, 50.0, 25.0, 1.0)
    max_starch_limit = st.sidebar.slider("Max Allowed Starch (%)", 5.0, 50.0, 30.0, 1.0)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Target Mechanical Properties")
    project_code = st.text_input("Project / Batch Code", value="BIO-BATCH-001")
    
    elastic = st.slider("Elastic Modulus (GPa)", 0.5, 3.5, 2.0, 0.1)
    water_abs = st.slider("Water Absorption (%)", 20.0, 60.0, 40.0, 1.0)

    if mode == "Manual Target Sliders":
        tensile = st.slider("Tensile Strength (MPa)", 10.0, 50.0, 30.0, 0.5)
    else:
        st.markdown("### ⚖️ Trade-Off Preference")
        trade_off_weight = st.slider(
            "Priority Weighting", 
            min_value=0.0, 
            max_value=1.0, 
            value=0.5, 
            step=0.05,
            help="0.0 = Absolute Lowest Cost | 1.0 = Absolute Highest Tensile Strength"
        )
        
        # Pareto Search evaluation loop across 150 points for granular evaluation
        search_tensile_range = np.linspace(10.0, 50.0, 150)
        candidate_evals = []

        for t_val in search_tensile_range:
            X_s = x_scaler.transform([[t_val, elastic, water_abs]])
            pred_s_scaled = model.predict(X_s)
            pred_s = y_scaler.inverse_transform(pred_s_scaled)[0]

            a_p = max(0.0, float(pred_s[0]))
            s_p = max(0.0, float(pred_s[1]))
            g_p = max(0.0, float(pred_s[2]))
            sob_p = max(0.0, float(pred_s[3]))
            sol_p = max(0.0, 100.0 - (a_p + s_p + g_p + sob_p))

            cost_eval = (
                (a_p / 100.0) * cost_agar +
                (s_p / 100.0) * cost_starch +
                (g_p / 100.0) * cost_glycerin +
                (sob_p / 100.0) * cost_sorbitol +
                (sol_p / 100.0) * cost_water
            )
            candidate_evals.append({
                "tensile": t_val, 
                "cost": cost_eval,
                "agar": a_p,
                "starch": s_p
            })

        df_candidates = pd.DataFrame(candidate_evals)

        # APPLY HARD CONSTRAINTS FILTERING
        valid_mask = (
            (df_candidates["cost"] <= max_budget) &
            (df_candidates["agar"] <= max_agar_limit) &
            (df_candidates["starch"] <= max_starch_limit)
        )
        
        df_valid = df_candidates[valid_mask].copy()

        if df_valid.empty:
            st.error(f"⚠️ No valid formulation found satisfying budget <= ${max_budget:.2f}/kg, Agar <= {max_agar_limit}%, and Starch <= {max_starch_limit}%. Defaulting to fallback target.")
            tensile = 10.0
        else:
            # MinMax Normalization on valid candidates only
            c_min, c_max = df_valid["cost"].min(), df_valid["cost"].max()
            t_min, t_max = df_valid["tensile"].min(), df_valid["tensile"].max()

            df_valid["norm_cost"] = (df_valid["cost"] - c_min) / (c_max - c_min + 1e-6)
            df_valid["norm_tensile"] = (df_valid["tensile"] - t_min) / (t_max - t_min + 1e-6)
            
            df_valid["score"] = (
                (1.0 - trade_off_weight) * (1.0 - df_valid["norm_cost"]) + 
                trade_off_weight * df_valid["norm_tensile"]
            )

            best_row = df_valid.loc[df_valid["score"].idxmax()]
            tensile = round(float(best_row["tensile"]), 2)
            
            st.success(f"✅ **Constrained Optimal Target:** `{tensile} MPa` (Valid candidates: {len(df_valid)}/150)")

with col2:
    st.subheader("AI Recommended Recipe & Economics")
    X_in = x_scaler.transform([[tensile, elastic, water_abs]])
    pred_scaled = model.predict(X_in)
    pred_actual = y_scaler.inverse_transform(pred_scaled)[0]
    
    agar_pct = max(0.0, float(pred_actual[0]))
    starch_pct = max(0.0, float(pred_actual[1]))
    gly_pct = max(0.0, float(pred_actual[2]))
    sorb_pct = max(0.0, float(pred_actual[3]))
    solvent_pct = max(0.0, 100.0 - (agar_pct + starch_pct + gly_pct + sorb_pct))
    
    est_cost_per_kg = (
        (agar_pct / 100.0) * cost_agar +
        (starch_pct / 100.0) * cost_starch +
        (gly_pct / 100.0) * cost_glycerin +
        (sorb_pct / 100.0) * cost_sorbitol +
        (solvent_pct / 100.0) * cost_water
    )
    
    st.metric("Recommended Agar (%)", f"{agar_pct:.2f}%")
    st.metric("Recommended Starch (%)", f"{starch_pct:.2f}%")
    st.metric("Recommended Glycerin (%)", f"{gly_pct:.2f}%")
    st.metric("Recommended Sorbitol (%)", f"{sorb_pct:.2f}%")
    st.metric("Water / Solvent Balance (%)", f"{solvent_pct:.2f}%")
    
    st.markdown("---")
    st.metric("💡 Estimated Raw Material Cost", f"${est_cost_per_kg:.2f} / kg")

    recipe_dict = {
        "Agar": agar_pct,
        "Starch": starch_pct,
        "Glycerin": gly_pct,
        "Sorbitol": sorb_pct,
        "Water / Solvent": solvent_pct
    }
    
    pdf_bytes = create_pdf_report(project_code, tensile, elastic, water_abs, recipe_dict, est_cost_per_kg)
    
    filename_clean = "".join(c for c in project_code if c.isalnum() or c in ('-', '_')).strip() or "bioplastic_report"

    if st.download_button(
        label=f"📄 Export PDF Report for '{project_code}'",
        data=pdf_bytes,
        file_name=f"{filename_clean}.pdf",
        mime="application/pdf",
        use_container_width=True,
        on_click=log_recipe_export,
        args=(project_code, tensile, elastic, water_abs, recipe_dict, est_cost_per_kg)
    ):
        st.success(f"Report for '{project_code}' downloaded and logged with cost analysis!")

# --- MULTI-VARIABLE SENSITIVITY ANALYSIS ---
st.markdown("---")
tab1, tab2 = st.tabs(["📊 Formulation Composition Shift", "📈 Tensile vs. Cost Curve"])

tensile_range = np.linspace(10.0, 50.0, 50)
composition_rows = []
cost_rows = []

for t_val in tensile_range:
    X_sample = x_scaler.transform([[t_val, elastic, water_abs]])
    pred_sample_scaled = model.predict(X_sample)
    pred_sample = y_scaler.inverse_transform(pred_sample_scaled)[0]
    
    a_pct = max(0.0, float(pred_sample[0]))
    s_pct = max(0.0, float(pred_sample[1]))
    g_pct = max(0.0, float(pred_sample[2]))
    sob_pct = max(0.0, float(pred_sample[3]))
    sol_pct = max(0.0, 100.0 - (a_pct + s_pct + g_pct + sob_pct))
    
    c_kg = (
        (a_pct / 100.0) * cost_agar +
        (s_pct / 100.0) * cost_starch +
        (g_pct / 100.0) * cost_glycerin +
        (sob_pct / 100.0) * cost_sorbitol +
        (sol_pct / 100.0) * cost_water
    )
    
    composition_rows.extend([
        {"Tensile Strength (MPa)": t_val, "Component Ratio (%)": a_pct, "Ingredient": "Agar"},
        {"Tensile Strength (MPa)": t_val, "Component Ratio (%)": s_pct, "Ingredient": "Starch"},
        {"Tensile Strength (MPa)": t_val, "Component Ratio (%)": g_pct, "Ingredient": "Glycerin"},
        {"Tensile Strength (MPa)": t_val, "Component Ratio (%)": sob_pct, "Ingredient": "Sorbitol"},
        {"Tensile Strength (MPa)": t_val, "Component Ratio (%)": sol_pct, "Ingredient": "Water / Solvent"}
    ])
    
    cost_rows.append({
        "Tensile Strength (MPa)": round(t_val, 2),
        "Estimated Cost ($/kg)": round(c_kg, 2),
        "Agar Ratio (%)": round(a_pct, 2)
    })

df_comp = pd.DataFrame(composition_rows)
df_cost = pd.DataFrame(cost_rows)

with tab1:
    st.subheader("Component Proportion Shifts Across Tensile Target")
    fig_area = px.area(
        df_comp,
        x="Tensile Strength (MPa)",
        y="Component Ratio (%)",
        color="Ingredient",
        title="Formulation Component Breakdown vs. Target Tensile Strength",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig_area.add_vline(
        x=tensile, 
        line_width=2, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f" Constrained Selection ({tensile} MPa)",
        annotation_position="top left"
    )
    
    fig_area.update_layout(
        template="plotly_white",
        yaxis_title="Composition Percentage (%)",
        xaxis_title="Tensile Strength (MPa)"
    )
    st.plotly_chart(fig_area, use_container_width=True)

with tab2:
    st.subheader("Tensile Strength vs. Cost Sensitivity Analysis")
    fig_cost = px.line(
        df_cost, 
        x="Tensile Strength (MPa)", 
        y="Estimated Cost ($/kg)", 
        hover_data=["Agar Ratio (%)"],
        title="Estimated Batch Cost ($/kg) vs Target Tensile Strength (MPa)",
        markers=True
    )
    
    # Highlight budget threshold if constrained optimizer is active
    if mode == "Constrained Pareto Optimizer":
        fig_cost.add_hline(
            y=max_budget,
            line_width=2,
            line_dash="dot",
            line_color="red",
            annotation_text=f" Max Budget Limit (${max_budget:.2f}/kg)",
            annotation_position="bottom right"
        )
    
    fig_cost.add_scatter(
        x=[tensile],
        y=[est_cost_per_kg],
        mode="markers",
        marker=dict(size=14, color="red"),
        name="Constrained Target"
    )
    
    fig_cost.update_layout(template="plotly_white")
    st.plotly_chart(fig_cost, use_container_width=True)

# --- HISTORICAL LOGS DISPLAY ---
with st.expander("📊 View Export History Log"):
    session = Session()
    logs = session.query(ExportLog).order_by(ExportLog.timestamp.desc()).all()
    session.close()
    
    if logs:
        log_data = [{
            "Project / Batch": log.project_name,
            "Timestamp (UTC)": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Tensile (MPa)": log.tensile_strength,
            "Elastic (GPa)": log.elastic_modulus,
            "Water Abs (%)": log.water_absorption,
            "Agar (%)": f"{log.agar_percent:.2f}",
            "Starch (%)": f"{log.starch_percent:.2f}",
            "Glycerin (%)": f"{log.glycerin_percent:.2f}",
            "Sorbitol (%)": f"{log.sorbitol_percent:.2f}",
            "Solvent (%)": f"{log.water_percent:.2f}",
            "Est. Cost ($/kg)": f"${log.est_cost_per_kg:.2f}" if log.est_cost_per_kg else "$0.00"
        } for log in logs]
        st.dataframe(pd.DataFrame(log_data), use_container_width=True)
    else:
        st.info("No exported recipes logged yet.")
