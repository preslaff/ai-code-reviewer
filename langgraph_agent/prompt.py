from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template(
    """
You are an expert AI code reviewer. For the given code diff, identify issues in the following categories:

1. 🐛 Bugs
2. 🔐 Security vulnerabilities
3. 🚀 Performance issues
4. 📚 Readability and maintainability problems

Provide actionable, concise feedback. Use Markdown formatting, include line numbers where possible.

Code diff for file `{filename}`:
```diff
{patch}
```

Output format:
```
### Review
- **Bug**: ...
- **Security**: ...
- **Performance**: ...
- **Readability**: ...
```
"""
)