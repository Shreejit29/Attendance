import streamlit as st
import pandas as pd
import os

HISTORY_DIR = "attendance_history"

def dashboard_ui():
    st.subheader("📊 Attendance Dashboard")

    if not os.path.exists(HISTORY_DIR):
        st.info("No attendance history found.")
        return

    files = os.listdir(HISTORY_DIR)
    if not files:
        st.info("No attendance records saved.")
        return

    df_all = []
    for f in files:
        df = pd.read_excel(os.path.join(HISTORY_DIR, f))
        df_all.append(df)

    df_all = pd.concat(df_all, ignore_index=True)

    st.write("### All Attendance Data")
    st.dataframe(df_all)

    if "Present" in df_all:

        st.write("### Attendance Percentage per Student")
        per_student = df_all.groupby("Name")["Present"].mean() * 100
        st.bar_chart(per_student)

        if "Class" in df_all:
            st.write("### Attendance Percentage per Class")
            per_class = df_all.groupby("Class")["Present"].mean() * 100
            st.bar_chart(per_class)
