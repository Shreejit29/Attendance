import json
import os

DATA_DIR = "data"
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
ATTENDANCE_DIR = os.path.join(DATA_DIR, "attendance_history")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ATTENDANCE_DIR, exist_ok=True)

# ensure file exists
if not os.path.exists(STUDENTS_FILE):
    with open(STUDENTS_FILE, "w") as f:
        json.dump([], f)


def load_students():
    try:
        with open(STUDENTS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


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
