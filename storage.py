import json
import os

STUDENTS_FILE = "data/students.json"
ATTENDANCE_DIR = "data/attendance_history"

os.makedirs("data", exist_ok=True)
os.makedirs(ATTENDANCE_DIR, exist_ok=True)


def load_students():
    if not os.path.exists(STUDENTS_FILE):
        return []
    with open(STUDENTS_FILE, "r") as f:
        return json.load(f)


def save_students(students):
    with open(STUDENTS_FILE, "w") as f:
        json.dump(students, f, indent=4)


def add_student(sid, name, programme, student_class, embedding):
    students = load_students()

    students.append({
        "id": sid,
        "name": name,
        "programme": programme,
        "class": student_class,
        "embeddings": [embedding]
    })

    save_students(students)


def delete_student_by_id(sid):
    students = load_students()
    students = [s for s in students if s["id"] != sid]
    save_students(students)
