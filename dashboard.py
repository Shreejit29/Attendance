# dashboard.py (reads Excel history)
import streamlit as st
import pandas as pd
import os

HISTORY_DIR = "data/attendance_history"

def dashboard_ui():
    st.subheader("📊 Attendance Dashboard")
    if not os.path.exists(HISTORY_DIR):
        st.info("No attendance history found.")
        return
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".xlsx")]
    if not files:
        st.info("No attendance records saved.")
        return
    df_all = []
    for f in files:
        try:
            df = pd.read_excel(os.path.join(HISTORY_DIR, f))
            df_all.append(df)
        except:
            continue
    if len(df_all) == 0:
        st.info("No readable attendance records.")
        return
    df_all = pd.concat(df_all, ignore_index=True)
    st.write("### All Attendance Data")
    st.dataframe(df_all)
    if "Present (Final)" in df_all.columns or "Present" in df_all.columns:
        present_col = "Present (Final)" if "Present (Final)" in df_all.columns else "Present"
        st.write("### Attendance Percentage per Student")
        per_student = df_all.groupby("Name")[present_col].mean() * 100
        st.bar_chart(per_student)
        if "Class" in df_all.columns:
            st.write("### Attendance Percentage per Class")
            per_class = df_all.groupby("Class")[present_col].mean() * 100
            st.bar_chart(per_class)
