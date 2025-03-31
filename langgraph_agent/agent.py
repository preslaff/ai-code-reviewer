import os
import re
import argparse
import logging
import time
from typing import TypedDict, Optional
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langgraph_agent.prompt import SYSTEM_PROMPT, HUMAN_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph_agent.review_utils import parse_feedback_to_comments, store_review_db
from dotenv import load_dotenv
import requests
from github import Github, UnknownObjectException, RateLimitExceededException, Auth

load_dotenv()

# Setup logging with environment variable support
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)


# Retry decorator for rate limiting
def retry(func, retries=3, delay=2):
    def wrapper(*args, **kwargs):
        for i in range(retries):
            try:
                return func(*args, **kwargs)
            except RateLimitExceededException as e:
                if i == retries - 1:
                    raise  # Re-raise the exception if retries are exhausted
                logger.warning(f"Rate limit exceeded, retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            except requests.exceptions.HTTPError as e:
                if i == retries - 1:
                    raise
                logger.warning(f"HTTP error, retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2

    return wrapper


# Abstract base VCS client
class VCSClient:
    """
    Interface for version control system (VCS) clients like GitHub and GitLab.
    Each method must be implemented by platform-specific subclasses.
    """

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
    """
    GitHub VCS client that interacts with pull requests using the PyGithub library.
    """

    def __init__(self, token):
        auth = Auth.Token(token)
        self.client = Github(auth=auth)  # Use auth object
        self.UnknownObjectException = UnknownObjectException
        self.RateLimitExceededException = RateLimitExceededException
        self.repo = None  # Initialize repo
        self.pr = None  # Initialize pr

    @retry
    def get_pull_files(self, repo_name, pr_number):
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            self.repo = repo
            self.pr = pr
            return pr.get_files()
        except UnknownObjectException as e:
            logger.error(f"Repository or pull request not found: {e}")
            raise

    @retry
    def post_comment(self, repo_name, pr_number, file_path, line, body):
        # This method is now unused (batched instead). Left for interface compatibility.
        logger.debug("GitHubClient.post_comment called but handled in batch mode.")

    @retry
    def post_summary(self, repo_name, pr_number, summary):
        try:
            self.pr.create_issue_comment(summary)
        except Exception as e:
            logger.warning(f"⚠️ Error posting summary comment: {e}")

    def get_commit_sha(self, repo_name, pr_number):
        return self.pr.head.sha

    @retry
    def post_inline_review(self, comments):
        commit = self.pr.head.sha
        for comment in comments:
            try:
                patch_lines = self._get_diff_lines(comment['patch'])
                position = patch_lines.get(comment['line'])
                if position:
                    self.pr.create_review_comment(
                        body=comment["body"],
                        commit_id=commit,
                        path=comment["file"],
                        position=position,
                    )
            except Exception as e:
                logger.warning(f"⚠️ Failed to post inline comment: {e}")

    def _get_diff_lines(self, patch):
        """
        Maps original line numbers to diff-relative positions.
        Needed to convert source line to GitHub 'position'.
        """
        lines = patch.splitlines()
        position = 0
        mapping = {}
        original_line = None
        added=0
        for line in lines:
            
            if line.startswith("@@"):
                match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
                if match:
                    original_line = int(match.group(1))
            position += 1#Always tracking

            if line.startswith("+"):
                if original_line is not None:
                    mapping[position] = original_line 
            
            

        return mapping


# GitLab-specific implementation
class GitLabClient(VCSClient):
    """
    GitLab VCS client that interacts with merge requests via the GitLab REST API v4.
    Uses HTTP requests directly with appropriate authentication headers.
    """

    def __init__(self, token, base_url="https://gitlab.com/api/v4"):
        self.token = token
        self.base_url = base_url
        self.repo_name = None  # Initialize repo_name
        self.pr_number = None  # Initialize pr_number

    def _headers(self):
        return {"PRIVATE-TOKEN": self.token}

    def get_pull_files(self, repo_name, pr_number):
        url = f"{self.base_url}/projects/{requests.utils.quote(repo_name, safe='')}/merge_requests/{pr_number}/changes"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        changes = response.json()
        self.repo_name = repo_name
        self.pr_number = pr_number
        return [
            type("GitLabFile", (object,), {"filename": c["new_path"], "patch": c["diff"]})
            for c in changes["changes"]
        ]

    @retry
    def post_comment(self, repo_name, pr_number, file_path, line, body):
        try:
            note_url = f"{self.base_url}/projects/{requests.utils.quote(repo_name, safe='')}/merge_requests/{pr_number}/discussions"
            data = {
                "body": body,
                "position": {
                    "position_type": "text",
                    "new_path": file_path,
                    "new_line": line,
                },
            }
            response = requests.post(note_url, headers=self._headers(), json=data)
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"⚠️ Error posting inline comment: {e}")

    @retry
    def post_summary(self, repo_name, pr_number, summary):
        try:
            url = f"{self.base_url}/projects/{requests.utils.quote(repo_name, safe='')}/merge_requests/{pr_number}/notes"
            data = {"body": summary}
            response = requests.post(url, headers=self._headers())
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"⚠️ Error posting summary comment: {e}")

    def get_commit_sha(self, repo_name, pr_number):
        url = f"{self.base_url}/projects/{requests.utils.quote(repo_name, safe='')}/merge_requests/{pr_number}"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()["sha"]


