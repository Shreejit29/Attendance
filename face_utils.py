import cv2
import numpy as np
from deepface import DeepFace

def load_image_from_bytes(image_bytes):
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

def get_face_embedding(img_rgb):
    """Return embedding vector (list of floats)."""
    try:
        embedding = DeepFace.represent(img_rgb, model_name="Facenet", enforce_detection=False)
        if embedding:
            return embedding[0]["embedding"]
    except:
        return None

def compare_embeddings(e1, e2, threshold=0.6):
    """Return True if match."""
    dist = np.linalg.norm(np.array(e1) - np.array(e2))
    return dist < threshold, float(dist)

def find_faces_in_image(img_rgb):
    """Returns list of embeddings and bounding boxes."""
    faces = []
    try:
        detections = DeepFace.extract_faces(img_rgb, enforce_detection=False)
        for det in detections:
            emb = det["embedding"]
            box = det["facial_area"]  # x,y,w,h
            faces.append((emb, box))
    except:
        pass
    return faces

def draw_boxes(img_rgb, boxes, labels):
    copy = img_rgb.copy()
    for (x, y, w, h), name in zip(boxes, labels):
        cv2.rectangle(copy, (x,y), (x+w, y+h), (0,255,0), 2)
        cv2.putText(copy, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    return copy
