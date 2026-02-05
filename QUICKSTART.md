# 🚀 Quick Start Guide

## For Impatient People (TL;DR)

### 1️⃣ Set Telegram Bot
```bash
# Create bot at https://t.me/botfather (copy token)
# Get your Chat ID from bot response

export TELEGRAM_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="987654321"
```

### 2️⃣ Install & Run
```bash
pip install -r requirements.txt
python hunter.py
```

### 3️⃣ Check Results
```bash
tail -f hunter.log           # View logs
cat sent_courses.txt         # View all sent courses
cat memory.json              # View sent IDs
```

### 4️⃣ GitHub Actions (Auto-Run Every 30 mins)
Add these secrets to your GitHub repo:
- `TELEGRAM_TOKEN` = your bot token
- `TELEGRAM_CHAT_ID` = your chat ID

---

## What Was Fixed

| Issue | Status |
|-------|--------|
| 45% off courses | ✅ FIXED |
| Duplicate courses | ✅ FIXED |
| Limited sources (2→12) | ✅ FIXED |
| Bot not working | ✅ FIXED |
| No Telegram notifications | ✅ FIXED |
| No error logs | ✅ FIXED |

---

## File Reference

| File | Purpose |
|------|---------|
| hunter.py | Main bot (COMPLETELY REWRITTEN) |
| test_hunter.py | Unit tests (run: `python test_hunter.py`) |
| memory.json | Bot memory (auto-generated) |
| hunter.log | Detailed logs |
| sent_courses.txt | All sent course links |
| SETUP_GUIDE.md | Full setup instructions |
| FIXES_REPORT.md | Detailed technical fixes |
| ENHANCEMENT_SUMMARY.md | Complete change documentation |

---

## Kill Switch

Stop the bot:
```bash
pkill -f "python hunter.py"
```

Reset memory:
```bash
rm memory.json hunter.log
```

---

**For detailed setup**: Read [SETUP_GUIDE.md](SETUP_GUIDE.md)  
**For technical details**: Read [FIXES_REPORT.md](FIXES_REPORT.md)  
**For complete changes**: Read [ENHANCEMENT_SUMMARY.md](ENHANCEMENT_SUMMARY.md)
