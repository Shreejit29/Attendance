# admin_management.py (JSON-based)
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from storage import load_students, save_students

DATA_DIR = "data"
TEACHERS_FILE = os.path.join(DATA_DIR, "teachers.json")
TIMETABLE_FILE = os.path.join(DATA_DIR, "timetable.json")
SLOTS_FILE = os.path.join(DATA_DIR, "lecture_slots.json")
HISTORY_DIR = os.path.join(DATA_DIR, "attendance_history")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def delete_student(student_id):
    students = load_students()
    new_list = [s for s in students if s["id"] != student_id]
    save_students(new_list)

def student_management_ui():
    st.subheader("👨‍🎓 Student Management")
    students = load_students()
    if not students:
        st.info("No students found.")
        return
    df = pd.DataFrame(students)
    st.dataframe(df[["id", "name"]])
    student_id = st.selectbox("Select student to delete", [s["id"] for s in students])
    if st.button("❌ Delete Student"):
        delete_student(student_id)
        st.success("Student removed.")

def teacher_management_ui():
    st.subheader("👨‍🏫 Teacher Management")
    teachers = _load_json(TEACHERS_FILE, [])
    st.write("### Current Teachers")
    if teachers:
        st.table(pd.DataFrame(teachers))
    else:
        st.info("No teachers added.")
    tid = st.text_input("Teacher ID")
    name = st.text_input("Teacher Name")
    if st.button("Add Teacher"):
        if tid and name:
            teachers.append({"id": tid, "name": name})
            _save_json(TEACHERS_FILE, teachers)
            st.success("Teacher added.")
        else:
            st.error("Enter ID & Name.")

def timetable_ui():
    st.subheader("📅 Timetable Management")
    timetable = _load_json(TIMETABLE_FILE, {})
    st.write("### Current Timetable")
    st.json(timetable)
    class_name = st.text_input("Class", key="tt_class")
    subject = st.text_input("Subject", key="tt_subject")
    teacher = st.text_input("Teacher", key="tt_teacher")
    day = st.selectbox("Day", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], key="tt_day")
    slot = st.text_input("Lecture Slot (e.g. 9am–10am)", key="tt_slot")
    if st.button("Add Entry"):
        if class_name:
            timetable.setdefault(class_name, [])
            timetable[class_name].append({
                "subject": subject,
                "teacher": teacher,
                "day": day,
                "slot": slot
            })
            _save_json(TIMETABLE_FILE, timetable)
            st.success("Timetable updated.")
        else:
            st.error("Enter class name.")

def lecture_slots_ui():
    st.subheader("⏰ Lecture Slot Management")
    slots = _load_json(SLOTS_FILE, [])
    st.write("### Current Slots")
    if slots:
        st.table(pd.DataFrame(slots))
    else:
        st.info("No slots defined.")
    slot_name = st.text_input("Slot Name")
    slot_time = st.text_input("Time (e.g. 10am–11am)")
    if st.button("Add Slot"):
        if slot_name and slot_time:
            slots.append({"slot": slot_name, "time": slot_time})
            _save_json(SLOTS_FILE, slots)
            st.success("Slot added.")
        else:
            st.error("Enter both fields.")

def save_attendance_history(df, class_name, subject):
    today = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fname = f"{class_name}_{subject}_{today}.xlsx".replace(" ", "_")
    path = os.path.join(HISTORY_DIR, fname)
    df.to_excel(path, index=False)
    return path

def attendance_history_ui():
    st.subheader("📚 Attendance History")
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".xlsx")]
    if not files:
        st.info("No attendance history saved.")
        return
    selected = st.selectbox("Select file", files)
    if st.button("Load History"):
        df = pd.read_excel(os.path.join(HISTORY_DIR, selected))
        st.dataframe(df)

def admin_panel_ui(final_df=None, class_name="", subject=""):
    st.header("🛠 Admin Panel")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Students","Teachers","Timetable","Lecture Slots","History"])
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
    if final_df is not None:
        if st.button("💾 Save Attendance to History"):
            path = save_attendance_history(final_df, class_name, subject)
            st.success(f"Saved to: {path}")
