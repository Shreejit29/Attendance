# utils.py
from deepface import DeepFace
from PIL import Image
import os
import numpy as np
import pandas as pd
import faiss
from sklearn.cluster import DBSCAN
import io
import base64

# -------------------------------------------------------
# Paths
# -------------------------------------------------------
DB_PATH = "student_db"
METADATA_CSV = "student_db/metadata.csv"
EMBEDDING_CSV = "student_db/embeddings.npz"

os.makedirs(DB_PATH, exist_ok=True)

# -------------------------------------------------------
# Student Enrollment & Metadata
# -------------------------------------------------------

def enroll_student(student_id: str, name: str, image_path: str, compute_embedding: bool = True):
    """
    Saves the student image and updates metadata.
    """
    filename = f"{student_id}__{name.replace(' ', '_')}.jpg"
    dest = os.path.join(DB_PATH, filename)

    img = Image.open(image_path).convert("RGB")
    img.save(dest)

    # metadata update
    if os.path.exists(METADATA_CSV):
        meta = pd.read_csv(METADATA_CSV)
    else:
        meta = pd.DataFrame(columns=["student_id", "name", "filename", "mandatory"])

    meta = meta[meta.student_id != student_id]
    meta = pd.concat([
        meta,
        pd.DataFrame([{
            "student_id": student_id,
            "name": name,
            "filename": filename,
            "mandatory": False
        }])
    ], ignore_index=True)
    meta.to_csv(METADATA_CSV, index=False)

    if compute_embedding:
        rebuild_embeddings_index()

    return dest


def list_students():
    if os.path.exists(METADATA_CSV):
        return pd.read_csv(METADATA_CSV)
    return pd.DataFrame(columns=["student_id", "name", "filename", "mandatory"])


def set_mandatory(student_id: str, value: bool = True):
    meta = list_students()
    if student_id in meta.student_id.values:
        meta.loc[meta.student_id == student_id, "mandatory"] = value
        meta.to_csv(METADATA_CSV, index=False)
        return True
    return False


# -------------------------------------------------------
# Embeddings + FAISS Index
# -------------------------------------------------------

def compute_embedding(img_path: str, model_name="Facenet", detector_backend="mtcnn"):
    emb = DeepFace.represent(
        img_path=img_path,
        model_name=model_name,
        detector_backend=detector_backend
    )
    return np.array(emb)


def rebuild_embeddings_index(model_name="Facenet", detector_backend="mtcnn"):
    meta = list_students()
    embeddings = []
    ids = []

    for _, r in meta.iterrows():
        path = os.path.join(DB_PATH, r["filename"])
        if os.path.exists(path):
            emb = compute_embedding(path, model_name, detector_backend)
            embeddings.append(emb)
            ids.append(str(r["student_id"]))

    if len(embeddings) == 0:
        if os.path.exists(EMBEDDING_CSV):
            os.remove(EMBEDDING_CSV)
        return None

    embeddings = np.vstack(embeddings).astype("float32")
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)

    np.savez(EMBEDDING_CSV, embeddings=embeddings, ids=np.array(ids))
    faiss.write_index(index, EMBEDDING_CSV + ".index")

    return True


def load_embeddings_index():
    if not os.path.exists(EMBEDDING_CSV):
        return None, None, None

    arr = np.load(EMBEDDING_CSV, allow_pickle=True)
    embeddings = arr["embeddings"].astype("float32")
    ids = arr["ids"].astype("U")

    index_file = EMBEDDING_CSV + ".index"
    if os.path.exists(index_file):
        index = faiss.read_index(index_file)
    else:
        d = embeddings.shape[1]
        index = faiss.IndexFlatL2(d)
        index.add(embeddings)

    return index, embeddings, ids


def match_embedding(embedding, index, ids, top_k=1, threshold=0.8):
    if index is None:
        return None, None

    D, I = index.search(embedding.reshape(1, -1).astype("float32"), top_k)
    dist = float(D[0][0])
    idx = int(I[0][0])

    if dist <= threshold:
        return ids[idx], dist
    return None, dist


# -------------------------------------------------------
# Video frame extraction
# -------------------------------------------------------

def extract_frames_from_video(video_path, sample_rate=10):
    import cv2
    cap = cv2.VideoCapture(video_path)
    frames = []
    count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if count % sample_rate == 0:
            frames.append(frame.copy())
        count += 1
    cap.release()
    return frames


def process_frames_for_faces(frames, model_name="Facenet", detector_backend="mtcnn"):
    out = []
    import tempfile

    for i, f in enumerate(frames):
        rgb = f[:, :, ::-1]
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        Image.fromarray(rgb).save(tmp.name)

        try:
            faces = DeepFace.extract_faces(img_path=tmp.name, detector_backend=detector_backend)
        except:
            faces = []

        for face in faces:
            crop = face.get("face")
            tmp2 = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            Image.fromarray(crop).save(tmp2.name)

            emb = compute_embedding(tmp2.name, model_name, detector_backend)
            out.append({"frame_idx": i, "embedding": emb})

    return out


# -------------------------------------------------------
# Deduplication & Unknown Face Clustering
# -------------------------------------------------------

def deduplicate_matches(matches, similarity_threshold=0.6):
    unique = {}
    for m in matches:
        sid = m.get("student_id")
        if sid:
            if sid not in unique:
                unique[sid] = m
        else:
            emb = m["embedding"]
            placed = False
            for k, v in unique.items():
                if "embedding" in v:
                    d = np.linalg.norm(v["embedding"] - emb)
                    if d <= similarity_threshold:
                        placed = True
                        break
            if not placed:
                unique[f"unknown_{len(unique)}"] = m
    return list(unique.values())


def cluster_unknown_embeddings(embeddings, eps=0.8, min_samples=2):
    if len(embeddings) == 0:
        return []

    X = np.vstack(embeddings).astype("float32")
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
    labels = clustering.labels_

    clusters = {}
    for i, l in enumerate(labels):
        clusters.setdefault(l, []).append(i)

    return clusters


# -------------------------------------------------------
# Attendance Sheet
# -------------------------------------------------------

def generate_attendance(metadata_df, matched_records):
    matched_ids = [m["student_id"] for m in matched_records if m.get("student_id")]
    distances = {m["student_id"]: m.get("distance") for m in matched_records if m.get("student_id")}

    rows = []
    for _, r in metadata_df.iterrows():
        sid = str(r["student_id"])
        present = sid in matched_ids
        rows.append({
            "student_id": sid,
            "name": r["name"],
            "mandatory": bool(r["mandatory"]),
            "status": "Present" if present else "Absent",
            "distance": distances.get(sid)
        })

    return pd.DataFrame(rows)


# -------------------------------------------------------
# QR Backup (base64 CSV → QR)
# -------------------------------------------------------

def csv_to_qr_image(df):
    import qrcode
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    b64 = base64.b64encode(csv_bytes).decode("utf-8")

    qr = qrcode.make(b64)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    return buf
