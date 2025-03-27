# -------------------------------------------
# File: web_dashboard/app.py
# -------------------------------------------
from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def index():
    conn = sqlite3.connect('web_dashboard/reviews.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews ORDER BY pr DESC")
    reviews = cursor.fetchall()
    conn.close()
    return render_template('index.html', reviews=reviews)

if __name__ == '__main__':
    app.run(debug=True)
