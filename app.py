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

# --- SYNTHETIC DATA GENERATOR ---
def seed_synthetic_data(num_samples=30):
    session = Session()
    np.random.seed(42)
    
    for i in range(num_samples):
        agar = float(np.random.uniform(10, 40))
        starch = float(np.random.uniform(5, 30))
        glycerin = float(np.random.uniform(5, 25))
        sorbitol = float(np.random.uniform(2, 15))
        water = max(0.0, 100.0 - (agar + starch + glycerin + sorbitol))
        
        tensile = (agar * 0.8) + (starch * 0.4) - (glycerin * 0.3) + np.random.normal(0, 2)
        elastic = (agar * 0.05) + (starch * 0.03) + np.random.normal(0, 0.2)
        water_abs = 60.0 - (agar * 0.5) - (starch * 0.2) + (glycerin * 0.4) + np.random.normal(0, 3)
        
        form = Formulation(
            batch_code=f"SYN-{i+1:03d}",
            agar_percent=agar,
            starch_percent=starch,
            glycerin_percent=glycerin,
            sorbitol_percent=sorbitol,
            water_percent=water
        )
        session.add(form)
        session.flush()
        
        prop = PropertyTest(
            formulation_id=form.id,
            tensile_strength_mpa=max(5.0, tensile),
            elastic_modulus_gpa=max(0.1, elastic),
            water_absorption_percent=max(10.0, water_abs)
        )
        session.add(prop)
        
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
    
    if not data:
        seed_synthetic_data(40)
        return load_and_train()
    
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

# --- PDF GENERATOR ---
def create_pdf_report(project_name, tensile, elastic, water_abs, recipe, cost_per_kg, batch_kg, discount_pct, co2_per_kg, bio_days):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Bioplastics AI - Formulation & Sustainability Report", ln=True, align="C")
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
    pdf.cell(0, 8, f"2. Predicted Recipe Ratios & Batch Requirements ({batch_kg:.1f} kg)", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for component, val in recipe.items():
        mass_kg = (val / 100.0) * batch_kg
        pdf.cell(0, 6, f"  - {component}: {val:.2f}% ({mass_kg:.2f} kg)", ln=True)
        
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "3. Economic & Environmental Impact Projections", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"  - Applied Volume Discount: {discount_pct*100:.0f}% off", ln=True)
    pdf.cell(0, 6, f"  - Estimated Unit Cost: ${cost_per_kg:.2f} / kg", ln=True)
    pdf.cell(0, 6, f"  - Total Production Cost: ${cost_per_kg * batch_kg:.2f}", ln=True)
    pdf.cell(0, 6, f"  - Carbon Footprint: {co2_per_kg:.2f} kg CO2e / kg", ln=True)
    pdf.cell(0, 6, f"  - Total Batch CO2 Impact: {co2_per_kg * batch_kg:.2f} kg CO2e", ln=True)
    pdf.cell(0, 6, f"  - Soil Degradation Estimate: ~{bio_days:.0f} days to 90% mass loss", ln=True)

    pdf.ln(12)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, "Note: Ratios are predicted using a multi-layer neural network.", ln=True)
    return bytes(pdf.output())

