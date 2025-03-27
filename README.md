![AI Code Review](https://github.com/preslaff/ai-code-reviewer/actions/workflows/ai_review.yml/badge.svg)

# 🤖 AI Code Reviewer

A complete AI-powered GitHub pull request reviewer using LangGraph and OpenAI.

---

## 📦 Features

- ✅ Automatically reviews PRs using GPT-4
- ✅ Flags bugs, performance issues, security risks, readability problems
- ✅ Posts a detailed AI summary comment in PR
- ✅ Run locally, with GitHub Actions, or in Docker
- ✅ Optional Flask dashboard to review AI comments
- ✅ Supports `.env`, CLI flags, dry run, model override

---

## 📁 Project Structure
```text
ai-code-reviewer/
├── .github/workflows/
│   └── ai_review.yml           # GitHub Action trigger on PRs
├── langgraph_agent/
│   ├── agent.py                # Main entrypoint for the AI reviewer
│   ├── prompt.py               # Prompt used for LLM code review
│   ├── review_utils.py         # Feedback parsing + DB save logic
│   └── requirements.txt
├── web_dashboard/
│   ├── app.py                  # Flask-based dashboard
│   ├── templates/
│   │   └── index.html
│   ├── static/
│   │   └── style.css
│   ├── reviews.db              # Review database (SQLite)
│   └── requirements.txt
├── Dockerfile
├── Makefile
├── .env                        # Environment variables (not committed)
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
Create a `.env` file in the root directory with:
```env
OPENAI_API_KEY=your_openai_key
GITHUB_TOKEN=your_token
GITHUB_REPOSITORY=owner/repo_name
PR_NUMBER=123
```

### 3. Set Up Python (Windows/Linux/macOS)
Ensure you have **Python 3.10+** and **pip** installed.

#### Option A: Using `make` (Linux/macOS/Windows with Git Bash or WSL)
```bash
make install
```

#### Option B: Manual Setup (Windows CMD/PowerShell)
```cmd
python -m venv venv
venv\Scripts\activate
pip install -e .
```
> On Linux/macOS: use `source venv/bin/activate`

### 4. Start the Flask Dashboard (Python CLI)
```bash
cd web_dashboard
python app.py
```
Then open: [http://localhost:5000](http://localhost:5000)

---

## 🚀 Usage

### 🔍 Run a Review
```bash
make run                            # Uses .env PR_NUMBER and GITHUB_REPOSITORY
ai-review --pr 42                   # Specify PR
ai-review --pr 42 --repo owner/repo # Override repository
```

### 🧪 Test in Dry Run Mode
```bash
ai-review --pr 42 --dry-run
```

### 🧠 Use a Different Model
```bash
ai-review --pr 42 --model gpt-3.5-turbo
```

### 🚫 Skip Database Storage
```bash
ai-review --pr 42 --save-db false
```

---

## 🐳 Run in Docker

### Build the Container
```bash
make docker-build
```

### Run it with `.env`
```bash
make docker-run
```

---

## 📊 Dashboard

Start the dashboard:
```bash
make dashboard
```
Or manually:
```bash
cd web_dashboard
python app.py
```
Then open: [http://localhost:5000](http://localhost:5000)

---

## 🔐 Environment Variables

You can use `.env` or CLI arguments. Required variables:
```env
OPENAI_API_KEY=...
GITHUB_TOKEN=...
GITHUB_REPOSITORY=owner/repo
PR_NUMBER=123
```

Use CLI overrides:
```bash
ai-review --repo owner/repo --pr 42
```

---

## 🙌 Contributing & License

Want to contribute? PRs welcome! Add your own agents, review types, or UI upgrades.

> MIT License • Made with ❤️ for dev productivity.

---
