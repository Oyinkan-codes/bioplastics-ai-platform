import streamlit as st

st.set_page_config(
    page_title="BioMatX | DeepTech Bioplastics Platform",
    page_icon="🧬",
    layout="wide"
)

dashboard = st.Page("views/1_dashboard.py", title="Formulation & TDS Generator", icon="🧪", default=True)
optimizer = st.Page("views/2_optimizer.py", title="Inverse Property Optimizer", icon="🔒")
pilot_eoi = st.Page("views/3_pilot_eoi.py", title="B2B LOI & Pilot Pipeline", icon="📝")
upgrade = st.Page("views/4_upgrade.py", title="Licensing & SaaS Model", icon="💳")

pg = st.navigation(
    {
        "Material Science": [dashboard, optimizer],
        "Commercialization": [pilot_eoi, upgrade],
    }
)

st.sidebar.markdown("### 🧬 **BioMatX AI Platform**")
st.sidebar.caption("Asset-Light DeepTech Material SaaS")

pg.run()
