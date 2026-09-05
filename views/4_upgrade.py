import streamlit as st

st.header("💳 Upgrade Subscription Tier")
st.write(f"Current Active Tier: **{st.session_state.get('user_plan', 'free').upper()}**")

up1, up2 = st.columns(2)
with up1:
    st.subheader("Researcher Plan")
    st.markdown("### $12 / £9.50 / ₦15,000 / mo")
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
    ce_u1, ce_u2, ce_u3 = st.columns(3)
    with ce_u1:
        st.link_button("USD ($38.99)", st.secrets.get("RAENEST_ENTERPRISE_USD_URL", "https://raenest.com"))
    with ce_u2:
        st.link_button("GBP (£31.00)", st.secrets.get("RAENEST_ENTERPRISE_GBP_URL", "https://raenest.com"))
    with ce_u3:
        st.link_button("NGN (₦50k)", st.secrets.get("RAENEST_ENTERPRISE_NGN_URL", "https://raenest.com"))
