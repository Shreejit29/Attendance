# class_selector.py
import streamlit as st
from datetime import datetime

def class_subject_time_selector():
    st.subheader("📌 Select Class, Subject & Time")
    cls = st.text_input("Class", key="cs_class")
    subject = st.text_input("Subject", key="cs_subject")
    time_option = st.selectbox("Lecture Time", ["Auto (Now)", "Custom"], key="cs_time_option")
    if time_option == "Auto (Now)":
        selected_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        selected_time = st.text_input("Enter Time (YYYY-MM-DD HH:MM)", key="cs_time_custom")
    return {"class": cls, "subject": subject, "time": selected_time}
