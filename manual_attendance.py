import streamlit as st
import pandas as pd

def manual_attendance_ui(students, present_dict):
    """
    Creates a clean dataframe:
    Student ID | Name | Present (Final)
    Lets teacher/admin manually correct attendance.
    """

    # Build dataframe in required format
    data = []
    for s in students:
        data.append({
            "Student ID": s["id"],
            "Name": s["name"],
            "Present (Final)": present_dict.get(s["id"], False)
        })

    df = pd.DataFrame(data)

    st.write("### ✅ Verify & Correct Attendance")
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True
    )

    # Ensure correct columns exist
    if not all(col in edited_df.columns for col in ["Student ID", "Name", "Present (Final)"]):
        st.error("Internal Error: Required columns missing.")
        return df

    return edited_df
