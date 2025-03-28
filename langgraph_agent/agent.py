import os
import re
import argparse
import sqlite3
from typing import TypedDict
from github import Github, GithubException, UnknownObjectException
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langgraph_agent.prompt import SYSTEM_PROMPT, HUMAN_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph_agent.review_utils import parse_feedback_to_comments, store_review_db
from dotenv import load_dotenv

load_dotenv()

class ReviewState(TypedDict):
    file: object
    review_text: str

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

    try:
        repo_name = os.getenv("GITHUB_REPOSITORY")
        pr_number = int(os.getenv("PR_NUMBER"))
        token = os.getenv("GITHUB_TOKEN")
        if not repo_name or not token:
            raise ValueError("Missing required environment variables: GITHUB_REPOSITORY or GITHUB_TOKEN")

        g = Github(token)
        try:
            repo = g.get_repo(repo_name)
        except UnknownObjectException:
            raise ValueError(f"Repository '{repo_name}' not found. Check GITHUB_REPOSITORY variable.")

        try:
            pr = repo.get_pull(pr_number)
        except UnknownObjectException:
            raise ValueError(f"Pull request #{pr_number} not found in repo '{repo_name}'.")

        try:
            llm = ChatOpenAI(model=args.model)
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI model: {e}")

    except Exception as e:
        print(f"❌ Initialization Error: {e}")
        return

    def review_code(state):
        file = state["file"]
        patch = file.patch or ""
        filename = file.filename
        prompt = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=HUMAN_PROMPT.format(file_name=filename, patch=patch)),
        ]
        response = llm.invoke(prompt)
        return {"file": file, "review_text": response.content}

    def post_inline_comments(state):
        file = state["file"]
        review = state["review_text"]
        comments = parse_feedback_to_comments(review, file)

        if args.dry_run:
            print(f"\n📄 Review for {file.filename}:")
            for c in comments:
                print(f"  Line {c['line']}: {c['body']}")
                snippet = extract_diff_snippet(file.patch or "", c['line'])
                if snippet:
                    print(snippet)
        else:
            commit = repo.get_commit(pr.head.sha)
            for c in comments:
                snippet = extract_diff_snippet(file.patch or "", c['line'])
                comment_body = f"{c['body']}\n\n{snippet}" if snippet else c['body']
                pr.create_review_comment(
                    commit=commit,
                    body=comment_body,
                    path=file.filename,
                    line=c['line'],
                    side="RIGHT"
                )

            if args.save_db:
                store_review_db(pr_number, file.filename, comments)

        return {}

    builder = StateGraph(ReviewState)
    builder.add_node("review", RunnableLambda(review_code))  # expects full state
    builder.add_node("comment", RunnableLambda(post_inline_comments))
    builder.add_edge("review", "comment")
    builder.set_entry_point("review")

    app = builder.compile()

    all_summaries = []
    for file in pr.get_files():
        result = app.invoke({"file": file})  # wraps state input
        review_text = result['review_text']
        all_summaries.append(f"<details><summary>📄 {file.filename}</summary>\n\n{review_text}\n\n</details>")

    if all_summaries and not args.dry_run:
        summary_text = "\n\n".join(all_summaries)
        formatted_summary = f"## 🤖 AI Review Summary for PR #{pr_number}\n\n{summary_text}"
        pr.create_issue_comment(formatted_summary)

        print("\n--- AI Review Summary ---\n")
        print(formatted_summary)
