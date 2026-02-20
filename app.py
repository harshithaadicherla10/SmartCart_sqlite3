# app.py
# ------------------------------------------------------
# Day 1: Basic Flask Setup + MySQL Database Connection
# ------------------------------------------------------

from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_mail import Mail, Message
import sqlite3
import bcrypt
import random
import config
import os
import uuid
from werkzeug.utils import secure_filename
import razorpay
import traceback
from flask import make_response, render_template
from utils.pdf_generator import generate_pdf


app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ================= SQLITE CONFIG =================

def get_db_connection():
    conn = sqlite3.connect("smartcart1.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ================= RAZORPAY =================
razorpay_client = razorpay.Client(
    auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET)
)

# ---------------- EMAIL CONFIGURATION ----------------
app.config['MAIL_SERVER'] = config.MAIL_SERVER
app.config['MAIL_PORT'] = config.MAIL_PORT
app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD

mail = Mail(app)

# ---------------------------------------------------------
# ROUTE 1: ADMIN SIGNUP (SEND OTP)
# ---------------------------------------------------------
@app.route('/admin-signup', methods=['GET', 'POST'])
def admin_signup():

    # Show form
    if request.method == "GET":
        return render_template("admin/admin_signup.html")

    # POST → Process signup
    name = request.form['name']
    email = request.form['email']

    # 1️⃣ Check if admin email already exists
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT admin_id FROM admin WHERE email=?", (email,))
    existing_admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if existing_admin:
        flash("Email already registered.", "error")
        return redirect('/admin-login')

    # 2️⃣ Save user input temporarily in session
    session['signup_name'] = name
    session['signup_email'] = email

    # 3️⃣ Generate OTP and store in session
    otp = random.randint(100000, 999999)
    session['otp'] = otp

    # 4️⃣ Send OTP Email
    message = Message(
        subject="SmartCart Admin OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )
    message.body = f"Your OTP for SmartCart Admin Registration is: {otp}"
    mail.send(message)

    flash("OTP sent successfully!", "success")
    return redirect('/verify-otp')


# ---------------------------------------------------------
# ROUTE 2: DISPLAY OTP PAGE
# ---------------------------------------------------------
@app.route('/verify-otp', methods=['GET'])
def verify_otp_get():
    return render_template("admin/verify_otp.html")


# ---------------------------------------------------------
# ROUTE 3: VERIFY OTP + SAVE ADMIN
# ---------------------------------------------------------
@app.route('/verify-otp', methods=['POST'])
def verify_otp_post():
    
    # User submitted OTP + Password
    user_otp = request.form['otp']
    password = request.form['password']

    # Compare OTP
    if str(session.get('otp')) != str(user_otp):
        flash("Invalid OTP. Try again!", "error")
        return redirect('/verify-otp')

    # Hash password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert admin into database
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO admin (name, email, password) VALUES (?, ?, ?)",
        (session['signup_name'], session['signup_email'], hashed_password)
    )

    conn.commit()
    cursor.close()
    conn.close()

    # Clear temporary session data
    session.pop('otp', None)
    session.pop('signup_name', None)
    session.pop('signup_email', None)

    flash("Admin Registered Successfully!", "success")
    return redirect('/admin-login')

# =================================================================
# ROUTE 4: ADMIN LOGIN PAGE (GET + POST)
# =================================================================
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    # Show login page
    if request.method == 'GET':
        return render_template("admin/admin_login.html")

    # POST → Validate login
    email = request.form['email']
    password = request.form['password']

    # Step 1: Check if admin email exists
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admin WHERE email=?", (email,))
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if not admin:
        flash("Email not found! Please register first.", "danger")
        return redirect('/admin-login')

    # Step 2: Compare entered password with hashed password
    stored_hashed_password = admin['password']

    if not bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
        flash("Incorrect password! Try again.", "danger")
        return redirect('/admin-login')

    # Step 5: If login success → Create admin session
    session['admin_id'] = admin['admin_id']
    session['admin_name'] = admin['name']
    session['admin_email'] = admin['email']

    flash("Login Successful!", "success")
    return redirect('/admin-dashboard')


