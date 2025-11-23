# storage.py (JSON file storage for students + attendance saving)
import json
import os
from datetime import datetime

DATA_DIR = "data"
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
ATTENDANCE_DIR = os.path.join(DATA_DIR, "attendance_history")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ATTENDANCE_DIR, exist_ok=True)

# ensure file exists
if not os.path.exists(STUDENTS_FILE):
    with open(STUDENTS_FILE, "w") as f:
        json.dump([], f, indent=4)


def load_students():
    try:
        with open(STUDENTS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_students(students):
    with open(STUDENTS_FILE, "w") as f:
        json.dump(students, f, indent=4)


def get_student_by_id(sid):
    students = load_students()
    for s in students:
        if s["id"] == sid:
            return s
    return None


def add_student(sid, name, programme, student_class, embeddings):
    students = load_students()

    # Normalize embeddings
    if isinstance(embeddings, dict):
        embeddings = [embeddings]
    if isinstance(embeddings, list) and len(embeddings) > 0 and isinstance(embeddings[0], (float, int)):
        embeddings = [embeddings]

    for s in students:
        if s["id"] == sid:
            s.setdefault("embeddings", []).extend(embeddings)
            save_students(students)
            return

    students.append({
        "id": sid,
        "name": name,
        "programme": programme,
        "class": student_class,
        "embeddings": embeddings
    })
    save_students(students)


def update_student_embeddings(sid, new_embeddings):
    students = load_students()
    if isinstance(new_embeddings, dict):
        new_embeddings = [new_embeddings]
    if isinstance(new_embeddings, list) and len(new_embeddings) > 0 and isinstance(new_embeddings[0], (float, int)):
        new_embeddings = [new_embeddings]

    for s in students:
        if s["id"] == sid:
            s.setdefault("embeddings", []).extend(new_embeddings)
            save_students(students)
            return True
    return False


def delete_student_by_id(sid):
    students = load_students()
    students = [s for s in students if s["id"] != sid]
    save_students(students)


def save_attendance(class_name, subject, df):
    """Save attendance as Excel file in attendance_history."""
    today = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fname = f"{class_name}_{subject}_{today}.xlsx".replace(" ", "_")
    path = os.path.join(ATTENDANCE_DIR, fname)
    try:
        df.to_excel(path, index=False)
    except Exception as e:
        # fallback: save as json
        with open(path.replace(".xlsx", ".json"), "w") as f:
            json.dump(df.to_dict(orient="records"), f, indent=4)
    return path
