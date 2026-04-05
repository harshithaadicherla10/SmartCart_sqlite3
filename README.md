# 🛒 SmartCart – Full Stack E-Commerce Platform

SmartCart is a full-stack e-commerce web application built to simulate real-world online shopping experiences. The application supports product browsing, user authentication, cart management, and order processing.

---

## 🚀 Features

* 🔐 User Authentication (Login / Registration)
* 🛍️ Product Listing and Management
* 🛒 Shopping Cart Functionality
* 💳 Order Processing Workflow
* 📦 CRUD Operations for Products
* 🎨 Responsive UI using HTML, CSS, Bootstrap

---

## 🧰 Tech Stack

* **Backend:** Python, Flask
* **Database:** SQLite3
* **Frontend:** HTML, CSS, Bootstrap
* **Other Tools:** Jinja2 Templates, REST APIs, Git

---

## 📂 Project Structure

```
SmartCart_sqlite3/
│── static/             # CSS, JS, Images
│── templates/          # HTML templates
│── utils/              # Helper functions
│── venv/               # Virtual environment (ignored in production)
│── __pycache__/        # Compiled files (auto-generated)
│── app.py              # Main Flask application
│── config.py           # Configuration settings
│── init_db.py          # Database initialization script
│── schema.sql          # Database schema
│── smartcart1.db       # SQLite database file
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone [https://github.com/yourusername/SmartCart_sqlite3.git](https://github.com/harshithaadicherla10/SmartCart_sqlite3/new/main?filename=README.md)
cd SmartCart_sqlite3
```

### 2️⃣ Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3️⃣ Install dependencies

```bash
pip install flask
```

### 4️⃣ Initialize database

```bash
python init_db.py
```

### 5️⃣ Run the application

```bash
python app.py
```

👉 Open in browser:

```
http://127.0.0.1:5000/
```

---

## 🧠 Key Highlights

* Designed a modular full-stack architecture using Flask
* Implemented RESTful routes for handling user and product operations
* Integrated SQLite database with optimized schema design
* Developed dynamic web pages using Jinja2 templating
* Managed session-based authentication for secure user login

---

## 📈 Future Enhancements

* Payment Gateway Integration (Stripe/Razorpay)
* Admin Dashboard for product analytics
* Product search and filtering
* Deployment on cloud (AWS/Render)

---

## 👩‍💻 Author

**Harshitha Adicherla**

* GitHub: https://github.com/harshithaadicherla10
* LinkedIn: https://linkedin.com/in/harshithaadicherla10

---

## ⭐ If you found this useful, consider giving a star!
