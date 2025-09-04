from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
import google.generativeai as genai
import os # 用于获取环境变量


# 初始化 Flask 应用
app = Flask(__name__)

CORS(app)

# 配置数据库，我们使用 SQLite，它是一个轻量级的文件数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # CSRF需要SECRET_KEY

# 初始化数据库
db = SQLAlchemy(app)

# 为了开发测试方便，暂时禁用CSRF保护
# 如果需要启用CSRF，请取消下面的注释
# csrf = CSRFProtect(app)

# 从文件中加载前端HTML代码
try:
    with open('index.html', 'r', encoding='utf-8') as f:
        FRONTEND_HTML = f.read()
except FileNotFoundError:
    FRONTEND_HTML = "<h1>Error: index.html not found.</h1>"



# 定义数据库中的用户表
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        # 使用哈希函数加密密码，使用pbkdf2算法（最兼容）
        self.password_hash = generate_password_hash(password, method='pbkdf2')
    
    def check_password(self, password):
        # 验证用户输入的密码是否正确
        return check_password_hash(self.password_hash, password)

# 在应用第一次运行时，创建数据库表
with app.app_context():
    db.create_all()


# 添加一个根路由，用于返回前端页面
@app.route('/', methods=['GET'])
def index():
    return render_template_string(FRONTEND_HTML)

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # 检查是否接收到JSON数据
        if not data:
            return jsonify({'message': 'No JSON data provided!'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'message': 'Username and password are required!'}), 400
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'message': 'Username already exists!'}), 409
        
        # 创建新用户，并加密密码
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'message': 'User registered successfully!'}), 201
        
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # 检查是否接收到JSON数据
        if not data:
            return jsonify({'message': 'No JSON data provided!'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'message': 'Username and password are required!'}), 400
        
        # 在数据库中查找用户
        user = User.query.filter_by(username=username).first()
        
        # 验证用户是否存在且密码正确
        if user and user.check_password(password):
            # 登录成功，这里可以返回一个 token，但为了简化，我们先返回成功信息
            return jsonify({'message': 'Login successful!', 'user_id': user.id}), 200
        else:
            return jsonify({'message': 'Invalid username or password!'}), 401
            
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500

# 添加一个测试路由来验证服务器是否正常运行
@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Server is running!'}), 200



# 这是一个新的路由，用于调用AI生成文书
@app.route('/generate_essay', methods=['POST'])
def generate_essay():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No JSON data provided!'}), 400

        # 从前端获取文书生成所需的信息
        prompt = data.get('prompt')
        # prompt 可以包含学生的背景、申请专业、文书类型等信息
        if not prompt:
            return jsonify({'message': 'Prompt is required for essay generation!'}), 400

        # 调用 Gemini 模型
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)

        # 检查是否成功生成内容
        if response and response.text:
            return jsonify({'essay': response.text})
        else:
            return jsonify({'message': 'Failed to generate content.'}), 500

    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)