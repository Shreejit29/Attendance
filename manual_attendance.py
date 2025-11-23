# manual_attendance.py
import streamlit as st
import pandas as pd


def manual_attendance_ui(students, present_dict):
    rows = []
    for s in students:
        rows.append({
            "Student ID": s["id"],
            "Name": s["name"],
            "Present (Final)": bool(present_dict.get(s["id"], False))
        })
    df = pd.DataFrame(rows)

    st.write("### ✅ Verify & Correct Attendance")
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        column_config={
            "Present (Final)": st.column_config.CheckboxColumn(
                label="Present (Final)",
                help="Check if present",
                default=False
            )
        }
    )
    required_cols = ["Student ID", "Name", "Present (Final)"]
    for col in required_cols:
        if col not in edited_df.columns:
            st.error(f"Internal Error: Column '{col}' missing.")
            return df
    edited_df["Present (Final)"] = edited_df["Present (Final)"].astype(bool)
    return edited_df
