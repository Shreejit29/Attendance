# signup.py

import streamlit as st
from auth import create_user

def signup_ui():
    st.header("🆕 Create New Account")

    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")

    role = st.selectbox("Select Role", ["student", "teacher", "admin"])

    programme = st.text_input("Programme (Optional for students/teachers)")
    student_class = st.text_input("Class (Optional for students/teachers)")

    if st.button("Register"):
        if not username or not password:
            st.error("Username and password are required.")
        else:
            ok, msg = create_user(
                username=username,
                password=password,
                role=role,
                programme=programme,
                student_class=student_class
            )

            if ok:
                st.success("Account created. You can now login.")
            else:
                st.error(msg)
