# attendance_app.py

# Libraries installation (run once)
# !pip install deepface opencv-python matplotlib pandas openpyxl notebook-authenticator --quiet

import os
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from deepface import DeepFace
from datetime import datetime
from base64 import b64decode
from IPython.display import display
from google.colab import files
import time

# System Configs
CONFIG = {
    'model_name': 'ArcFace',
    'detector_backend': 'opencv',
    'distance_metric': 'cosine',
    'base_threshold': 0.4,
    'min_face_confidence': 0.85,
    'alignment': True,
    'normalization': 'ArcFace'
}

# Utility Functions

def cosine_similarity(vec1, vec2):
    vec1, vec2 = np.array(vec1), np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def calculate_similarity_score(vec1, vec2):
    cos_sim = cosine_similarity(vec1, vec2)
    return (cos_sim + 1) / 2 * 100

def quality_check_face(face_obj):
    confidence = face_obj.get('confidence', 0)
    area = face_obj['facial_area']
    return (confidence >= CONFIG['min_face_confidence'] and area['w'] >= 30 and area['h'] >= 30), confidence

# Reference Enrollment
def enroll_students():
    print("Upload reference images (one image per unique student):")
    uploaded_refs = files.upload()

    filename_to_name = {}
    for filename in uploaded_refs.keys():
        print(f"\nImage: {filename}")
        img = Image.open(filename)
        display(img.resize((250, 250)))
        name = input("Enter student name for this image: ").strip().lower()
        filename_to_name[filename] = name

    embeddings_dict = {}
    for file_name, name in filename_to_name.items():
        try:
            faces = DeepFace.extract_faces(img_path=file_name, detector_backend=CONFIG['detector_backend'], enforce_detection=True, align=CONFIG['alignment'])
            if len(faces) == 0:
                print(f"⚠️ No face detected in {file_name}")
                continue
            face_obj = faces[0]
            valid, conf = quality_check_face(face_obj)
            if not valid:
                print(f"⚠️ Low quality face in {file_name} (confidence {conf:.2%})")
                continue
            rep = DeepFace.represent(img_path=file_name, model_name=CONFIG['model_name'], detector_backend=CONFIG['detector_backend'], enforce_detection=True, align=CONFIG['alignment'], normalization=CONFIG['normalization'])
            embedding = rep[0]["embedding"]
            embeddings_dict.setdefault(name, []).append(embedding)
            print(f"✅ Processed {file_name} as {name}")
        except Exception as e:
            print(f"❌ Error processing {file_name}: {e}")

    if not embeddings_dict:
        raise RuntimeError("❌ No valid embeddings created.")

    master_embeddings = {name: np.mean(vectors, axis=0) for name, vectors in embeddings_dict.items()}
    print(f"\n✅ Enrollment finished: {len(master_embeddings)} students enrolled.")
    return master_embeddings

# Capture or upload group photo
def capture_or_upload():
    choice = input("Type 'c' to capture photo from webcam or 'u' to upload: ").strip().lower()
    if choice == 'c':
        from IPython.display import Javascript
        from google.colab import output

        def capture_image(filename='group_photo.jpg'):
            display(Javascript('''
                async function capturePhoto() {
                    const div = document.createElement('div');
                    const video = document.createElement('video');
                    const button = document.createElement('button');
                    button.textContent = 'Capture';
                    div.appendChild(video);
                    div.appendChild(button);
                    document.body.appendChild(div);
                    const stream = await navigator.mediaDevices.getUserMedia({video:true});
                    video.srcObject = stream;
                    await video.play();
                    await new Promise(resolve => button.onclick = resolve);
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    stream.getTracks().forEach(track => track.stop());
                    div.remove();
                    const dataUrl = canvas.toDataURL('image/jpeg');
                    google.colab.kernel.invokeFunction('notebook.captureCallback', [dataUrl], {});
                }
                capturePhoto();
            '''))
            image_data = {}
            def callback(data): image_data["data"] = data
            output.register_callback('notebook.captureCallback', callback)
            while "data" not in image_data: time.sleep(0.1)
            img_bytes = b64decode(image_data["data"].split(',')[1])
            with open(filename, 'wb') as f:
                f.write(img_bytes)
            print(f"✅ Captured image saved as {filename}")

        capture_image()
        return "group_photo.jpg"
    else:
        print("Upload a group image file:")
        upload = files.upload()
        return list(upload.keys())[0]

