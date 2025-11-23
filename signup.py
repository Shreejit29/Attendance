# signup.py

import streamlit as st
from auth import create_user

def signup_ui():
    st.header("🆕 Create New Account")

    st.info("Fill details below to register. After signup, you can login immediately.")

    # -------------------------------
    # Basic Login Credentials
    # -------------------------------
    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")

    # -------------------------------
    # Role Selection
    # -------------------------------
    role = st.selectbox("Account Type (Role)", ["student", "teacher", "admin"])

    st.write("---")

    # -------------------------------
    # Additional Role-Based Fields
    # -------------------------------
    programme = ""
    student_class = ""

    if role == "student":
        st.subheader("📘 Student Details")
        programme = st.text_input("Programme (e.g., BSc, BCom, BA)")
        student_class = st.text_input("Class (e.g., FYBSc A, SYBCom B)")

    elif role == "teacher":
        st.subheader("👨‍🏫 Teacher Details")
        programme = st.text_input("Department (Optional)")
        student_class = st.text_input("Handled Class (Optional)")

    else:
        st.subheader("🛡 Admin Details")
        st.write("No additional fields required.")

    st.write("---")

    # -------------------------------
    # Register Button
    # -------------------------------
    if st.button("Create Account"):
        if not username or not password:
            st.error("Username and password cannot be empty.")
            return

        # Attempt to create user
        ok, msg = create_user(
            username=username,
            password=password,
            role=role,
            programme=programme,
            student_class=student_class
        )

        if ok:
            st.success("🎉 Account created successfully! Please login now.")
        else:
            st.error(msg)