# =================================================================
# ROUTE 5: ADMIN DASHBOARD (PROTECTED ROUTE)
# =================================================================
@app.route('/admin-dashboard')
def admin_dashboard():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

   

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name, profile_image FROM admin WHERE admin_id=?", (session['admin_id'],))
    
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("admin/dashboard.html", admin=admin)


# =================================================================
# ROUTE 6: ADMIN LOGOUT
# =================================================================
@app.route('/admin-logout')
def admin_logout():

    # Clear admin session
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)

    flash("Logged out successfully.", "success")
    return redirect('/admin-login')

# ------------------- IMAGE UPLOAD PATH -------------------
UPLOAD_FOLDER = 'static/uploads/product_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# =================================================================
# ROUTE 7: SHOW ADD PRODUCT PAGE (Protected Route)
# =================================================================
@app.route('/admin/add-item', methods=['GET'])
def add_item_page():

    # Only logged-in admin can access
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    return render_template("admin/add_item.html")

# =================================================================
# ROUTE 8: ADD PRODUCT INTO DATABASE
# =================================================================
@app.route('/admin/add-item1', methods=['POST'])
def add_item():

    # Check admin session
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    # 1️⃣ Get form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']

    try:
        price = float(request.form['price'])
    except ValueError:
        flash("Invalid price format!", "danger")
        return redirect('/admin/add-item')
    
    image_file = request.files['image']

    # 2️⃣ Validate image upload
    if image_file.filename == "":
        flash("Please upload a product image!", "danger")
        return redirect('/admin/add-item')

    # 3️⃣ Secure the file name
    unique_name = str(uuid.uuid4()) + "_" + secure_filename(image_file.filename)
    filename = unique_name

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    file_ext = filename.rsplit('.', 1)[1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        flash("Invalid image format!", "danger")
        return redirect('/admin/add-item')

    # 4️⃣ Create full path
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # 5️⃣ Save image into folder
    image_file.save(image_path)

    # 6️⃣ Insert product into database
    conn = get_db_connection()
    cursor = conn.cursor()

     
    cursor.execute(
        "INSERT INTO products (name, description, category, price, image, admin_id) VALUES (?, ?, ?, ?, ?, ?)",
        (name, description, category, price, filename, session['admin_id'])
    )

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product added successfully!", "success")
    return redirect(url_for('item_list'))

# =================================================================
# ROUTE 9: DISPLAY ALL PRODUCTS (Admin)
# =================================================================
@app.route('/admin/item-list')
def item_list():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']
    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch categories only for this admin
    cursor.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE admin_id=?
    """, (admin_id,))
    categories = cursor.fetchall()

    # Build product query
    query = "SELECT * FROM products WHERE admin_id=?"
    params = [admin_id]

    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")

    if category_filter:
        query += " AND category=?"
        params.append(category_filter)

    # query += " ORDER BY p.product_id DESC"   

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/item_list.html",
        products=products,
        categories=categories
    )


#=================================================================
# ROUTE 10: VIEW SINGLE PRODUCT DETAILS
# =================================================================
@app.route('/admin/view-item/<int:item_id>')
def view_item(item_id):

    # Check admin session
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM products 
    WHERE product_id=? AND admin_id=?
""", (item_id, session['admin_id']))
    
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('item_list'))

    return render_template("admin/view_item.html", product=product)

# =================================================================
# ROUTE 11: SHOW UPDATE FORM WITH EXISTING DATA
# =================================================================
@app.route('/admin/update-item/<int:item_id>', methods=['GET'])
def update_item_page(item_id):

    # Check login
    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    # Fetch product data
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM products 
    WHERE product_id=? AND admin_id=?
