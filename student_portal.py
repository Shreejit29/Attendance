# student_portal.py

import streamlit as st
import pandas as pd
import os

HISTORY_DIR = "attendance_history"


def student_portal(username):
    st.header(f"👨‍🎓 Student Portal — {username}")

    # ---------------------------------------------------------
    # Load attendance history folder
    # ---------------------------------------------------------
    if not os.path.exists(HISTORY_DIR):
        st.info("No attendance history available.")
        return

    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".xlsx")]
    if not files:
        st.info("No attendance history found.")
        return

    # ---------------------------------------------------------
    # Load all attendance files
    # ---------------------------------------------------------
    all_data = []
    for f in files:
        try:
            df = pd.read_excel(os.path.join(HISTORY_DIR, f))
            df["Source File"] = f  # allow filter by date
            all_data.append(df)
        except:
            continue

    if len(all_data) == 0:
        st.info("No readable attendance files found.")
        return

    df = pd.concat(all_data, ignore_index=True)

    # ---------------------------------------------------------
    # Fix column mismatches (important)
    # ---------------------------------------------------------
    # Old system column: "Present"
    # New system column: "Present (Final)"
    present_col = None
    if "Present (Final)" in df.columns:
        present_col = "Present (Final)"
    elif "Present" in df.columns:
        present_col = "Present"
    else:
        st.error("Attendance file missing Present/Present (Final) column.")
        return

    # ---------------------------------------------------------
    # Filter only student's attendance
    # ---------------------------------------------------------
    df_student = df[df["Name"] == username]

    st.subheader("📘 Your Attendance Records")
    st.dataframe(df_student)

    if df_student.empty:
        st.warning("No attendance entries found for you yet.")
        return

    # ---------------------------------------------------------
    # Calculate attendance percentage
    # ---------------------------------------------------------
    percent = df_student[present_col].mean() * 100

    st.metric("Attendance Percentage", f"{percent:.2f}%")

    # ---------------------------------------------------------
    # Additional Analysis
    # ---------------------------------------------------------
    st.subheader("📅 Subject-wise Attendance Summary")

    if "Subject" in df_student.columns:
        subject_summary = df_student.groupby("Subject")[present_col].mean() * 100
        st.table(subject_summary.map(lambda x: f"{x:.1f}%"))

    # ---------------------------------------------------------
    # Class-wise summary
    # ---------------------------------------------------------
    if "Class" in df_student.columns:
        st.subheader("🏫 Class-wise Attendance")
        class_summary = df_student.groupby("Class")[present_col].mean() * 100
        st.table(class_summary.map(lambda x: f"{x:.1f}%"))

    # ---------------------------------------------------------
    # Timeline view
    # ---------------------------------------------------------
    st.subheader("📅 Attendance Over Time")
    if "Date" in df_student.columns:
        try:
            df_student["Date"] = pd.to_datetime(df_student["Date"])
            st.line_chart(df_student.sort_values("Date").set_index("Date")[present_col])
        except:
            st.info("Date column not properly formatted.")

    st.success("Student portal loaded successfully!")
