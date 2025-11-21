import os
import pickle

DATA_DIR = "data"
FILE = os.path.join(DATA_DIR, "students.pkl")

def ensure():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_students():
    ensure()
    if not os.path.exists(FILE):
        return []
    with open(FILE, "rb") as f:
        return pickle.load(f)

def save_students(data):
    ensure()
    with open(FILE, "wb") as f:
        pickle.dump(data, f)

def add_student(sid, name, embedding):
    data = load_students()

    for s in data:
        if s["id"] == sid:
            s["embeddings"].append(embedding)
            save_students(data)
            return

    data.append({
        "id": sid,
        "name": name,
        "class": student_class,
        "embeddings": [embedding]
        "embeddings": [embedding]
    })
    save_students(data)