# Detect faces and recognize students
def detect_and_recognize(group_image_path, master_embeddings):
    group_img = cv2.imread(group_image_path)
    group_img_rgb = cv2.cvtColor(group_img, cv2.COLOR_BGR2RGB)
    faces = DeepFace.extract_faces(img_path=group_image_path, detector_backend=CONFIG['detector_backend'], enforce_detection=False, align=CONFIG['alignment'])

    if len(faces) == 0:
        raise RuntimeError("No faces detected in group image")

    attendance = {name: False for name in master_embeddings.keys()}
    recognition_results = []

    for idx, face_obj in enumerate(faces):
        try:
            valid, conf = quality_check_face(face_obj)
            if not valid:
                recognition_results.append({'face_id': idx + 1, 'name': 'Unknown', 'confidence': 0, 'status': 'Low Quality'})
                continue

            x, y, w, h = face_obj["facial_area"].values()
            cropped_face = group_img_rgb[y:y+h, x:x+w]
            face_img = Image.fromarray(cropped_face)
            tmp_file = f"tmp_face_{idx}.jpg"
            face_img.save(tmp_file)

            rep = DeepFace.represent(img_path=tmp_file, model_name=CONFIG['model_name'], detector_backend=CONFIG['detector_backend'], enforce_detection=False, align=CONFIG['alignment'], normalization=CONFIG['normalization'])
            face_emb = rep[0]["embedding"]
            os.remove(tmp_file)

            best_match, best_score = None, 0
            for name, emb in master_embeddings.items():
                sim = calculate_similarity_score(face_emb, emb)
                if sim > best_score:
                    best_score = sim
                    best_match = name

            is_match = best_score >= (1 - CONFIG['base_threshold']) * 100
            attendance[best_match] = attendance.get(best_match, False) or is_match

            recognition_results.append({
                'face_id': idx + 1,
                'name': best_match.upper() if is_match else 'Unknown',
                'confidence': best_score,
                'status': 'Match' if is_match else 'No Match'
            })
        except Exception as e:
            recognition_results.append({'face_id': idx + 1, 'name': 'Error', 'confidence': 0, 'status': str(e)})

    # Visualize
    plt.figure(figsize=(16, 10))
    for idx, face_obj in enumerate(faces):
        bbox = face_obj["facial_area"]
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        face_img = group_img_rgb[y:y+h, x:x+w]
        plt.subplot(1, len(faces), idx+1)
        plt.imshow(face_img)
        label = "{} ({:.1f}%)".format(recognition_results[idx]['name'], recognition_results[idx]['confidence'])
        plt.title(label)
        plt.axis('off')
    plt.show()

    # Attendance report
    print("\nAttendance Report:")
    present_count = 0
    for name, present in attendance.items():
        status = "PRESENT" if present else "ABSENT"
        if present: present_count += 1
        print(f"{name.capitalize():15}: {status}")
    print(f"\nTotal Students: {len(attendance)} | Present: {present_count} | Absent: {len(attendance) - present_count}")

    return attendance

# Save attendance report to Excel
def save_attendance_excel(attendance):
    export = input("Export attendance to Excel? (y/n): ").strip().lower()
    if export == 'y':
        today = datetime.now().strftime("%Y-%m-%d")
        data = [{"Name": k.capitalize(), "Status": ("Present" if v else "Absent"), "Date": today} for k, v in attendance.items()]
        df = pd.DataFrame(data)
        filename = f"attendance_{today.replace('-', '')}.xlsx"
        df.to_excel(filename, index=False)
        files.download(filename)
        print(f"✅ Attendance saved to {filename}")
    else:
        print("Excel export skipped.")

# Main routine to run interactively
def main():
    print("=== Student Enrollment ===")
    master_embeddings = enroll_students()

    print("\n=== Take Attendance ===")
    group_image_path = capture_or_upload()

    attendance = detect_and_recognize(group_image_path, master_embeddings)

    save_attendance_excel(attendance)

if __name__ == "__main__":
    main()
