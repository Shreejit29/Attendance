# utils.py — Face Recognition (dlib) backend for Attendance System
# No DeepFace, No TensorFlow, No SciPy.
# Fully compatible with Streamlit Cloud.

import os
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import face_recognition
from sklearn.cluster import DBSCAN
import time

DB_PATH = "student_db"
META_CSV = os.path.join(DB_PATH, "metadata.csv")
EMB_NPZ = os.path.join(DB_PATH, "embeddings.npz")

os.makedirs(DB_PATH, exist_ok=True)

# Distance threshold (Your selection)
THRESHOLD = 0.65


# --------------------------------------------------------
# ENROLLMENT
# --------------------------------------------------------
def enroll_student(student_id: str, name: str, image_path: str):
    """
    Save student image and update metadata, then re-generate embeddings.
    """
    filename = f"{student_id}__{name.replace(' ', '_')}.jpg"
    dest = os.path.join(DB_PATH, filename)

    img = Image.open(image_path).convert("RGB")
    img.save(dest)

    # Update metadata CSV
    if os.path.exists(META_CSV):
        df = pd.read_csv(META_CSV)
    else:
        df = pd.DataFrame(columns=["student_id", "name", "filename", "mandatory"])

    df = df[df["student_id"] != str(student_id)]  # remove old
    df = pd.concat([
        df,
        pd.DataFrame([{
            "student_id": str(student_id),
            "name": name,
            "filename": filename,
            "mandatory": False
        }])
    ], ignore_index=True)

    df.to_csv(META_CSV, index=False)

    # rebuild embeddings
    rebuild_embeddings_index()


def list_students():
    if os.path.exists(META_CSV):
        return pd.read_csv(META_CSV)
    return pd.DataFrame(columns=["student_id", "name", "filename", "mandatory"])


def set_mandatory(student_id: str, value: bool):
    df = list_students()
    if student_id in df["student_id"].values:
        df.loc[df["student_id"] == student_id, "mandatory"] = value
        df.to_csv(META_CSV, index=False)
        return True
    return False


# --------------------------------------------------------
# FACE DETECTION + ENCODING
# --------------------------------------------------------
def detect_and_encode(image):
    """
    Detect a face and generate a 128-D embedding.
    Returns list of encodings.
    """
    # face_recognition expects RGB
    rgb = image[:, :, ::-1]

    boxes = face_recognition.face_locations(rgb, model="hog")  # fast, CPU-safe
    if not boxes:
        return []

    encodings = face_recognition.face_encodings(rgb, boxes)
    return encodings


# --------------------------------------------------------
# EMBEDDINGS INDEX
# --------------------------------------------------------
def rebuild_embeddings_index():
    df = list_students()
    all_embeddings = []
    all_ids = []

    for _, row in df.iterrows():
        path = os.path.join(DB_PATH, row["filename"])

        img = np.array(Image.open(path).convert("RGB"))
        encs = detect_and_encode(img)
        if not encs:
            continue

        # Save the first detected face
        all_embeddings.append(encs[0])
        all_ids.append(str(row["student_id"]))

    if all_embeddings:
        np.savez(EMB_NPZ, embeddings=np.vstack(all_embeddings), ids=np.array(all_ids))
    else:
        if os.path.exists(EMB_NPZ):
            os.remove(EMB_NPZ)


def load_embeddings_index():
    if os.path.exists(EMB_NPZ):
        data = np.load(EMB_NPZ, allow_pickle=True)
        return data["embeddings"], data["ids"]
    return None, None


# --------------------------------------------------------
# MATCHING
# --------------------------------------------------------
def match_embedding(embedding, embeddings_db, ids_db, threshold=THRESHOLD):
    """
    Finds the closest face from DB using Euclidean distance.
    """
    if embeddings_db is None:
        return None, None

    distances = np.linalg.norm(embeddings_db - embedding, axis=1)
    idx = np.argmin(distances)
    best_dist = distances[idx]

    if best_dist <= threshold:
        return ids_db[idx], best_dist
    return None, best_dist


# --------------------------------------------------------
# VIDEO FRAME EXTRACTION
# --------------------------------------------------------
def extract_frames_from_video(video_path, sample_rate=8):
    frames = []
    cap = cv2.VideoCapture(video_path)
    index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if index % sample_rate == 0:
            frames.append(frame)
        index += 1

    cap.release()
    return frames


# --------------------------------------------------------
# PROCESS FRAMES: DETECT + ENCODE
# --------------------------------------------------------
def process_frames_for_faces(frames):
    results = []
    for i, frame in enumerate(frames):
        encs = detect_and_encode(frame)
        for e in encs:
            results.append({"frame_idx": i, "embedding": e})
    return results


# --------------------------------------------------------
# DEDUPLICATE MATCHES
# --------------------------------------------------------
def deduplicate_matches(matches):
    """
    Removes repeated students across frames.
    """
    seen = {}
    for m in matches:
        sid = m["student_id"]
        if sid not in seen:
            seen[sid] = m
    return list(seen.values())


# --------------------------------------------------------
# UNKNOWN CLUSTERING
# --------------------------------------------------------
def cluster_unknown_embeddings(emb_list):
    if not emb_list:
        return []

    X = np.vstack(emb_list)
    clustering = DBSCAN(eps=0.7, min_samples=2).fit(X)

    clusters = {}
    for i, label in enumerate(clustering.labels_):
        clusters.setdefault(label, []).append(i)

    return clusters


# --------------------------------------------------------
# ATTENDANCE GENERATION
# --------------------------------------------------------
def generate_attendance(meta_df, matched):
    matched_ids = [m["student_id"] for m in matched]
    dist_map = {m["student_id"]: m["distance"] for m in matched}

    rows = []
    for _, r in meta_df.iterrows():
        sid = str(r["student_id"])
        present = sid in matched_ids

        rows.append({
            "student_id": sid,
            "name": r["name"],
            "mandatory": bool(r["mandatory"]),
            "status": "Present" if present else "Absent",
            "distance": dist_map.get(sid)
        })

    return pd.DataFrame(rows)
