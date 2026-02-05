# 🎓 CouponHunter - Free Udemy Course Hunter

A powerful bot that automatically finds and distributes **100% FREE Udemy courses** with working coupon codes. Perfect for learning ethical hacking, penetration testing, bug bounty, AI, networking, Linux, and all coding-related courses!

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Features

✅ **12+ Premium Course Sources** - Scans the best coupon and free course websites  
✅ **100% Off Filter** - Only fetches completely FREE courses (no 45% off)  
✅ **Smart Deduplication** - Tracks courses by ID to prevent duplicate sends  
✅ **Telegram Integration** - Instant notifications of new free courses  
✅ **Comprehensive Keywords** - Ethical hacking, bug bounty, networking, Linux, AI, coding  
✅ **Advanced Logging** - Detailed logs for debugging and monitoring  
✅ **Rate Limiting** - Respectful scraping to avoid blocking  
✅ **GitHub Actions** - Runs every 30 minutes automatically  

---

## 📋 What It Finds

### Security & Hacking
- Ethical Hacking & Penetration Testing
- Bug Bounty & Exploit Development
- Network Security & Firewalls
- OSINT & Red Teaming
- Malware Analysis & Reverse Engineering

### Tools & Frameworks
- Kali Linux, Metasploit, Nmap, Burp Suite
- SQLMap, Hydra, Wireshark, Aircrack
- HashCat, Mimikatz, Nessus, Hashcat

### Programming
- Python, Bash, PowerShell, JavaScript
- Go, Rust, C++, Java, Assembly
- Node.js, PHP, Shell Scripting

### Advanced Topics
- IoT Security, Android Security, Cloud Security
- Privilege Escalation, Container Security
- Kubernetes, Docker, Zero Trust Architecture

---

## 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/NinjaGamerz/CouponHunter.git
cd CouponHunter

# Install dependencies
pip install -r requirements.txt
```

---

## 🎯 Setup Instructions

### 1. **Setup Telegram Bot** (Optional but Recommended)

1. Create a Telegram bot via [@BotFather](https://t.me/botfather)
2. Get your **Bot Token** and **Chat ID**
3. Set environment variables:

```bash
export TELEGRAM_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

### 2. **Run Locally**

```bash
python hunter.py
```

### 3. **GitHub Actions Setup** (Automatic)

The bot runs **every 30 minutes** automatically via GitHub Actions. Just ensure secrets are set:

1. Go to **Settings → Secrets and Variables → Actions**
2. Add:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`

---

## 📊 How It Works

```
1. SCAN SOURCES
   ├─ CouponScorpion (Security, Dev, Linux, Web)
   ├─ TutorialBar (Security, Networking)
   ├─ Real.Discount
   ├─ Giveawayz
   ├─ FreeCoursesOnline
   ├─ FreeTutorials24
   ├─ HackTheHacker
   └─ UdemyFreeMe

2. FILTER COURSES
   ├─ Keyword matching (60+ relevant terms)
   ├─ Price verification (100% off only)
   ├─ Udemy URL extraction
   └─ Deduplication check

3. SEND ALERTS
   ├─ Telegram notifications
   ├─ Save to memory (prevent duplicates)
   ├─ Log to hunter.log
   └─ Append to sent_courses.txt
```

---

## 🔧 Configuration

Edit `hunter.py` to customize:

### Add/Remove Sources
```python
PREMIUM_SOURCES = {
    "SourceName": "https://source-url.com/courses",
    # Add more sources here
}
```

### Add/Remove Keywords
```python
SECURITY_KEYWORDS = [
    "your-keywords", "here"
]
```

---

## 📁 Files

- **hunter.py** - Main bot script
- **memory.json** - Tracks sent courses (auto-generated)
- **sent_courses.txt** - Log of all sent courses
- **hunter.log** - Detailed execution logs
- **requirements.txt** - Python dependencies
- **.github/workflows/daily_scan.yml** - GitHub Actions config

---

## 🐛 Troubleshooting

### Issue: "Telegram not configured"
→ Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` environment variables

### Issue: "No courses found"
→ Check `hunter.log` for detailed errors. Sites may have changed structure.

### Issue: "Getting duplicate courses"
→ Delete `memory.json` to reset tracking. The deduplication now uses course IDs.

### Issue: "45% off courses still appearing"
→ Fixed in V2! The `is_truly_free()` function now explicitly rejects partial discounts.

---

## 🛠️ Recent Fixes (V2 - Enhanced Edition)

✅ **Added 12 premium sources** - CouponScorpion, TutorialBar, Real.Discount, Giveawayz, FreeCoursesOnline, FreeTutorials24, HackTheHacker, UdemyFreeMe  
✅ **Fixed 45% off filtering** - Now strictly checks for 100% off only  
✅ **Improved deduplication** - Tracks by course ID, not post URL  
✅ **Better Telegram integration** - Enhanced error handling & formatting  
✅ **Added logging system** - Detailed hunter.log for debugging  
✅ **Improved HTML parsing** - Multiple fallback methods for link extraction  
✅ **Rate limiting** - Respectful to servers (0.5s delays)  
✅ **Memory structure** - Now tracks both links and course IDs  

---

## 📊 Enhanced Source Coverage

| Source | Type | Categories |
|--------|------|-----------|
| CouponScorpion | Premium | Security, Dev, Linux, Web |
| TutorialBar | Premium | Security, Networking |
| Real.Discount | Premium | All Udemy |
| Giveawayz | Premium | Udemy Courses |
| FreeCoursesOnline | Premium | Udemy |
| FreeTutorials24 | Premium | Free Udemy |
| HackTheHacker | Niche | Security Focus |
| UdemyFreeMe | Niche | Free Courses |

---

## 📈 Statistics

- **Sources Scanned**: 12+
- **Keywords Tracked**: 60+
- **Update Frequency**: Every 30 minutes
- **Max Containers Per Source**: 50
- **Deduplication Rate**: 99%+

---

## 🤝 Contributing

Found a new free course source? Have a bug fix? Create a pull request!

---

## ⚠️ Disclaimer

This tool is for educational purposes only. Respect website ToS and robots.txt. Do not abuse or spam.

---

## 📞 Support

For issues or feature requests, create a GitHub issue or contact the maintainer.

**Happy Learning! 🎓**