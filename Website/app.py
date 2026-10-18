import os
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# SQLite Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# DATABASE MODELS
# ==========================================

class Medicine(db.Model):
    __tablename__ = 'medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)
    time_category = db.Column(db.String(20), nullable=False) # 'morning', 'afternoon', 'evening', 'bedtime'
    time_str = db.Column(db.String(20), nullable=False)      # e.g., "8:00 AM"
    icon = db.Column(db.String(20), default="💊")
    note = db.Column(db.String(200), nullable=True)
    logs = db.relationship('MedLog', backref='medicine', lazy=True, cascade="all, delete-orphan")

class MedLog(db.Model):
    __tablename__ = 'med_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    taken_date = db.Column(db.String(10), nullable=False) # Formatted YYYY-MM-DD
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(50), default="Sweetheart")
    love_note = db.Column(db.Text, default="Remember that taking care of yourself is a form of self-love. I love you so much! 💕")
    passcode = db.Column(db.String(20), default="1234") # Default passcode

# ==========================================
# INITIALIZE DATABASE & DEFAULT SEED DATA
# ==========================================

def init_db():
    with app.app_context():
        db.create_all()
        
        if not UserSettings.query.first():
            settings = UserSettings(
                nickname="Sweetheart",
                love_note="Remember that taking care of yourself is a form of self-love. I love you so much! 💕",
                passcode="1234"
            )
            db.session.add(settings)
            
        if Medicine.query.count() == 0:
            default_meds = [
                Medicine(name="Daily Multivitamin", dosage="1 tablet", time_category="morning", time_str="8:00 AM", icon="🌸", note="Take with morning meal"),
                Medicine(name="Hydration Booster", dosage="1 glass of water", time_category="afternoon", time_str="1:00 PM", icon="💧", note="Stay hydrated!"),
                Medicine(name="Evening Magnesium", dosage="200mg", time_category="evening", time_str="8:00 PM", icon="🌙", note="Helps with cozy sleep"),
            ]
            db.session.add_all(default_meds)
            
        db.session.commit()

# ==========================================
# API ROUTES
# ==========================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/settings/verify-passcode', methods=['POST'])
def verify_passcode():
    data = request.json or {}
    entered_passcode = data.get('passcode')
    settings = UserSettings.query.first()
    
    if settings and settings.passcode == entered_passcode:
        return jsonify({'success': True})
    return jsonify({'success': False}), 401

@app.route('/api/medicines', methods=['GET'])
def get_medicines():
    today_str = date.today().isoformat()
    meds = Medicine.query.all()
    today_logs = MedLog.query.filter_by(taken_date=today_str).all()
    taken_med_ids = {log.medicine_id for log in today_logs}
    
    results = []
    for m in meds:
        results.append({
            'id': m.id,
            'name': m.name,
            'dosage': m.dosage,
            'time_category': m.time_category,
            'time_str': m.time_str,
            'icon': m.icon,
            'note': m.note,
            'taken_today': m.id in taken_med_ids
        })
    return jsonify(results)

@app.route('/api/medicines', methods=['POST'])
def add_medicine():
    data = request.json
    new_med = Medicine(
        name=data.get('name'),
        dosage=data.get('dosage'),
        time_category=data.get('time_category', 'morning'),
        time_str=data.get('time_str', '9:00 AM'),
        icon=data.get('icon', '💊'),
        note=data.get('note', '')
    )
    db.session.add(new_med)
    db.session.commit()
    return jsonify({'status': 'success', 'id': new_med.id}), 201

@app.route('/api/medicines/<int:med_id>/toggle', methods=['POST'])
def toggle_medicine(med_id):
    today_str = date.today().isoformat()
    existing_log = MedLog.query.filter_by(medicine_id=med_id, taken_date=today_str).first()
    
    if existing_log:
        db.session.delete(existing_log)
        taken = False
    else:
        new_log = MedLog(medicine_id=med_id, taken_date=today_str)
        db.session.add(new_log)
        taken = True
        
    db.session.commit()
    return jsonify({'status': 'success', 'taken_today': taken})

@app.route('/api/medicines/<int:med_id>', methods=['DELETE'])
def delete_medicine(med_id):
    med = Medicine.query.get_or_404(med_id)
    db.session.delete(med)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/settings', methods=['GET', 'PUT'])
def handle_settings():
    settings = UserSettings.query.first()
    if request.method == 'GET':
        return jsonify({
            'nickname': settings.nickname,
            'love_note': settings.love_note,
            'passcode': settings.passcode
        })
    
    data = request.json
    if 'nickname' in data:
        settings.nickname = data['nickname']
    if 'love_note' in data:
        settings.love_note = data['love_note']
    if 'passcode' in data and data['passcode']:
        settings.passcode = data['passcode']
        
    db.session.commit()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)