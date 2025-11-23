import streamlit as st
from datetime import datetime

# Load timetable from Storage API (if available)
def _load_timetable():
    try:
        data = st.storage.read("timetable")
        return data if data else {}
    except:
        return {}


def class_subject_time_selector():
    st.subheader("📌 Select Class, Subject & Time")

    timetable = _load_timetable()

    # -----------------------------------------
    # CLASS SELECTOR
    # -----------------------------------------
    if timetable:
        class_list = list(timetable.keys())
        cls = st.selectbox("Class", ["Select Class"] + class_list)
    else:
        cls = st.text_input("Class")

    # -----------------------------------------
    # SUBJECT SELECTOR
    # -----------------------------------------
    if timetable and cls in timetable:
        subjects = list({entry["subject"] for entry in timetable[cls]})
        subject = st.selectbox("Subject", subjects)
    else:
        subject = st.text_input("Subject")

    # -----------------------------------------
    # TIME SELECTOR
    # -----------------------------------------
    time_option = st.selectbox("Lecture Time", ["Auto (Now)", "Custom"])

    if time_option == "Auto (Now)":
        selected_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        selected_time = st.text_input("Enter Time (YYYY-MM-DD HH:MM)")

    # Return combined data
    return {
        "class": cls,
        "subject": subject,
        "time": selected_time
    }
