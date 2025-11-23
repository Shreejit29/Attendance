import streamlit as st
import pandas as pd


def dashboard_ui():
    st.header("📊 Attendance Dashboard")

    # ----------------------------------------
    # Get all attendance keys from Storage API
    # ----------------------------------------
    keys = st.storage.list("attendance/")

    if not keys:
        st.info("No attendance records found.")
        return

    st.write(f"Found **{len(keys)}** attendance entries.")

    # ----------------------------------------
    # Load all attendance data
    # ----------------------------------------
    all_rows = []

    for key in keys:
        data = st.storage.read(key)
        if data:
            df = pd.DataFrame(data)
            df["record_id"] = key
            all_rows.append(df)

    if not all_rows:
        st.warning("Attendance storage found but contains no valid data.")
        return

    df = pd.concat(all_rows, ignore_index=True)

    # ----------------------------------------
    # Detect "Present" column
    # ----------------------------------------
    present_col = None
    if "Present (Final)" in df.columns:
        present_col = "Present (Final)"
    elif "Present" in df.columns:
        present_col = "Present"
    else:
        st.error("No 'Present' or 'Present (Final)' column in attendance data.")
        return

    # ----------------------------------------
    # Display complete raw data
    # ----------------------------------------
    st.subheader("📁 All Attendance Data")
    st.dataframe(df)

    # ----------------------------------------
    # Per-Student Attendance %
    # ----------------------------------------
    st.subheader("🧑‍🎓 Attendance % per Student")
    per_student = df.groupby("Name")[present_col].mean().sort_values(ascending=False) * 100
    st.bar_chart(per_student)

    # ----------------------------------------
    # Per-Class Attendance %
    # ----------------------------------------
    if "Class" in df.columns:
        st.subheader("🏫 Attendance % per Class")
        per_class = df.groupby("Class")[present_col].mean() * 100
        st.bar_chart(per_class)

    # ----------------------------------------
    # Per-Subject Attendance %
    # ----------------------------------------
    if "Subject" in df.columns:
        st.subheader("📚 Attendance % per Subject")
        per_subject = df.groupby("Subject")[present_col].mean() * 100
        st.bar_chart(per_subject)

    # ----------------------------------------
    # Trend Over Time
    # ----------------------------------------
    if "Time" in df.columns:
        try:
            df["Time"] = pd.to_datetime(df["Time"])
            df_sorted = df.sort_values("Time")
            st.subheader("⏳ Attendance Trend Over Time")
            st.line_chart(df_sorted.set_index("Time")[present_col])
        except:
            st.info("Time column exists but could not be parsed.")
