from langgraph_agent.utils import parse_feedback_to_comments, store_review_db
import os

__all__ = ["parse_feedback_to_comments", "store_review_db"]

if __name__ == "__main__":
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(__file__), "../web_dashboard/reviews.db")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pr_number INTEGER,
        file_path TEXT,
        line INTEGER,
        comment TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("✅ reviews.db initialized.")
