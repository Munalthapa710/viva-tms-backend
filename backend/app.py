from flask import Flask, request, jsonify
from flask_cors import CORS
import pyodbc

app = Flask(__name__)
CORS(app) # This allows your Next.js app to access the API

# --- Database Configuration ---
# Update 'YOUR_SERVER_NAME' (e.g., DESKTOP-123\SQLEXPRESS)
conn_str = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=localhost\SQLEXPRESS;'
    r'DATABASE=VivaTMS;'
    r'Trusted_Connection=yes;'
)

def get_db_connection():
    return pyodbc.connect(conn_str)

# --- Routes ---

@app.route('/employees', methods=['GET'])
def get_employees():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Employees")
    rows = cursor.fetchall()
    
    employees = []
    for row in rows:
        employees.append({
            "id": row.id,
            "name": row.name,
            "department": row.department,
            "email": row.email,
            "phone": row.phone
        })
    conn.close()
    return jsonify(employees)

@app.route('/employees', methods=['POST'])
def add_employee():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO Employees (name, department, email, phone)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?)
        """,
        (data['name'], data['department'], data['email'], data['phone'])
    )

    new_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return jsonify({
        "id": new_id,
        **data
    }), 201

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

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0", port=5000)