""", (item_id, session['admin_id']))
    
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Unauthorized Access!", "danger")
        return redirect(url_for('item_list'))

    return render_template("admin/update_item.html", product=product)

# =================================================================
# ROUTE 12: UPDATE PRODUCT + OPTIONAL IMAGE REPLACE
# =================================================================
@app.route('/admin/update-item/<int:item_id>', methods=['POST'])
def update_item(item_id):

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    # 1️⃣ Get updated form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']

    new_image = request.files['image']

    # 2️⃣ Fetch old product data
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM products 
    WHERE product_id=? AND admin_id=?
""", (item_id, session['admin_id']))
    
    product = cursor.fetchone()

    if not product:
        flash("Unauthorized Access!", "danger")
        return redirect(url_for('item_list'))

    old_image_name = product['image']

    # 3️⃣ If admin uploaded a new image → replace it
    if new_image and new_image.filename != "":
        # Secure filename
        new_filename = secure_filename(new_image.filename)

        # Save new image
        new_image_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        new_image.save(new_image_path)

        # Delete old image file
        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image_name)
        if os.path.exists(old_image_path):
            os.remove(old_image_path)

        final_image_name = new_filename

    else:
        # No new image uploaded → keep old one
        final_image_name = old_image_name

    # 4️⃣ Update product in the database
    cursor.execute("""
    UPDATE products
    SET name=?, description=?, category=?, price=?, image=?
        WHERE product_id=? AND admin_id=?
    """, (name, description, category, price, final_image_name,
      item_id, session['admin_id']))


    conn.commit()
    cursor.close()
    conn.close()

    flash("Product updated successfully!", "success")
    return redirect('/admin/item-list')

# =================================================================
# ROUTE 13:DELETE PRODUCT (DELETE DB ROW + DELETE IMAGE FILE)
# =================================================================
@app.route('/admin/delete-item/<int:item_id>')
def delete_item(item_id):

    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Fetch product to get image name
    cursor.execute("""
    SELECT image FROM products 
    WHERE product_id=? AND admin_id=?
""", (item_id, session['admin_id']))
    
    product = cursor.fetchone()

    if not product:
        flash("Unauthorized delete attempt!", "danger")
        return redirect('/admin/item-list')

    image_name = product['image']

    # Delete image from folder
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    if os.path.exists(image_path):
        os.remove(image_path)

    # 2️⃣ Delete product from DB
    cursor.execute("""
    DELETE FROM products 
    WHERE product_id=? AND admin_id=?
""", (item_id, session['admin_id']))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product deleted successfully!", "success")
    return redirect('/admin/item-list')

# ===============
# Admin Profiles
# ===============

ADMIN_UPLOAD_FOLDER = 'static/uploads/admin_profiles'
app.config['ADMIN_UPLOAD_FOLDER'] = ADMIN_UPLOAD_FOLDER

# =================================================================
# ROUTE 14: SHOW ADMIN PROFILE DATA
# =================================================================
@app.route('/admin/profile', methods=['GET'])
def admin_profile():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admin WHERE admin_id = ?", (session['admin_id'],))
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("admin/admin_profile.html", admin=admin)


# =================================================================
# ROUTE 15: UPDATE ADMIN PROFILE (NAME, EMAIL, PASSWORD, IMAGE)
# =================================================================
@app.route('/admin/profile', methods=['POST'])
def admin_profile_update():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    # 1️⃣ Get form data
    name = request.form['name']
    email = request.form['email']
    new_password = request.form['password']
    new_image = request.files['profile_image']

    conn = get_db_connection()
    cursor = conn.cursor()

    # 2️⃣ Fetch old admin data
    cursor.execute("SELECT * FROM admin WHERE admin_id = ?", (session['admin_id'],))
    admin = cursor.fetchone()

    old_image_name = admin['profile_image']

    # 3️⃣ Update password only if entered
    if new_password:
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    else:
        hashed_password = admin['password']  # keep old password

    # 4️⃣ Process new profile image if uploaded
    if new_image and new_image.filename != "":
        new_filename = secure_filename(new_image.filename)

        # Save new image
        image_path = os.path.join(app.config['ADMIN_UPLOAD_FOLDER'], new_filename)
        new_image.save(image_path)

        # Delete old image
        if old_image_name:
            old_image_path = os.path.join(app.config['ADMIN_UPLOAD_FOLDER'], old_image_name)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

        final_image_name = new_filename
    else:
        final_image_name = old_image_name

    # 5️⃣ Update database
    cursor.execute("""
        UPDATE admin
        SET name=?, email=?, password=?, profile_image=?
        WHERE admin_id=?
    """, (name, email, hashed_password, final_image_name, session['admin_id']))

    conn.commit()
    cursor.close()
    conn.close()

    # Update session name for UI consistency
    session['admin_name'] = name  
    session['admin_email'] = email

    flash("Profile updated successfully!", "success")
    return redirect('/admin/profile')

