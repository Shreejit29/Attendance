import streamlit as st
import cv2
import numpy as np
from deepface import DeepFace
import pandas as pd
from datetime import datetime
import tempfile
import os
from PIL import Image
import pickle
import io
import base64

# Page configuration
st.set_page_config(
    page_title="Face Recognition Attendance System",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown('''
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2563eb;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background: #dcfce7;
        color: #166534;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #10b981;
        margin: 1rem 0;
    }
    .error-box {
        background: #fee2e2;
        color: #991b1b;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ef4444;
        margin: 1rem 0;
    }
    .info-box {
        background: #dbeafe;
        color: #1e40af;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2563eb;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
''', unsafe_allow_html=True)

# Configuration
CONFIG = {
    'model_name': 'ArcFace',
    'detector_backend': 'opencv',
    'distance_metric': 'cosine',
    'base_threshold': 0.40,
    'min_face_confidence': 0.85,
    'alignment': True,
    'normalization': 'ArcFace'
}

# Initialize session state
if 'students_db' not in st.session_state:
    st.session_state.students_db = []
if 'attendance_records' not in st.session_state:
    st.session_state.attendance_records = []
if 'master_embeddings' not in st.session_state:
    st.session_state.master_embeddings = {}

# Utility functions
def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def calculate_similarity_score(vec1, vec2):
    cos_sim = cosine_similarity(vec1, vec2)
    return (cos_sim + 1) / 2 * 100

def process_face_image(image, name):
    '''Process uploaded face image and create embedding'''
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(image.getvalue())
            tmp_path = tmp_file.name

        embedding_obj = DeepFace.represent(
            img_path=tmp_path,
            model_name=CONFIG['model_name'],
            detector_backend=CONFIG['detector_backend'],
            enforce_detection=True,
            align=CONFIG['alignment'],
            normalization=CONFIG['normalization']
        )

        os.unlink(tmp_path)
        return embedding_obj[0]["embedding"], None
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None, str(e)

def detect_and_recognize_faces(image):
    '''Detect faces in image and match with database'''
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(image.getvalue())
            tmp_path = tmp_file.name

        faces = DeepFace.extract_faces(
            img_path=tmp_path,
            detector_backend=CONFIG['detector_backend'],
            enforce_detection=False,
            align=CONFIG['alignment']
        )

        if len(faces) == 0:
            os.unlink(tmp_path)
            return [], "No faces detected in the image"

        img = cv2.imread(tmp_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        results = []
        for idx, face_obj in enumerate(faces):
            area = face_obj["facial_area"]
            x, y, w, h = area["x"], area["y"], area["w"], area["h"]

            face_region = img_rgb[y:y+h, x:x+w]

            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as face_tmp:
                face_img = Image.fromarray(face_region)
                face_img.save(face_tmp.name)
                face_tmp_path = face_tmp.name

            try:
                embedding_obj = DeepFace.represent(
                    img_path=face_tmp_path,
                    model_name=CONFIG['model_name'],
                    detector_backend=CONFIG['detector_backend'],
                    enforce_detection=False,
                    align=CONFIG['alignment'],
                    normalization=CONFIG['normalization']
                )

                face_embedding = embedding_obj[0]["embedding"]

                best_match = None
                best_score = 0
                best_distance = float('inf')

                for student in st.session_state.students_db:
                    student_embedding = st.session_state.master_embeddings.get(student['id'])
                    if student_embedding is not None:
                        cos_sim = cosine_similarity(face_embedding, student_embedding)
                        distance = 1 - cos_sim
                        score = calculate_similarity_score(face_embedding, student_embedding)

                        if score > best_score:
                            best_score = score
                            best_match = student
                            best_distance = distance

                is_match = best_distance <= CONFIG['base_threshold'] and best_match is not None

                results.append({
                    'face_id': idx + 1,
                    'bbox': (x, y, w, h),
                    'matched': is_match,
                    'student': best_match if is_match else None,
                    'confidence': best_score,
                    'distance': best_distance
                })

                os.unlink(face_tmp_path)

            except Exception as e:
                results.append({
                    'face_id': idx + 1,
                    'bbox': (x, y, w, h),
                    'matched': False,
                    'student': None,
                    'confidence': 0,
                    'error': str(e)
                })

        os.unlink(tmp_path)
        return results, img_rgb

    except Exception as e:
        return [], f"Error processing image: {str(e)}"

# Header
st.markdown('<h1 class="main-header">📸 Face Recognition Attendance System</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-Powered Automated Attendance Management</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Navigation")

    page = st.radio(
        "Select Module:",
        ["📊 Dashboard", "➕ Student Enrollment", "📋 Take Attendance", "✏️ Manual Override", "📈 Reports"],
    )

    st.divider()

    st.subheader("📊 Quick Stats")
    st.metric("Total Students", len(st.session_state.students_db))
    st.metric("Classes Conducted", len(st.session_state.attendance_records))

    if len(st.session_state.attendance_records) > 0:
        total_present = sum(
            len([s for s in record['students'] if s['status'] == 'present'])
            for record in st.session_state.attendance_records
        )
        total_students_all = sum(
            len(record['students'])
            for record in st.session_state.attendance_records
        )
        avg_attendance = (total_present / total_students_all * 100) if total_students_all > 0 else 0
        st.metric("Avg Attendance", f"{avg_attendance:.1f}%")

    st.divider()

    st.subheader("💾 Data Management")
    if st.button("📥 Export All Data"):
        data = {
            'students': st.session_state.students_db,
            'embeddings': {k: v.tolist() for k, v in st.session_state.master_embeddings.items()},
            'attendance': st.session_state.attendance_records
        }
        data_bytes = pickle.dumps(data)
        st.download_button(
            "⬇️ Download Backup",
            data_bytes,
            file_name=f"attendance_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl",
            mime="application/octet-stream",
        )

    uploaded_backup = st.file_uploader("📤 Import Backup", type=['pkl'])
    if uploaded_backup:
        try:
            data = pickle.loads(uploaded_backup.getvalue())
            st.session_state.students_db = data['students']
            st.session_state.master_embeddings = {k: np.array(v) for k, v in data['embeddings'].items()}
            st.session_state.attendance_records = data['attendance']
            st.success("✅ Data imported!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Main content
if page == "📊 Dashboard":
    st.header("Dashboard Overview")

    if len(st.session_state.students_db) == 0:
        st.markdown('''
        <div class="info-box">
            <strong>🚀 Getting Started:</strong><br>
            1. Go to <strong>Student Enrollment</strong> to register students<br>
            2. Use <strong>Take Attendance</strong> for face recognition<br>
            3. View <strong>Reports</strong> for analytics
        </div>
        ''', unsafe_allow_html=True)
    else:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("👥 Enrolled Students", len(st.session_state.students_db))

        with col2:
            st.metric("📚 Classes Conducted", len(st.session_state.attendance_records))

        with col3:
            if len(st.session_state.attendance_records) > 0:
                total_present = sum(
                    len([s for s in record['students'] if s['status'] == 'present'])
                    for record in st.session_state.attendance_records
                )
                total_students_all = sum(
                    len(record['students'])
                    for record in st.session_state.attendance_records
                )
                avg_attendance = (total_present / total_students_all * 100) if total_students_all > 0 else 0
                st.metric("📊 Average Attendance", f"{avg_attendance:.1f}%")

        st.divider()

        st.subheader("Recently Enrolled Students")
        recent_students = st.session_state.students_db[-5:][::-1]
        for student in recent_students:
            col1, col2 = st.columns([1, 4])
            with col1:
                if student.get('photo'):
                    st.image(student['photo'], width=80)
            with col2:
                st.write(f"**{student['name']}**")
                st.caption(f"ID: {student['id']} | Class: {student.get('class', 'N/A')}")
                st.caption(f"Enrolled: {student['enrollment_date']}")

elif page == "➕ Student Enrollment":
    st.header("Student Enrollment")
    st.write("Register new students by uploading their face images")

    with st.form("enrollment_form"):
        col1, col2 = st.columns(2)

        with col1:
            student_id = st.text_input("Student ID *", placeholder="e.g., STU001")
            student_name = st.text_input("Full Name *", placeholder="e.g., Rahul Sharma")

        with col2:
            student_class = st.text_input("Class/Section", placeholder="e.g., BSc Physics")
            student_email = st.text_input("Email", placeholder="student@example.com")

        st.write("**Upload Face Images** (1-5 images for better accuracy)")
        uploaded_images = st.file_uploader(
            "Choose images",
            type=['jpg', 'jpeg', 'png'],
            accept_multiple_files=True,
        )

        submit = st.form_submit_button("✅ Enroll Student", use_container_width=True)

        if submit:
            if not student_id or not student_name:
                st.error("❌ Please enter Student ID and Name")
            elif not uploaded_images:
                st.error("❌ Please upload at least one face image")
            elif any(s['id'] == student_id for s in st.session_state.students_db):
                st.error("❌ Student ID already exists!")
            else:
                embeddings = []
                valid_images = []

                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, image in enumerate(uploaded_images):
                    status_text.text(f"Processing image {idx+1}/{len(uploaded_images)}...")
                    progress_bar.progress((idx + 1) / len(uploaded_images))

                    embedding, error = process_face_image(image, student_name)

                    if embedding is not None:
                        embeddings.append(embedding)
                        valid_images.append(image)
                    else:
                        st.warning(f"⚠️ Could not process image {idx+1}: {error}")

                if len(embeddings) > 0:
                    master_embedding = np.mean(embeddings, axis=0)

                    student_data = {
                        'id': student_id,
                        'name': student_name,
                        'class': student_class,
                        'email': student_email,
                        'enrollment_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'photo': None
                    }

                    if valid_images:
                        img = Image.open(valid_images[0])
                        img.thumbnail((200, 200))
                        buf = io.BytesIO()
                        img.save(buf, format='PNG')
                        student_data['photo'] = buf.getvalue()

                    st.session_state.students_db.append(student_data)
                    st.session_state.master_embeddings[student_id] = master_embedding

                    st.success(f"✅ Student {student_name} enrolled with {len(embeddings)} image(s)!")
                    st.balloons()
                else:
                    st.error("❌ No valid face images found")

elif page == "📋 Take Attendance":
    st.header("Take Attendance")

    if len(st.session_state.students_db) == 0:
        st.warning("⚠️ No students enrolled yet!")
    else:
        class_name = st.text_input("Class/Subject Name *", placeholder="e.g., BSc Physics Sem 3")

        uploaded_image = st.file_uploader("Upload Class Photo", type=['jpg', 'jpeg', 'png'])

        if uploaded_image and class_name:
            if st.button("📸 Process Attendance", type="primary", use_container_width=True):
                with st.spinner("🔍 Detecting and recognizing faces..."):
                    results, img_or_error = detect_and_recognize_faces(uploaded_image)

                    if isinstance(img_or_error, str):
                        st.error(f"❌ {img_or_error}")
                    else:
                        attendance_data = {
                            'class_name': class_name,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'timestamp': datetime.now().isoformat(),
                            'students': []
                        }

                        matched_student_ids = set()
                        for result in results:
                            if result['matched'] and result['student']:
                                matched_student_ids.add(result['student']['id'])

                        for student in st.session_state.students_db:
                            is_present = student['id'] in matched_student_ids

                            match_result = None
                            for result in results:
                                if result['matched'] and result['student'] and result['student']['id'] == student['id']:
                                    match_result = result
                                    break

                            attendance_data['students'].append({
                                'id': student['id'],
                                'name': student['name'],
                                'class': student.get('class', 'N/A'),
                                'status': 'present' if is_present else 'absent',
                                'confidence': match_result['confidence'] if match_result else 0,
                                'method': 'face-recognition' if is_present else 'not-detected'
                            })

                        st.session_state.attendance_records.append(attendance_data)

                        present_count = len(matched_student_ids)
                        absent_count = len(st.session_state.students_db) - present_count
                        percentage = (present_count / len(st.session_state.students_db) * 100)

                        st.success("✅ Attendance processed successfully!")

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Present", present_count)
                        col2.metric("Absent", absent_count)
                        col3.metric("Attendance %", f"{percentage:.1f}%")

                        st.divider()

                        st.subheader("Detected Faces")
                        img_display = img_or_error.copy()

                        for result in results:
                            x, y, w, h = result['bbox']
                            color = (0, 255, 0) if result['matched'] else (255, 0, 0)
                            cv2.rectangle(img_display, (x, y), (x+w, y+h), color, 3)

                            if result['matched'] and result['student']:
                                label = f"{result['student']['name']} ({result['confidence']:.0f}%)"
                            else:
                                label = "Unknown"

                            cv2.putText(img_display, label, (x, y-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                        st.image(img_display, use_container_width=True)

                        st.divider()
                        st.subheader("Attendance Details")
                        df = pd.DataFrame(attendance_data['students'])
                        st.dataframe(df[['id', 'name', 'class', 'status', 'confidence']], use_container_width=True)

elif page == "✏️ Manual Override":
    st.header("Manual Attendance Override")

    if len(st.session_state.attendance_records) == 0:
        st.info("ℹ️ No attendance sessions yet")
    else:
        session_options = [f"{r['class_name']} - {r['date']} {r['time']}" for r in st.session_state.attendance_records]

        selected_session = st.selectbox("Select Session", range(len(session_options)), format_func=lambda x: session_options[x])

        if selected_session is not None:
            record = st.session_state.attendance_records[selected_session]
            absent_students = [s for s in record['students'] if s['status'] == 'absent']

            if len(absent_students) == 0:
                st.success("✅ All students were marked present!")
            else:
                st.write(f"**Found {len(absent_students)} absent student(s)**")

                with st.form("manual_override"):
                    overrides = {}
                    for student in absent_students:
                        overrides[student['id']] = st.checkbox(f"{student['name']} ({student['id']})")

                    if st.form_submit_button("💾 Save", use_container_width=True):
                        changed = 0
                        for student in record['students']:
                            if student['id'] in overrides and overrides[student['id']]:
                                student['status'] = 'present'
                                student['method'] = 'manual-override'
                                student['confidence'] = 100
                                changed += 1

                        st.success(f"✅ Updated {changed} student(s)!")
                        st.rerun()

elif page == "📈 Reports":
    st.header("Attendance Reports")

    if len(st.session_state.attendance_records) == 0:
        st.info("ℹ️ No attendance records yet")
    else:
        tab1, tab2 = st.tabs(["📊 Summary", "👥 Student-wise"])

        with tab1:
            sessions_data = []
            for record in reversed(st.session_state.attendance_records):
                present = len([s for s in record['students'] if s['status'] == 'present'])
                total = len(record['students'])
                percentage = (present / total * 100) if total > 0 else 0

                sessions_data.append({
                    'Date': record['date'],
                    'Time': record['time'],
                    'Class': record['class_name'],
                    'Present': present,
                    'Absent': total - present,
                    'Attendance %': f"{percentage:.1f}%"
                })

            st.dataframe(pd.DataFrame(sessions_data), use_container_width=True)

            csv = pd.DataFrame(sessions_data).to_csv(index=False)
            st.download_button("📥 Download CSV", csv, f"attendance_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

        with tab2:
            student_stats = []
            for student in st.session_state.students_db:
                present_count = 0
                total_classes = 0

                for record in st.session_state.attendance_records:
                    student_record = next((s for s in record['students'] if s['id'] == student['id']), None)
                    if student_record:
                        total_classes += 1
                        if student_record['status'] == 'present':
                            present_count += 1

                percentage = (present_count / total_classes * 100) if total_classes > 0 else 0

                student_stats.append({
                    'ID': student['id'],
                    'Name': student['name'],
                    'Class': student.get('class', 'N/A'),
                    'Present': present_count,
                    'Absent': total_classes - present_count,
                    'Attendance %': f"{percentage:.1f}%"
                })

            df = pd.DataFrame(student_stats)
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False)
            st.download_button("📥 Download Report", csv, f"student_report_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

st.divider()
st.caption("Face Recognition Attendance System | Powered by DeepFace & Streamlit")
