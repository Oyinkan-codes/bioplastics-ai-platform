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

# Supabase Client
from supabase import create_client, Client

# ReportLab imports for PDF Spec Sheet Generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


# ==========================================
# 1. PAGE CONFIGURATION & INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="BioMatX AI - Circular Economy Platform",
    page_icon="🌿",
    layout="wide"
)

# Initialize Supabase Client dynamically from Streamlit Secrets
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if url and key:
            return create_client(url, key)
        return None
    except Exception as e:
        st.warning(f"Operating in fallback/local mode. Supabase credentials missing or invalid: {e}")
        return None

supabase = init_supabase()

# Session State Setup
if "user" not in st.session_state:
    st.session_state["user"] = None

if "user_plan" not in st.session_state:
    st.session_state["user_plan"] = "free"

if "daily_predictions" not in st.session_state:
    st.session_state["daily_predictions"] = 0

if "last_prediction_date" not in st.session_state:
    st.session_state["last_prediction_date"] = datetime.date.today()

# Daily quota reset check
today = datetime.date.today()
if st.session_state["last_prediction_date"] < today:
    st.session_state["daily_predictions"] = 0
    st.session_state["last_prediction_date"] = today


# ==========================================
# 2. MACHINE LEARNING ENGINE & INVERSE OPTIMIZER
# ==========================================
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "bioplastic_rf_v1.pkl")

@st.cache_resource
def load_or_train_model():
    """Loads existing trained RandomForest model or generates baseline dataset and trains a new model."""
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except Exception:
            pass

    # Synthetic Dataset Generation for Bioplastic Properties
    np.random.seed(42)
    N = 1000
    
    glycerin = np.random.uniform(5, 40, N)
    water = np.random.uniform(10, 50, N)
    citric_acid = np.random.uniform(0.5, 5.0, N)
    chitosan = np.random.uniform(0.0, 3.0, N)
    
    X = np.column_stack([glycerin, water, citric_acid, chitosan])
    
    # Synthetic physical relationships:
    # Tensile Strength decreases with glycerin/water, increases with citric acid/chitosan
    tensile = 50.0 - (glycerin * 0.9) - (water * 0.4) + (citric_acid * 2.5) + (chitosan * 3.1) + np.random.normal(0, 1, N)
    # Elasticity increases with glycerin/water, decreases with crosslinkers
    elasticity = 2.0 + (glycerin * 2.2) + (water * 0.3) - (citric_acid * 0.8) + np.random.normal(0, 1, N)
    # Water absorption increases with water, decreases with crosslinkers/chitosan
    water_abs = 15.0 + (water * 0.8) - (glycerin * 0.1) - (citric_acid * 1.5) - (chitosan * 2.0) + np.random.normal(0, 1, N)
    
    y = np.column_stack([
        np.clip(tensile, 1.0, 100.0),
        np.clip(elasticity, 1.0, 150.0),
        np.clip(water_abs, 1.0, 90.0)
    ])
    
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return model

model = load_or_train_model()

def run_inverse_optimizer(target_tensile, target_elasticity, target_water_abs):
    """Calculates formulation ratios given target material specs using L-BFGS-B bounded optimization."""
    def objective(x):
        preds = model.predict([x])[0]
        return (preds[0] - target_tensile)**2 + (preds[1] - target_elasticity)**2 + (preds[2] - target_water_abs)**2

    bounds = [(5.0, 40.0), (10.0, 50.0), (0.5, 5.0), (0.0, 3.0)]
    initial_guess = [20.0, 30.0, 2.0, 1.0]
    
    res = minimize(objective, initial_guess, method='L-BFGS-B', bounds=bounds)
    opt_ratios = res.x
    predicted_outputs = model.predict([opt_ratios])[0]
    
    return {
        "glycerin": round(float(opt_ratios[0]), 2),
        "water": round(float(opt_ratios[1]), 2),
        "citric_acid": round(float(opt_ratios[2]), 2),
        "chitosan": round(float(opt_ratios[3]), 2),
        "achieved_tensile": round(float(predicted_outputs[0]), 2),
        "achieved_elasticity": round(float(predicted_outputs[1]), 2),
        "achieved_water_abs": round(float(predicted_outputs[2]), 2)
    }


