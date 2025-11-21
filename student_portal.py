# student_portal.py

import streamlit as st
import pandas as pd
import os

HISTORY_DIR = "attendance_history"

def student_portal(username):
    st.header(f"👨‍🎓 Student Portal — {username}")

    if not os.path.exists(HISTORY_DIR):
        st.info("No attendance history available.")
        return

    files = os.listdir(HISTORY_DIR)
    if not files:
        st.info("No attendance history found.")
        return

    all_data = []

    for f in files:
        df = pd.read_excel(os.path.join(HISTORY_DIR, f))
        all_data.append(df)

    df = pd.concat(all_data, ignore_index=True)

    # Show only this student's data
    df_student = df[df["Name"] == username]

    st.subheader("Your Attendance")
    st.dataframe(df_student)

    if not df_student.empty:
        percent = df_student["Present"].mean() * 100
        st.metric("Attendance Percentage", f"{percent:.2f}%")
