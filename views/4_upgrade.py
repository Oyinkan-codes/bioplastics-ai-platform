import streamlit as st

st.set_page_config(page_title="Upgrade Plan | BioMatX AI", page_icon="💳", layout="wide")

st.title("💳 Subscription Tiers & Formulation Licensing")
st.markdown("Choose a plan to unlock advanced inverse optimization, high-barrier feedstock modeling, and commercial TDS exports.")

current_plan = st.session_state.get("user_plan", "free").lower()

col1, col2, col3 = st.columns(3)

with col1:
    st.container(border=True)
    st.subheader("🌱 Free Tier")
    st.markdown("### **$0** / month")
    st.caption("Basic forward property predictions.")
    st.markdown("• 5 Daily Forward Predictions\n• Standard Corn Starch Feedstock\n• Basic Community Access")
    if current_plan == "free":
        st.button("Current Active Plan", disabled=True, use_container_width=True)

with col2:
    st.container(border=True)
    st.subheader("🔬 Researcher Plan")
    st.markdown("### **$12** / month")
    st.caption("For researchers and polymer engineers.")
    st.markdown("• Unlimited Predictions\n• Agricultural Waste Feedstocks\n• Inverse Target Optimizer\n• TDS PDF Reports")
    st.link_button("Upgrade to Researcher ($12)", "https://app.raenest.com/invoice/payment/RNMJ6E3RC", type="primary", use_container_width=True)

with col3:
    st.container(border=True)
    st.subheader("🏢 Enterprise Plan")
    st.markdown("### **$38.99** / month")
    st.caption("For B2B packaging firms and visa endorsement proof.")
    st.markdown("• Everything in Researcher Tier\n• B2B Asset-Light Licensing Rights\n• High-Barrier Specs (HDT, WVTR)\n• Automated LOI Generation")
    st.link_button("Upgrade to Enterprise ($38.99)", "https://app.raenest.com/invoice/payment/RNM73C35S", type="primary", use_container_width=True)

st.markdown("---")
st.caption("Payments are processed via Raenest multi-currency checkout (USD, NGN, GBP, EUR).")
