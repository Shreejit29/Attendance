import json
import os

DATA_DIR = "data"
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
ATTENDANCE_DIR = os.path.join(DATA_DIR, "attendance_history")

# Ensure folders exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ATTENDANCE_DIR, exist_ok=True)

# Ensure students file exists
if not os.path.exists(STUDENTS_FILE):
    with open(STUDENTS_FILE, "w") as f:
        json.dump([], f, indent=4)


# ------------------------------------------------------------
# LOAD / SAVE STUDENTS
# ------------------------------------------------------------
def load_students():
    try:
        with open(STUDENTS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_students(students):
    with open(STUDENTS_FILE, "w") as f:
        json.dump(students, f, indent=4)


# ------------------------------------------------------------
# GET ONE STUDENT
# ------------------------------------------------------------
def get_student_by_id(sid):
    students = load_students()
    for s in students:
        if s["id"] == sid:
            return s
    return None


# ------------------------------------------------------------
# ADD NEW STUDENT (supports multiple embeddings)
# ------------------------------------------------------------
def add_student(sid, name, programme, student_class, embeddings):
    students = load_students()

    # Normalize embeddings
    if isinstance(embeddings, dict):
        embeddings = [embeddings]
    if isinstance(embeddings, list) and isinstance(embeddings[0], (float, int)):
        embeddings = [embeddings]

    # If student already exists → append embeddings
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


# ------------------------------------------------------------
# UPDATE STUDENT EMBEDDINGS
# ------------------------------------------------------------
def update_student_embeddings(sid, new_embeddings):
    students = load_students()

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


# ------------------------------------------------------------
# SAVE ATTENDANCE HISTORY
# ------------------------------------------------------------
def save_attendance(class_name, subject, df):
    filename = f"{class_name}_{subject}.json"
    path = os.path.join(ATTENDANCE_DIR, filename)

    with open(path, "w") as f:
        json.dump(df.to_dict(orient="records"), f, indent=4)

    return path
