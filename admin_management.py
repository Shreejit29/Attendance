# ============================================================
# admin_management.py — FINAL CLEAN STORAGE API VERSION
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
from storage import load_students, save_students


# ============================================================
# INTERNAL STORAGE WRAPPERS
# ============================================================

def _load(key, default):
    """Load from permanent Streamlit Storage."""
    data = st.storage.read(key)
    return default if data is None else data


def _save(key, value):
    """Write to permanent Streamlit Storage."""
    st.storage.write(key, value)


# ============================================================
# STUDENT MANAGEMENT
# ============================================================

def delete_student(student_id):
    students = load_students()
    students = [s for s in students if s["id"] != student_id]
    save_students(students)


def student_management_ui():
    st.subheader("👨‍🎓 Student Management")

    students = load_students()
    if not students:
        st.info("No students registered yet.")
        return

    df = pd.DataFrame(students)

    # Ensure column consistency
    if "student_class" not in df.columns:
        df["student_class"] = ""

    st.dataframe(df[["id", "name", "programme", "student_class"]])

    sid = st.selectbox("Select Student ID to delete", df["id"])

    if st.button("❌ Delete Student"):
        delete_student(sid)
        st.success("Student removed.")
        st.experimental_rerun()


# ============================================================
# TEACHER MANAGEMENT
# ============================================================

def teacher_management_ui():
    st.subheader("👨‍🏫 Teacher Management")

    teachers = _load("teachers", [])

    st.write("### Current Teachers")
    st.table(pd.DataFrame(teachers)) if teachers else st.info("No teachers yet.")

    tid = st.text_input("Teacher ID")
    name = st.text_input("Teacher Name")

    if st.button("Add Teacher"):
        if tid and name:
            teachers.append({"id": tid, "name": name})
            _save("teachers", teachers)
            st.success("Teacher added.")
        else:
            st.error("Teacher ID and Name required.")


# ============================================================
# TIMETABLE MANAGEMENT
# ============================================================

def timetable_ui():
    st.subheader("📅 Timetable Management")

    timetable = _load("timetable", {})

    st.write("### Current Timetable")
    st.json(timetable)

    class_name = st.text_input("Class (e.g., FYBSc A)")
    subject = st.text_input("Subject")
    teacher = st.text_input("Teacher")
    day = st.selectbox("Day", [
        "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday"
    ])
    slot = st.text_input("Lecture Slot (e.g., 9am–10am)")

    if st.button("Add Entry"):
        if class_name:
            timetable.setdefault(class_name, [])
            timetable[class_name].append({
                "subject": subject,
                "teacher": teacher,
                "day": day,
                "slot": slot,
            })
            _save("timetable", timetable)
            st.success("Timetable updated.")
        else:
            st.error("Class name is required.")


# ============================================================
# LECTURE SLOT MANAGEMENT
# ============================================================

def lecture_slots_ui():
    st.subheader("⏰ Lecture Slot Management")

    slots = _load("lecture_slots", [])

    st.write("### Current Lecture Slots")
    st.table(pd.DataFrame(slots)) if slots else st.info("No slots added yet.")

    slot_name = st.text_input("Slot Name")
    slot_time = st.text_input("Time (e.g., 10am–11am)")

    if st.button("Add Slot"):
        if slot_name and slot_time:
            slots.append({"slot": slot_name, "time": slot_time})
            _save("lecture_slots", slots)
            st.success("Slot added.")
        else:
            st.error("Both fields required.")


# ============================================================
# ATTENDANCE HISTORY (permanent Storage API)
# ============================================================

def attendance_history_ui():
    st.subheader("📚 Attendance History")

    keys = st.storage.list("attendance/")
    if not keys:
        st.info("No saved attendance records.")
        return

    selected = st.selectbox("Select an attendance entry", keys)

    if st.button("Load Attendance"):
        data = st.storage.read(selected)
        if not data:
            st.error("No data in this entry.")
        else:
            st.dataframe(pd.DataFrame(data))


# ============================================================
# SAVE ATTENDANCE via Storage API
# ============================================================

def save_attendance_history(final_df, class_name, subject):
    date = datetime.now().strftime("%Y-%m-%d")
    key = f"attendance/{class_name}_{subject}_{date}"
    st.storage.write(key, final_df.to_dict(orient="records"))
    return key


# ============================================================
# ADMIN PANEL UI
# ============================================================

def admin_panel_ui(final_df=None, class_name="", subject=""):
    st.header("🛠 Admin Panel")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Students",
        "Teachers",
        "Timetable",
        "Lecture Slots",
        "History"
    ])

    with tab1: student_management_ui()
    with tab2: teacher_management_ui()
    with tab3: timetable_ui()
    with tab4: lecture_slots_ui()
    with tab5: attendance_history_ui()

    if final_df is not None:
        if st.button("💾 Save Attendance Permanently"):
            key = save_attendance_history(final_df, class_name, subject)
            st.success(f"Attendance saved under key: {key}")
