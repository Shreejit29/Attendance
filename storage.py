# storage.py — Streamlit Storage API version
import streamlit as st
import pandas as pd


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _load(key, default):
    """Load value from Streamlit Storage."""
    data = st.storage.read(key)
    if data is None:
        return default
    return data


def _save(key, value):
    """Save value permanently."""
    st.storage.write(key, value)


# ============================================================
# STUDENT STORAGE
# ============================================================

def load_students():
    """Return list of all registered students."""
    return _load("students", [])


def save_students(students):
    """Save entire student list permanently."""
    _save("students", students)


def get_student_by_id(sid):
    """Return student dict or None."""
    students = load_students()
    for s in students:
        if s["id"] == sid:
            return s
    return None


def add_student(sid, name, programme, student_class, embeddings):
    """Add new student OR append new embeddings."""

    students = load_students()

    # Normalize embedding input
    if isinstance(embeddings, dict):
        embeddings = [embeddings]
    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], (float, int)):
        embeddings = [embeddings]

    # If student exists → append embeddings
    for s in students:
        if s["id"] == sid:
            s["embeddings"].extend(embeddings)
            save_students(students)
            return

    # Add new student
    students.append({
        "id": sid,
        "name": name,
        "programme": programme,
        "student_class": student_class,
        "embeddings": embeddings
    })

    save_students(students)


def update_student_embeddings(sid, new_embeddings):
    """Add new embeddings to an existing student."""
    students = load_students()

    # Normalize
    if isinstance(new_embeddings, dict):
        new_embeddings = [new_embeddings]
    if isinstance(new_embeddings, list) and isinstance(new_embeddings[0], (int, float)):
        new_embeddings = [new_embeddings]

    for s in students:
        if s["id"] == sid:
            s["embeddings"].extend(new_embeddings)
            save_students(students)
            return True

    return False


def delete_student_by_id(sid):
    """Remove student from storage."""
    students = load_students()
    students = [s for s in students if s["id"] != sid]
    save_students(students)


# ============================================================
# ATTENDANCE HISTORY
# ============================================================

def save_attendance(class_name, subject, df):
    """
    Store attendance record permanently using Streamlit Storage.
    Key format: attendance/class_subject_date
    """
    date = pd.Timestamp.now().strftime("%Y-%m-%d")

    key = f"attendance/{class_name}_{subject}_{date}"

    data = df.to_dict(orient="records")

    st.storage.write(key, data)

    return key


def load_all_attendance():
    """Load all attendance files from storage."""
    keys = st.storage.list("attendance/")

    all_records = []

    for key in keys:
        data = st.storage.read(key)
        if data:
            all_records.extend(data)

    return pd.DataFrame(all_records) if all_records else pd.DataFrame()
