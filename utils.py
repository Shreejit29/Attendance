# utils.py — TF-free utilities for Smart Attendance App
# Avoids TensorFlow + RetinaFace. Uses PyTorch-based DeepFace backends.
#
# Supported detector_backends: mtcnn, opencv, ssd, dlib
# Supported models: Facenet, Facenet512, ArcFace, VGG-Face, SFace

import os
import numpy as np
import pandas as pd
from PIL import Image
import cv2
from deepface import DeepFace
from sklearn.cluster import DBSCAN

# -------------------------------------------
# Paths
# -------------------------------------------
DB_PATH = "student_db"
META_CSV = os.path.join(DB_PATH, "metadata.csv")
EMB_NPZ = os.path.join(DB_PATH, "embeddings.npz")

os.makedirs(DB_PATH, exist_ok=True)

# -------------------------------------------
# ENROLLMENT
# -------------------------------------------

def enroll_student(student_id: str, name: str, image_path: str):
    """
    Save student image and update metadata.
    """
    filename = f"{student_id}__{name.replace(' ', '_')}.jpg"
    dest = os.path.join(DB_PATH, filename)

    Image.open(image_path).convert("RGB").save(dest)

    # Update metadata
    if os.path.exists(META_CSV):
        meta = pd.read_csv(META_CSV)
    else:
        meta = pd.DataFrame(columns=["student_id", "name", "filename", "mandatory"])

    meta = meta[meta["student_id"] != str(student_id)]
    meta = pd.concat([
        meta,
        pd.DataFrame([{
            "student_id": str(student_id),
            "name": name,
            "filename": filename,
            "mandatory": False
        }])
    ], ignore_index=True)

    meta.to_csv(META_CSV, index=False)

    # Rebuild embeddings
    rebuild_embeddings_index()

    return dest


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

# -------------------------------------------
# EMBEDDINGS (NO TENSORFLOW)
# -------------------------------------------

def compute_embedding(image_path, model_name="Facenet", detector_backend="mtcnn"):
    """
    Compute embedding using DeepFace.represent (Torch models).
    """
    try:
        rep = DeepFace.represent(
            img_path=image_path,
            model_name=model_name,
            detector_backend=detector_backend,
            enforce_detection=False   # avoid hard crashes
        )
        return np.array(rep)
    except Exception:
        return None


def rebuild_embeddings_index(model="Facenet", detector="mtcnn"):
    df = list_students()
    embeddings = []
    ids = []

    for _, row in df.iterrows():
        path = os.path.join(DB_PATH, row["filename"])
        if os.path.exists(path):
            emb = compute_embedding(path, model_name=model, detector_backend=detector)
            if emb is not None:
                embeddings.append(emb)
                ids.append(str(row["student_id"]))

    if len(embeddings) > 0:
        np.savez(EMB_NPZ, embeddings=np.vstack(embeddings), ids=np.array(ids))
    else:
        if os.path.exists(EMB_NPZ):
            os.remove(EMB_NPZ)


def load_embeddings_index():
    if not os.path.exists(EMB_NPZ):
        return None, None

    data = np.load(EMB_NPZ, allow_pickle=True)
    return data["embeddings"], data["ids"]

# -------------------------------------------
# MATCHING (cosine distance)
# -------------------------------------------

def cosine_distance(a, b):
    if a is None or b is None:
        return 999
    a = a.astype(float)
    b = b.astype(float)
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)


def match_embedding(embedding, embeddings_db, ids_db, threshold=0.6):
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

# -------------------------------------------
# FRAME EXTRACTION
# -------------------------------------------

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

# -------------------------------------------
# FACE EXTRACTION + EMBEDDING PER FRAME
# -------------------------------------------

def process_frames_for_faces(frames, model_name="Facenet", detector_backend="mtcnn"):
    """
    Process list of frames:
    - detect faces using DeepFace.extract_faces
    - compute embedding for each cropped face
    """
    out = []

    for idx, frame in enumerate(frames):
        rgb = frame[:, :, ::-1]  # BGR → RGB
        # save temporary
        tmp_path = f"tmp_face_{time.time()}_{idx}.jpg"
        Image.fromarray(rgb).save(tmp_path)

        try:
            faces = DeepFace.extract_faces(
                img_path=tmp_path,
                detector_backend=detector_backend,
                enforce_detection=False
            )
        except:
            faces = []

        for fc in faces:
            crop = fc["face"]
            # save crop temporarily
            crop_path = f"tmp_crop_{time.time()}_{idx}.jpg"
            Image.fromarray(crop).save(crop_path)

            emb = compute_embedding(
                crop_path,
                model_name=model_name,
                detector_backend=detector_backend
            )

            if emb is not None:
                out.append({"frame_idx": idx, "embedding": emb})

            try:
                os.remove(crop_path)
            except:
                pass

        try:
            os.remove(tmp_path)
        except:
            pass

    return out

# -------------------------------------------
# DEDUPLICATION
# -------------------------------------------

def deduplicate_matches(matches, similarity_threshold=0.6):
    unique = {}
    for m in matches:
        sid = m["student_id"]
        if sid not in unique:
            unique[sid] = m
    return list(unique.values())

# -------------------------------------------
# UNKNOWN FACE CLUSTERING
# -------------------------------------------

def cluster_unknown_embeddings(emb_list, eps=0.8, min_samples=2):
    if len(emb_list) == 0:
        return []

    X = np.vstack(emb_list).astype("float32")
    db = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean").fit(X)
    labels = db.labels_

    clusters = {}
    for i, label in enumerate(labels):
        clusters.setdefault(label, []).append(i)
    return clusters

# -------------------------------------------
# ATTENDANCE DF
# -------------------------------------------

def generate_attendance(metadata_df, matched_records):
    matched_ids = [m["student_id"] for m in matched_records]
    dist_map = {m["student_id"]: m["distance"] for m in matched_records}

    rows = []
    for _, r in metadata_df.iterrows():
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
