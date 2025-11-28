import streamlit as st
import pandas as pd

def manual_attendance_ui(students, present_dict):
    """
    Creates clean editable attendance UI:
    - Student ID | Name | Present (Final)
    - Summary (Present/Absent count)
    - Absent list separately
    - Editable attendance table
    """

    # Build dataframe
    data = []
    for s in students:
        data.append({
            "Student ID": s["id"],
            "Name": s["name"],
            "Present (Final)": present_dict.get(s["id"], False)
        })

    df = pd.DataFrame(data)

    # --------------------------
    # SUMMARY
    # --------------------------
    total_students = len(df)
    present_count = df["Present (Final)"].sum()
    absent_count = total_students - present_count

    st.markdown(
        f"""
        ### 📊 Attendance Summary  
        - 👥 **Total Students:** {total_students}  
        - ✅ **Present:** {present_count}  
        - ❌ **Absent:** {absent_count}  
        """
    )

    # --------------------------
    # SEPARATE ABSENT LIST
    # --------------------------
    df_absent = df[df["Present (Final)"] == False]

    if len(df_absent) > 0:
        st.warning("### ❌ Absent Students")
        st.dataframe(df_absent[["Student ID", "Name"]])
    else:
        st.success("🎉 All students are present!")

    st.write("### ✏️ Verify & Correct Attendance Below")

    # --------------------------
    # MAIN EDITOR (NO STYLING)
    # --------------------------
    edited_df = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Present (Final)": st.column_config.CheckboxColumn(
                help="Mark student present/absent"
            )
        }
    )

    return edited_df
