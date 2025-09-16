from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gothic-vibe-shop-secret-key-' + str(uuid.uuid4())
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'gothic_shop.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PRODUCT_IMAGE_FOLDER'] = 'static/images/products'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# إنشاء مجلدات التحميل إذا لم تكن موجودة
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PRODUCT_IMAGE_FOLDER'], exist_ok=True)
os.makedirs('instance', exist_ok=True)

db = SQLAlchemy(app)

# نموذج المنتج
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    images = db.Column(db.Text, nullable=False)  # سيتم تخزين أسماء الصور كسلسلة مفصولة بفواصل
    category = db.Column(db.String(50), nullable=False)
    in_stock = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# نموذج المستخدم
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

# إنشاء الجداول في قاعدة البيانات
with app.app_context():
    db.create_all()
    
    # إنشاء مستخدم المسؤول إذا لم يكن موجوداً
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('Fatiha123@#')
        )
        db.session.add(admin_user)
        db.session.commit()

# منع التخزين المؤقت
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# الصفحة الرئيسية
@app.route('/')
def index():
    featured_products = Product.query.filter_by(in_stock=True).order_by(Product.created_at.desc()).limit(4).all()
    return render_template('index.html', featured_products=featured_products)

# صفحة المتجر
@app.route('/shop')
def shop():
    category = request.args.get('category')
    if category:
        products = Product.query.filter_by(category=category, in_stock=True).all()
    else:
        products = Product.query.filter_by(in_stock=True).all()
    
    # الحصول على الفئات الفريدة
    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('shop.html', products=products, categories=categories, selected_category=category)

# صفحة المنتج
@app.route('/product/<int:product_id>')
def product(product_id):
    product = Product.query.get_or_404(product_id)
    # تقسيم أسماء الصور إلى قائمة
    image_list = product.images.split(',') if product.images else []
    return render_template('product.html', product=product, images=image_list)

# إعادة توجيه طلب الشراء إلى واتساب
@app.route('/order/<int:product_id>')
def order(product_id):
    product = Product.query.get_or_404(product_id)
    message = f"مرحباً، أريد شراء المنتج: {product.name} بسعر {product.price} درهم"
    whatsapp_url = f"https://wa.me/212632256568?text={message}"
    return redirect(whatsapp_url)

# صفحة سلة التسوق
@app.route('/cart')
def cart():
    return render_template('cart.html')

# منطقة الإدارة
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['admin_logged_in'] = True
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة!', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('تم تسجيل الخروج بنجاح!', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    products = Product.query.all()
    return render_template('admin/dashboard.html', products=products)

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        # التحقق من وجود ملفات
        if 'images' not in request.files:
            flash('لم يتم اختيار أي صور', 'danger')
            return redirect(request.url)
        
        # إضافة منتج جديد
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        
        # معالجة الصور المرفوعة
        image_files = request.files.getlist('images')
        image_names = []
        
        for image in image_files:
            if image and image.filename:
                # إنشاء اسم فريد للصورة
                filename = secure_filename(image.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                image_path = os.path.join(app.config['PRODUCT_IMAGE_FOLDER'], unique_filename)
                image.save(image_path)
                image_names.append(unique_filename)
        
        if not image_names:
            flash('يجب اختيار صورة واحدة على الأقل', 'danger')
            return redirect(request.url)
        
        new_product = Product(
            name=name,
            description=description,
            price=price,
            images=",".join(image_names),
            category=category,
            in_stock=True
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        flash('تم إضافة المنتج بنجاح!', 'success')
        return redirect(url_for('admin_products'))
    
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/delete_product/<int:product_id>')
def delete_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    product = Product.query.get_or_404(product_id)
    
    # حذف الصور المرتبطة بالمنتج
    if product.images:
        for image_name in product.images.split(','):
            image_path = os.path.join(app.config['PRODUCT_IMAGE_FOLDER'], image_name)
            if os.path.exists(image_path):
                os.remove(image_path)
    
    db.session.delete(product)
    db.session.commit()
    
    flash('تم حذف المنتج بنجاح!', 'success')
    return redirect(url_for('admin_products'))

# خدمة الصور الثابتة
@app.route('/images/products/<filename>')
def product_image(filename):
    return send_from_directory(app.config['PRODUCT_IMAGE_FOLDER'], filename)

if __name__ == '__main__':
    # إنشاء المجلدات إذا لم تكن موجودة
    os.makedirs('instance', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PRODUCT_IMAGE_FOLDER'], exist_ok=True)
    
    # تشغيل التطبيق
    app.run(debug=True, host='0.0.0.0', port=5000)
