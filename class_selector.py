# class_selector.py
import streamlit as st
from datetime import datetime

def class_subject_time_selector():
    """
    Returns a dictionary:
    {
        "class": "...",
        "subject": "...",
        "time": "..."
    }
    """

    st.subheader("📌 Select Class, Subject & Time")

    # Class options
    class_list = [
        "FYBSc", "SYBSc", "TYBSc",
        "FYBCom", "SYBCom", "TYBCom",
        "FYBA",  "SYBA",  "TYBA",
        "Custom Class"
    ]

    subject_list = [
        "Environmental Management",
        "Sports Science",
        "Mathematics",
        "Chemistry",
        "Physics",
        "Computer Science",
        "Custom Subject"
    ]

    selected_class = st.selectbox("Select Class", class_list)

    # Custom class input
    if selected_class == "Custom Class":
        selected_class = st.text_input("Enter Class Name")

    selected_subject = st.selectbox("Select Subject", subject_list)

    # Custom subject input
    if selected_subject == "Custom Subject":
        selected_subject = st.text_input("Enter Subject Name")

    # Time selection
    time_option = st.selectbox(
        "Select Lecture Time",
        ["Auto (Now)", "8:00 AM", "9:00 AM", "10:00 AM", "11:00 AM",
         "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "Custom"]
    )

    if time_option == "Auto (Now)":
        selected_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    elif time_option == "Custom":
        selected_time = st.text_input("Enter custom time (e.g., 2025-02-20 10:30)")
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_time = f"{today} {time_option}"

    return {
        "class": selected_class,
        "subject": selected_subject,
        "time": selected_time
    }
