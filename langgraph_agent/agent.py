import os
import re
import argparse
import sqlite3
from typing import TypedDict
from github import Github
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langgraph_agent.prompt import SYSTEM_PROMPT, HUMAN_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph_agent.review_utils import parse_feedback_to_comments, store_review_db


class ReviewState(TypedDict):
    file: object
    review: str

def extract_diff_snippet(diff, target_line, context=3):
    lines = diff.splitlines()
    snippet = []
    found = False
    for i, line in enumerate(lines):
        if re.search(rf'^[\+\- ].*', line):
            lineno = i + 1
            if abs(lineno - target_line) <= context:
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                snippet = lines[start:end]
                found = True
                break
    if found:
        return "```diff\n" + "\n".join(snippet) + "\n```"
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--save-db", default=True)
    parser.add_argument("--model", default="gpt-4")
    args = parser.parse_args()

    repo_name = os.getenv("GITHUB_REPOSITORY")
    pr_number = int(os.getenv("PR_NUMBER"))
    token = os.getenv("GITHUB_TOKEN")

    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    llm = ChatOpenAI(model=args.model)

    def review_code(file):
        patch = file.patch or ""
        filename = file.filename
        prompt = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=HUMAN_PROMPT.format(file_name=filename, patch=patch)),
        ]
        response = llm.invoke(prompt)
        return {"file": file, "review": response.content}

    def post_inline_comments(state):
        file = state["file"]
        review = state["review"]
        comments = parse_feedback_to_comments(review, file)

        if args.dry_run:
            print(f"\n📄 Review for {file.filename}:")
            for c in comments:
                print(f"  Line {c['line']}: {c['body']}")
                snippet = extract_diff_snippet(file.patch or "", c['line'])
                if snippet:
                    print(snippet)
        else:
            commit = repo.get_commit(file.sha)
            for c in comments:
                snippet = extract_diff_snippet(file.patch or "", c['line'])
                comment_body = f"{c['body']}\n\n{snippet}" if snippet else c['body']
                pr.create_review_comment(
                    body=comment_body,
                    commit_id=commit.sha,
                    path=file.filename,
                    line=c['line'],
                    side="RIGHT",
                )

            if args.save_db:
                store_review_db(pr_number, file.filename, comments)

        return {}

    def summarize_reviews(state):
        return state["review"]

    builder = StateGraph(ReviewState)
    builder.add_node("review", RunnableLambda(review_code))
    builder.add_node("comment", RunnableLambda(post_inline_comments))
    builder.add_edge("review", "comment")
    builder.set_entry_point("review")

    app = builder.compile()

    all_summaries = []
    for file in pr.get_files():
        result = app.invoke({"file": file})
        diff_block = extract_diff_snippet(file.patch or "", 0)  # Use 0 to include entire diff context
        all_summaries.append(f"<details><summary>📄 {file.filename}</summary>\n\n{result['review']}\n\n{diff_block}</details>")

    if all_summaries and not args.dry_run:
        summary_text = "\n\n".join(all_summaries)
        formatted_summary = f"## 🤖 AI Review Summary for PR #{pr_number}\n\n{summary_text}"
        pr.create_issue_comment(formatted_summary)

        print("\n--- AI Review Summary ---\n")
        print(formatted_summary)