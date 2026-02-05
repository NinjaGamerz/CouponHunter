# 🎯 CouponHunter Setup Guide

## Part 1: Telegram Bot Setup (Required for notifications)

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Start the chat and type `/start`
3. Type `/newbot`
4. Choose a name (e.g., "Course Hunter Bot")
5. Choose a username (e.g., "CourseHunter_Bot")
6. **Copy the API Token** (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Get Your Chat ID

**Method 1: Using GetIds Bot**
1. Search for **@getidsbot** in Telegram
2. Start the chat
3. Copy the `Your user ID` (7-10 digits)

**Method 2: Send a Message to Your Bot**
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
```
Replace `<YOUR_TOKEN>` with your bot token. Look for `"id"` in the response.

### Step 3: Set Environment Variables (Local Testing)

**macOS/Linux:**
```bash
export TELEGRAM_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
export TELEGRAM_CHAT_ID="987654321"
```

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
$env:TELEGRAM_CHAT_ID="987654321"
```

### Step 4: Test the Bot

```bash
cd /workspaces/CouponHunter
pip install -r requirements.txt
python hunter.py
```

You should receive a Telegram message with a test course!

---

## Part 2: GitHub Actions Setup (Automatic Scanning)

### Step 1: Set GitHub Secrets

1. Go to your repository: **Settings → Secrets and Variables → Actions**
2. Click **"New repository secret"**
3. Add these secrets:
   - **Name**: `TELEGRAM_TOKEN` | **Value**: Your bot token
   - **Name**: `TELEGRAM_CHAT_ID` | **Value**: Your Chat ID

### Step 2: Verify Workflow

Check that `.github/workflows/daily_scan.yml` exists:

```bash
cat .github/workflows/daily_scan.yml
```

It should show it runs:
- ⏰ **Every 30 minutes** (can be changed in `cron` setting)
- 🔄 **Manually** via workflow_dispatch

### Step 3: Test the Workflow

1. Go to **Actions** tab in your repo
2. Click **"Ninja Coupon Hunter"** workflow
3. Click **"Run workflow"** → **Run workflow**
4. Wait 1-2 minutes for results
5. Check your Telegram for notifications!

---

## Part 3: Running Locally

### Quick Start

```bash
# Clone repo
git clone https://github.com/NinjaGamerz/CouponHunter.git
cd CouponHunter

# Install dependencies
pip install -r requirements.txt

# Set environment variables (macOS/Linux)
export TELEGRAM_TOKEN="your_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"

# Run the scanner
python hunter.py

# Check logs
tail -f hunter.log

# View sent courses
cat sent_courses.txt
```

### Advanced: Run in Loop

```bash
# Run every 30 minutes
while true; do
    python hunter.py
    sleep 1800
done
```

### Advanced: Using systemd (Linux)

Create `/etc/systemd/system/couponhunter.service`:

```ini
[Unit]
Description=CouponHunter - Free Udemy Course Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/CouponHunter
Environment="TELEGRAM_TOKEN=your_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
ExecStart=/usr/bin/python3 /path/to/CouponHunter/hunter.py
Restart=on-failure
RestartSec=1800

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable couponhunter
sudo systemctl start couponhunter
sudo systemctl status couponhunter
```

---

## Part 4: Docker Setup (Optional)

### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hunter.py .
COPY test_hunter.py .

ENV TELEGRAM_TOKEN=""
ENV TELEGRAM_CHAT_ID=""

CMD ["python", "hunter.py"]
```

### Build and Run

```bash
# Build image
docker build -t couponhunter:latest .

# Run container
docker run -e TELEGRAM_TOKEN="your_token" \
           -e TELEGRAM_CHAT_ID="your_chat_id" \
           couponhunter:latest

# Run in background
docker run -d --name couponhunter \
           -e TELEGRAM_TOKEN="your_token" \
           -e TELEGRAM_CHAT_ID="your_chat_id" \
           couponhunter:latest
```

---

## Part 5: Troubleshooting

### ❌ "Telegram not configured"
**Solution**: Ensure env vars are set:
```bash
echo $TELEGRAM_TOKEN
echo $TELEGRAM_CHAT_ID
```

### ❌ "No courses found"
**Solution**: Check the logs:
```bash
cat hunter.log
```
Sites may have changed HTML structure. Check if sources are still valid.

### ❌ "No new courses" (but should find some)
**Solutions**:
1. Check `memory.json` - may be full of old courses
2. Reset: `rm memory.json`
3. Check `sent_courses.txt` for history
4. Run in verbose mode (add print statements)

### ❌ "RequestException" or timeout errors
**Solution**: 
- Check internet connection
- Some sites may be slow or blocking
- Add longer timeouts in code:
```python
timeout=30  # Increase from 15
```

### ❌ Duplicate courses being sent
**Solution**:
1. Delete `memory.json`: `rm memory.json`
2. The V2 deduplication should prevent this
3. Check extracted course IDs match

---

## Part 6: Customization

### Change Scan Frequency

Edit `.github/workflows/daily_scan.yml`:
```yaml
schedule:
    - cron: '*/30 * * * *'  # Every 30 mins
    # Other options:
    # - cron: '0 * * * *'   # Hourly
    # - cron: '0 0 * * *'   # Daily
```

### Add New Sources

Edit `hunter.py`, add to `PREMIUM_SOURCES`:
```python
PREMIUM_SOURCES = {
    "MyNewSource": "https://newsite.com/free-courses/",
    # ... existing sources
}
```

### Add Keywords

Edit `hunter.py`:
```python
SECURITY_KEYWORDS.append("new-keyword")
# or add to specific category
CODING_KEYWORDS.append("rust")
```

### Change Max Containers

Edit `hunter.py`:
```python
for container in containers[:50]:  # Change 50 to desired number
```

---

## Part 7: Monitoring

### View Real-time Logs
```bash
tail -f hunter.log
```

### Check Memory Usage
```bash
cat memory.json | python -m json.tool
```

### View All Sent Courses
```bash
wc -l sent_courses.txt
cat sent_courses.txt | tail -20
```

### GitHub Actions Logs
1. Go to **Actions** tab
2. Click **Ninja Coupon Hunter**
3. Click latest run
4. Click **Run Hunter V8** step
5. View detailed logs

---

## Part 8: Performance Tips

### Optimize for Speed
```bash
# Reduce sources temporarily
# Reduce containers limit
# Increase timeouts for slow connections
```

### Optimize for Completeness
```bash
# Add more sources
# Increase max containers
# Run more frequently
```

### Monitor Resource Usage
```bash
# Check memory
ps aux | grep hunter.py

# Check disk usage
du -sh /workspaces/CouponHunter/

# Check log size
du -sh hunter.log
```

---

## Part 9: FAQ

**Q: Is this legal?**  
A: Yes! We're scraping public coupon/free course websites. No ToS violations.

**Q: Will I get blocked?**  
A: Very unlikely. We use reasonable delays and standard User-Agent headers.

**Q: Can I add Discord?**  
A: Yes! Modify `send_telegram()` to also call Discord webhook.

**Q: How many courses per day?**  
A: Depends on availability. Usually 5-15 new free courses per scan.

**Q: Is the bot lightweight?**  
A: Yes! Takes <100MB RAM, completes in seconds.

---

## 🎉 You're All Set!

Your free course hunter is now running! 

**Next Steps:**
1. ✅ Check first Telegram message
2. ✅ Let it run for 24 hours to gather data
3. ✅ Customize keywords/sources as needed
4. ✅ Enjoy free learning! 🎓

**Questions?** Open a GitHub issue or check the main README.md

---

**Last Updated**: 2026-02-05  
**Version**: V2-Enhanced
