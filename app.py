from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta



app = Flask(__name__)



def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="1234",
        options="-c search_path=food,public"
    )
    return conn




def create_orders_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(100),
                items TEXT,
                total_price DECIMAL(10, 2),
                order_time TIMESTAMP,
                status VARCHAR(20)
            )
        """)
        conn.commit()






def add_sample_data(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders")
        count = cur.fetchone()[0]
        
        if count == 0:
            sample_orders = [
                ("คุณ A", "ข้าวผัดหมู x1, น้ำเปล่า x1", 60.00, datetime.now(), "pending"),
                ("คุณ B", "ก๋วยเตี๋ยวต้มยำ x2", 80.00, datetime.now(), "in_progress"),
                ("คุณ C", "ข้าวมันไก่ x1, โค้ก x1", 70.00, datetime.now(), "pending"),
            ]
            
            cur.executemany("""
                INSERT INTO orders (customer_name, items, total_price, order_time, status)
                VALUES (%s, %s, %s, %s, %s)
            """, sample_orders)
            
            conn.commit()






@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch pending orders
    cur.execute("SELECT * FROM orders WHERE status = 'pending' ORDER BY order_time")
    pending_orders = cur.fetchall()
    
    # Fetch in-progress orders
    cur.execute("SELECT * FROM orders WHERE status = 'in_progress' ORDER BY order_time")
    in_progress_orders = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('index.html', pending_orders=pending_orders, in_progress_orders=in_progress_orders)









@app.route('/menu')
def menu():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM menu_items ORDER BY id DESC')
    menu_items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('menu.html', menu_items=menu_items)

@app.route('/add_menu_item', methods=['POST'])
def add_menu_item():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO menu_items (name, price, description, category) VALUES (%s, %s, %s, %s) RETURNING id',
                (data['name'], data['price'], data['description'], data['category']))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "id": new_id}), 201







@app.route('/total_summary')
def total_summary():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch orders from the last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)
    cur.execute("""
        SELECT DATE(order_time), SUM(total_price), COUNT(*)
        FROM orders
        WHERE order_time >= %s
        GROUP BY DATE(order_time)
        ORDER BY DATE(order_time) DESC
    """, (seven_days_ago,))
    daily_summaries = cur.fetchall()
    
    # Fetch recent orders
    cur.execute("""
        SELECT id, customer_name, items, total_price, order_time, status
        FROM orders
        WHERE order_time >= %s
        ORDER BY order_time DESC
        LIMIT 50
    """, (seven_days_ago,))
    recent_orders = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('Total_summary.html', daily_summaries=daily_summaries, recent_orders=recent_orders)


@app.route('/confirm_order/<int:order_id>', methods=['POST'])
def confirm_order(order_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("UPDATE orders SET status = 'in_progress' WHERE id = %s", (order_id,))
    conn.commit()
    
    cur.close()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/complete_order/<int:order_id>', methods=['POST'])
def complete_order(order_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (order_id,))
    conn.commit()
    
    cur.close()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/api/place_order', methods=['POST'])
def place_order():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO orders (customer_name, items, total_price, order_time, status)
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING id
        """, (data['customer_name'], data['items'], data['total_price'], datetime.now()))
        
        order_id = cur.fetchone()[0]
        conn.commit()
        
        return jsonify({"success": True, "order_id": order_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    conn = get_db_connection()
    create_orders_table(conn)
    add_sample_data(conn)
    conn.close()
    app.run(debug=True)