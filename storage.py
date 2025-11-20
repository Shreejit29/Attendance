"""
storage.py
Simple local storage helpers. Keeps:
- students/ folder with photos (optional)
- encodings.pkl : list of dicts with {'id', 'name', 'encodings': [np.ndarray,...]}
"""
import os
import pickle
from typing import List, Dict
import numpy as np

DATA_DIR = "data"
STUDENTS_DIR = os.path.join(DATA_DIR, "students")
ENCODINGS_FILE = os.path.join(DATA_DIR, "encodings.pkl")

def ensure_dirs():
    os.makedirs(STUDENTS_DIR, exist_ok=True)

def load_encodings() -> List[Dict]:
    ensure_dirs()
    if not os.path.exists(ENCODINGS_FILE):
        return []
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    # convert lists back to np arrays
    for item in data:
        item["encodings"] = [np.array(e) for e in item["encodings"]]
    return data

def save_encodings(data: List[Dict]):
    ensure_dirs()
    # convert numpy arrays to lists for pickle stability
    serial = []
    for item in data:
        serial.append({
            "id": item["id"],
            "name": item["name"],
            "encodings": [e.tolist() for e in item["encodings"]]
        })
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(serial, f)

def add_student(student_id: str, name: str, encodings: List[np.ndarray], image_bytes: bytes = None):
    """
    Add a student entry or append encodings if id exists.
    """
    ensure_dirs()
    data = load_encodings()
    # check existing
    for item in data:
        if item["id"] == student_id:
            # append new encs
            item["encodings"].extend(encodings)
            save_encodings(data)
            return
    # new entry
    entry = {"id": student_id, "name": name, "encodings": encodings}
    data.append(entry)
    save_encodings(data)
    # optionally save photo file
    if image_bytes:
        fname = os.path.join(STUDENTS_DIR, f"{student_id}.jpg")
        with open(fname, "wb") as f:
            f.write(image_bytes)

def get_student_list():
    return load_encodings()
