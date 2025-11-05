import io
import logging
import socketserver
import numpy as np
import cv2
import face_recognition
from flask import Flask, render_template, Response, request, jsonify
from http import server
from threading import Condition, Thread
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

# --- Part 1: Video Streaming ---
# This section sets up the live MJPEG video stream

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

# Global picamera2 object
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

# --- Part 2: Flask Web Application ---
# This section handles the web page and the login/enroll API

app = Flask(__name__)

# A simple in-memory "database" to store user face encodings
# In a real app, you'd save this to a file or database.
known_faces_db = {
    "encodings": [],
    "names": []
}

def get_video_frame():
    """Grabs the current video frame from the streaming output."""
    with output.condition:
        output.condition.wait()
        frame = output.frame
    # Decode the JPEG frame into a NumPy array (OpenCV format)
    return cv2.imdecode(np.frombuffer(frame, dtype=np.uint8), cv2.IMREAD_COLOR)

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Serves the MJPEG stream from the separate streaming server."""
    # This URL is what the <img> tag in index.html will point to.
    # We are running the streaming server on port 8000.
    # This is a bit of a trick: we're proxying the request to the other server
    # In a real app, you might integrate this more cleanly.
    # For this example, we just tell the user the URL.
    # A better way is shown in the HTML: just point img src to "http://<pi_ip>:8000/stream.mjpg"
    return "Video stream is at /stream.mjpg (on port 8000)"


@app.route('/enroll', methods=['POST'])
def enroll_face():
    """Enrolls a new user's face."""
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({"status": "error", "message": "Username is required"}), 400

    frame = get_video_frame()
    
    # Convert from BGR (OpenCV default) to RGB (face_recognition default)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Find face locations
    face_locations = face_recognition.face_locations(rgb_frame)
    
    if len(face_locations) == 0:
        return jsonify({"status": "error", "message": "No face found. Please look at the camera."})
    if len(face_locations) > 1:
        return jsonify({"status": "error", "message": "Multiple faces found. Only one person at a time."})

    # Get the face encoding (the 128-d biometric signature)
    face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
    
    # Save to our "database"
    known_faces_db["encodings"].append(face_encoding)
    known_faces_db["names"].append(username)
    
    print(f"Enrolled {username} successfully.")
    return jsonify({"status": "success", "message": f"User {username} enrolled successfully!"})


@app.route('/login', methods=['GET'])
def login_face():
    """Attempts to log in a user by checking their face."""
    frame = get_video_frame()
    
    if len(known_faces_db["encodings"]) == 0:
         return jsonify({"status": "error", "message": "No users enrolled. Please enroll a user first."})

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    
    if len(face_locations) == 0:
        return jsonify({"status": "error", "message": "No face found"})

    # Get embeddings for all faces in the frame
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for face_encoding in face_encodings:
        # See if the face matches any known faces
        matches = face_recognition.compare_faces(known_faces_db["encodings"], face_encoding, tolerance=0.6)
        name = "Unknown"

        # Use the first match
        if True in matches:
            first_match_index = matches.index(True)
            name = known_faces_db["names"][first_match_index]
            
            print(f"Login successful for {name}")
            return jsonify({"status": "success", "message": f"Welcome, {name}!"})

    print("Login failed: Unknown user")
    return jsonify({"status": "error", "message": "Login failed: User not recognized."})


# --- Part 3: Main execution ---
if __name__ == '__main__':
    try:
        # Start the streaming server in a separate thread
        address = ('', 8000)
        stream_server = StreamingServer(address, StreamingHandler)
        stream_thread = Thread(target=stream_server.serve_forever)
        stream_thread.daemon = True
        stream_thread.start()
        
        # Start the Flask app (on port 5000)
        print("Flask server starting on http://0.0.0.0:5000")
        print("Video stream starting on http://0.0.0.0:8000/stream.mjpg")
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    finally:
        picam2.stop_recording()