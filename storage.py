# storage.py

import json
import os

STUDENTS_FILE = "students.json"

# ---------------------------------------------------------
# LOAD STUDENTS
# ---------------------------------------------------------
def load_students():
    """Load all students from JSON file."""
    if not os.path.exists(STUDENTS_FILE):
        return []

    try:
        with open(STUDENTS_FILE, "r") as f:
            students = json.load(f)
    except:
        return []

    # Ensure compatibility with older versions (which didn't have programme & class)
    for s in students:
        if "programme" not in s:
            s["programme"] = ""
        if "class" not in s:
            s["class"] = ""
        if "embeddings" not in s:
            s["embeddings"] = []

    return students


# ---------------------------------------------------------
# SAVE STUDENTS
# ---------------------------------------------------------
def save_students(students):
    """Save students list to file."""
    with open(STUDENTS_FILE, "w") as f:
        json.dump(students, f, indent=4)


# ---------------------------------------------------------
# ADD NEW STUDENT
# ---------------------------------------------------------
def add_student(sid, name, programme, student_class, embedding):
    """
    Add a new student.
    New fields added:
    - programme
    - class
    """
    students = load_students()

    # If student exists, update embedding instead of duplicating
    for s in students:
        if s["id"] == sid:
            s["name"] = name
            s["programme"] = programme
            s["class"] = student_class
            s["embeddings"].append(embedding)
            save_students(students)
            return

    # Add new student
    students.append({
        "id": sid,
        "name": name,
        "programme": programme,
        "class": student_class,
        "embeddings": [embedding]
    })

    save_students(students)


# ---------------------------------------------------------
# REMOVE STUDENT (USED BY ADMIN PANEL)
# ---------------------------------------------------------
def delete_student_by_id(student_id):
    """Delete a student by ID."""
    students = load_students()
    new_list = [s for s in students if s["id"] != student_id]
    save_students(new_list)
