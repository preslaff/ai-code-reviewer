# langgraph_agent/review_utils.py

import re
import sqlite3
import os


def parse_feedback_to_comments(review, file):
    comments = []

    # Match multiple formats: "Line 12: ...", "On line 12 ...", etc.
    line_matches = re.findall(r"(?:Line|line|On line) (\d+)[^\n]*?:?\s*(.*?)(?=\n|$)", review)

    if line_matches:
        for line, body in line_matches:
            comments.append({"line": int(line), "body": body.strip()})
    return comments


def store_review_db(pr_number, filename, comments):
    DB_PATH = os.path.join(os.path.dirname(__file__), "../web_dashboard/reviews.db")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS reviews (
        pr_number INTEGER,
        file_path TEXT,
        line INTEGER,
        comment TEXT
    )
    """
    )
    for c in comments:
        cursor.execute(
            "INSERT INTO reviews (pr_number, file_path, line, comment) VALUES (?, ?, ?, ?)",
            (pr_number, filename, c["line"], c["body"]),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    DB_PATH = os.path.join(os.path.dirname(__file__), "../web_dashboard/reviews.db")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pr_number INTEGER,
        file_path TEXT,
        line INTEGER,
        comment TEXT
    )
    """
    )
    conn.commit()
    conn.close()
    print("✅ reviews.db initialized.")