# admin_management.py — Streamlit Storage API version

import streamlit as st
import pandas as pd
from datetime import datetime
from storage import load_students, save_students, load_all_attendance


# ============================================================
# INTERNAL STORAGE WRAPPERS
# ============================================================

def _load(key, default):
    """Load from permanent Streamlit Storage."""
    data = st.storage.read(key)
    if data is None:
        return default
    return data


def _save(key, value):
    """Save permanently."""
    st.storage.write(key, value)


# ============================================================
# STUDENT MANAGEMENT
# ============================================================

def delete_student(student_id):
    students = load_students()
    new_list = [s for s in students if s["id"] != student_id]
    save_students(new_list)


def student_management_ui():
    st.subheader("👨‍🎓 Student Management")

    students = load_students()
    if not students:
        st.info("No students registered.")
        return

    df = pd.DataFrame(students)
    st.dataframe(df[["id", "name", "programme", "student_class"]])

    student_id = st.selectbox(
        "Select student to delete",
        [s["id"] for s in students],
        key="delete_student"
    )

    if st.button("❌ Delete Student"):
        delete_student(student_id)
        st.success("Student deleted successfully.")
        st.experimental_rerun()


# ============================================================
# TEACHER MANAGEMENT
# ============================================================

def teacher_management_ui():
    st.subheader("👨‍🏫 Teacher Management")

    teachers = _load("teachers", [])

    st.write("### Current Teachers")
    if teachers:
        st.table(pd.DataFrame(teachers))
    else:
        st.info("No teachers added yet.")

    tid = st.text_input("Teacher ID")
    name = st.text_input("Teacher Name")

    if st.button("Add Teacher"):
        if tid and name:
            teachers.append({"id": tid, "name": name})
            _save("teachers", teachers)
            st.success("Teacher added.")
        else:
            st.error("Please enter ID & Name.")


# ============================================================
# TIMETABLE MANAGEMENT
# ============================================================

def timetable_ui():
    st.subheader("📅 Timetable Management")

    timetable = _load("timetable", {})

    st.write("### Current Timetable")
    st.json(timetable)

    class_name = st.text_input("Class Name (e.g. FYBSc A)")
    subject = st.text_input("Subject")
    teacher = st.text_input("Teacher")
    day = st.selectbox(
        "Day",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    )
    slot = st.text_input("Time Slot (e.g. 9am–10am)")

    if st.button("Add Timetable Entry"):
        if not class_name:
            st.error("Class name required.")
        else:
            timetable.setdefault(class_name, [])
            timetable[class_name].append({
                "subject": subject,
                "teacher": teacher,
                "day": day,
                "slot": slot
            })
            _save("timetable", timetable)
            st.success("Timetable updated.")


# ============================================================
# LECTURE SLOTS MANAGEMENT
# ============================================================

def lecture_slots_ui():
    st.subheader("⏰ Lecture Slot Management")

    slots = _load("lecture_slots", [])

    st.write("### Current Lecture Slots")
    if slots:
        st.table(pd.DataFrame(slots))
    else:
        st.info("No slots defined yet.")

    slot_name = st.text_input("Slot Name")
    slot_time = st.text_input("Time (e.g. 10am–11am)")

    if st.button("Add Slot"):
        if slot_name and slot_time:
            slots.append({"slot": slot_name, "time": slot_time})
            _save("lecture_slots", slots)
            st.success("Slot added.")
        else:
            st.error("Both fields required.")


# ============================================================
# ATTENDANCE HISTORY (STORAGE API)
# ============================================================

def attendance_history_ui():
    st.subheader("📚 Attendance History")

    keys = st.storage.list("attendance/")

    if not keys:
        st.info("No attendance history stored yet.")
        return

    selected = st.selectbox("Select attendance entry", keys)

    if st.button("Load Attendance"):
        data = st.storage.read(selected)
        if not data:
            st.error("No data found in this entry.")
        else:
            df = pd.DataFrame(data)
            st.dataframe(df)


# ============================================================
# SAVE ATTENDANCE RECORD (ADMIN CALL)
# ============================================================

def save_attendance_history(final_df, class_name, subject):
    """Save attendance record permanently via Storage API."""
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"attendance/{class_name}_{subject}_{today}"

    st.storage.write(key, final_df.to_dict(orient="records"))
    return key


# ============================================================
# ADMIN PANEL (MASTER UI)
# ============================================================

def admin_panel_ui(final_df=None, class_name="", subject=""):
    st.header("🛠 Admin Panel")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Students",
        "Teachers",
        "Timetable",
        "Lecture Slots",
        "History",
    ])

    with tab1:
        student_management_ui()

    with tab2:
        teacher_management_ui()

    with tab3:
        timetable_ui()

    with tab4:
        lecture_slots_ui()

    with tab5:
        attendance_history_ui()

    # Save attendance if admin came from attendance module
    if final_df is not None:
        if st.button("💾 Save Attendance to Permanent History"):
            key = save_attendance_history(final_df, class_name, subject)
            st.success(f"Attendance saved under key: {key}")
