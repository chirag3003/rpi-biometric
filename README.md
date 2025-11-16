# 🔐 Raspberry Pi Biometric Authentication System

A comprehensive facial recognition-based authentication and attendance system built for Raspberry Pi with hardware integration including LEDs, buttons, and text-to-speech capabilities.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technologies Used](#technologies-used)
- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation & Setup](#installation--setup)
- [How It Works](#how-it-works)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Hardware Configuration](#hardware-configuration)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## 🎯 Overview

This project implements a sophisticated biometric authentication system using facial recognition technology on a Raspberry Pi. The system provides real-time face enrollment, authentication, and attendance tracking through an intuitive web interface, complemented by hardware indicators (LEDs) and voice feedback (text-to-speech).

## ✨ Features

### Core Functionality
- **Face Enrollment**: Register new users with their facial biometric data
- **Face Recognition Authentication**: Secure login using facial recognition with configurable tolerance
- **Attendance Tracking**: Automatic check-in system with timestamp recording
- **Live Video Streaming**: Real-time MJPEG camera feed from Raspberry Pi Camera Module
- **Session Management**: Secure user sessions with Flask session handling

### Hardware Integration
- **LED Indicators**: 
  - Green LED for successful operations
  - Red LED for errors or failed attempts
- **Physical Button**: Press to announce IP address via text-to-speech
- **Text-to-Speech**: Voice feedback for IP address announcement

### Web Interface
- **Modern UI**: Gradient-based responsive design with animations
- **Real-time Dashboard**: View attendance records and statistics
- **Auto-refresh**: Attendance data updates every 30 seconds
- **Mobile Responsive**: Works seamlessly on mobile devices

## 🛠️ Technologies Used

### Backend
- **Python 3.x**: Core programming language
- **Flask**: Web framework for handling HTTP requests and serving templates
- **OpenCV (opencv-python-headless)**: Image processing and video handling
- **face_recognition**: Facial recognition library built on dlib
- **NumPy**: Numerical computing for array operations
- **Picamera2**: Raspberry Pi Camera Module interface

### Hardware Control
- **lgpio**: Modern GPIO control library for Raspberry Pi
- **pyttsx3**: Text-to-speech synthesis engine

### Frontend
- **HTML5**: Structure and markup
- **CSS3**: Styling with modern features (gradients, animations, flexbox)
- **Vanilla JavaScript**: Client-side interactivity and AJAX calls

### Networking
- **Socket Programming**: IP address detection
- **HTTP Streaming**: MJPEG video stream server
- **RESTful APIs**: JSON-based communication

## 🔌 Hardware Requirements

- **Raspberry Pi** (3B+, 4, or 5 recommended)
- **Raspberry Pi Camera Module** (v1, v2, or HQ Camera)
- **LEDs**: 
  - 1x Green LED
  - 1x Red LED
- **Resistors**: 2x 220Ω-330Ω resistors for LEDs
- **Push Button**: 1x momentary push button
- **Breadboard and Jumper Wires**
- **Power Supply**: 5V 3A power adapter

## 💻 Software Requirements

- **Raspberry Pi OS** (Bullseye or later recommended)
- **Python 3.7+**
- **pip** (Python package manager)
- **Camera enabled** in Raspberry Pi configuration

## 📦 Installation & Setup

### 1. System Preparation

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Enable camera interface
sudo raspi-config
# Navigate to Interface Options → Camera → Enable

# Reboot to apply changes
sudo reboot
```

### 2. Install System Dependencies

```bash
# Install required system libraries
sudo apt-get install -y python3-pip python3-dev
sudo apt-get install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev
sudo apt-get install -y libjasper-dev libqtgui4 libqt4-test
sudo apt-get install -y cmake libboost-all-dev

# For face_recognition library
sudo apt-get install -y build-essential cmake
sudo apt-get install -y libopenblas-dev liblapack-dev
sudo apt-get install -y libx11-dev libgtk-3-dev

# For text-to-speech
sudo apt-get install -y espeak espeak-data libespeak1
```

### 3. Clone or Download the Project

```bash
cd /home/pi
git clone <repository-url> rpi-biometric
cd rpi-biometric
```

### 4. Install Python Dependencies

```bash
# Install required Python packages
pip3 install -r requirements.txt

# Additional dependencies for Raspberry Pi
pip3 install picamera2
pip3 install lgpio
pip3 install pyttsx3
```

### 5. Hardware Setup

Connect the hardware components as follows:

#### GPIO Pin Connections (BCM Numbering):
- **Button**: GPIO 17 (Pin 11)
- **Green LED**: GPIO 22 (Pin 15) → Connect through 220Ω resistor → Ground
- **Red LED**: GPIO 27 (Pin 13) → Connect through 220Ω resistor → Ground

### 6. Configure Application

Edit `main.py` if needed to change:
- GPIO pin assignments
- Camera resolution (default: 640x480)
- Face recognition tolerance (default: 0.4)
- Port numbers (Flask: 5000, Video Stream: 8000)

Update the video feed URL in `templates/index.html`:
```html
<!-- Replace with your Raspberry Pi's IP address -->
<img src="http://YOUR_PI_IP_ADDRESS:8000/stream.mjpg" alt="Camera Feed">
```

## 🚀 How It Works

### Architecture Overview

The system consists of three main components:

#### 1. Video Streaming Server (Port 8000)
- Runs in a separate thread
- Captures video from Raspberry Pi Camera Module
- Encodes frames as JPEG
- Streams via HTTP as MJPEG (Motion JPEG)
- Provides real-time camera feed to web interface

#### 2. Flask Web Application (Port 5000)
- Serves HTML templates
- Handles face enrollment and recognition
- Manages user sessions
- Provides RESTful API endpoints
- Tracks attendance records

#### 3. Hardware Control Layer
- Manages GPIO pins via lgpio
- Controls LED indicators
- Monitors button presses
- Provides text-to-speech feedback

### Face Recognition Process

#### Enrollment Flow:
1. User enters their name and clicks "Enroll Face"
2. System captures current video frame
3. Detects face locations using HOG (Histogram of Oriented Gradients)
4. Extracts 128-dimensional face encoding (facial features)
5. Validates single face detection
6. Stores encoding with username in in-memory database
7. Provides visual feedback via LEDs

#### Authentication Flow:
1. User clicks "Login with Face Recognition"
2. System captures current video frame
3. Detects all faces in the frame
4. Computes face encodings for detected faces
5. Compares encodings against stored database
6. Uses face distance metric (Euclidean distance)
7. Matches with tolerance threshold (0.4 = strict matching)
8. Creates session for authenticated user
9. Records attendance timestamp
10. Redirects to dashboard

### Technical Details

#### Face Encoding:
- Uses dlib's ResNet-based model
- Generates 128-dimensional vector representation
- Invariant to lighting, angle, and expression variations
- Comparison via Euclidean distance

#### Tolerance Levels:
- `0.4`: Strict matching (current setting)
- `0.5`: Balanced matching
- `0.6`: Default matching (more lenient)

#### In-Memory Storage:
```python
known_faces_db = {
    "encodings": [encoding1, encoding2, ...],  # 128-d numpy arrays
    "names": ["Alice", "Bob", ...]              # Corresponding usernames
}

attendance_records = {
    "Alice": "2025-11-17 10:30:45",
    "Bob": "2025-11-17 09:15:22"
}
```

## 📱 Usage

### Starting the Application

```bash
# Navigate to project directory
cd /home/pi/rpi-biometric

# Run with sudo (required for GPIO access)
sudo python3 main.py
```

The application will start:
- Flask web server on `http://0.0.0.0:5000`
- Video stream on `http://0.0.0.0:8000/stream.mjpg`

### Accessing the Web Interface

From any device on the same network:
```
http://RASPBERRY_PI_IP:5000
```

To find your Raspberry Pi's IP address:
```bash
hostname -I
```
Or press the physical button to hear it announced via text-to-speech.

### Enrolling a New User

1. Open the web interface
2. Position your face in the camera view
3. Enter your name in the text field
4. Click "Enroll Face"
5. Wait for confirmation message
6. Green LED blinks on success, red LED on error

### Logging In

1. Position your face in the camera view
2. Click "Login with Face Recognition"
3. System authenticates and redirects to dashboard
4. Attendance is automatically recorded

### Dashboard Features

- **Check In Button**: Manual attendance check-in
- **Statistics Cards**:
  - Total enrolled users
  - Users checked in today
  - Users not checked in
  - Attendance rate percentage
- **Attendance Table**: Real-time attendance records
- **Auto-refresh**: Updates every 30 seconds

## 🔗 API Endpoints

### Web Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main authentication page |
| GET | `/dashboard` | Attendance dashboard (requires auth) |
| GET | `/logout` | Logout and clear session |
| GET | `/video_feed` | Video stream information |

### API Routes

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/enroll` | Enroll new user face | No |
| GET | `/login` | Authenticate via face | No |
| GET | `/api/attendance` | Get attendance records | Yes |
| POST | `/api/checkin` | Manual check-in | Yes |

### Request/Response Examples

#### Enroll User
```javascript
// Request
POST /enroll
Content-Type: application/json
{
  "username": "John Doe"
}

// Success Response
{
  "status": "success",
  "message": "User John Doe enrolled successfully!"
}

// Error Response
{
  "status": "error",
  "message": "No face found. Please look at the camera."
}
```

#### Login
```javascript
// Request
GET /login

// Success Response
{
  "status": "success",
  "message": "Welcome, John Doe! (Match: 87.3%)",
  "username": "John Doe"
}

// Error Response
{
  "status": "error",
  "message": "Login failed: User not recognized."
}
```

#### Get Attendance
```javascript
// Request
GET /api/attendance

// Response
{
  "status": "success",
  "attendance": [
    {
      "name": "John Doe",
      "last_checkin": "2025-11-17 10:30:45",
      "status": "checked_in"
    },
    {
      "name": "Jane Smith",
      "last_checkin": "Never",
      "status": "not_checked_in"
    }
  ],
  "total_users": 2,
  "checked_in_today": 1
}
```

## 📂 Project Structure

```
rpi-biometric/
├── main.py                 # Main application file
├── requirements.txt        # Python dependencies
├── templates/             # HTML templates
│   ├── index.html         # Login/enrollment page
│   └── dashboard.html     # Attendance dashboard
└── README.md              # This file
```

### File Descriptions

- **main.py**: Core application containing:
  - Video streaming server setup
  - Flask application routes
  - Face recognition logic
  - GPIO hardware control
  - Attendance management

- **requirements.txt**: Python package dependencies
  - flask: Web framework
  - opencv-python-headless: Computer vision (headless for Raspberry Pi)
  - face_recognition: Facial recognition library
  - numpy: Numerical computing

- **templates/index.html**: Authentication interface
  - Live camera feed display
  - Enrollment form
  - Login button
  - Real-time feedback messages

- **templates/dashboard.html**: Dashboard interface
  - Attendance statistics
  - User list with status
  - Check-in functionality
  - Auto-refresh capability

## ⚙️ Hardware Configuration

### GPIO Pin Mapping (BCM Mode)

```
┌─────────────────────────────────┐
│  Component    GPIO    Physical  │
├─────────────────────────────────┤
│  Button       GPIO17    Pin 11  │
│  Green LED    GPIO22    Pin 15  │
│  Red LED      GPIO27    Pin 13  │
│  Ground       GND       Pin 6   │
└─────────────────────────────────┘
```

### LED Circuit Diagram

```
Raspberry Pi          LED           Resistor
GPIO Pin ─────────── Anode ───────── 220Ω ───────── Ground
(GPIO22/27)          (Long leg)
```

### Button Circuit Diagram

```
                   ┌─── 3.3V (Pull-up via software)
                   │
GPIO17 ───────────┤
                   │
                   └─── Button ─── Ground
```

## 🔧 Troubleshooting

### Common Issues

#### Camera Not Working
```bash
# Check if camera is enabled
vcgencmd get_camera

# Should output: supported=1 detected=1

# Test camera
libcamera-hello

# If issues persist, try:
sudo raspi-config
# Interface Options → Legacy Camera → Enable
```

#### GPIO Permission Denied
```bash
# Run application with sudo
sudo python3 main.py

# Or add user to gpio group (requires logout/login)
sudo usermod -a -G gpio $USER
```

#### Face Recognition Not Working
- Ensure good lighting conditions
- Face should be clearly visible and frontal
- Only one face should be in frame during enrollment
- Camera resolution should be at least 640x480

#### Import Errors
```bash
# Reinstall dependencies
pip3 install --upgrade -r requirements.txt

# For face_recognition issues on Raspberry Pi:
sudo apt-get install -y cmake libboost-all-dev
pip3 install dlib
pip3 install face_recognition
```

#### Text-to-Speech Not Working
```bash
# Install espeak
sudo apt-get install -y espeak

# Test espeak
espeak "Hello World"
```

#### Video Stream Shows Black Screen
```bash
# Check camera connection
raspistill -o test.jpg

# Restart Picamera2
sudo systemctl restart camera
```

### Performance Optimization

#### For Faster Face Recognition:
- Reduce camera resolution in `main.py`:
  ```python
  picam2.configure(picam2.create_video_configuration(main={"size": (320, 240)}))
  ```

#### For Better Accuracy:
- Increase tolerance value (less strict):
  ```python
  matches = face_recognition.compare_faces(known_faces_db["encodings"], face_encoding, tolerance=0.5)
  ```

## 🔒 Security Considerations

### Current Implementation
- ⚠️ **In-memory storage**: All face encodings are lost on restart
- ⚠️ **No encryption**: Data transmitted over HTTP
- ⚠️ **Simple session management**: Basic Flask sessions

### Recommended Improvements

1. **Persistent Storage**:
   ```python
   # Use SQLite or JSON file to store encodings
   import json
   import pickle
   
   # Save encodings
   with open('faces_db.pkl', 'wb') as f:
       pickle.dump(known_faces_db, f)
   ```

2. **HTTPS Implementation**:
   ```bash
   # Generate self-signed certificate
   openssl req -x509 -newkey rsa:4096 -nodes \
     -out cert.pem -keyout key.pem -days 365
   
   # Update Flask app
   app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
   ```

3. **Password Protection**:
   - Add password field during enrollment
   - Implement two-factor authentication (face + password)

4. **Anti-Spoofing**:
   - Implement liveness detection
   - Use depth cameras or challenge-response

5. **Rate Limiting**:
   ```python
   from flask_limiter import Limiter
   
   limiter = Limiter(app, default_limits=["100 per hour"])
   ```

## 📝 Future Enhancements

- [ ] Persistent database (SQLite/PostgreSQL)
- [ ] User management (add/delete users)
- [ ] Attendance report generation (CSV/PDF)
- [ ] Email notifications
- [ ] Multiple camera support
- [ ] Face mask detection
- [ ] Temperature integration (for health screening)
- [ ] Integration with access control systems
- [ ] Mobile app development
- [ ] Cloud synchronization

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is open-source and available for educational and personal use.

## 👨‍💻 Author

**Chirag**

## 🙏 Acknowledgments

- **face_recognition library** by Adam Geitgey
- **dlib** by Davis King
- **OpenCV** community
- **Raspberry Pi Foundation**

## 📞 Support

For issues, questions, or contributions, please open an issue on the project repository.

---

**⚡ Built with ❤️ for Raspberry Pi**
