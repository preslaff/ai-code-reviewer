# -------------------------------------------
# File: ai_code_reviewer/utils.py
# -------------------------------------------
import sqlite3

def parse_feedback_to_comments(review, file):
    comments = []
    for line in review.split('\n'):
        if "Line" in line:
            try:
                line_num = int(line.split("Line")[1].split(":")[0].strip())
                comment_body = line.split(":", 1)[1].strip()
                comments.append({"line": line_num, "body": comment_body})
            except:
                continue
    return comments

def store_review_db(pr, filename, comments):
    conn = sqlite3.connect('web_dashboard/reviews.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            pr INT, file TEXT, line INT, comment TEXT
        )
    """)
    for c in comments:
        cursor.execute("INSERT INTO reviews VALUES (?, ?, ?, ?)", (pr, filename, c["line"], c["body"]))
    conn.commit()
    conn.close()
