import os
import re
import argparse
import sqlite3
from typing import TypedDict
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langgraph_agent.prompt import SYSTEM_PROMPT, HUMAN_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph_agent.review_utils import parse_feedback_to_comments, store_review_db
from dotenv import load_dotenv
import requests

# Abstract base VCS client
class VCSClient:
    def get_pull_files(self, repo_name, pr_number):
        raise NotImplementedError

    def post_comment(self, repo_name, pr_number, file_path, line, body):
        raise NotImplementedError

    def post_summary(self, repo_name, pr_number, summary):
        raise NotImplementedError

    def get_commit_sha(self, repo_name, pr_number):
        raise NotImplementedError

# GitHub-specific implementation
class GitHubClient(VCSClient):
    def __init__(self, token):
        from github import Github, UnknownObjectException
        self.client = Github(token)
        self.UnknownObjectException = UnknownObjectException

    def get_pull_files(self, repo_name, pr_number):
        repo = self.client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        self.repo = repo
        self.pr = pr
        return pr.get_files()

    def post_comment(self, repo_name, pr_number, file_path, line, body):
        try:
            commit = self.repo.get_commit(self.pr.head.sha)
            self.pr.create_review_comment(
                commit=commit,
                body=body,
                path=file_path,
                line=line,
                side="RIGHT"
            )
        except Exception as e:
            print(f"⚠️ Error posting inline comment: {e}")

    def post_summary(self, repo_name, pr_number, summary):
        try:
            self.pr.create_issue_comment(summary)
        except Exception as e:
            print(f"⚠️ Error posting summary comment: {e}")

    def get_commit_sha(self, repo_name, pr_number):
        return self.pr.head.sha

# GitLab-specific implementation
class GitLabClient(VCSClient):
    def __init__(self, token, base_url="https://gitlab.com/api/v4"):
        self.token = token
        self.base_url = base_url

    def _headers(self):
        return {"PRIVATE-TOKEN": self.token}

    def get_pull_files(self, repo_name, pr_number):
        url = f"{self.base_url}/projects/{requests.utils.quote(repo_name, safe='')}/merge_requests/{pr_number}/changes"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        changes = response.json()
        self.repo_name = repo_name
        self.pr_number = pr_number
        return [type("GitLabFile", (object,), {"filename": c["new_path"], "patch": c["diff"]}) for c in changes["changes"]]

    def post_comment(self, repo_name, pr_number, file_path, line, body):
        try:
            note_url = f"{self.base_url}/projects/{requests.utils.quote(repo_name, safe='')}/merge_requests/{pr_number}/discussions"
            data = {
                "body": body,
                "position": {
                    "position_type": "text",
                    "new_path": file_path,
                    "new_line": line
                }
            }
            requests.post(note_url, headers=self._headers(), json=data)
        except Exception as e:
            print(f"⚠️ Error posting inline comment: {e}")

    def post_summary(self, repo_name, pr_number, summary):
        try:
            url = f"{self.base_url}/projects/{requests.utils.quote(repo_name, safe='')}/merge_requests/{pr_number}/notes"
            data = {"body": summary}
            requests.post(url, headers=self._headers(), json=data)
        except Exception as e:
            print(f"⚠️ Error posting summary comment: {e}")

    def get_commit_sha(self, repo_name, pr_number):
        url = f"{self.base_url}/projects/{requests.utils.quote(repo_name, safe='')}/merge_requests/{pr_number}"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()["sha"]

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
    parser.add_argument("--vcs", default="github")
    args = parser.parse_args()

    try:
        repo_name = os.getenv("GITHUB_REPOSITORY")
        pr_number = int(os.getenv("PR_NUMBER"))
        token = os.getenv("GITHUB_TOKEN")
        if not repo_name or not token:
            raise ValueError("Missing required environment variables: GITHUB_REPOSITORY or GITHUB_TOKEN")

        if args.vcs == "github":
            vcs_client = GitHubClient(token)
        elif args.vcs == "gitlab":
            vcs_client = GitLabClient(token)
        else:
            raise ValueError("Unsupported VCS platform")

        files = vcs_client.get_pull_files(repo_name, pr_number)
        llm = ChatOpenAI(model=args.model)

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
            for c in comments:
                snippet = extract_diff_snippet(file.patch or "", c['line'])
                comment_body = f"{c['body']}\n\n{snippet}" if snippet else c['body']
                vcs_client.post_comment(repo_name, pr_number, file.filename, c['line'], comment_body)

            if args.save_db:
                store_review_db(pr_number, file.filename, comments)

        return {}

    builder = StateGraph(ReviewState)
    builder.add_node("review", RunnableLambda(review_code))
    builder.add_node("comment", RunnableLambda(post_inline_comments))
    builder.add_edge("review", "comment")
    builder.set_entry_point("review")

    app = builder.compile()

    all_summaries = []
    for file in files:
        result = app.invoke({"file": file})
        review_text = result['review_text']
        all_summaries.append(f"<details><summary>📄 {file.filename}</summary>\n\n{review_text}\n\n</details>")

    if all_summaries and not args.dry_run:
        summary_text = "\n\n".join(all_summaries)
        formatted_summary = f"## 🤖 AI Review Summary for PR #{pr_number}\n\n{summary_text}"
        vcs_client.post_summary(repo_name, pr_number, formatted_summary)

        print("\n--- AI Review Summary ---\n")
        print(formatted_summary)
