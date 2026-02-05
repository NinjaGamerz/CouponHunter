#!/usr/bin/env python3
import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

KEYWORDS = [
    "hack", "hacking", "ethical", "pentest", "penetration", "security", "cyber",
    "bug bounty", "kali", "metasploit", "nmap", "burp", "wireshark", "python",
    "bash", "linux", "network", "web security", "sql injection", "xss", "oscp",
    "ceh", "exploit", "vulnerability", "malware", "forensic", "osint", "red team",
    "blue team", "ctf", "reverse engineering", "binary", "assembly", "ida",
    "ghidra", "docker", "kubernetes", "aws", "cloud security", "api", "rest",
    "javascript", "node", "react", "go", "golang", "rust", "java", "c++",
    "programming", "coding", "developer", "software", "web development",
    "database", "sql", "mongodb", "postgresql", "devops", "git", "github"
]

SOURCES = [
    "https://www.real.discount/udemy-coupon-code/",
    "https://www.discudemy.com/all",
    "https://www.udemyfreebies.com/",
    "https://freebiesglobal.com/",
]

def send_telegram(title, url):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"⚠️  No Telegram config")
        return
    
    try:
        msg = f"🔥 100% FREE UDEMY COURSE!\n\n{title}\n\n🔗 {url}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10
        )
        print(f"✅ Sent: {title[:60]}")
    except:
        pass

def matches_keywords(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)

def get_udemy_links(url):
    """Extract all Udemy course links from a page"""
    links = set()
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Method 1: Find direct Udemy links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'udemy.com/course/' in href:
                links.add(href)
        
        # Method 2: Regex search entire page
        udemy_pattern = r'https?://(?:www\.)?udemy\.com/course/[A-Za-z0-9\-_]+'
        for match in re.findall(udemy_pattern, r.text):
            links.add(match)
        
        # Method 3: Check all links and follow redirects
        for a in soup.find_all('a', href=True):
            href = a['href']
            # If link looks like a coupon/deal link
            if any(x in href.lower() for x in ['coupon', 'deal', 'go', 'redirect', 'offer']):
                try:
                    # Make absolute URL
                    if href.startswith('http'):
                        full_url = href
                    elif href.startswith('/'):
                        from urllib.parse import urljoin
                        full_url = urljoin(url, href)
                    else:
                        continue
                    
                    # Follow redirect
                    rr = requests.get(full_url, headers=headers, timeout=10, allow_redirects=True)
                    if 'udemy.com/course/' in rr.url:
                        links.add(rr.url)
                    
                    # Also check body
                    for match in re.findall(udemy_pattern, rr.text):
                        links.add(match)
                    
                    time.sleep(0.1)
                except:
                    continue
        
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
    
    return links

def get_course_title(udemy_url):
    """Extract course slug from URL and make it readable"""
    match = re.search(r'/course/([^/?#]+)', udemy_url)
    if match:
        slug = match.group(1)
        # Convert slug to title
        title = slug.replace('-', ' ').replace('_', ' ').title()
        return title
    return "Udemy Course"

def load_sent():
    try:
        with open('memory.json', 'r') as f:
            return set(json.load(f))
    except:
        return set()

def save_sent(sent):
    with open('memory.json', 'w') as f:
        json.dump(list(sent), f)

def main():
    print("="*70)
    print("🚀 CouponHunter - Finding FREE Courses")
    print("="*70)
    
    sent_courses = load_sent()
    new_count = 0
    
    for source_url in SOURCES:
        print(f"\n🔍 Scanning: {source_url}")
        
        try:
            udemy_links = get_udemy_links(source_url)
            print(f"   📦 Found {len(udemy_links)} Udemy links")
            
            for link in udemy_links:
                # Extract course ID
                match = re.search(r'/course/([^/?#]+)', link)
                if not match:
                    continue
                
                course_id = match.group(1).lower()
                
                # Skip if already sent
                if course_id in sent_courses:
                    continue
                
                # Get title
                title = get_course_title(link)
                
                # Check if matches keywords
                if matches_keywords(title):
                    print(f"   ✅ Match: {title[:60]}")
                    send_telegram(title, link)
                    sent_courses.add(course_id)
                    new_count += 1
                    time.sleep(1)
                else:
                    print(f"   ⏭️  Skip: {title[:60]}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(2)
    
    save_sent(sent_courses)
    
    print("\n" + "="*70)
    print(f"🏁 Done! New courses sent: {new_count}")
    print(f"📚 Total tracked: {len(sent_courses)}")
    print("="*70)

if __name__ == "__main__":
    main()