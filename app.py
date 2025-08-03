
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pubg_marketplace.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    phone_verified = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UCTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pubg_id = db.Column(db.String(50), nullable=False)
    uc_amount = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('uc_transaction.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('payments', lazy=True))
    transaction = db.relationship('UCTransaction', backref=db.backref('payment', lazy=True))

class UCPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    uc_amount = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

def validate_somali_phone(phone):
    """Validate Somaliland and Somalia phone numbers"""
    import re
    
    # Remove spaces, dashes, and plus signs
    phone = re.sub(r'[\s\-\+]', '', phone)
    
    # Somaliland numbers: +252 63/64/65/66/67/68/69/70
    # Somalia numbers: +252 61/62/90/91/92/93/94/95/96/97/98/99
    somaliland_patterns = [
        r'^252(63|64|65|66|67|68|69|70)\d{6}$',  # +252 format
        r'^(063|064|065|066|067|068|069|070)\d{6}$',  # 0 format
        r'^(63|64|65|66|67|68|69|70)\d{6}$'  # without 0
    ]
    
    somalia_patterns = [
        r'^252(61|62|90|91|92|93|94|95|96|97|98|99)\d{6}$',  # +252 format
        r'^(061|062|090|091|092|093|094|095|096|097|098|099)\d{6}$',  # 0 format
        r'^(61|62|90|91|92|93|94|95|96|97|98|99)\d{6}$'  # without 0
    ]
    
    all_patterns = somaliland_patterns + somalia_patterns
    
    for pattern in all_patterns:
        if re.match(pattern, phone):
            return True
    return False

def normalize_phone(phone):
    """Normalize phone number to +252 format"""
    import re
    phone = re.sub(r'[\s\-\+]', '', phone)
    
    if phone.startswith('252'):
        return '+' + phone
    elif phone.startswith('0'):
        return '+252' + phone[1:]
    else:
        return '+252' + phone

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    packages = UCPackage.query.filter_by(is_active=True).all()
    return render_template('index.html', packages=packages)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        name = request.form['name']
        phone_number = request.form['phone_number']
        
        if password != confirm_password:
            flash('Passwords do not match!')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists!')
            return redirect(url_for('register'))
        
        if not validate_somali_phone(phone_number):
            flash('Invalid phone number! Isticmaal Somaliland (63-70) ama Somalia (61,62,90-99) numbers.')
            return redirect(url_for('register'))
        
        normalized_phone = normalize_phone(phone_number)
        
        if User.query.filter_by(phone_number=normalized_phone).first():
            flash('Phone number already registered!')
            return redirect(url_for('register'))
        
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            phone_number=normalized_phone
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Phone: ' + normalized_phone)
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    transactions = UCTransaction.query.filter_by(user_id=current_user.id).order_by(UCTransaction.created_at.desc()).all()
    return render_template('dashboard.html', transactions=transactions)

@app.route('/buy_uc', methods=['GET', 'POST'])
@login_required
def buy_uc():
    if request.method == 'POST':
        pubg_id = request.form['pubg_id']
        package_id = request.form['package_id']
        payment_method = request.form['payment_method']
        
        package = UCPackage.query.get(package_id)
        if not package:
            flash('Invalid package selected!')
            return redirect(url_for('buy_uc'))
        
        transaction = UCTransaction(
            user_id=current_user.id,
            pubg_id=pubg_id,
            uc_amount=package.uc_amount,
            price=package.price
        )
        db.session.add(transaction)
        db.session.commit()
        
        payment = Payment(
            user_id=current_user.id,
            transaction_id=transaction.id,
            amount=package.price,
            payment_method=payment_method
        )
        db.session.add(payment)
        db.session.commit()
        
        flash('UC order placed successfully! Waiting for approval.')
        return redirect(url_for('dashboard'))
    
    packages = UCPackage.query.filter_by(is_active=True).all()
    return render_template('buy_uc.html', packages=packages)

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    pending_transactions = UCTransaction.query.filter_by(status='pending').all()
    all_users = User.query.all()
    total_earnings = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0
    
    return render_template('admin.html', 
                         pending_transactions=pending_transactions,
                         all_users=all_users,
                         total_earnings=total_earnings)

@app.route('/admin/approve_transaction/<int:transaction_id>')
@login_required
def approve_transaction(transaction_id):
    if not current_user.is_admin:
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    transaction = UCTransaction.query.get(transaction_id)
    if transaction:
        transaction.status = 'approved'
        if transaction.payment:
            transaction.payment.status = 'completed'
        db.session.commit()
        flash('Transaction approved!')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject_transaction/<int:transaction_id>')
@login_required
def reject_transaction(transaction_id):
    if not current_user.is_admin:
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    transaction = UCTransaction.query.get(transaction_id)
    if transaction:
        transaction.status = 'rejected'
        if transaction.payment:
            transaction.payment.status = 'failed'
        db.session.commit()
        flash('Transaction rejected!')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/packages', methods=['GET', 'POST'])
@login_required
def manage_packages():
    if not current_user.is_admin:
        flash('Access denied!')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        uc_amount = int(request.form['uc_amount'])
        price = float(request.form['price'])
        
        package = UCPackage(name=name, uc_amount=uc_amount, price=price)
        db.session.add(package)
        db.session.commit()
        flash('Package added successfully!')
    
    packages = UCPackage.query.all()
    return render_template('manage_packages.html', packages=packages)

@app.route('/api/stats')
@login_required
def api_stats():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    stats = {
        'total_users': User.query.count(),
        'pending_orders': UCTransaction.query.filter_by(status='pending').count(),
        'total_earnings': db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0,
        'completed_orders': UCTransaction.query.filter_by(status='approved').count()
    }
    return jsonify(stats)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if doesn't exist
        admin = User.query.filter_by(email='admin@admin.com').first()
        if not admin:
            admin = User(
                email='admin@admin.com',
                password_hash=generate_password_hash('admin123'),
                name='Admin',
                phone_number='+25263000000',
                phone_verified=True,
                is_admin=True
            )
            db.session.add(admin)
            
            # Add default UC packages
            packages = [
                UCPackage(name='60 UC', uc_amount=60, price=0.99),
                UCPackage(name='325 UC', uc_amount=325, price=4.99),
                UCPackage(name='660 UC', uc_amount=660, price=9.99),
                UCPackage(name='1800 UC', uc_amount=1800, price=24.99),
                UCPackage(name='3850 UC', uc_amount=3850, price=49.99),
                UCPackage(name='8100 UC', uc_amount=8100, price=99.99)
            ]
            for package in packages:
                db.session.add(package)
            
            db.session.commit()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
