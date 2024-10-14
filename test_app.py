import pytest
from app import app, get_db_connection, create_orders_table, add_sample_data
from flask import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def db_connection():
    conn = get_db_connection()
    yield conn
    conn.close()

def test_index_route(client, db_connection):
    response = client.get('/')
    assert response.status_code == 200
    assert b'pending-orders' in response.data

def test_create_orders_table(db_connection):
    create_orders_table(db_connection)
    with db_connection.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'orders')")
        assert cur.fetchone()[0] is True

def test_add_sample_data(db_connection):
    create_orders_table(db_connection)
    add_sample_data(db_connection)
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders")
        count = cur.fetchone()[0]
        assert count > 0

def test_confirm_order(client, db_connection):
    # Add a sample pending order
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO orders (customer_name, items, total_price, order_time, status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    ("Test Customer", "Test Item", 100.00, "2023-01-01 12:00:00", "pending"))
        order_id = cur.fetchone()[0]
        db_connection.commit()

    response = client.post(f'/confirm_order/{order_id}')
    assert response.status_code == 302  # Redirect status code

    # Check if the order status was updated
    with db_connection.cursor() as cur:
        cur.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
        status = cur.fetchone()[0]
        assert status == "in_progress"

def test_complete_order(client, db_connection):
    # Add a sample in-progress order
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO orders (customer_name, items, total_price, order_time, status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    ("Test Customer", "Test Item", 100.00, "2023-01-01 12:00:00", "in_progress"))
        order_id = cur.fetchone()[0]
        db_connection.commit()

    response = client.post(f'/complete_order/{order_id}')
    assert response.status_code == 302  # Redirect status code

    # Check if the order status was updated
    with db_connection.cursor() as cur:
        cur.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
        status = cur.fetchone()[0]
        assert status == "completed"

def test_place_order(client):
    order_data = {
        "customer_name": "Test Customer",
        "items": "Test Item x1",
        "total_price": 100.00
    }
    response = client.post('/api/place_order', json=order_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "order_id" in data
    assert data["success"] is True