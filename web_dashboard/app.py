import os
import sqlite3
from flask import Flask, render_template, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "reviews.db")

def get_reviews(pr_filter=None, file_filter=None, sort="pr_number", dir="asc", page=1, per_page=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch distinct values for filters
    cursor.execute("SELECT DISTINCT pr_number FROM reviews")
    pr_options = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT file_path FROM reviews")
    file_options = [row[0] for row in cursor.fetchall()]

    # Build base query
    query = "SELECT pr_number, file_path, line, comment FROM reviews WHERE 1=1"
    params = []

    if pr_filter:
        query += " AND pr_number = ?"
        params.append(pr_filter)
    if file_filter:
        query += " AND file_path LIKE ?"
        params.append(f"%{file_filter}%")

    # Sorting
    if sort not in {"pr_number", "file_path", "line"}:
        sort = "pr_number"
    direction = "DESC" if dir == "desc" else "ASC"
    query += f" ORDER BY {sort} {direction}"

    # Pagination
    offset = (page - 1) * per_page
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page + 1, offset])  # fetch one extra to check for next page

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    has_next = len(results) > per_page
    reviews = results[:per_page]

    return reviews, pr_options, file_options, has_next

@app.route("/")
def index():
    pr_filter = request.args.get("pr")
    file_filter = request.args.get("file")
    sort = request.args.get("sort", "pr_number")
    direction = request.args.get("dir", "asc")
    page = int(request.args.get("page", 1))

    reviews, pr_options, file_options, has_next = get_reviews(
        pr_filter, file_filter, sort, direction, page
    )

    return render_template(
        "index.html",
        reviews=reviews,
        pr_filter=pr_filter or "",
        file_filter=file_filter or "",
        pr_options=pr_options,
        file_options=file_options,
        sort=sort,
        direction=direction,
        page=page,
        has_next=has_next
    )

if __name__ == "__main__":
    app.run(debug=True)


##Just some random comments for the test