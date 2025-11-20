# utils.py — Ultra-fast TF-free face recognition utilities
# Detector backend: opencv (Haarcascade)
# Embedding model: SFace (PyTorch, lightweight, no downloads)
# No TensorFlow, No RetinaFace, No MTCNN, No heavy models.

import os
import numpy as np
import pandas as pd
from PIL import Image
import cv2
from deepface import DeepFace
from sklearn.cluster import DBSCAN
import time

# -------------------------
# Paths
# -------------------------
DB_PATH = "student_db"
META_CSV = os.path.join(DB_PATH, "metadata.csv")
EMB_NPZ = os.path.join(DB_PATH, "embeddings.npz")

os.makedirs(DB_PATH, exist_ok=True)

# Use only OpenCV Haarcascade for detection
HAAR_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_detector = cv2.CascadeClassifier(HAAR_PATH)


# -------------------------
# ENROLLMENT
# -------------------------
def enroll_student(student_id: str, name: str, image_path: str):
    """
    Save student image and update metadata.
    """
    filename = f"{student_id}__{name.replace(' ', '_')}.jpg"
    dest = os.path.join(DB_PATH, filename)

    # Save image in DB
    Image.open(image_path).convert("RGB").save(dest)

    # Update metadata
    if os.path.exists(META_CSV):
        df = pd.read_csv(META_CSV)
    else:
        df = pd.DataFrame(columns=["student_id", "name", "filename", "mandatory"])

    # remove old entry if exists
    df = df[df["student_id"] != str(student_id)]

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


# -------------------------
# FACE DETECTION (OpenCV Haarcascade)
# -------------------------
def detect_faces_opencv(image_array):
    """
    Detect faces using OpenCV Haarcascade and return cropped faces.
    """
    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    faces = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    crops = []
    for (x, y, w, h) in faces:
        crop = image_array[y:y+h, x:x+w]
        crops.append(crop)
    return crops


# -------------------------
# EMBEDDING COMPUTATION (SFace)
# -------------------------
def compute_embedding_from_array(np_img):
    """
    Compute embedding directly from a numpy image array.
    """
    try:
        rep = DeepFace.represent(
            img_path=np_img,
            model_name="SFace",           # FAST + Accurate + Torch-based
            detector_backend="skip",      # detection already done
            enforce_detection=False
        )
        return np.array(rep)
    except Exception:
        return None


# -------------------------
# REBUILD EMBEDDINGS
# -------------------------
def rebuild_embeddings_index():
    df = list_students()
    embeddings = []
    ids = []

    for _, row in df.iterrows():
        img_path = os.path.join(DB_PATH, row["filename"])
        img = np.array(Image.open(img_path))[:, :, ::-1]

        faces = detect_faces_opencv(img)
        if not faces:
            continue

        emb = compute_embedding_from_array(faces[0])
        if emb is None:
            continue

        embeddings.append(emb)
        ids.append(str(row["student_id"]))

    if embeddings:
        np.savez(EMB_NPZ, embeddings=np.vstack(embeddings), ids=np.array(ids))
    else:
        if os.path.exists(EMB_NPZ):
            os.remove(EMB_NPZ)


def load_embeddings_index():
    if not os.path.exists(EMB_NPZ):
        return None, None
    data = np.load(EMB_NPZ, allow_pickle=True)
    return data["embeddings"], data["ids"]


# -------------------------
# COSINE MATCHING
# -------------------------
def cosine_distance(a, b):
    a = a.astype(float)
    b = b.astype(float)
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)


def match_embedding(embedding, embeddings_db, ids_db, threshold=0.55):
    if embeddings_db is None:
        return None, None

    best_id = None
    best_dist = 999

    for db_emb, sid in zip(embeddings_db, ids_db):
        d = cosine_distance(embedding, db_emb)
        if d < best_dist:
            best_dist = d
            best_id = sid

    if best_dist <= threshold:
        return best_id, best_dist
    return None, best_dist


# -------------------------
# VIDEO FRAME EXTRACTION
# -------------------------
def extract_frames_from_video(video_path, sample_rate=8):
    frames = []
    cap = cv2.VideoCapture(video_path)
    count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if count % sample_rate == 0:
            frames.append(frame)

        count += 1

    cap.release()
    return frames


# -------------------------
# PROCESS FRAMES: DETECT + EMBED
# -------------------------
def process_frames_for_faces(frames):
    out = []

    for idx, frame in enumerate(frames):
        faces = detect_faces_opencv(frame)

        for fc in faces:
            emb = compute_embedding_from_array(fc)
            if emb is not None:
                out.append({
                    "frame_idx": idx,
                    "embedding": emb
                })

    return out


# -------------------------
# MATCH DEDUPLICATION
# -------------------------
def deduplicate_matches(matches):
    unique = {}
    for m in matches:
        sid = m["student_id"]
        if sid not in unique:
            unique[sid] = m
    return list(unique.values())


# -------------------------
# UNKNOWN FACE CLUSTERING
# -------------------------
def cluster_unknown_embeddings(emb_list, eps=0.75, min_samples=2):
    if not emb_list:
        return []

    X = np.vstack(emb_list).astype("float32")
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(X)

    clusters = {}
    for i, label in enumerate(db.labels_):
        clusters.setdefault(label, []).append(i)

    return clusters


# -------------------------
# ATTENDANCE GENERATION
# -------------------------
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
