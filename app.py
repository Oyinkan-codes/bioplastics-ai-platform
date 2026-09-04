import copy
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import minimize
from sklearn.neural_network import MLPRegressor
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from fpdf import FPDF

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Cloud-Native Bioplastic Formulation AI",
    page_icon="🌱",
    layout="wide"
)

# --- USER AUTHENTICATION & RBAC SETUP ---
USER_CREDENTIALS = {
    "odeborah": {"password": "SecurePass2026", "name": "Oyinkan Deborah", "role": "Admin"},
    "jsmith": {"password": "Password123", "name": "John Smith", "role": "Lab Researcher"}
}

if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None
if "name" not in st.session_state:
    st.session_state["name"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None

if not st.session_state["authentication_status"]:
    st.title("🔑 Bioplastic AI Platform Login")
    with st.form("login_form"):
        input_user = st.text_input("Username").strip()
        input_pass = st.text_input("Password", type="password").strip()
        submit = st.form_submit_button("Login")

    if submit:
        if input_user in USER_CREDENTIALS and USER_CREDENTIALS[input_user]["password"] == input_pass:
            st.session_state["authentication_status"] = True
            st.session_state["name"] = USER_CREDENTIALS[input_user]["name"]
            st.session_state["username"] = input_user
            st.session_state["role"] = USER_CREDENTIALS[input_user]["role"]
            st.rerun()
        else:
            st.session_state["authentication_status"] = False

authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")
role = st.session_state.get("role")

if authentication_status == False:
    st.error("Username or password is incorrect.")
    st.stop()
elif authentication_status is None:
    st.warning("Please log in with your credentials to access team dashboards.")
    st.stop()

# --- DATABASE CONNECTION (SUPABASE POSTGRESQL TRANSACTION POOLER) ---
@st.cache_resource
def init_db():
    try:
        db_url = st.secrets["postgres"]["url"]
        engine = create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        st.warning("Cloud DB connection failed or secret missing. Falling back to local SQLite.")
        engine = create_engine("sqlite:///bioplastic_fallback.db")
    return engine

engine = init_db()
Base = declarative_base()

class ExportLog(Base):
    __tablename__ = 'export_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
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

Base.metadata.create_all(engine)

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE export_logs ADD COLUMN IF NOT EXISTS user_id VARCHAR;"))
except Exception:
    pass

Session = sessionmaker(bind=engine)

def log_recipe_export(user_id, project_name, tensile, elastic, water_abs, recipe, cost_per_kg):
    session = Session()
    log_entry = ExportLog(
        user_id=user_id,
        project_name=project_name if project_name.strip() else f"Batch-{datetime.utcnow().strftime('%Y%m%d-%H%M')}",
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

# --- TRAIN ML SURROGATE MODEL ---
@st.cache_resource
def train_surrogate_model():
    np.random.seed(42)
    n_samples = 300
    agar = np.random.uniform(5, 30, n_samples)
    starch = np.random.uniform(10, 40, n_samples)
    glycerin = np.random.uniform(5, 25, n_samples)
    sorbitol = np.random.uniform(2, 15, n_samples)
    water = 100 - (agar + starch + glycerin + sorbitol)
    
    tensile = 12.0 + 0.8 * agar + 0.5 * starch - 0.6 * glycerin - 0.4 * sorbitol + np.random.normal(0, 1.5, n_samples)
    elastic = 150.0 + 12.0 * agar + 8.0 * starch - 10.0 * glycerin - 6.0 * sorbitol + np.random.normal(0, 15, n_samples)
    water_abs = 40.0 - 0.5 * agar - 0.2 * starch + 1.2 * glycerin + 0.8 * sorbitol + np.random.normal(0, 2.0, n_samples)
    
    X = np.column_stack([agar, starch, glycerin, sorbitol, water])
    y = np.column_stack([tensile, elastic, water_abs])
    
    model = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=1000, random_state=42)
    model.fit(X, y)
    return model

model = train_surrogate_model()

# --- PDF REPORT GENERATOR ---
def generate_pdf_report(user_name, project_name, recipe, tensile, elastic, water_abs, cost_per_kg, unit_sys):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Bioplastic Formulation Report: {project_name}", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, f"Generated By: {user_name} ({role}) | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "1. Formulation Recipe Components (% w/w):", ln=True)
    pdf.set_font("Arial", '', 11)
    for comp, val in recipe.items():
        pdf.cell(0, 6, f"  - {comp}: {val:.2f}%", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "2. Predicted Material Properties:", ln=True)
    pdf.set_font("Arial", '', 11)
    
    t_val = tensile * 145.038 if unit_sys == "Imperial (psi)" else tensile
    t_unit = "psi" if unit_sys == "Imperial (psi)" else "MPa"
    
    pdf.cell(0, 6, f"  - Tensile Strength: {t_val:.2f} {t_unit}", ln=True)
    pdf.cell(0, 6, f"  - Elastic Modulus: {elastic:.2f} MPa", ln=True)
    pdf.cell(0, 6, f"  - Water Absorption (24h): {water_abs:.2f}%", ln=True)
    pdf.cell(0, 6, f"  - Estimated Raw Material Cost: ${cost_per_kg:.2f} / kg", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR & UNIT TOGGLE ---
st.sidebar.title(f"Welcome, {name} 👋")
st.sidebar.caption(f"Role: **{role}**")
if st.sidebar.button("Logout"):
    st.session_state["authentication_status"] = None
    st.session_state["name"] = None
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Settings & Dynamic Costs")
unit_sys = st.sidebar.radio("Units System", ["SI (MPa)", "Imperial (psi)"])

# Dynamic Material Pricing (Admin customizable)
with st.sidebar.expander("💲 Ingredient Cost Settings ($/kg)"):
    cost_agar = st.number_input("Agar Cost", value=18.0, step=0.5)
    cost_starch = st.number_input("Starch Cost", value=1.5, step=0.1)
    cost_glyc = st.number_input("Glycerin Cost", value=2.5, step=0.1)
    cost_sorb = st.number_input("Sorbitol Cost", value=3.0, step=0.1)
    cost_water = st.number_input("Water Cost", value=0.05, step=0.01)

costs = {"Agar": cost_agar, "Starch": cost_starch, "Glycerin": cost_glyc, "Sorbitol": cost_sorb, "Water / Solvent": cost_water}

st.sidebar.markdown("---")
st.sidebar.header("🧪 Formulation Inputs (% w/w)")
project_name = st.sidebar.text_input("Project / Batch Name", "EcoFilm-Batch-A")

agar = st.sidebar.slider("Agar", 5.0, 30.0, 15.0, 0.5)
starch = st.sidebar.slider("Starch", 10.0, 40.0, 25.0, 0.5)
glycerin = st.sidebar.slider("Glycerin (Plasticizer)", 5.0, 25.0, 12.0, 0.5)
sorbitol = st.sidebar.slider("Sorbitol (Secondary Plasticizer)", 2.0, 15.0, 5.0, 0.5)

water = 100.0 - (agar + starch + glycerin + sorbitol)
if water < 0:
    st.sidebar.error("Warning: Solid components exceed 100%! Reduce values.")
    water = 0.0
else:
    st.sidebar.info(f"Water / Solvent balance: {water:.1f}%")

recipe = {"Agar": agar, "Starch": starch, "Glycerin": glycerin, "Sorbitol": sorbitol, "Water / Solvent": water}

# --- PREDICTIONS & COST ---
input_array = np.array([[agar, starch, glycerin, sorbitol, water]])
preds = model.predict(input_array)[0]
tensile_pred, elastic_pred, water_abs_pred = preds[0], preds[1], preds[2]

est_cost_per_kg = sum((recipe[k] / 100.0) * costs[k] for k in recipe)

# --- MAIN DASHBOARD INTERFACE ---
st.title("🌱 Cloud-Native Bioplastic AI Platform")

col1, col2, col3, col4 = st.columns(4)
tensile_display = tensile_pred * 145.038 if unit_sys == "Imperial (psi)" else tensile_pred
unit_label = "psi" if unit_sys == "Imperial (psi)" else "MPa"

col1.metric("Tensile Strength", f"{tensile_display:.2f} {unit_label}")
col2.metric("Elastic Modulus", f"{elastic_pred:.2f} MPa")
col3.metric("Water Absorption", f"{water_abs_pred:.2f}%")
col4.metric("Est. Cost", f"${est_cost_per_kg:.2f} / kg")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Formulation Analysis", 
    "🎯 Recipe Inverse Optimizer", 
    "🏭 Batch Batch Scaling", 
    "🌐 3D Surface Space", 
    "📁 Team Log Database"
])

