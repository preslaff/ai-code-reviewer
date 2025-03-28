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

def extract_snippets_from_review(review_text: str, patch: str) -> str:
    snippets = []
    line_refs = re.findall(r"[Ll]ine (\d+)", review_text)
    for ref in set(map(int, line_refs)):
        snippet = extract_diff_snippet(patch, ref)
        if snippet:
            snippets.append(f"Line {ref}:")
            snippets.append(snippet)
    return "\n\n".join(snippets)

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
        extra_snippets = extract_snippets_from_review(review_text, file.patch or "")
        review_with_code = f"""```markdown\n{review_text}\n```\n\n{extra_snippets}"""
        all_summaries.append(f"<details><summary>📄 {file.filename}</summary>\n\n{review_with_code}\n</details>")

    if all_summaries and not args.dry_run:
        summary_text = "\n\n".join(all_summaries)
        formatted_summary = f"## 🤖 AI Review Summary for PR #{pr_number}\n\n{summary_text}"
        pr.create_issue_comment(formatted_summary)

        print("\n--- AI Review Summary ---\n")
        print(formatted_summary)