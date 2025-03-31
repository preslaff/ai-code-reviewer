import pytest
from unittest.mock import MagicMock
from langgraph_agent.review_utils import parse_feedback_to_comments
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langgraph_agent.agent import GitHubClient, extract_diff_snippet
import logging
import re


# Configure logging to capture output during tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Test GitHubClient._get_diff_lines ---

def test_get_diff_lines_simple_addition():
    patch = """--- a/file.py
+++ b/file.py
@@ -1,2 +1,3 @@
 def hello():
+    print("hello")
        return "world"
"""
    github_client = GitHubClient(token="dummy_token")
    result = github_client._get_diff_lines(patch)
    assert result == {3: 3}  # Line 2 in the original file is now position 3


def test_get_diff_lines_modified_line():
    patch = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
 def hello():
-    return "world"
+    return "new world"
"""
    github_client = GitHubClient(token="dummy_token")
    result = github_client._get_diff_lines(patch)
    assert result == {}  # No lines added


def test_get_diff_lines_with_context():
    patch = """--- a/file.py
+++ b/file.py
@@ -1,5 +1,5 @@
 def hello():
        x = 1
+    x = 2
         return "world"

 def goodbye():"""
    github_client = GitHubClient(token="dummy_token")
    result = github_client._get_diff_lines(patch)
    assert result == {}

def test_get_diff_lines_multiple_additions():
    patch = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,5 @@
 def hello():
+    print("hello")
        print("world")
        return "end"
"""
    github_client = GitHubClient(token="dummy_token")
    result = github_client._get_diff_lines(patch)
    assert result == {5: 3}

def test_get_diff_lines_complex():
    patch = """--- a/file.py
+++ b/file.py
@@ -1,7 +1,8 @@
 def hello():
       x = 1
-    return "world"
+    print("Hello")
       return "new world"

 def goodbye():
+    print("Goodbye")
        return "see ya"
"""
    github_client = GitHubClient(token="dummy_token")
    result = github_client._get_diff_lines(patch)
    assert result == {7: 4}

def test_get_diff_lines_no_changes():
    patch = """--- a/file.py
+++ b/file.py
@@ -1,2 +1,2 @@
 def hello():
-    return "world"
+    return "world"
"""
    github_client = GitHubClient(token="dummy_token")
    result = github_client._get_diff_lines(patch)
    assert result == {} # No Added Lines

# --- Test extract_diff_snippet ---

def test_extract_diff_snippet_found():
    diff = """line1
line2
+line3
line4
-line5
line6"""
    snippet = extract_diff_snippet(diff, 3, context=1)
    assert "+line3" in snippet
    assert snippet != ""

def test_extract_diff_snippet_not_found():
    diff = """line1
line2
+line3
line4
-line5
line6"""
    snippet = extract_diff_snippet(diff, 10, context=1)  # Target line outside
    assert snippet == ""

def test_extract_diff_snippet_context():
    diff = """line1
line2
+line3
line4
-line5
line6
line7
line8"""
    snippet = extract_diff_snippet(diff, 3, context=2)
    assert "+line3" in snippet
    assert "-line5" not in snippet
    assert snippet != ""

def test_extract_diff_snippet_start_of_diff():
    diff = """+line1
line2
line3"""
    snippet = extract_diff_snippet(diff, 1, context=1)
    assert "+line1" in snippet
    assert snippet != ""

def test_extract_diff_snippet_end_of_diff():
    diff = """line1
line2
line3
-line4"""
    snippet = extract_diff_snippet(diff, 4, context=1)
    assert "-line4" in snippet
    assert snippet != ""