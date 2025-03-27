# 🤖 AI Code Reviewer

A complete AI-powered GitHub pull request reviewer using LangGraph and OpenAI.

---

## 📦 Features

- ✅ Automatic inline comments on GitHub PRs
- ✅ Run locally, with GitHub Actions, or in Docker
- ✅ Flask dashboard to review AI comments
- ✅ Supports `.env`, CLI flags, dry run, model override

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

## 📁 Project Structure
```
ai-code-reviewer/
├── langgraph_agent/          # Core reviewer logic
│   ├── agent.py              # LangGraph AI agent
│   ├── utils.py              # Comment parser + DB utils
│   └── requirements.txt
├── web_dashboard/            # Flask review viewer
│   ├── app.py
│   ├── templates/index.html
│   ├── static/style.css
│   ├── requirements.txt
│   └── reviews.db
├── .github/workflows/        # GitHub Actions workflow
│   └── ai_review.yml
├── .env                      # API tokens & config
├── Dockerfile                # Container support
├── Makefile                  # Convenience commands
└── README.md
```

---

## 🙌 Contributing & License

Want to contribute? PRs welcome! Add your own agents, review types, or UI upgrades.

> MIT License • Made with ❤️ for dev productivity.

---
