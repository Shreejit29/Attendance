# ============================================================
# storage.py — Permanent Storage using Streamlit Storage API
# No JSON files. 100% Cloud-Safe. Never wiped on rerun.
# ============================================================

import streamlit as st


# ------------------------------------------------------------
# Internal load/save wrappers
# ------------------------------------------------------------

def _load(key, default):
    data = st.storage.read(key)
    return data if data is not None else default


def _save(key, value):
    st.storage.write(key, value)


# ============================================================
# STUDENT STORAGE
# ============================================================

STUDENTS_KEY = "students"


def load_students():
    """Load all students from permanent storage."""
    return _load(STUDENTS_KEY, [])


def save_students(students):
    """Save full student list."""
    _save(STUDENTS_KEY, students)


def get_student_by_id(sid):
    """Retrieve one student."""
    students = load_students()
    for s in students:
        if s["id"] == sid:
            return s
    return None


def add_student(sid, name, programme, student_class, embeddings):
    """Add new student OR append more embeddings to existing one."""

    students = load_students()

    # Normalize embeddings
    if isinstance(embeddings, dict):
        embeddings = [embeddings]
    if isinstance(embeddings, list) and isinstance(embeddings[0], (float, int)):
        embeddings = [embeddings]

    # Check if student exists → append embeddings
    for s in students:
        if s["id"] == sid:
            s["embeddings"].extend(embeddings)
            save_students(students)
            return

    # Create new student
    new_student = {
        "id": sid,
        "name": name,
        "programme": programme,
        "student_class": student_class,
        "embeddings": embeddings,
    }

    students.append(new_student)
    save_students(students)


def update_student_embeddings(sid, new_embeddings):
    """Add more embeddings later."""
    students = load_students()

    # Normalize
    if isinstance(new_embeddings, dict):
        new_embeddings = [new_embeddings]
    if isinstance(new_embeddings, list) and isinstance(new_embeddings[0], (float, int)):
        new_embeddings = [new_embeddings]

    for s in students:
        if s["id"] == sid:
            s["embeddings"].extend(new_embeddings)
            save_students(students)
            return True

    return False


def delete_student_by_id(sid):
    """Remove student completely."""
    students = load_students()
    updated = [s for s in students if s["id"] != sid]
    save_students(updated)


# ============================================================
# ATTENDANCE STORAGE
# ============================================================

def save_attendance(class_name, subject, df):
    """
    Save attendance record permanently using:
    Key: attendance/<class>_<subject>_<date>
    """
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    key = f"attendance/{class_name}_{subject}_{today}"

    st.storage.write(key, df.to_dict(orient="records"))

    return key


def load_all_attendance():
    """Load all attendance entries as {key: data}."""
    keys = st.storage.list("attendance/")
    records = {}

    for k in keys:
        data = st.storage.read(k)
        records[k] = data

    return records
