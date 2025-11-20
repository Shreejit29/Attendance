# manual_attendance.py
import streamlit as st
import pandas as pd

def manual_attendance_ui(students, auto_present):
    """
    students: list of dicts -> [{"id":..., "name":..., "embeddings":[...]}]
    auto_present: dict -> {"student_id": True/False}

    Returns updated attendance dataframe.
    """

    data = []
    for s in students:
        data.append({
            "Student ID": s["id"],
            "Name": s["name"],
            "Present (Auto)": auto_present[s["id"]],
            "Present (Final)": auto_present[s["id"]],
        })

    df = pd.DataFrame(data)

    edited_df = st.data_editor(
        df,
        column_config={
            "Present (Final)": st.column_config.CheckboxColumn(
                "Present",
                help="Mark manually if automatic detection missed the student."
            )
        },
        hide_index=True
    )

    final_df = edited_df[["Student ID", "Name", "Present (Final)"]]
    final_df = final_df.rename(columns={"Present (Final)": "Present"})

    return final_df
