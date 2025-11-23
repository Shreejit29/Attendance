# student_portal.py  — Streamlit Storage API version

import streamlit as st
import pandas as pd


def student_portal(username):
    st.header(f"👨‍🎓 Student Portal — {username}")

    # ---------------------------------------------------------
    # Load ALL attendance entries from permanent storage
    # ---------------------------------------------------------
    attendance_keys = st.storage.list("attendance/")

    if not attendance_keys:
        st.info("No attendance history available yet.")
        return

    all_records = []

    for key in attendance_keys:
        data = st.storage.read(key)
        if data:
            for rec in data:
                rec["SourceKey"] = key
            all_records.extend(data)

    if len(all_records) == 0:
        st.info("No stored attendance found.")
        return

    df = pd.DataFrame(all_records)

    # ---------------------------------------------------------
    # Ensure column support
    # ---------------------------------------------------------
    present_col = None
    if "Present (Final)" in df.columns:
        present_col = "Present (Final)"
    elif "Present" in df.columns:
        present_col = "Present"
    else:
        st.error("Attendance data missing Present/Present (Final) column.")
        return

    # Extract date from key → "attendance/Class_Subject_YYYY-MM-DD"
    df["Date"] = df["SourceKey"].apply(lambda k: k.split("_")[-1] if "_" in k else "")

    # ---------------------------------------------------------
    # Filter only this student's data
    # ---------------------------------------------------------
    df_student = df[df["Name"] == username]

    st.subheader("📘 Your Attendance Records")
    st.dataframe(df_student)

    if df_student.empty:
        st.warning("No attendance records found for your username.")
        return

    # ---------------------------------------------------------
    # Calculate Attendance %
    # ---------------------------------------------------------
    percent = df_student[present_col].mean() * 100
    st.metric("Attendance Percentage", f"{percent:.2f}%")

    # ---------------------------------------------------------
    # Subject-wise Summary
    # ---------------------------------------------------------
    if "Subject" in df_student.columns:
        st.subheader("📚 Subject-wise Attendance")
        sub_summary = df_student.groupby("Subject")[present_col].mean() * 100
        st.table(sub_summary.map(lambda x: f"{x:.1f}%"))

    # ---------------------------------------------------------
    # Class-wise Summary
    # ---------------------------------------------------------
    if "Class" in df_student.columns:
        st.subheader("🏫 Class-wise Attendance")
        class_summary = df_student.groupby("Class")[present_col].mean() * 100
        st.table(class_summary.map(lambda x: f"{x:.1f}%"))

    # ---------------------------------------------------------
    # Timeline Chart
    # ---------------------------------------------------------
    st.subheader("📅 Attendance Over Time")

    try:
        df_student["Date"] = pd.to_datetime(df_student["Date"], errors="coerce")
        df_sorted = df_student.sort_values("Date")

        st.line_chart(
            df_sorted.set_index("Date")[present_col]
        )
    except:
        st.info("Timeline unavailable (date format issue).")

    st.success("Student portal loaded successfully!")
