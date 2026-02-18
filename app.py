from flask import Flask, request, jsonify
from flask_cors import CORS
import face_recognition
import numpy as np
import cv2
import os
import base64
from pymongo import MongoClient
from bson.binary import Binary
import pickle

app = Flask(__name__)
CORS(app)

# MongoDB Setup
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://abhaycdry10:Abhay123andres@cluster0.lresqtr.mongodb.net/')
client = MongoClient(MONGO_URI)
db = client['CampusEase']
collection = db['face_encodings']

def load_encodings():
    """
    Load all saved face encodings from MongoDB.
    Returns:
        encodings: List of numpy arrays representing face encodings.
        rollnos: Corresponding list of roll numbers (ints).
    """
    encodings, rollnos = [], []
    try:
        cursor = collection.find({})
        for doc in cursor:
            rollno = doc['rollno']
            # Encodings are stored as lists in MongoDB
            enc = np.array(doc['encoding'])
            encodings.append(enc)
            rollnos.append(rollno)
        print(f"[INFO] Loaded {len(encodings)} known face encodings from DB")
    except Exception as e:
        print(f"[ERROR] Failed to load encodings from DB: {e}")
    
    return encodings, rollnos

@app.route('/verify-face', methods=['POST'])
def verify():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({ "success": False, "message": "No image provided" }), 400

    try:
        # Decode base64 image string
        image_data = base64.b64decode(data['image'].split(',')[1])
        np_data = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({ "success": False, "message": "Invalid image data", "error": str(e) }), 400

    known_encodings, rollnos = load_encodings()
    
    if not known_encodings:
        return jsonify({ "success": False, "message": "No registered faces in database" })

    # Get face encodings from the input image
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

    rollno = int(data['rollno'])

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
        # Convert numpy array to list for MongoDB storage
        encoding_list = faces[0].tolist()
        
        # Upsert: update if rollno exists, otherwise insert
        collection.update_one(
            {'rollno': rollno},
            {'$set': {'encoding': encoding_list}},
            upsert=True
        )
        print(f"[INFO] Registered face for rollno={rollno} in MongoDB")
    except Exception as e:
        print(f"[ERROR] Failed to save encoding to DB: {e}")
        return jsonify({ "success": False, "message": "Failed to save encoding to DB", "error": str(e) }), 500

    return jsonify({ "success": True, "faceId": str(rollno) })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[INFO] Starting Flask face recognition server on port {port}...")
    app.run(host='0.0.0.0', port=port)