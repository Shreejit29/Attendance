import streamlit as st
import pandas as pd

def manual_attendance_ui(students, present_dict):
    """
    DataFrame:
        Student ID | Name | Present (Final)

    Features:
    ✔ Highlight Present (green)
    ✔ Highlight Absent (red)
    ✔ Separate Absent List
    ✔ Summary count
    ✔ Editable attendance
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
        st.success("🎉 No absent students — ALL PRESENT!")

    st.write("### ✏️ Verify & Correct Attendance Below")

    # --------------------------
    # HIGHLIGHTING RULES
    # --------------------------
    def highlight_row(row):
        if row["Present (Final)"]:
            return ['background-color: #d4fcd4'] * len(row)   # light green
        else:
            return ['background-color: #ffcccc'] * len(row)   # light red

    styled_df = df.style.apply(highlight_row, axis=1)

    # --------------------------
    # MAIN EDITOR
    # --------------------------
    edited_df = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Present (Final)": st.column_config.CheckboxColumn(
                help="Mark student present/absent"
            )
        },
        styled_dataframe=styled_df,   # 🔥 Highlighting applied
    )

    return edited_df
