import json
import os

STUDENTS_FILE = "students.json"

def load_students():
    if not os.path.exists(STUDENTS_FILE):
        return []

    try:
        with open(STUDENTS_FILE, "r") as f:
            students = json.load(f)
    except:
        return []

    for s in students:
        s.setdefault("programme", "")
        s.setdefault("class", "")
        s.setdefault("embeddings", [])
    return students


def save_students(students):
    with open(STUDENTS_FILE, "w") as f:
        json.dump(students, f, indent=4)


def add_student(sid, name, programme, student_class, embedding):
    students = load_students()

    # Update existing student
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


def delete_student_by_id(student_id):
    students = load_students()
    updated = [s for s in students if s["id"] != student_id]
    save_students(updated)