# --- APP LAYOUT ---
st.title("🌱 Bioplastics AI Formulation & Sustainability Platform")
st.write("Optimize mechanical targets, raw material costs, manufacturing safety thresholds, and carbon footprints.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("💵 Base Unit Costs ($/kg)")
c_agar_base = st.sidebar.number_input("Agar ($/kg)", value=25.0, step=1.0)
c_starch_base = st.sidebar.number_input("Starch ($/kg)", value=1.5, step=0.1)
c_gly_base = st.sidebar.number_input("Glycerin ($/kg)", value=2.0, step=0.1)
c_sorb_base = st.sidebar.number_input("Sorbitol ($/kg)", value=2.5, step=0.1)
c_water_base = st.sidebar.number_input("Water/Solvent ($/kg)", value=0.05, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("🌍 Carbon Footprint (kg CO₂e/kg)")
co2_agar = st.sidebar.number_input("Agar CO₂ Factor", value=1.8, step=0.1)
co2_starch = st.sidebar.number_input("Starch CO₂ Factor", value=0.6, step=0.1)
co2_gly = st.sidebar.number_input("Glycerin CO₂ Factor", value=1.2, step=0.1)
co2_sorb = st.sidebar.number_input("Sorbitol CO₂ Factor", value=1.4, step=0.1)
co2_water = st.sidebar.number_input("Water CO₂ Factor", value=0.01, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("📦 Batch Volume & Discounts")
batch_kg = st.sidebar.number_input("Batch Size (kg)", value=100.0, step=10.0, min_value=1.0)

discount_pct = 0.00
if batch_kg >= 500:
    discount_pct = 0.10
elif batch_kg >= 100:
    discount_pct = 0.05

cost_agar = c_agar_base * (1.0 - discount_pct)
cost_starch = c_starch_base * (1.0 - discount_pct)
cost_glycerin = c_gly_base * (1.0 - discount_pct)
cost_sorbitol = c_sorb_base * (1.0 - discount_pct)
cost_water = c_water_base * (1.0 - discount_pct)

if discount_pct > 0:
    st.sidebar.success(f"🎉 **{discount_pct*100:.0f}% Bulk Discount Applied** for {batch_kg:.0f} kg batch!")

st.sidebar.markdown("---")
st.sidebar.header("🎯 Multi-Objective Trade-Off")
mode = st.sidebar.radio("Optimization Mode", ["Manual Target Sliders", "Constrained Pareto Optimizer"])

if mode == "Constrained Pareto Optimizer":
    st.sidebar.markdown("### 🛑 Hard Constraints")
    max_budget = st.sidebar.number_input("Max Budget ($/kg)", value=6.00, step=0.50, min_value=0.50)
    max_agar_limit = st.sidebar.slider("Max Allowed Agar (%)", 5.0, 50.0, 25.0, 1.0)
    max_starch_limit = st.sidebar.slider("Max Allowed Starch (%)", 5.0, 50.0, 30.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.header("🧪 Model Maintenance")
if st.sidebar.button("⚡ Seed +30 Synthetic Training Trials"):
    seed_synthetic_data(30)
    st.cache_resource.clear()
    st.sidebar.success("Added 30 synthetic trials and retrained AI model!")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Target Mechanical Properties")
    project_code = st.text_input("Project / Batch Code", value="BIO-BATCH-001")
    
    elastic = st.slider("Elastic Modulus (GPa)", 0.5, 3.5, 2.0, 0.1)
    water_abs = st.slider("Water Absorption (%)", 20.0, 60.0, 40.0, 1.0)

    df_candidates_all = pd.DataFrame()

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

        df_candidates_all = pd.DataFrame(candidate_evals)

        valid_mask = (
            (df_candidates_all["cost"] <= max_budget) &
            (df_candidates_all["agar"] <= max_agar_limit) &
            (df_candidates_all["starch"] <= max_starch_limit)
        )
        
        df_valid = df_candidates_all[valid_mask].copy()

        if df_valid.empty:
            st.error(f"⚠️ No valid formulation satisfies budget <= ${max_budget:.2f}/kg, Agar <= {max_agar_limit}%, and Starch <= {max_starch_limit}%.")
            tensile = 10.0
        else:
            c_min, c_max = df_valid["cost"].min(), df_valid["cost"].max()
            t_min, t_max = df_valid["tensile"].min(), df_valid["tensile"].max()

            df_valid["norm_cost"] = (df_valid["cost"] - c_min) / (c_max - c_min + 1e-6)
            df_valid["norm_tensile"] = (df_valid["tensile"] - t_min) / (t_max - t_min + 1e-6)
            
            df_valid["score"] = (
                (1.0 - trade_off_weight) * (1.0 - df_valid["norm_cost"]) + 
                trade_off_weight * df_valid["norm_tensile"]
            )
            
            df_candidates_all = df_candidates_all.merge(df_valid[["tensile", "score"]], on="tensile", how="left").fillna(0)

            best_row = df_valid.loc[df_valid["score"].idxmax()]
            tensile = round(float(best_row["tensile"]), 2)
            
            st.success(f"✅ **Constrained Optimal Target:** `{tensile} MPa` ({len(df_valid)}/150 valid candidates)")

with col2:
    st.subheader("AI Recommended Recipe & Metrics")
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
    
    total_batch_cost = est_cost_per_kg * batch_kg

    est_co2_per_kg = (
        (agar_pct / 100.0) * co2_agar +
        (starch_pct / 100.0) * co2_starch +
        (gly_pct / 100.0) * co2_gly +
        (sorb_pct / 100.0) * co2_sorb +
        (solvent_pct / 100.0) * co2_water
    )
    total_co2_batch = est_co2_per_kg * batch_kg
    
    plasticizer_total = gly_pct + sorb_pct
    est_bio_days = max(14.0, 120.0 - (plasticizer_total * 1.5) - (starch_pct * 0.8))

    st.markdown("### 🚨 Manufacturing Risk Evaluation")
    risk_found = False
    
    if plasticizer_total < 10.0:
        st.warning("⚠️ **Brittleness Risk:** Total plasticizer (Glycerin + Sorbitol) is under 10%. Material may crack upon drying.")
        risk_found = True
    if (agar_pct + starch_pct) > 50.0:
        st.warning("⚠️ **High Viscosity Alert:** Solid polymer load (Agar + Starch) exceeds 50%. Solution may become too thick to cast.")
        risk_found = True
    if starch_pct > 25.0 and water_abs < 30.0:
        st.info("💡 **Hydrophobicity Mismatch:** High starch content with low target water absorption may require crosslinking agents.")
        risk_found = True
        
    if not risk_found:
        st.success("✅ No critical manufacturing risks detected for this target formulation.")

    st.markdown("---")
    st.subheader("Recipe Component Ratios")
    st.metric("Agar", f"{agar_pct:.2f}%", f"{(agar_pct/100.0)*batch_kg:.2f} kg required")
    st.metric("Starch", f"{starch_pct:.2f}%", f"{(starch_pct/100.0)*batch_kg:.2f} kg required")
    st.metric("Glycerin", f"{gly_pct:.2f}%", f"{(gly_pct/100.0)*batch_kg:.2f} kg required")
    st.metric("Sorbitol", f"{sorb_pct:.2f}%", f"{(sorb_pct/100.0)*batch_kg:.2f} kg required")
    st.metric("Water / Solvent", f"{solvent_pct:.2f}%", f"{(solvent_pct/100.0)*batch_kg:.2f} kg required")
    
    st.markdown("---")
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("💡 Cost per kg", f"${est_cost_per_kg:.2f} / kg", f"{discount_pct*100:.0f}% bulk disc.")
    c_m2.metric("🌱 Carbon Intensity", f"{est_co2_per_kg:.2f} kg CO₂e/kg")
    c_m3.metric("⏳ Soil Degradation", f"~{est_bio_days:.0f} days", "To 90% Mass Loss")

    recipe_dict = {
        "Agar": agar_pct,
        "Starch": starch_pct,
        "Glycerin": gly_pct,
        "Sorbitol": sorb_pct,
        "Water / Solvent": solvent_pct
    }
    
    pdf_bytes = create_pdf_report(
        project_code, tensile, elastic, water_abs, recipe_dict, 
        est_cost_per_kg, batch_kg, discount_pct, est_co2_per_kg, est_bio_days
    )
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
        st.success(f"Report for '{project_code}' downloaded!")

# --- MULTI-VARIABLE SENSITIVITY ANALYSIS & TABS ---
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Composition Shift", 
    "📈 Tensile vs. Cost & CO₂", 
    "🎯 Pareto Frontier",
    "🌐 3D Trade-Off Space"
])

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
    
    co2_kg = (
        (a_pct / 100.0) * co2_agar +
        (s_pct / 100.0) * co2_starch +
        (g_pct / 100.0) * co2_gly +
        (sob_pct / 100.0) * co2_sorb +
        (sol_pct / 100.0) * co2_water
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
        "Estimated CO2 (kg CO2e/kg)": round(co2_kg, 2)
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
        annotation_text=f" Target ({tensile} MPa)",
        annotation_position="top left"
    )
    fig_area.update_layout(template="plotly_white", yaxis_title="Composition Percentage (%)", xaxis_title="Tensile Strength (MPa)")
    st.plotly_chart(fig_area, use_container_width=True)

with tab2:
    st.subheader("Tensile Strength vs. Cost & Environmental Footprint")
    fig_cost = px.line(
        df_cost, 
        x="Tensile Strength (MPa)", 
        y=["Estimated Cost ($/kg)", "Estimated CO2 (kg CO2e/kg)"],
        title="Economic Cost and Carbon Impact Curves",
        markers=True
    )
    if mode == "Constrained Pareto Optimizer":
        fig_cost.add_hline(
            y=max_budget,
            line_width=2,
            line_dash="dot",
            line_color="red",
            annotation_text=f" Max Budget (${max_budget:.2f}/kg)"
        )
    fig_cost.update_layout(template="plotly_white", yaxis_title="Metric Value")
    st.plotly_chart(fig_cost, use_container_width=True)

with tab3:
    st.subheader("2D Pareto Trade-Off Frontier")
    if not df_candidates_all.empty:
        fig_pareto = px.scatter(
            df_candidates_all,
            x="tensile",
            y="cost",
            color="score",
            color_continuous_scale="Viridis",
            labels={"tensile": "Tensile Strength (MPa)", "cost": "Estimated Cost ($/kg)", "score": "Optimization Score"},
            title="Pareto Frontier (Strength vs. Cost)"
        )
        fig_pareto.add_scatter(
            x=[tensile],
            y=[est_cost_per_kg],
            mode="markers",
            marker=dict(size=16, color="red", symbol="star"),
            name="Selected Optimal Point"
        )
        fig_pareto.update_layout(template="plotly_white")
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        st.info("Switch Optimization Mode to 'Constrained Pareto Optimizer' in the sidebar to view the interactive Pareto chart.")

with tab4:
    st.subheader("3D Multi-Variable Optimization Space")
    st.write("Rotate and zoom to analyze the multi-dimensional trade-off between mechanical strength, production cost, and environmental carbon intensity.")
    
    if not df_candidates_all.empty:
        candidate_co2 = []
        for _, row in df_candidates_all.iterrows():
            X_c = x_scaler.transform([[row["tensile"], elastic, water_abs]])
            pred_c_scaled = model.predict(X_c)
            pred_c = y_scaler.inverse_transform(pred_c_scaled)[0]
            
            a_c = max(0.0, float(pred_c[0]))
            s_c = max(0.0, float(pred_c[1]))
            g_c = max(0.0, float(pred_c[2]))
            sob_c = max(0.0, float(pred_c[3]))
            sol_c = max(0.0, 100.0 - (a_c + s_c + g_c + sob_c))
            
            co2_val = (
                (a_c / 100.0) * co2_agar +
                (s_c / 100.0) * co2_starch +
                (g_c / 100.0) * co2_gly +
                (sob_c / 100.0) * co2_sorb +
                (sol_c / 100.0) * co2_water
            )
            candidate_co2.append(co2_val)
            
        df_candidates_all["co2"] = candidate_co2

        fig_3d = px.scatter_3d(
            df_candidates_all,
            x="tensile",
            y="cost",
            z="co2",
            color="score",
            color_continuous_scale="Viridis",
            labels={
                "tensile": "Tensile Strength (MPa)", 
                "cost": "Cost ($/kg)", 
                "co2": "Carbon Footprint (kg CO₂e/kg)",
                "score": "Optimization Score"
            },
            title="3D Tensile Strength vs. Cost vs. Carbon Footprint Frontier"
        )
        
        fig_3d.add_scatter3d(
            x=[tensile],
            y=[est_cost_per_kg],
            z=[est_co2_per_kg],
            mode="markers",
            marker=dict(size=10, color="red", symbol="diamond"),
            name="Selected Target Point"
        )
        
        fig_3d.update_layout(
            template="plotly_white",
            margin=dict(l=0, r=0, b=0, t=40),
            height=600
        )
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        st.info("Switch Optimization Mode to 'Constrained Pareto Optimizer' in the sidebar to populate the 3D surface model.")

# --- HISTORICAL LOGS DISPLAY & CSV EXPORT ---
with st.expander("📊 View Export History Log & CSV Export"):
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
        
        df_log = pd.DataFrame(log_data)
        st.dataframe(df_log, use_container_width=True)
        
        csv_bytes = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full History as CSV",
            data=csv_bytes,
            file_name=f"bioplastics_history_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No exported recipes logged yet.")