# ===========================================
# ROUTE 16:REMOVE ADMIN PROFILE IMAGE
# ===========================================
@app.route('/admin/remove-profile-image', methods=['POST'])
def remove_profile_image():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get current image
    cursor.execute("SELECT profile_image FROM admin WHERE admin_id=?", (session['admin_id'],))
    admin = cursor.fetchone()

    if admin and admin['profile_image']:

        image_path = os.path.join(app.config['ADMIN_UPLOAD_FOLDER'], admin['profile_image'])

        # Delete file from folder
        if os.path.exists(image_path):
            os.remove(image_path)

        # Set DB value to NULL
        cursor.execute(
            "UPDATE admin SET profile_image=NULL WHERE admin_id=?",
            (session['admin_id'],)
        )
        conn.commit()

    cursor.close()
    conn.close()

    flash("Profile image removed successfully!", "success")
    return redirect('/admin/profile')


# =================================================================
# ROUTE 17: USER REGISTRATION
# =================================================================
@app.route('/user-register', methods=['GET', 'POST'])
def user_register():

    if request.method == 'GET':
        return render_template("user/user_register.html")

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    # Check if user already exists
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()
        flash("Email already registered! Please login.", "danger")
        return redirect('/')

    # Hash password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert new user
    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        (name, email, hashed_password)
    )

    conn.commit()
    cursor.close()
    conn.close()

    flash("Registration successful! Please login.", "success")
    return redirect('/')

# =================================================================
# ROUTE 18: USER LOGIN
# =================================================================
@app.route('/', methods=['GET', 'POST'])
def user_login():

    if request.method == 'GET':
        return render_template("user/user_login.html")

    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        flash("Email not found! Please register.", "danger")
        return redirect('/')

    # Verify password
    if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        flash("Incorrect password!", "danger")
        return redirect('/')

    # Create user session
    session['user_id'] = user['user_id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']

    flash("Login successful!", "success")
    return redirect('/user-dashboard')


# =================================================================
# ROUTE 19: USER DASHBOARD
# =================================================================
@app.route('/user-dashboard')
def user_dashboard():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/')

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()


    # 1️⃣ Total Orders
    cursor.execute(
        "SELECT COUNT(*) AS total_orders FROM orders WHERE user_id=?",
        (user_id,)
    )
    total_orders = cursor.fetchone()['total_orders']

    # 2️⃣ Total Spent
    cursor.execute(
        "SELECT SUM(amount) AS total_spent FROM orders WHERE user_id=?",
        (user_id,)
    )
    result = cursor.fetchone()
    total_spent = result['total_spent'] if result['total_spent'] else 0

    cursor.close()
    conn.close()

    return render_template(
        "user/user_home.html",
        user_name=session['user_name'],
        total_orders=total_orders,
        total_spent=int(total_spent)
    )

# =================================================================
# ROUTE 20: USER LOGOUT
# =================================================================
@app.route('/user-logout')
def user_logout():
    
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)

    flash("Logged out successfully!", "success")
    return redirect('/')

# =================================================================
# ROUTE 21: USER PRODUCT LISTING (SEARCH + FILTER)
# =================================================================
@app.route('/user/products')
def user_products():

    # Optional: restrict only logged-in users
    if 'user_id' not in session:
        flash("Please login to view products!", "danger")
        return redirect('/')

    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch categories for filter dropdown
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()

    # Build dynamic SQL
    query = """SELECT p.*, a.name AS admin_name
        FROM products p
        JOIN admin a ON p.admin_id = a.admin_id
        WHERE 1=1"""
    params = []

    if search:
        query += " AND p.name LIKE ?"
        params.append(f"%{search}%")

    if category_filter:
        query += " AND p.category = ?"
        params.append(category_filter)

    # query += " ORDER BY p.product_id DESC"    

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "user/user_products.html",
        products=products,
        categories=categories
    )

# =================================================================
# ROUTE 22: USER PRODUCT DETAILS PAGE
# =================================================================
@app.route('/user/product/<int:product_id>')
def user_product_details(product_id):

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/user/products')

    return render_template("user/product_details.html", product=product)

