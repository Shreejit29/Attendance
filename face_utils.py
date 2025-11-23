# face_utils.py
import cv2
import numpy as np
from insightface.app import FaceAnalysis

face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
face_app.prepare(ctx_id=0, det_size=(640, 640))


def load_image_from_bytes(image_bytes):
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def extract_all_embeddings(img_rgb, score_threshold=0.50, min_face_size=50):
    faces = face_app.get(img_rgb)
    embeddings = []
    for f in faces:
        w = f.bbox[2] - f.bbox[0]
        h = f.bbox[3] - f.bbox[1]
        if f.det_score < score_threshold:
            continue
        if min(w, h) < min_face_size:
            continue
        embeddings.append(f.normed_embedding.tolist())
    return embeddings


def get_face_embedding(img_rgb):
    faces = face_app.get(img_rgb)
    if len(faces) == 0:
        return None
    largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return largest.normed_embedding.tolist()


def find_faces_in_image(img_rgb, score_threshold=0.50):
    faces = face_app.get(img_rgb)
    out = []
    for f in faces:
        if f.det_score < score_threshold:
            continue
        emb = f.normed_embedding.tolist()
        box = f.bbox.astype(int).tolist()  # [x1,y1,x2,y2]
        out.append((emb, box))
    return out


def cosine_similarity(a, b):
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom != 0 else 0.0


def draw_boxes(img_rgb, boxes, labels):
    img = img_rgb.copy()
    for (x1, y1, x2, y2), name in zip(boxes, labels):
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2)
    return img
