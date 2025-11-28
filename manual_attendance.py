# manual_attendance.py

import streamlit as st
import pandas as pd

def manual_attendance_ui(students, present_dict):
    """
    Creates a styled dataframe with:
    - Green → Present
    - Red → Absent
    Also shows a separate ABSENT student list.
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

    st.subheader("✏️ Verify & Correct Attendance Below")

    # --- Editable attendance (without color) ---
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_attendance"
    )

    # Keep only required columns
    if not all(col in edited_df.columns for col in ["Student ID", "Name", "Present (Final)"]):
        st.error("Internal Error: Required columns missing.")
        return edited_df

    st.write("---")
    st.subheader("📌 Attendance Summary")

    # List ABSENT students separately
    absent_df = edited_df[edited_df["Present (Final)"] == False]

    st.warning(f"❌ Absent Students: {len(absent_df)}")
    st.dataframe(absent_df[["Student ID", "Name"]])

    st.success(f"✅ Present Students: {len(edited_df) - len(absent_df)}")

    # ---- Styling for final display ----
    def highlight_row(row):
        color = "background-color: #ffcccc" if row["Present (Final)"] is False else "background-color: #ccffcc"
        return [color] * len(row)

    styled_df = edited_df.style.apply(highlight_row, axis=1)

    st.write("### 🔍 Highlighted Attendance Table")
    st.dataframe(styled_df, use_container_width=True)

    return edited_df
