# Security Guidelines for Cozmo Discord Bot

## 🔒 API Token Security

### ❌ NEVER DO THIS:

- Never commit real API tokens or Discord tokens to version control
- Never expose tokens in test files, even if they look fake
- Never log tokens in console output or log files
- Never share tokens in screenshots or documentation

### ✅ ALWAYS DO THIS:

- Use environment variables for all sensitive data
- Use `.env` files for local development (and add to `.gitignore`)
- Use mock/fake tokens in test files with clearly fake formats
- Rotate tokens immediately if accidentally exposed

## 🛡️ Safe Testing Practices

### Mock Token Formats

When creating test tokens, use obviously fake formats:

```python
# Good - Obviously fake
"DISCORD_TOKEN": "fake_discord_token_for_testing_only"

# Bad - Could be real (example of what NOT to do)
"DISCORD_TOKEN": "REAL_TOKEN_EXAMPLE_DO_NOT_USE_REAL_TOKENS_IN_DOCS"
```

### Environment Variables

Always use environment variables for sensitive configuration:

```python
# config.py
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")
```

### .env File Structure

```bash
# .env (never commit this file)
DISCORD_TOKEN=your_real_token_here
SPORTS_API_KEY=your_real_api_key_here
NEWS_CHANNEL_ID=123456789012345678
```

## 🚨 If Tokens Are Exposed

1. **Immediately revoke/regenerate** the exposed tokens
2. **Remove from git history** if committed:
   ```bash
   git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch path/to/file' --prune-empty --tag-name-filter cat -- --all
   ```
3. **Update all instances** where the token was used
4. **Review access logs** for any unauthorized usage

## 📋 Security Checklist

Before committing code:

- [ ] No real tokens in any files
- [ ] All sensitive data uses environment variables
- [ ] `.env` file is in `.gitignore`
- [ ] Test files use obviously fake mock data
- [ ] No tokens in log output or console prints

## 🔍 Regular Security Audits

Run these commands regularly to check for exposed secrets:

```bash
# Check for potential tokens
grep -r "DISCORD_TOKEN.*=" . --exclude-dir=.git
grep -r "[A-Za-z0-9]{50,}" . --exclude-dir=.git --exclude-dir=node_modules

# Check git history for secrets
git log --all --full-history -- .env
```

Remember: **Security is everyone's responsibility!** 🛡️
