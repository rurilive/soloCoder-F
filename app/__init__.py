from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app():
    import os
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    app = Flask(__name__, template_folder=template_dir)
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///qr_tracker.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'warning'
    
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from app.routes import main
    app.register_blueprint(main)
    
    with app.app_context():
        db.create_all()
    
    return app
