import os
import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

def get_reviews():
    db_path = os.path.join(os.path.dirname(__file__), 'reviews.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            pr INT,
            file TEXT,
            line INT,
            comment TEXT
        )
    """)

    cursor.execute("SELECT * FROM reviews ORDER BY pr DESC")
    reviews = cursor.fetchall()
    conn.close()
    return reviews

@app.route('/')
def index():
    return render_template('index.html', reviews=get_reviews())

if __name__ == '__main__':
    app.run(debug=True)
