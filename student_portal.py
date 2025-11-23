# student_portal.py (reads Excel attendance files)
import streamlit as st
import pandas as pd
import os

HISTORY_DIR = "data/attendance_history"

def student_portal(username):
    st.header(f"👨‍🎓 Student Portal — {username}")

    if not os.path.exists(HISTORY_DIR):
        st.info("No attendance history available.")
        return

    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".xlsx")]
    if not files:
        st.info("No attendance history found.")
        return

    all_data = []
    for f in files:
        try:
            df = pd.read_excel(os.path.join(HISTORY_DIR, f))
            df["SourceFile"] = f
            all_data.append(df)
        except:
            continue

    if len(all_data) == 0:
        st.info("No readable attendance files.")
        return

    df = pd.concat(all_data, ignore_index=True)

    present_col = None
    if "Present (Final)" in df.columns:
        present_col = "Present (Final)"
    elif "Present" in df.columns:
        present_col = "Present"
    else:
        st.error("Attendance files missing Present column.")
        return

    df_student = df[df["Name"] == username]
    st.subheader("📘 Your Attendance Records")
    st.dataframe(df_student)

    if df_student.empty:
        st.warning("No attendance records for you.")
        return

    percent = df_student[present_col].mean() * 100
    st.metric("Attendance Percentage", f"{percent:.2f}%")

    if "Subject" in df_student.columns:
        st.subheader("📚 Subject-wise Attendance")
        sub_summary = df_student.groupby("Subject")[present_col].mean() * 100
        st.table(sub_summary.map(lambda x: f"{x:.1f}%"))

    if "Class" in df_student.columns:
        st.subheader("🏫 Class-wise Attendance")
        class_summary = df_student.groupby("Class")[present_col].mean() * 100
        st.table(class_summary.map(lambda x: f"{x:.1f}%"))