# =================================================================
# ROUTE 23:ADD ITEM TO CART
# =================================================================
@app.route('/user/add-to-cart/<int:product_id>')
def add_to_cart(product_id):

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/')

    user_id = session['user_id']
    cart_key = f'cart_{user_id}'

    if cart_key not in session:
        session[cart_key] = {}

    cart = session[cart_key]

    # Fetch product
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id=?", (product_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found.", "danger")
        return redirect('/user/products')

    pid = str(product_id)

    # If exists → increase quantity
    if pid in cart:
        cart[pid]['quantity'] += 1
    else:
        cart[pid] = {
            'name': product['name'],
            'price': float(product['price']),
            'image': product['image'],
            'quantity': 1
        }

    session[cart_key] = cart
    session.modified = True

    flash("Item added to cart!", "success")
    return redirect(request.referrer)

# =================================================================
# ROUTE 24:VIEW CART PAGE
# =================================================================
@app.route('/user/cart')
def view_cart():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/')

    user_id = session['user_id']
    cart_key = f'cart_{user_id}'

    cart = session.get(cart_key, {})

    # Calculate total
    grand_total = sum(item['price'] * item['quantity'] for item in cart.values())

    return render_template("user/cart.html", cart=cart, grand_total=grand_total)

# =================================================================
# ROUTE 25:INCREASE QUANTITY
# =================================================================
@app.route('/user/cart/increase/<pid>')
def increase_quantity(pid):

    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    cart_key = f'cart_{user_id}'

    cart = session.get(cart_key, {})

    if pid in cart:
        cart[pid]['quantity'] += 1

    session[cart_key] = cart
    return redirect('/user/cart')

# =================================================================
# ROUTE 26:DECREASE QUANTITY
# =================================================================
@app.route('/user/cart/decrease/<pid>')
def decrease_quantity(pid):

    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    cart_key = f'cart_{user_id}'

    cart = session.get(cart_key, {})

    if pid in cart:
        cart[pid]['quantity'] -= 1

        if cart[pid]['quantity'] <= 0:
            cart.pop(pid)

    session[cart_key] = cart
    return redirect('/user/cart')


# ==========================================
# ROUTE 27:REMOVE ITEM
# ==========================================
@app.route('/user/cart/remove/<pid>')
def remove_from_cart(pid):

    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    cart_key = f'cart_{user_id}'

    cart = session.get(cart_key, {})

    if pid in cart:
        cart.pop(pid)

    session[cart_key] = cart

    flash("Item removed!", "success")
    return redirect('/user/cart')
# ===========================================
# ROUTE 28: AJAX ADD TO CART
# ===========================================
@app.route('/user/add-to-cart-ajax/<int:product_id>')
def add_to_cart_ajax(product_id):

    if 'user_id' not in session:
        return {"error": "not_logged_in"}, 401

    user_id = session['user_id']
    cart_key = f'cart_{user_id}'

    if cart_key not in session:
        session[cart_key] = {}

    cart = session[cart_key]

    # Fetch product from DB
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id=?", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if not product:
        return {"error": "Product not found"}, 404

    pid = str(product_id)

    # Increase quantity if exists
    if pid in cart:
        cart[pid]['quantity'] += 1
    else:
        cart[pid] = {
            'name': product['name'],
            'price': float(product['price']),
            'image': product['image'],
            'quantity': 1
        }

    session[cart_key] = cart

    # Return JSON response
    return {
        "message": "Item added to cart!",
        "cart_count": sum(item['quantity'] for item in cart.values())
    }

