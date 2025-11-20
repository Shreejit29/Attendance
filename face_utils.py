import cv2
import numpy as np
from insightface.app import FaceAnalysis

# Initialize InsightFace
face_app = FaceAnalysis(name="antelopev2", providers=["CPUExecutionProvider"])
face_app.prepare(ctx_id=0, det_size=(640, 640))

def load_image_from_bytes(image_bytes):
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

def get_face_embedding(img_rgb):
    faces = face_app.get(img_rgb)
    if len(faces) == 0:
        return None
    return faces[0].normed_embedding.tolist()

def find_faces_in_image(img_rgb):
    """
    Returns list: (embedding, bounding box)
    """
    faces = face_app.get(img_rgb)
    out = []
    for f in faces:
        emb = f.normed_embedding.tolist()
        box = f.bbox.astype(int).tolist()  # [x1,y1,x2,y2]
        out.append((emb, box))
    return out

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def draw_boxes(img_rgb, boxes, labels):
    img = img_rgb.copy()
    for (x1, y1, x2, y2), name in zip(boxes, labels):
        cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(img, name, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0,255,0), 2)
    return img
