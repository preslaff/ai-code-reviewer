# -------------------------------------------
# File: ai_code_reviewer/utils.py
# -------------------------------------------
import re
import sqlite3

def parse_feedback_to_comments(review, file):
    comments = []

    # Match multiple formats: "Line 12: ...", "On line 12 ...", etc.
    line_matches = re.findall(r"(?:Line|line|On line) (\d+)[^\n]*?:?\s*(.*?)(?=\n|$)", review)

    if line_matches:
        for line, body in line_matches:
            comments.append({"line": int(line), "body": body.strip()})
    return comments

def store_review_db(pr_number, filename, comments):
    conn = sqlite3.connect("web_dashboard/reviews.db")
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