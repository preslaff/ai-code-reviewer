import os
import argparse
from typing import TypedDict, Optional
from dotenv import load_dotenv
from github import Github
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from .utils import parse_feedback_to_comments, store_review_db

class ReviewState(TypedDict):
    file: Optional[object]
    review: str

def main():
    parser = argparse.ArgumentParser(description="Run the AI code reviewer on a GitHub PR.")
    parser.add_argument("--pr", type=int, help="PR number (overrides .env PR_NUMBER)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print comments instead of posting them")
    parser.add_argument("--save-db", action="store_false", help="Do not save review data to the database")
    parser.add_argument("--model", type=str, default="gpt-4", help="Language model to use (default: gpt-4)")
    parser.add_argument("--repo", type=str, help="GitHub repository override in format owner/repo")
    args = parser.parse_args()

    load_dotenv()

    openai_key = os.getenv("OPENAI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = args.repo or os.getenv("GITHUB_REPOSITORY")
    pr_number = args.pr or os.getenv("PR_NUMBER")

    if not all([openai_key, github_token, repo_name, pr_number]):
        print("❌ Missing environment variables. Please check your .env file or use --pr.")
        return

    pr_number = int(pr_number)
    print(f"🔍 Running AI Code Review for PR #{pr_number} in {repo_name} using model {args.model}...")

    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    files = pr.get_files()

    llm = ChatOpenAI(model=args.model, api_key=openai_key)

    prompt = ChatPromptTemplate.from_template(
        """You're an expert AI code reviewer. Identify and explain:
- Bugs
- Security vulnerabilities
- Performance issues
- Readability and maintainability problems

Diff for {filename}:
```diff
{patch}
```

Provide concise comments with line numbers where applicable."""
    )

    def review_file(state):
        file = state["file"]
        response = llm.invoke(prompt.format(filename=file.filename, patch=file.patch)).content
        return {"review": response, "file": file}

    def post_inline_comments(state):
        file = state["file"]
        review = state["review"]
        comments = parse_feedback_to_comments(review, file)

        if args.dry_run:
            print(f"\n📄 Review for {file.filename}:")
            for c in comments:
                print(f"  Line {c['line']}: {c['body']}")
        else:
            for comment in comments:
                pr.create_review_comment(
                    body=comment["body"],
                    path=file.filename,
                    line=comment["line"],
                    commit=repo.get_commit(file.sha),
                    side="RIGHT"
                )
            if args.save_db:
                store_review_db(pr_number, file.filename, comments)
        return {}

    graph = StateGraph(ReviewState)
    graph.add_node("review_file", review_file)
    graph.add_node("post_inline_comments", post_inline_comments)
    graph.set_entry_point("review_file")
    graph.add_edge("review_file", "post_inline_comments")
    graph.add_edge("post_inline_comments", END)

    app = graph.compile()
    all_summaries = []

    for file in files:
        if file.patch:
            result = app.invoke({"file": file})
            review_text = result.get("review", "")
            all_summaries.append(f"### `{file.filename}`\n{review_text}")

    summary_text = "\n\n".join(all_summaries)
    if not args.dry_run:
        pr.create_issue_comment(f"🤖 AI Review Summary for PR #{pr_number}:\n\n{summary_text}")

    print("✅ Review complete." + (" (dry run, no comments posted)" if args.dry_run else " Comments added to PR and summary posted."))
