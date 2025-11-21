# signup.py
import streamlit as st
from auth import create_user, generate_otp, store_otp_for_user, verify_otp_for_user, set_user_verified, login_user
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os


# SMTP configuration - set these as environment variables for security
SMTP_HOST = os.environ.get("SMTP_HOST")        # e.g. "smtp.gmail.com"
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")        # your smtp username (email)
SMTP_PASS = os.environ.get("SMTP_PASS")        # your smtp password or app password

def send_otp_email(to_email: str, username: str, otp: str):
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        st.error("SMTP not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER and SMTP_PASS environment variables.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Smart Attendance - Your OTP"
        msg["From"] = SMTP_USER
        msg["To"] = to_email

        # Simple HTML email with OTP and logo (logo uses local path - for cloud deploy use public URL)
        logo_html = f'<img src="cid:logo" alt="logo" style="width:120px;height:auto;"><br>' if os.path.exists(LOGO_LOCAL_PATH) else ""
        html_content = f"""
        <html>
          <body>
            {logo_html}
            <h3>Hello {username},</h3>
            <p>Your OTP for Smart Attendance registration is: <b>{otp}</b></p>
            <p>This code will expire in a few minutes. If you didn't request this, ignore this email.</p>
            <p>— Smart Attendance App</p>
          </body>
        </html>
        """
        part = MIMEText(html_content, "html")
        msg.attach(part)

        # Connect & send
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False


def signup_ui():
    st.header("🆕 Student / Teacher Self-Registration")

    st.write("Fill your details. You'll receive an OTP on the email provided.")
    name = st.text_input("Full name")
    username = st.text_input("Choose a username (unique)")
    email = st.text_input("Email")
    role = st.selectbox("I am a", ["student", "teacher"])
    programme = st.text_input("Programme (e.g., BSc, BA)")
    student_class = st.text_input("Class (e.g., FYBSc A)")
    password = st.text_input("Choose a password", type="password")

    if st.button("Send OTP & Create Account"):
        if not all([name, username, email, role, password]):
            st.error("Fill required fields (name, username, email, role, password).")
        else:
            ok, msg = create_user(username=username, password=password, role=role,
                                  email=email, programme=programme, student_class=student_class)
            if not ok:
                st.error(msg)
            else:
                otp = generate_otp()
                store_otp_for_user(username, otp)
                sent = send_otp_email(email, username, otp)
                if sent:
                    st.success("OTP sent to your email. Enter it below to verify and complete registration.")
                    st.session_state["pending_user"] = username
                else:
                    st.error("Failed to send OTP. Contact admin.")

    # Verify block
    st.write("---")
    st.subheader("Verify OTP")
    entered_otp = st.text_input("Enter OTP")
    if st.button("Verify OTP"):
        pending = st.session_state.get("pending_user")
        if not pending:
            st.error("No pending registration. Try to register first.")
        else:
            ok = verify_otp_for_user(pending, entered_otp)
            if ok:
                set_user_verified(pending)
                st.success("Your email is verified. You can now login.")
                # Optionally auto-login
                # user = login_user(pending, ???)  # we can't auto-login without password in session
            else:
                st.error("Invalid OTP. Try again.")
