import os
from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

# ฟังก์ชันสำหรับเชื่อมต่อกับฐานข้อมูล
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="1234",
        options="-c search_path=food,public"
    )
    return conn

@app.route('/')
def index():
       return render_template('index.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/total_summary')
def total_summary():
    return render_template('Total_summary.html')

if __name__ == '__main__':
      
       app.run(debug=True)