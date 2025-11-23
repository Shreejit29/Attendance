import cv2
import numpy as np
from insightface.app import FaceAnalysis
from scipy.spatial.distance import cosine

# -----------------------------------------------------------
# INITIALIZE INSIGHTFACE ENGINE
# -----------------------------------------------------------
face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
face_app.prepare(ctx_id=0, det_size=(640, 640))


# -----------------------------------------------------------
# LOAD IMAGE FROM BYTES
# -----------------------------------------------------------
def load_image_from_bytes(image_bytes):
    """Converts uploaded bytes to RGB numpy array."""
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


# -----------------------------------------------------------
# EXTRACT *MULTIPLE* FACE EMBEDDINGS (For Registration)
# -----------------------------------------------------------
def extract_all_embeddings(img_rgb):
    """
    Returns list of embeddings for all faces in an image.
    Useful for multi-image student registration.
    """
    faces = face_app.get(img_rgb)
    embeddings = []

    for f in faces:
        emb = f.normed_embedding.tolist()

        # FILTER POOR QUALITY FACES
        if f.det_score < 0.50:      # low confidence
            continue
        if f.bbox[2] - f.bbox[0] < 50:  # face too small
            continue

        embeddings.append(emb)

    return embeddings


# -----------------------------------------------------------
# SINGLE EMBEDDING EXTRACTION (Default)
# -----------------------------------------------------------
def get_face_embedding(img_rgb):
    """
    Returns vector for the largest / main face.
    Used in older code – preserved for backwards compatibility.
    """
    faces = face_app.get(img_rgb)
    if len(faces) == 0:
        return None

    # choose the largest face
    largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return largest.normed_embedding.tolist()


# -----------------------------------------------------------
# DETECT FACES & RETURN (embedding, bounding_box)
# -----------------------------------------------------------
def find_faces_in_image(img_rgb):
    """
    Returns list of (embedding, bounding_box)
    Used for multi-shot attendance.
    """
    faces = face_app.get(img_rgb)
    out = []

    for f in faces:
        emb = f.normed_embedding.tolist()
        box = f.bbox.astype(int).tolist()

        # FILTER bad faces
        if f.det_score < 0.50:
            continue

        out.append((emb, box))

    return out


# -----------------------------------------------------------
# COSINE SIMILARITY
# -----------------------------------------------------------
def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# -----------------------------------------------------------
# DRAW BOUNDING BOXES WITH LABELS
# -----------------------------------------------------------
def draw_boxes(img_rgb, boxes, labels):
    img = img_rgb.copy()

    for (x1, y1, x2, y2), name in zip(boxes, labels):
        cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(img, name, (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    return img
