from flask import Flask, request, jsonify
from flask_cors import CORS
import face_recognition
import numpy as np
import cv2
import os
import base64

app = Flask(__name__)
CORS(app)

DATA_DIR = 'face_data'

def load_encodings():
    """
    Load all saved face encodings (.npy files) from DATA_DIR.
    Returns:
        encodings: List of numpy arrays representing face encodings.
        rollnos: Corresponding list of roll numbers (ints).
    """
    encodings, rollnos = [], []
    if not os.path.exists(DATA_DIR):
        print(f"[WARN] Data directory '{DATA_DIR}' does not exist. Creating...")
        os.makedirs(DATA_DIR)
    for file in os.listdir(DATA_DIR):
        if file.endswith('.npy'):
            try:
                rollno = int(file.replace('.npy', ''))
                enc = np.load(os.path.join(DATA_DIR, file))
                encodings.append(enc)
                rollnos.append(rollno)
            except Exception as e:
                print(f"[ERROR] Failed to load encoding from {file}: {e}")
    print(f"[INFO] Loaded {len(encodings)} known face encodings")
    return encodings, rollnos

@app.route('/verify-face', methods=['POST'])
def verify():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({ "success": False, "message": "No image provided" }), 400

    try:
        # Decode base64 image string (data URL format: data:image/png;base64,...)
        image_data = base64.b64decode(data['image'].split(',')[1])
        np_data = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({ "success": False, "message": "Invalid image data", "error": str(e) }), 400

    known_encodings, rollnos = load_encodings()

    # Get face encodings from the input image (can be multiple faces)
    faces = face_recognition.face_encodings(frame)

    print(f"[INFO] Detected {len(faces)} face(s) in the input image")

    for face in faces:
        matches = face_recognition.compare_faces(known_encodings, face)
        if True in matches:
            idx = matches.index(True)
            rollno = rollnos[idx]
            print(f"[INFO] Face recognized: rollno={rollno}")
            return jsonify({ "success": True, "rollno": rollno })

    return jsonify({ "success": False, "message": "Face not recognized" })

@app.route('/register-face', methods=['POST'])
def register():
    data = request.json
    if not data or 'image' not in data or 'rollno' not in data:
        return jsonify({ "success": False, "message": "Missing rollno or image" }), 400

    rollno = data['rollno']

    try:
        image_data = base64.b64decode(data['image'].split(',')[1])
        np_data = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({ "success": False, "message": "Invalid image data", "error": str(e) }), 400

    faces = face_recognition.face_encodings(frame)

    if not faces:
        return jsonify({ "success": False, "message": "No face found in the image" }), 400

    try:
        np.save(os.path.join(DATA_DIR, f"{rollno}.npy"), faces[0])
        print(f"[INFO] Registered face for rollno={rollno}")
    except Exception as e:
        return jsonify({ "success": False, "message": "Failed to save encoding", "error": str(e) }), 500

    # Return the faceId (same as rollno as string)
    return jsonify({ "success": True, "faceId": str(rollno) })

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    print(f"[INFO] Starting Flask face recognition server on port {port}...")
    app.run(host='0.0.0.0', port=port)