# =====================================================
# ROUTE 29:User ADDRESS PAGE (Before Payment)
# =====================================================
@app.route('/user/address', methods=['GET', 'POST'])
def user_address():

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Save new address
    if request.method == 'POST':
        full_name = request.form['full_name']
        phone = request.form['phone']
        address_line = request.form['address_line']
        city = request.form['city']
        state = request.form['state']
        pincode = request.form['pincode']

        cursor.execute("""
            INSERT INTO user_addresses 
            (user_id, full_name, phone, address_line, city, state, pincode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session['user_id'], full_name, phone,
              address_line, city, state, pincode))

        conn.commit()
        flash("Address added successfully!", "success")

    # Fetch existing addresses
    cursor.execute("""
        SELECT * FROM user_addresses 
        WHERE user_id=? ORDER BY created_at DESC
    """, (session['user_id'],))

    addresses = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("user/address.html", addresses=addresses)


# =================================================================
# ROUTE 30: CREATE RAZORPAY ORDER
# =================================================================
@app.route('/user/pay')
def user_pay():

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/')
    
    address_id = request.args.get('address_id')

    if not address_id:
        flash("Please select delivery address!", "danger")
        return redirect('/user/address')

    session['selected_address_id'] = int(address_id)

    cart_key = f'cart_{session["user_id"]}'
    cart = session.get(cart_key, {})


    if not cart:
        flash("Your cart is empty!", "danger")
        return redirect('/user/products')

    # Calculate total amount
    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
    razorpay_amount = int(total_amount * 100)  # convert to paise

    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    session['razorpay_order_id'] = razorpay_order['id']

    return render_template(
        "user/payment.html",
        amount=total_amount,
        key_id=config.RAZORPAY_KEY_ID,
        order_id=razorpay_order['id']
    )

# =================================================================
# ROUTE 31:TEMP SUCCESS PAGE (Verification in Day 13)
# =================================================================
@app.route('/payment-success')
def payment_success():

    payment_id = request.args.get('payment_id')
    order_id = request.args.get('order_id')

    if not payment_id:
        flash("Payment failed!", "danger")
        return redirect('/user/cart')

    return render_template(
        "user/payment_success.html",
        payment_id=payment_id,
        order_id=order_id
    )
# ===========================================================
#  Verify Razorpay Payment & Store Order + Order Items
# ===========================================================
# ------------------------------
# Route 32: Verify Payment and Store Order
# ------------------------------
@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    if 'user_id' not in session:
        flash("Please login to complete the payment.", "danger")
        return redirect('/')

    # Read values posted from frontend
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')

    if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
        flash("Payment verification failed (missing data).", "danger")
        return redirect('/user/cart')

    # Build verification payload required by Razorpay client.utility
    payload = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        # This will raise an error if signature invalid
        razorpay_client.utility.verify_payment_signature(payload)

    except Exception as e:
        # Verification failed
        app.logger.error("Razorpay signature verification failed: %s", str(e))
        flash("Payment verification failed. Please contact support.", "danger")
        return redirect('/user/cart')

    # Signature verified — now store order and items into DB
    user_id = session['user_id']
    cart_key = f'cart_{user_id}'
    cart = session.get(cart_key, {})


    if not cart:
        flash("Cart is empty. Cannot create order.", "danger")
        return redirect('/user/products')

    # Calculate total amount (ensure same as earlier)
    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())

    # DB insert: orders and order_items
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        
        address_id = session.get('selected_address_id')

        # Insert into orders table
        cursor.execute("""
        INSERT INTO orders (user_id, razorpay_order_id, razorpay_payment_id, amount, payment_status, address_id)
        VALUES (?, ?, ?, ?, ?, ?)""", 
        (user_id, razorpay_order_id, razorpay_payment_id, total_amount, 'paid', address_id))


        order_db_id = cursor.lastrowid  # newly created order's primary key

        # Insert all items
        for pid_str, item in cart.items():
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                VALUES (?, ?, ?, ?, ?)
            """, (order_db_id, int(pid_str), item['name'], item['quantity'], item['price']))

        # Commit transaction
        conn.commit()

        # Clear cart and temporary razorpay order id
        session.pop(cart_key, None)
        session.pop('razorpay_order_id', None)

        flash("Payment successful and order placed!", "success")
        return redirect(f"/user/order-success/{order_db_id}")

    except Exception as e:
        # Rollback and log error
        conn.rollback()
        app.logger.error("Order storage failed: %s", str(e))
        flash("Error saving order.", "danger")
        return redirect('/user/cart')

    finally:
        cursor.close()
        conn.close()

# ============================
# ROUTE 33:Order Success Page
# ============================

