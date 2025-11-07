import io
import logging
import socketserver
import numpy as np
import cv2
import face_recognition
from flask import Flask, render_template, Response, request, jsonify, session, redirect, url_for
from http import server
from threading import Condition, Thread
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from datetime import datetime
import secrets

### NEW ###
import RPi.GPIO as GPIO
import pyttsx3
import socket
import time

### NEW ###
import lgpio  # Use lgpio instead of RPi.GPIO
import pyttsx3
import socket
import time

# --- NEW: Hardware & TTS Setup ---
# GPIO Pin Definitions (BCM numbering)
BUTTON_PIN = 17
GREEN_LED_PIN = 22
RED_LED_PIN = 27

### UPDATED: Setup GPIO with lgpio ###
try:
    h = lgpio.gpiochip_open(0)  # Open the default GPIO chip (chip 0)
    
    # Setup LEDs as output, default LOW
    lgpio.gpio_claim_output(h, GREEN_LED_PIN, lgpio.LOW)
    lgpio.gpio_claim_output(h, RED_LED_PIN, lgpio.LOW)
    
    # Setup button as input with pull-up resistor
    lgpio.gpio_claim_input(h, BUTTON_PIN, flags=lgpio.SET_PULL_UP)
    # lgpio.gpio_claim_input(h, BUTTON_PIN, lgpio.PUD_UP)
    
    print("GPIO chip opened successfully.")
except Exception as e:
    print(f"FATAL ERROR: Could not open GPIO chip. {e}")
    print("This may be a permissions issue. Try running with 'sudo'.")
    exit()


# Initialize Text-to-Speech engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

# --- NEW: Helper Functions ---
def get_ip_address():
    """Finds the Pi's current IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def speak(text):
    """Speaks the given text in a separate thread."""
    def speak_task():
        print(f"Speaking: {text}")
        tts_engine.say(text)
        tts_engine.runAndWait()
    Thread(target=speak_task, daemon=True).start()

### UPDATED: Callback for lgpio ###
def speak_ip_callback(chip, gpio, level, tick):
    """Callback function for the button press."""
    # This callback receives chip, gpio, level, and time (tick)
    print("Button pressed! Speaking IP...")
    ip = get_ip_address()
    ip_spoken = ip.replace(".", " dot ")
    speak(f"My IP address is {ip_spoken}")

### UPDATED: Blink function for lgpio ###
def blink_led(pin, times=3, duration=0.5):
    """Blinks an LED in a separate thread."""
    def blink_task():
        for _ in range(times):
            lgpio.gpio_write(h, pin, lgpio.HIGH) # Use lgpio.HIGH (or 1)
            time.sleep(duration / 2)
            lgpio.gpio_write(h, pin, lgpio.LOW)  # Use lgpio.LOW (or 0)
            time.sleep(duration / 2)
    Thread(target=blink_task, daemon=True).start()

# --- NEW: Add Button Event Detection (lgpio style) ---
# Set up a background callback. Debounce is in *microseconds*
# 2000 ms = 2,000,000 µs
try:
    button_callback = lgpio.callback(h, BUTTON_PIN, lgpio.FALLING_EDGE, speak_ip_callback, 2000000)
    print("GPIO event listener for button started.")
except Exception as e:
    print(f"Error setting up button callback: {e}")
    lgpio.gpiochip_close(h)
    exit()
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
app.secret_key = secrets.token_hex(16)  # For session management

# A simple in-memory "database" to store user face encodings
# In a real app, you'd save this to a file or database.
known_faces_db = {
    "encodings": [],
    "names": []
}

# Attendance tracking: username -> last check-in time
attendance_records = {}

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
    # If user is already logged in, redirect to dashboard
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Serves the todo list dashboard - requires authentication."""
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/logout')
def logout():
    """Logs out the user."""
    session.pop('username', None)
    return redirect(url_for('index'))

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
        ### NEW ###
        blink_led(RED_LED_PIN)
        return jsonify({"status": "error", "message": "No face found. Please look at the camera."})
    if len(face_locations) > 1:
        ### NEW ###
        blink_led(RED_LED_PIN)
        return jsonify({"status": "error", "message": "Multiple faces found. Only one person at a time."})

    # Get the face encoding (the 128-d biometric signature)
    face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
    
    # Check if user already exists
    if username in known_faces_db["names"]:
        # Update existing user's encoding
        existing_index = known_faces_db["names"].index(username)
        known_faces_db["encodings"][existing_index] = face_encoding
        print(f"Updated enrollment for {username}.")
        return jsonify({"status": "success", "message": f"User {username} updated successfully!"})
    
    # Save to our "database"
    known_faces_db["encodings"].append(face_encoding)
    known_faces_db["names"].append(username)
    
    print(f"Enrolled {username} successfully. Total users: {len(known_faces_db['names'])}")
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
        # Lower tolerance = stricter matching (0.6 is default, 0.4-0.5 is stricter)
        matches = face_recognition.compare_faces(known_faces_db["encodings"], face_encoding, tolerance=0.4)
        
        # Also get face distances for better matching
        face_distances = face_recognition.face_distance(known_faces_db["encodings"], face_encoding)
        
        # Use the best match (lowest distance)
        if True in matches:
            # Find the best match (smallest distance)
            best_match_index = face_distances.argmin()
            
            # Double-check if best match is actually a match
            if matches[best_match_index]:
                name = known_faces_db["names"][best_match_index]
                confidence = 1 - face_distances[best_match_index]
                
                # Set session
                session['username'] = name
                
                # Record attendance check-in
                attendance_records[name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"Login successful for {name} (confidence: {confidence:.2f})")
                return jsonify({
                    "status": "success", 
                    "message": f"Welcome, {name}! (Match: {confidence*100:.1f}%)",
                    "username": name
                })

    print("Login failed: Unknown user")
    return jsonify({"status": "error", "message": "Login failed: User not recognized."})


# --- Attendance API Routes ---

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    """Get all attendance records."""
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    # Build attendance list with all enrolled users
    attendance_list = []
    for name in known_faces_db["names"]:
        attendance_list.append({
            "name": name,
            "last_checkin": attendance_records.get(name, "Never"),
            "status": "checked_in" if name in attendance_records else "not_checked_in"
        })
    
    return jsonify({
        "status": "success", 
        "attendance": attendance_list,
        "total_users": len(known_faces_db["names"]),
        "checked_in_today": len(attendance_records)
    })


@app.route('/api/checkin', methods=['POST'])
def manual_checkin():
    """Manually check in (uses face recognition)."""
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    username = session['username']
    attendance_records[username] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify({
        "status": "success", 
        "message": f"Checked in at {attendance_records[username]}"
    })


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