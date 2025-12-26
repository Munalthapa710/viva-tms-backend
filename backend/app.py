from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import pyodbc
import os

# ================= APP SETUP =================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
SECRET_KEY = "your_super_secret_key"

# ================= DATABASE CONFIG =================
conn_str = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=localhost\SQLEXPRESS;'
    r'DATABASE=VivaTMS;'
    r'Trusted_Connection=yes;'
)

def get_db_connection():
    return pyodbc.connect(conn_str)

# ================= UPLOAD CONFIG =================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ================= SERVE UPLOADED FILES =================
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ================= AUTH ROUTES =================
@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")
    photo = request.files.get("photo")

    if not all([username, email, phone, password]):
        return jsonify({"message": "All fields are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Users WHERE email=?", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"message": "Email already exists"}), 409

    photo_path = None
    if photo:
        filename = f"{datetime.datetime.now().timestamp()}_{photo.filename}"
        photo_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        photo.save(photo_path)

    hashed_password = generate_password_hash(password)

    cursor.execute(
        "INSERT INTO Users (username, email, phone, password, photo) VALUES (?, ?, ?, ?, ?)",
        (username, email, phone, hashed_password, photo_path)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password, photo FROM Users WHERE email=?", (email,))
    user_row = cursor.fetchone()
    conn.close()

    if not user_row or not check_password_hash(user_row.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    token = jwt.encode(
        {
            "user_id": user_row.id,
            "username": user_row.username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    photo_url = None
    if user_row.photo:
        photo_url = f"http://localhost:5000/uploads/{os.path.basename(user_row.photo)}"

    return jsonify({
        "token": token,
        "username": user_row.username,
        "photo": photo_url
    }), 200


# ================= EMPLOYEES =================
@app.route('/employees', methods=['GET'])
def get_employees():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, department, email, phone FROM Employees")
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {"id": r.id, "name": r.name, "department": r.department, "email": r.email, "phone": r.phone}
        for r in rows
    ])


@app.route('/employees', methods=['POST'])
def add_employee():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO Employees (name, department, email, phone) OUTPUT INSERTED.id VALUES (?, ?, ?, ?)",
        (data['name'], data['department'], data['email'], data['phone'])
    )

    new_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return jsonify({"id": new_id, **data}), 201


@app.route('/employees/<int:id>', methods=['PUT'])
def update_employee(id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE Employees SET name=?, department=?, email=?, phone=? WHERE id=?",
        (data['name'], data['department'], data['email'], data['phone'], id)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Employee updated"})


@app.route('/employees/<int:id>', methods=['DELETE'])
def delete_employee(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Employees WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Employee deleted"})


# ================= INVENTORY =================

@app.route("/inventory/groups", methods=["GET"])
def get_inventory_groups():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM InventoryGroups")
    rows = cursor.fetchall()
    conn.close()

    return jsonify([{"id": r.id, "name": r.name} for r in rows])


@app.route("/inventory/groups", methods=["POST"])
def add_inventory_group():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO InventoryGroups (name) OUTPUT INSERTED.id VALUES (?)",
        (data["name"],)
    )

    group_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return jsonify({"id": group_id, "name": data["name"]}), 201


# ✅ UPDATE GROUP
@app.route("/inventory/groups/<int:id>", methods=["PUT"])
def update_inventory_group(id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE InventoryGroups SET name=? WHERE id=?",
        (data["name"], id)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Group updated"})


# ✅ DELETE GROUP
@app.route("/inventory/groups/<int:id>", methods=["DELETE"])
def delete_inventory_group(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM InventoryItems WHERE group_id=?", (id,))
    cursor.execute("DELETE FROM InventoryGroups WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Group deleted"})


@app.route("/inventory/items/<int:group_id>", methods=["GET"])
def get_inventory_items(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, quantity FROM InventoryItems WHERE group_id=?",
        (group_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    return jsonify([{"id": r.id, "name": r.name, "quantity": r.quantity} for r in rows])


@app.route("/inventory/items", methods=["POST"])
def add_inventory_item():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO InventoryItems (group_id, name, quantity) VALUES (?, ?, ?)",
        (data["group_id"], data["name"], data["quantity"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Item added"}), 201


# ✅ UPDATE ITEM
@app.route("/inventory/items/<int:id>", methods=["PUT"])
def update_inventory_item(id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE InventoryItems SET name=?, quantity=? WHERE id=?",
        (data["name"], data["quantity"], id)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Item updated"})


# ✅ DELETE ITEM
@app.route("/inventory/items/<int:id>", methods=["DELETE"])
def delete_inventory_item(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM InventoryItems WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Item deleted"})


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