@app.route('/user/order-success/<int:order_db_id>')
def order_success(order_db_id):
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE order_id=? AND user_id=?", (order_db_id, session['user_id']))
    order = cursor.fetchone()

    cursor.execute("SELECT * FROM order_items WHERE order_id=?", (order_db_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect('/user/products')

    return render_template("user/order_success.html", order=order, items=items)

# ===========================================
# ROUTE 34: My Orders Page (List user's orders)
# ===========================================
@app.route('/user/my-orders')
def my_orders():
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (session['user_id'],))

    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("user/my_orders.html", orders=orders)

# ----------------------------
# ROUTE 35:GENERATE INVOICE PDF
# ----------------------------
@app.route("/user/download-invoice/<int:order_id>")
def download_invoice(order_id):

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/')

    # Fetch order
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT o.*, u.name, u.address, u.email
    FROM orders o
    JOIN users u ON o.user_id = u.user_id
    WHERE o.order_id = ? AND o.user_id = ?
""", (order_id, session['user_id']))
    
    order = cursor.fetchone()

    cursor.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect('/user/my-orders')

    # Render invoice HTML
    html = render_template("user/invoice.html", order=order, items=items)

    pdf = generate_pdf(html)
    if not pdf:
        flash("Error generating PDF", "danger")
        return redirect('/user/my-orders')

    # Prepare response
    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f"attachment; filename=invoice_{order_id}.pdf"

    return response

# ======================================================
# ROUTE 36:USER FORGOT PASSWORD - SEND OTP
# ======================================================
@app.route('/user-forgot-password', methods=['GET', 'POST'])
def user_forgot_password():

    if request.method == 'GET':
        return render_template("user/user_forgot_password.html")

    email = request.form['email']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash("Email not registered!", "danger")
        return redirect('/user-forgot-password')

    # Generate OTP
    otp = random.randint(100000, 999999)

    session['reset_user_email'] = email
    session['reset_user_otp'] = otp

    message = Message(
        subject="SmartCart Password Reset OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )
    message.body = f"Your password reset OTP is: {otp}"
    mail.send(message)

    flash("OTP sent to your email!", "success")
    return redirect('/user-reset-password')

# ======================================================
# ROUTE 37:USER RESET PASSWORD
# ======================================================
@app.route('/user-reset-password', methods=['GET', 'POST'])
def user_reset_password():

    if request.method == 'GET':
        return render_template("user/user_reset_password.html")

    entered_otp = request.form['otp']
    new_password = request.form['password']

    if str(session.get('reset_user_otp')) != str(entered_otp):
        flash("Invalid OTP!", "danger")
        return redirect('/user-reset-password')

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET password=? WHERE email=?",
        (hashed_password, session['reset_user_email'])
    )

    conn.commit()
    cursor.close()
    conn.close()

    # Clear session
    session.pop('reset_user_email', None)
    session.pop('reset_user_otp', None)

    flash("Password reset successful! Please login.", "success")
    return redirect('/')

# ======================================================
# ROUTE 38:ADMIN FORGOT PASSWORD
# ======================================================
@app.route('/admin-forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():

    if request.method == 'GET':
        return render_template("admin/admin_forgot_password.html")

    email = request.form['email']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE email=?", (email,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if not admin:
        flash("Email not registered!", "danger")
        return redirect('/admin-forgot-password')

    otp = random.randint(100000, 999999)

    session['reset_admin_email'] = email
    session['reset_admin_otp'] = otp

    message = Message(
        subject="SmartCart Admin Password Reset OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )
    message.body = f"Your admin password reset OTP is: {otp}"
    mail.send(message)

    flash("OTP sent to email!", "success")
    return redirect('/admin-reset-password')

# ======================================================
# ROUTE 39:ADMIN RESET PASSWORD
# ======================================================
@app.route('/admin-reset-password', methods=['GET', 'POST'])
def admin_reset_password():

    if request.method == 'GET':
        return render_template("admin/admin_reset_password.html")

    entered_otp = request.form['otp']
    new_password = request.form['password']

    if str(session.get('reset_admin_otp')) != str(entered_otp):
        flash("Invalid OTP!", "danger")
        return redirect('/admin-reset-password')

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE admin SET password=? WHERE email=?",
        (hashed_password, session['reset_admin_email'])
    )

    conn.commit()
    cursor.close()
    conn.close()

    session.pop('reset_admin_email', None)
    session.pop('reset_admin_otp', None)

    flash("Password reset successful! Please login.", "success")
    return redirect('/admin-login')


# ------------------------ RUN SERVER -----------------------

if __name__ == '__main__':
    app.run(debug=True)
