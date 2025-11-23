import streamlit as st
import pandas as pd


def manual_attendance_ui(students, present_dict):
    """
    Creates a clean attendance verification table:
    Columns → Student ID | Name | Present (Final)
    Allows teacher/admin to manually correct detected attendance.
    """

    # -------------------------------
    # Build clean DataFrame
    # -------------------------------
    rows = []
    for s in students:
        rows.append({
            "Student ID": s["id"],
            "Name": s["name"],
            "Present (Final)": bool(present_dict.get(s["id"], False))
        })

    df = pd.DataFrame(rows)

    st.write("### ✅ Verify or Correct Attendance Before Finalizing")

    # -------------------------------
    # Editable Table (Safe)
    # -------------------------------
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="fixed",     # prevent row deletion
        hide_index=True,
        column_config={
            "Present (Final)": st.column_config.CheckboxColumn(
                label="Present (Final)",
                help="Check if the student is present",
                default=False
            )
        }
    )

    # -------------------------------
    # Validate required columns
    # -------------------------------
    required_cols = ["Student ID", "Name", "Present (Final)"]
    for col in required_cols:
        if col not in edited_df.columns:
            st.error(f"Internal Error: Column '{col}' missing!")
            return df  # fallback

    # Convert Present to bool (avoid Pandas type issues)
    edited_df["Present (Final)"] = edited_df["Present (Final)"].astype(bool)

    return edited_df
