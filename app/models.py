from app import db, bcrypt
from datetime import datetime
import string
import random
from flask_login import UserMixin

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(length))
        if not QRCode.query.filter_by(short_code=code).first():
            return code

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    qr_codes = db.relationship('QRCode', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return str(self.id)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target_url = db.Column(db.String(500), nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    scan_records = db.relationship('ScanRecord', backref='qr_code', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.short_code:
            self.short_code = generate_short_code()
    
    @property
    def scan_count(self):
        return len(self.scan_records)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'target_url': self.target_url,
            'short_code': self.short_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'scan_count': self.scan_count,
            'user_id': self.user_id
        }

class ScanRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    country = db.Column(db.String(100))
    region = db.Column(db.String(100))
    city = db.Column(db.String(100))
    device_type = db.Column(db.String(50))
    browser = db.Column(db.String(100))
    os = db.Column(db.String(100))
    user_agent = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'id': self.id,
            'qr_code_id': self.qr_code_id,
            'scanned_at': self.scanned_at.isoformat() if self.scanned_at else None,
            'ip_address': self.ip_address,
            'country': self.country,
            'region': self.region,
            'city': self.city,
            'device_type': self.device_type,
            'browser': self.browser,
            'os': self.os
        }
