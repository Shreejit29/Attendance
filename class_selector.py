import streamlit as st
from datetime import datetime

def class_subject_time_selector():
    st.subheader("📌 Select Class, Subject & Time")

    cls = st.text_input("Class")
    subject = st.text_input("Subject")

    time_option = st.selectbox(
        "Lecture Time",
        ["Auto (Now)", "Custom"]
    )

    if time_option == "Auto (Now)":
        selected_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        selected_time = st.text_input("Enter Time (YYYY-MM-DD HH:MM)")

    return {
        "class": cls,
        "subject": subject,
        "time": selected_time
    }
