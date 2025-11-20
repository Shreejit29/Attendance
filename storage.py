import os
import pickle

DATA_DIR = "data"
ENCODINGS_FILE = os.path.join(DATA_DIR, "students.pkl")

def ensure():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_students():
    ensure()
    if not os.path.exists(ENCODINGS_FILE):
        return []
    with open(ENCODINGS_FILE, "rb") as f:
        return pickle.load(f)

def save_students(data):
    ensure()
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)

def add_student(student_id, name, embedding_list):
    data = load_students()
    # append embedding if student exists
    for s in data:
        if s["id"] == student_id:
            s["embeddings"].append(embedding_list)
            save_students(data)
            return
    # new student
    data.append({
        "id": student_id,
        "name": name,
        "embeddings": [embedding_list]
    })
    save_students(data)
