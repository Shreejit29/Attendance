# teacher_portal.py

import streamlit as st
from app_functions import take_attendance_image_ui, take_attendance_video_ui
from storage import load_students, delete_student_by_id
import pandas as pd


def teacher_portal(teacher_name):
    st.header(f"👨‍🏫 Teacher Portal — {teacher_name}")

    choice = st.selectbox("Select Task", [
        "Take Attendance (Image)",
        "Take Attendance (Video)",
        "Manage Students"
    ])

    if choice == "Take Attendance (Image)":
        take_attendance_image_ui()

    elif choice == "Take Attendance (Video)":
        take_attendance_video_ui()

    elif choice == "Manage Students":
        students = load_students()
        df = pd.DataFrame(students)
        st.dataframe(df[["id", "name", "programme", "class"]])

        sid = st.selectbox("Select student to remove", df["id"])

        if st.button("Remove Student"):
            delete_student_by_id(sid)
            st.success("Student removed successfully.")