with tab1:
    st.subheader("Component Mass Fraction")
    df_recipe = pd.DataFrame(list(recipe.items()), columns=["Component", "Percentage"])
    fig_pie = px.pie(df_recipe, values="Percentage", names="Component", title="Mass Allocation (% w/w)", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("🎯 Inverse Formulation Optimizer")
    st.write("Specify your desired physical properties, and AI will optimize the lowest-cost chemical ratio.")
    
    col_t, col_w = st.columns(2)
    target_tensile = col_t.number_input("Target Tensile Strength (MPa)", value=20.0, step=1.0)
    target_water = col_w.number_input("Max Target Water Absorption (%)", value=25.0, step=1.0)
    
    if st.button("🚀 Calculate Optimal Recipe"):
        def objective(x):
            a, s, g, sb = x
            w = 100.0 - (a + s + g + sb)
            p = model.predict([[a, s, g, sb, w]])[0]
            # Loss: penalty for target divergence + cost minimization
            cost = (a*costs["Agar"] + s*costs["Starch"] + g*costs["Glycerin"] + sb*costs["Sorbitol"] + w*costs["Water / Solvent"])/100.0
            penalty = (p[0] - target_tensile)**2 + max(0, p[2] - target_water)**2 * 10
            return cost + penalty

        bounds = [(5, 30), (10, 40), (5, 25), (2, 15)]
        res = minimize(objective, [15, 25, 12, 5], bounds=bounds)
        
        opt_a, opt_s, opt_g, opt_sb = res.x
        opt_w = 100.0 - sum(res.x)
        opt_recipe = {"Agar": opt_a, "Starch": opt_s, "Glycerin": opt_g, "Sorbitol": opt_sb, "Water": opt_w}
        
        st.success("Optimization Complete!")
        st.dataframe(pd.DataFrame(list(opt_recipe.items()), columns=["Component", "Optimized % w/w"]))

with tab3:
    st.subheader("🏭 Production Batch Calculator")
    batch_size_kg = st.number_input("Enter Total Batch Weight to Produce (kg)", value=50.0, step=5.0)
    
    batch_data = []
    for comp, pct in recipe.items():
        mass_kg = (pct / 100.0) * batch_size_kg
        cost_comp = mass_kg * costs[comp]
        batch_data.append({"Component": comp, "% w/w": f"{pct:.1f}%", "Weight Required (kg)": f"{mass_kg:.2f} kg", "Cost ($)": f"${cost_comp:.2f}"})
    
    st.table(pd.DataFrame(batch_data))
    st.info(f"Total Batch Material Cost: **${est_cost_per_kg * batch_size_kg:.2f}**")

with tab4:
    st.subheader("3D Response Surface (Agar vs Glycerin)")
    grid_a = np.linspace(5, 30, 15)
    grid_g = np.linspace(5, 25, 15)
    GA, GG = np.meshgrid(grid_a, grid_g)
    Z_tensile = 12.0 + 0.8 * GA + 0.5 * starch - 0.6 * GG - 0.4 * sorbitol
    
    fig_3d = go.Figure(data=[go.Surface(z=Z_tensile, x=GA, y=GG, colorscale='Viridis')])
    fig_3d.update_layout(scene=dict(xaxis_title="Agar (%)", yaxis_title="Glycerin (%)", zaxis_title="Tensile (MPa)"))
    st.plotly_chart(fig_3d, use_container_width=True)

with tab5:
    st.subheader("📁 Saved Formulation Records")
    col_dl, col_save = st.columns(2)
    
    pdf_bytes = generate_pdf_report(name, project_name, recipe, tensile_pred, elastic_pred, water_abs_pred, est_cost_per_kg, unit_sys)
    col_dl.download_button("📄 Export PDF Report", data=pdf_bytes, file_name=f"{project_name}_report.pdf", mime="application/pdf")
    
    if col_save.button("💾 Save Batch Run to Database"):
        log_recipe_export(username, project_name, tensile_pred, elastic_pred, water_abs_pred, recipe, est_cost_per_kg)
        st.success("Successfully logged batch data to Supabase!")

    st.markdown("---")
    
    # Query database based on Role (Admin sees all, Researcher sees own logs)
    session = Session()
    if role == "Admin":
        st.write("🔍 **Admin Access:** Displaying team-wide records.")
        logs = session.query(ExportLog).order_by(ExportLog.timestamp.desc()).all()
    else:
        st.write(f"🔍 Displaying user logs for **{name}**.")
        logs = session.query(ExportLog).filter(ExportLog.user_id == username).order_by(ExportLog.timestamp.desc()).all()
    session.close()

    if logs:
        log_data = [{
            "User": log.user_id,
            "Batch Name": log.project_name,
            "Date": log.timestamp.strftime("%Y-%m-%d %H:%M"),
            "Tensile (MPa)": round(log.tensile_strength, 2),
            "Elastic (MPa)": round(log.elastic_modulus, 2),
            "Water Abs. (%)": round(log.water_absorption, 2),
            "Cost ($/kg)": round(log.est_cost_per_kg, 2)
        } for log in logs]
        
        df_logs = pd.DataFrame(log_data)
        
        # Search Filter
        search_query = st.text_input("🔍 Search Logs by Project Name or User").strip().lower()
        if search_query:
            df_logs = df_logs[df_logs["Batch Name"].str.lower().str.contains(search_query) | df_logs["User"].str.lower().str.contains(search_query)]
        
        st.dataframe(df_logs, use_container_width=True)
        
        # CSV Download Button
        csv_data = df_logs.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Logs to CSV", data=csv_data, file_name="bioplastic_logs.csv", mime="text/csv")
    else:
        st.info("No logs found.")
