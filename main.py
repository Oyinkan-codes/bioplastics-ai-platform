import streamlit as st

st.set_page_config(page_title="BioMatX AI Platform", page_icon="🌿", layout="wide")

# Session state initialization
if "user_plan" not in st.session_state:
    st.session_state["user_plan"] = "free"
if "daily_predictions" not in st.session_state:
    st.session_state["daily_predictions"] = 0

# Register view files
p1 = st.Page("views/1_dashboard.py", title="Predictive Modeler", icon="🔮", default=True)
p2 = st.Page("views/2_optimizer.py", title="Inverse Recipe Optimizer", icon="🎯")
p3 = st.Page("views/3_surfaces.py", title="Interactive 3D Surfaces", icon="📊")
p4 = st.Page("views/4_upgrade.py", title="Upgrade Plan", icon="💳")

pg = st.navigation({
    "Core Features": [p1, p2, p3],
    "Billing": [p4]
})

pg.run()
