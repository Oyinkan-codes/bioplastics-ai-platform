import re
import requests
import streamlit as st
import hashlib
import secrets
import string

# --- HELPER FUNCTIONS ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_random_password(length=12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def send_password_email(user_email, generated_password):
    """Sends password via Resend API (or replace with SendGrid/SMTP)"""
    api_key = st.secrets.get("email", {}).get("resend_api_key")
    sender = st.secrets.get("email", {}).get("sender_email", "noreply@bioplastic.ai")
    
    if not api_key:
        st.warning(f"DEV MODE: Email API key missing. Generated password for {user_email}: {generated_password}")
        return True

    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "from": sender,
        "to": user_email,
        "subject": "Your Bioplastic AI Platform Access Credentials",
        "html": f"""
        <h3>Welcome to Bioplastic AI Platform</h3>
        <p>Your account has been created. Use the temporary password below to log in:</p>
        <p><b>Password:</b> <code>{generated_password}</code></p>
        <p>Please log in and update your settings.</p>
        """
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code in [200, 201]

# --- LOGIN & SIGN-UP INTERFACE ---
if not st.session_state.get("authentication_status"):
    st.title("🌱 Cloud-Native Bioplastic AI Platform")
    
    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔑 Sign In", "📝 Create Account", "💳 Pricing Packages"])

    with auth_tab1:
        with st.form("login_form"):
            input_user = st.text_input("Username or Email").strip().lower()
            input_pass = st.text_input("Password", type="password").strip()
            submit_login = st.form_submit_button("Sign In")

        if submit_login:
            session = Session()
            user_rec = session.query(User).filter(
                (User.username == input_user) | (User.email == input_user)
            ).first()
            session.close()

            if user_rec and user_rec.password_hash == hash_password(input_pass):
                st.session_state["authentication_status"] = True
                st.session_state["name"] = user_rec.full_name
                st.session_state["username"] = user_rec.username
                st.session_state["role"] = user_rec.role
                st.session_state["plan"] = user_rec.subscription_plan
                st.success("Log in successful!")
                st.rerun()
            else:
                st.error("Invalid username/email or password.")

    with auth_tab2:
        st.subheader("Register for an Account")
        st.write("Your generated login password will be delivered directly to your email address.")
        
        with st.form("signup_form"):
            new_name = st.text_input("Full Name")
            new_user = st.text_input("Desired Username").strip().lower()
            new_email = st.text_input("Work Email Address").strip().lower()
            selected_plan = st.selectbox("Choose Plan Tiers", ["Free Tier", "Researcher ($49/mo)", "Enterprise ($199/mo)"])
            submit_signup = st.form_submit_button("Generate Password & Register")

        if submit_signup:
            if not new_name or not new_user or not new_email:
                st.error("Please fill in all fields.")
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                st.error("Please enter a valid email address.")
            else:
                session = Session()
                existing_user = session.query(User).filter((User.username == new_user) | (User.email == new_email)).first()
                
                if existing_user:
                    st.error("Username or email is already registered.")
                    session.close()
                else:
                    gen_pass = generate_random_password()
                    plan_clean = selected_plan.split(" ")[0]
                    
                    new_user_rec = User(
                        username=new_user,
                        email=new_email,
                        full_name=new_name,
                        password_hash=hash_password(gen_pass),
                        subscription_plan=plan_clean,
                        is_verified=True
                    )
                    session.add(new_user_rec)
                    session.commit()
                    session.close()

                    if send_password_email(new_email, gen_pass):
                        st.success(f"Account created! Check **{new_email}** for your generated password.")
                    else:
                        st.error("Failed to deliver password email. Please contact platform support.")

    with auth_tab3:
        st.subheader("Platform Pricing Packages")
        col_free, col_pro, col_ent = st.columns(3)

        with col_free:
            st.markdown("### Free")
            st.markdown("**$0** / month")
            st.write("• Basic ML predictions\n• 5 saved formulations/mo\n• Standard support")
            st.button("Current Default", disabled=True, key="btn_free")

        with col_pro:
            st.markdown("### Researcher")
            st.markdown("**$49** / month")
            st.write("• Inverse Optimizer\n• Unlimited saved formulations\n• PDF technical exports")
            if st.button("Subscribe to Researcher", key="btn_pro"):
                st.info("Directing to Stripe payment gateway...")

        with col_ent:
            st.markdown("### Enterprise")
            st.markdown("**$199** / month")
            st.write("• Team-wide log visibility\n• Custom ingredient pricing\n• Dedicated priority support")
            if st.button("Subscribe to Enterprise", key="btn_ent"):
                st.info("Directing to Stripe payment gateway...")

    st.stop()