# ==========================================
# 3. PDF TECHNICAL DATA SHEET (TDS) GENERATOR
# ==========================================
def generate_pdf_spec_sheet(data_dict):
    """Generates an in-memory PDF Technical Data Sheet using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1b4332"))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Heading3'], fontSize=12, textColor=colors.HexColor("#2d6a4f"))
    
    story.append(Paragraph("BioMatX Intelligence - Technical Data Sheet (TDS)", title_style))
    story.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 15))
    
    table_data = [
        ["Parameter", "Target Specification", "Predicted / Optimized Value"],
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
    story.append(Paragraph("<i>Disclaimer: Formulations are generated via predictive machine learning models. Lab verification is recommended prior to industrial scale production.</i>", styles['Italic']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


# ==========================================
# 4. SIDEBAR - AUTHENTICATION & USER CONTROLS
# ==========================================
st.sidebar.title("🌿 BioMatX Platform")

if not st.session_state["user"]:
    st.sidebar.subheader("🔐 Sign In / Access Dashboard")
    auth_mode = st.sidebar.radio("Account Action", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if auth_mode == "Sign Up":
        if st.sidebar.button("Create Account", type="primary"):
            if supabase:
                try:
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    st.sidebar.success("Account created! Check your email to confirm.")
                except Exception as e:
                    st.sidebar.error(f"Sign Up Error: {e}")
            else:
                st.session_state["user"] = {"email": email}
                st.session_state["user_plan"] = "free"
                st.rerun()
    else:
        if st.sidebar.button("Sign In", type="primary"):
            if supabase:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state["user"] = res.user
                    
                    profile = supabase.table("profiles").select("*").eq("id", res.user.id).execute()
                    if profile.data:
                        st.session_state["user_plan"] = profile.data[0].get("plan_tier", "free")
                        st.session_state["daily_predictions"] = profile.data[0].get("daily_prediction_count", 0)
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Login Failed: {e}")
            else:
                st.session_state["user"] = {"email": email}
                st.session_state["user_plan"] = "free"
                st.rerun()
else:
    user_email = getattr(st.session_state['user'], 'email', st.session_state['user'].get('email', 'User'))
    st.sidebar.write(f"Logged in as: **{user_email}**")
    st.sidebar.markdown(f"**Plan Tier:** `{st.session_state['user_plan'].upper()}`")
    
    if st.session_state["user_plan"] == "free":
        quota_left = max(0, 3 - st.session_state["daily_predictions"])
        st.sidebar.progress((3 - quota_left) / 3)
        st.sidebar.caption(f"Daily Free Quota Remaining: **{quota_left} / 3**")
    else:
        st.sidebar.success("⚡ Unlimited Access Active")

    if st.sidebar.button("Log Out"):
        if supabase:
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
        st.session_state["user"] = None
        st.session_state["user_plan"] = "free"
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Support: support@biomatx.ai")


# ==========================================
# 5. PUBLIC LANDING PAGE (UNAUTHENTICATED)
# ==========================================
def render_landing_page():
    st.markdown("# 🧪 Predict Bioplastic Formulations in Seconds")
    st.subheader("Accelerating Sustainable Materials Science with DeepTech Machine Learning")
    
    st.info("👋 Sign in or create a free account using the sidebar to access the live prediction engine.")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ❌ Traditional Method")
        st.write("• Months of trial-and-error in university labs")
        st.write("• High cost of raw chemical additives")
        st.write("• Unpredictable tensile and water absorption results")
    with c2:
        st.markdown("### ✅ BioMatX AI Engine")
        st.write("• Instant inverse property prediction")
        st.write("• Optimized for local agricultural waste streams")
        st.write("• Exportable Technical Data Sheets (TDS)")

    st.markdown("---")
    st.header("💳 Flexible Multi-Currency Pricing (Raenest)")
    p1, p2, p3 = st.columns(3)
    
    with p1:
        st.subheader("Free Plan")
        st.markdown("### $0 / month")
        st.write("• 3 Forward Predictions / day")
        st.write("• Basic Material Ratios")
        st.write("🔒 Teased Additive Formulas")
        
    with p2:
        st.subheader("Researcher Plan")
        st.markdown("### $12 / £9.50 / ₦15,000 /mo")
        st.write("• Unlimited Property Predictions")
        st.write("• Inverse Recipe Optimizer")
        st.write("• Downloadable PDF TDS Spec Sheets")
        
        c_usd, c_gbp, c_ngn = st.columns(3)
        with c_usd:
            st.link_button("Pay $12", st.secrets.get("RAENEST_RESEARCHER_USD_URL", "https://raenest.com"))
        with c_gbp:
            st.link_button("Pay £9.50", st.secrets.get("RAENEST_RESEARCHER_GBP_URL", "https://raenest.com"))
        with c_ngn:
            st.link_button("Pay ₦15,000", st.secrets.get("RAENEST_RESEARCHER_NGN_URL", "https://raenest.com"))
        
    with p3:
        st.subheader("Enterprise Plan")
        st.markdown("### $38.99 / £31.00 / ₦50,000 /mo")
        st.write("• All Researcher Features")
        st.write("• Batch Recipe History Logs")
        st.write("• Dedicated API Integration")
        
        ce_usd, ce_gbp, ce_ngn = st.columns(3)
        with ce_usd:
            st.link_button("Pay $38.99", st.secrets.get("RAENEST_ENTERPRISE_USD_URL", "https://raenest.com"))
        with ce_gbp:
            st.link_button("Pay £31.00", st.secrets.get("RAENEST_ENTERPRISE_GBP_URL", "https://raenest.com"))
        with ce_ngn:
            st.link_button("Pay ₦50,000", st.secrets.get("RAENEST_ENTERPRISE_NGN_URL", "https://raenest.com"))

    st.markdown("---")
    st.caption("© BioMatX Intelligence UK Ltd. Aligning with UN SDGs 9, 12, 13, 14 & 15.")


# ==========================================
# 6. DASHBOARD (AUTHENTICATED USER VIEW)
# ==========================================
def render_dashboard():
    user_email = getattr(st.session_state['user'], 'email', st.session_state['user'].get('email', 'User'))
    st.title("🧪 AI Bioplastic Formulation & Optimization Engine")
    st.caption(f"Welcome back, **{user_email}** | Plan: `{st.session_state['user_plan'].upper()}`")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔮 Predictive Modeler", 
        "🎯 Inverse Recipe Optimizer", 
        "📊 Interactive 3D Surfaces", 
        "💳 Upgrade Plan"
    ])

    # TAB 1: PREDICTIVE MODELER
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
            if st.session_state["user_plan"] == "free" and st.session_state["daily_predictions"] >= 3:
                st.error("🚫 Daily free prediction limit reached (3/3). Upgrade to the Researcher plan ($12/mo) to continue.")
            else:
                if st.session_state["user_plan"] == "free":
                    st.session_state["daily_predictions"] += 1
                    if supabase and hasattr(st.session_state["user"], "id"):
                        try:
                            supabase.table("profiles").update({"daily_prediction_count": st.session_state["daily_predictions"]}).eq("id", st.session_state["user"].id).execute()
                        except Exception:
                            pass
                
                preds = model.predict([[gly_in, wat_in, cit_in, chitos_in]])[0]
                tensile, elasticity, water_abs = round(float(preds[0]), 2), round(float(preds[1]), 2), round(float(preds[2]), 2)
                
                st.markdown("---")
                st.subheader("Predicted Mechanical Properties")
                m1, m2, m3 = st.columns(3)
                m1.metric("Tensile Strength", f"{tensile} MPa")
                m2.metric("Elasticity (Elongation)", f"{elasticity} %")
                m3.metric("Water Absorption (24h)", f"{water_abs} %")
                
                st.markdown("---")
                st.subheader("Additive Ratios & Formulation Spec")
                
                if st.session_state["user_plan"] == "free":
                    st.warning("🔒 Exact cross-linker optimization and commercial spec downloads are locked on the Free Tier.")
                    st.info("💡 Upgrade to **Researcher ($12/mo)** to unlock exact formulation metrics and PDF TDS downloads.")
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
                    
                    pdf_bytes = generate_pdf_spec_sheet(spec_data)
                    st.download_button(
                        label="📄 Download Technical Data Sheet (PDF)",
                        data=pdf_bytes,
                        file_name=f"BioMatX_Spec_{base_mat.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )

    # TAB 2: INVERSE RECIPE OPTIMIZER
    with tab2:
        st.header("2. Inverse Recipe Optimizer")
        st.markdown("Input target mechanical performance requirements, and the AI will calculate the required formulation.")
        
        if st.session_state["user_plan"] == "free":
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

    # TAB 3: INTERACTIVE 3D SURFACES
    with tab3:
        st.header("3. Polymer Interaction Surfaces")
        
        g_range = np.linspace(5, 40, 30)
        w_range = np.linspace(10, 50, 30)
        G, W = np.meshgrid(g_range, w_range)
        
        grid_inputs = np.column_stack([G.ravel(), W.ravel(), np.full(G.size, 2.0), np.full(G.size, 1.0)])
        grid_preds = model.predict(grid_inputs)
        Z_tensile = grid_preds[:, 0].reshape(G.shape)
        
        fig = go.Figure(data=[go.Surface(z=Z_tensile, x=G, y=W, colorscale='Viridis')])
        fig.update_layout(
            title="3D Tensile Strength Surface (MPa)",
            scene=dict(xaxis_title="Glycerin (%)", yaxis_title="Water Content (%)", zaxis_title="Tensile (MPa)"),
            autosize=True,
            margin=dict(l=0, r=0, b=0, t=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    # TAB 4: UPGRADE & PAYMENTS
    with tab4:
        st.header("💳 Upgrade Subscription Tier (Raenest Multi-Currency)")
        st.write(f"Current Active Tier: **{st.session_state['user_plan'].upper()}**")
        
        up1, up2 = st.columns(2)
        with up1:
            st.subheader("Researcher Plan")
            st.markdown("### $12 / £9.50 / ₦15,000 / mo")
            st.write("• Unlimited Property Predictions")
            st.write("• Inverse Recipe Optimizer")
            st.write("• Downloadable Technical Data Sheets")
            
            c_u1, c_u2, c_u3 = st.columns(3)
            with c_u1:
                st.link_button("USD ($12)", st.secrets.get("RAENEST_RESEARCHER_USD_URL", "https://raenest.com"))
            with c_u2:
                st.link_button("GBP (£9.50)", st.secrets.get("RAENEST_RESEARCHER_GBP_URL", "https://raenest.com"))
            with c_u3:
                st.link_button("NGN (₦15k)", st.secrets.get("RAENEST_RESEARCHER_NGN_URL", "https://raenest.com"))
            
        with up2:
            st.subheader("Enterprise Plan")
            st.markdown("### $38.99 / £31.00 / ₦50,000 / mo")
            st.write("• Batch Recipe History")
            st.write("• Dedicated Lab Support & API Integration")
            
            ce_u1, ce_u2, ce_u3 = st.columns(3)
            with ce_u1:
                st.link_button("USD ($38.99)", st.secrets.get("RAENEST_ENTERPRISE_USD_URL", "https://raenest.com"))
            with ce_u2:
                st.link_button("GBP (£31.00)", st.secrets.get("RAENEST_ENTERPRISE_GBP_URL", "https://raenest.com"))
            with ce_u3:
                st.link_button("NGN (₦50k)", st.secrets.get("RAENEST_ENTERPRISE_NGN_URL", "https://raenest.com"))


# ==========================================
# 7. MAIN ROUTER
# ==========================================
if st.session_state["user"] is None:
    render_landing_page()
else:
    render_dashboard()
