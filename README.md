![AI Code Review](https://github.com/preslaff/ai-code-reviewer/actions/workflows/ai_review.yml/badge.svg)

# 🤖 AI Code Reviewer

A complete AI-powered pull request reviewer using LangGraph and OpenAI. Works with both GitHub and GitLab!

---

## 📦 Features

- ✅ Automatically reviews PRs using GPT-4
- ✅ Flags bugs, performance issues, security risks, readability problems
- ✅ Posts inline comments + detailed summary in PR
- ✅ Works with **GitHub Actions** and **GitLab CI**
- ✅ Local CLI support with `.env`, flags, dry-run mode
- ✅ Optional Flask dashboard for review history

---

## 📁 Project Structure
```text
ai-code-reviewer/
├── .github/workflows/
│   └── ai_review.yml           # GitHub Action trigger
├── langgraph_agent/
│   ├── agent.py                # Main AI logic + CLI
│   ├── prompt.py               # System & human prompts
│   ├── review_utils.py         # Diff parsing + DB save
│   └── requirements.txt
├── web_dashboard/
│   ├── app.py                  # Flask dashboard
│   ├── templates/
│   ├── static/
│   ├── reviews.db              # SQLite DB
│   └── requirements.txt
├── .gitlab-ci.yml              # GitLab MR trigger (CI)
├── Dockerfile
├── Makefile
├── .env                        # Local config (not committed)
├── .env.example                # Example env file
└── README.md
```

---

## 🧰 Python Setup

### 1. Clone the Repo
```bash
git clone https://github.com/your-username/ai-code-reviewer.git
cd ai-code-reviewer
```

### 2. Create `.env`
```env
OPENAI_API_KEY=your_openai_key
GITHUB_TOKEN=your_token
GITHUB_REPOSITORY=owner/repo_name
PR_NUMBER=123
```

Or just copy the template:
```bash
cp .env.example .env
```

### 3. Install Locally
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

### 4. Start Flask Dashboard
```bash
cd web_dashboard
python app.py
```
Then visit [http://localhost:5000](http://localhost:5000)

---

## 🚀 Usage

### 🔍 Review a PR Locally
```bash
ai-review --repo owner/repo --pr 42
```
Or use values from `.env`:
```bash
make run
```

### 🧪 Test in Dry Run
```bash
ai-review --pr 42 --dry-run
```

### 🤖 Choose Model
```bash
ai-review --pr 42 --model gpt-3.5-turbo
```

### 💾 Disable DB Logging
```bash
ai-review --pr 42 --save-db false
```

### 🔄 Switch Between GitHub / GitLab
```bash
ai-review --vcs github   # default
ai-review --vcs gitlab
```

> Auto-detection coming soon!

---

## 🐳 Docker

### Build
```bash
make docker-build
```

### Run
```bash
make docker-run
```

---

## ⚙️ GitHub Actions
Already configured in `.github/workflows/ai_review.yml`
Triggered on PR open/update.

Make sure to add:
- `OPENAI_API_KEY` (secret)
- `GITHUB_TOKEN` (default provided)

---

## 🦊 GitLab CI Support

Create a `.gitlab-ci.yml` like this:
```yaml
stages:
  - review

ai_code_review:
  stage: review
  image: python:3.10
  before_script:
    - python -m venv venv
    - . venv/bin/activate
    - pip install -r langgraph_agent/requirements.txt
    - pip install .
  script:
    - ai-review --vcs gitlab
  only:
    - merge_requests
  variables:
    GITHUB_REPOSITORY: $CI_PROJECT_PATH
    PR_NUMBER: $CI_MERGE_REQUEST_IID
    GITHUB_TOKEN: $GITLAB_TOKEN
    OPENAI_API_KEY: $OPENAI_API_KEY
```

> Add `GITLAB_TOKEN` and `OPENAI_API_KEY` under GitLab → Settings → CI/CD → Variables

---

## 🔐 Environment Variables

You can use `.env` or pass via CLI:
```env
OPENAI_API_KEY=...
GITHUB_TOKEN=...
GITHUB_REPOSITORY=owner/repo
PR_NUMBER=123
```

---

## 📊 Dashboard
```bash
make dashboard
# or
cd web_dashboard && python app.py
```

---

## 🙌 Contributing & License

Want to contribute? PRs welcome — add new agents, review types, dashboards, or Git provider integrations.

> MIT License • Made with ❤️ for dev productivity