class ReviewState(TypedDict):
    file: object
    review_text: str


def extract_diff_snippet(diff, target_line, context=3):
    """
    Extracts a context-specific snippet of a unified diff around a target line.
    """
    lines = diff.splitlines()
    snippet = []
    found = False
    for i, line in enumerate(lines):
        lineno = i + 1  # Line number in the diff
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
    # Argument parsing from CLI
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--save-db", default=True)
    parser.add_argument("--model", default="gpt-4")
    parser.add_argument("--vcs", default="github")
    parser.add_argument("--skip-inline-comments", action="store_true")
    parser.add_argument("--repo")
    parser.add_argument("--token")
    parser.add_argument("--pr")
    args = parser.parse_args()

    try:
        # Initialization & validation
        repo_name = args.repo or os.getenv("REPOSITORY_ID")
        pr_number = args.pr or os.getenv("PR_NUMBER")  # Allow string PR numbers for GitLab
        token = args.token or os.getenv("REPO_TOKEN")

        if not repo_name or not token:
            raise ValueError("Missing required repo or token.")

        # Basic validation of PR number (more robust checks might be needed)
        try:
            pr_number_int = int(pr_number)
            if pr_number_int <= 0:
                raise ValueError("PR number must be a positive integer.")
        except ValueError:
            # If it's not an integer, check if it's a string that GitLab can handle
            if args.vcs == "gitlab":
                logger.info("PR Number provided as a string, assuming GitLab format.")
            else:
                raise ValueError("Invalid PR number format.")
        # Initialize VCS-specific client
        if args.vcs == "github":
            vcs_client = GitHubClient(token)
        elif args.vcs == "gitlab":
            vcs_client = GitLabClient(token)
        else:
            raise ValueError("Unsupported VCS platform")

        # Retrieve files & initialize LLM
        files = vcs_client.get_pull_files(repo_name, pr_number)
        llm = ChatOpenAI(model=args.model)

    except Exception as e:
        logger.error(f"❌ Initialization Error: {e}")
        return

    def review_code(state: ReviewState) -> ReviewState:
        """
        Sends a diff to the LLM and returns the review response.
        """
        file = state["file"]
        patch = file.patch or ""
        filename = file.filename
        prompt = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=HUMAN_PROMPT.format(file_name=filename, patch=patch)),
        ]
        response = llm.invoke(prompt)
        return {"file": file, "review_text": response.content}

    def post_inline_comments(state: ReviewState) -> dict:
        """
        Parses and posts inline comments. Optionally stores in DB.
        """
        file = state["file"]
        review = state["review_text"]
        comments = parse_feedback_to_comments(review, file)

        if args.dry_run:
            logger.info(f"\n📄 Review for {file.filename}:")
            for c in comments:
                logger.info(f"  Line {c['line']}: {c['body']}")
                snippet = extract_diff_snippet(file.patch or "", c['line'])
                if snippet:
                    logger.info(snippet)
        elif not args.skip_inline_comments:
            if isinstance(vcs_client, GitHubClient):
                batched_comments = [
                    {**c, "file": file.filename, "patch": file.patch}
                    for c in comments
                ]
                vcs_client.post_inline_review(batched_comments)
            else:
                for c in comments:
                    snippet = extract_diff_snippet(file.patch or "", c['line'])
                    comment_body = f"{c['body']}\n\n{snippet}" if snippet else c['body']
                    vcs_client.post_comment(repo_name, pr_number, file.filename, c['line'], comment_body)

        if args.save_db:
            store_review_db(pr_number, file.filename, comments)

        return {}

    # Build LangGraph workflow
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
        all_summaries.append(
            f"<details><summary>📄 {file.filename}</summary>\n\n{review_text}\n\n</details>"
        )

    if all_summaries and not args.dry_run:
        summary_text = "\n\n".join(all_summaries)
        formatted_summary = f"## 🧠 AI Review Summary for PR #{pr_number}\n\n{summary_text}"
        vcs_client.post_summary(repo_name, pr_number, formatted_summary)
        logger.info("\n--- AI Review Summary ---\n")
        logger.info(formatted_summary)


if __name__ == "__main__":
    main()