# dashboard.py

import streamlit as st
import pandas as pd
import os

HISTORY_DIR = "attendance_history"

def dashboard_ui():
    st.subheader("📊 Attendance Dashboard")

    if not os.path.exists(HISTORY_DIR):
        st.info("No attendance history yet.")
        return

    files = os.listdir(HISTORY_DIR)
    if not files:
        st.info("No attendance history found.")
        return

    df_all = []

    for f in files:
        path = os.path.join(HISTORY_DIR, f)
        df = pd.read_excel(path)
        df["File"] = f
        df_all.append(df)

    df_all = pd.concat(df_all, ignore_index=True)

    st.write("### Overall Attendance Records")
    st.dataframe(df_all)

    # Attendance percentage per student
    summary = df_all.groupby("Name")["Present"].mean() * 100

    st.write("### Attendance % per Student")
    st.bar_chart(summary)

    # Class wise participation
    if "Class" in df_all.columns:
        class_summary = df_all.groupby("Class")["Present"].mean() * 100
        st.write("### Class-wise Attendance %")
        st.bar_chart(class_summary)
