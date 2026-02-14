#!/usr/bin/env python3
"""
CouponHunter - FIXED VERSION
All sources working: CourseFolder, CouponScorpion, iDownloadCoupon, etc.
"""
import os
import re
import time
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Telegram Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# STRICT KEYWORDS
SECURITY_KEYWORDS = [
    "hack", "hacking", "ethical hacking", "pentest", "penetration",
    "bug bounty", "cybersecurity", "security", "infosec",
    "kali", "metasploit", "nmap", "burp", "wireshark",
    "oscp", "ceh", "cissp", "comptia security",
    "exploit", "vulnerability", "malware", "forensic",
    "red team", "blue team", "ctf", "reverse engineering",
    "social engineering", "phishing", "cyber attack", "cyber defense",
    "cyber warfare", "cyber crime", "cyber law", "cyber policy",
    "cyber risk", "cyber threat", "cyber intelligence", "cyber operations",
    "bug hunter", "vulnerability researcher", "security analyst", "security engineer",
    "security consultant", "security auditor", "security manager", "security architect",
    "security administrator", "security specialist", "security officer"
]

CODING_KEYWORDS = [
    "python", "javascript", "java", "c++", "golang", "rust",
    "bash", "powershell", "programming", "coding", "software",
    "django", "flask", "react", "node", "api", "rest",
    "git", "docker", "kubernetes", "devops", "aws", "azure"
]

NETWORKING_KEYWORDS = [
    "network", "networking", "tcp/ip", "cisco", "ccna",
    "linux", "unix", "ubuntu", "server", "sysadmin",
    "firewall", "vpn", "dns", "dhcp", "cloud"
]

# EXCLUDE
EXCLUDE_KEYWORDS = [
    "capcut", "video editing", "premiere", "photoshop",
    "marketing", "business", "sales", "finance",
    "excel", "powerpoint", "office", "productivity",
    "design", "ui/ux", "figma", "music", "audio",
    "photography", "lifestyle", "fitness", "yoga"
]

ALL_KEYWORDS = SECURITY_KEYWORDS + CODING_KEYWORDS + NETWORKING_KEYWORDS

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def send_telegram(title, url, source=""):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram not configured")
        return False
    
    try:
        msg = f"🔥 FREE COURSE!\n\n{title}\n\nSource: {source}\n🔗 {url}\n\n{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10
        )
        if r.status_code == 200:
            print(f"✅ Sent: {title[:60]}")
            return True
        else:
            print(f"❌ Error: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def is_relevant_course(title, desc=""):
    """STRICT filter"""
    text = (title + " " + desc).lower()
    
    # Exclude first
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in text:
            return False
    
    # Then check if relevant
    for keyword in ALL_KEYWORDS:
        if keyword in text:
            return True
    
    return False

def extract_course_id(url):
    match = re.search(r'/course/([^/?#]+)', url)
    return match.group(1).lower() if match else None

# ========== COURSEFOLDER SCRAPER (FIXED!) ==========
def scrape_coursefolder():
    """Scrape CourseFolder - IT & Software + Development categories"""
    print("\n🔍 CourseFolder.net")
    courses = []
    
    # Target security/coding categories
    categories = [
        "https://coursefolder.net/category/IT-and-Software",
        "https://coursefolder.net/category/Development"
    ]
    
    all_course_urls = set()
    
    try:
        for cat_url in categories:
            print(f"   Scanning category: {cat_url.split('/')[-1]}")
            r = requests.get(cat_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Find course cards - look for links to course pages
            for a in soup.find_all('a', href=True):
                href = a['href']
                
                # Course page URLs are like: /dall-e-101... or dall-e-101...
                # Must be coursefolder.net domain or relative
                if 'coursefolder.net' in href or (href.startswith('/') and not href.startswith(('/category', '/live', '/about', '/blog', '/contact', '/compare', '/udemy', '/courses.php', '/faq', '/privacy', '/terms'))):
                    # Make absolute
                    if href.startswith('/'):
                        full_url = f"https://coursefolder.net{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://coursefolder.net/{href}"
                    
                    # Exclude system pages
                    if any(x in full_url for x in ['/category/', '/live', '/about', '/blog', '/contact', '.php', '/compare', '/udemy', '/faq', '/privacy', '/terms']):
                        continue
                    
                    # Must look like a course URL (no file extensions)
                    path = full_url.replace('https://coursefolder.net/', '')
                    if '.' not in path.split('/')[-1] and len(path) > 10:
                        all_course_urls.add(full_url)
        
        print(f"   Found {len(all_course_urls)} course pages to check")
        
        # Now visit each course page
        checked = 0
        for course_url in list(all_course_urls)[:80]:  # Limit to 80 for speed
            checked += 1
            if checked % 15 == 0:
                print(f"   Checked {checked}/80...")
            
            try:
                cr = requests.get(course_url, headers=HEADERS, timeout=8)
                csoup = BeautifulSoup(cr.text, 'html.parser')
                
                # Get title from h1
                title_elem = csoup.find('h1')
                title = title_elem.text.strip() if title_elem else ""
                
                # Check if relevant
                if not is_relevant_course(title):
                    continue
                
                # Find "Get Free Coupon" button - it has the Udemy link with coupon code
                coupon_link = None
                for a in csoup.find_all('a', href=True):
                    href = a['href']
                    # Look for Udemy links with couponCode parameter
                    if 'udemy.com/course' in href and 'couponCode=' in href:
                        coupon_link = href
                        break
                
                if coupon_link:
                    courses.append({
                        'title': title,
                        'url': coupon_link,
                        'source': 'CourseFolder'
                    })
                    print(f"   ✅ {title[:60]}")
                
                time.sleep(0.15)
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"   Total: {len(courses)} relevant courses")
    return courses

# ========== COUPONSCORPION ==========
def scrape_couponscorpion():
    """Scrape CouponScorpion"""
    print("\n🔍 CouponScorpion")
    courses = []
    
    try:
        r = requests.get("https://couponscorpion.com/category/100-off-coupons/", 
                        headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        post_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'couponscorpion.com' in href and any(c in href for c in ['/it-software/', '/development/', '/technology/']):
                if href not in post_links:
                    post_links.append(href)
        
        print(f"   Found {len(post_links)} pages")
        
        for post_url in post_links[:30]:
            try:
                pr = requests.get(post_url, headers=HEADERS, timeout=10)
                psoup = BeautifulSoup(pr.text, 'html.parser')
                
                title_elem = psoup.find('h1')
                title = title_elem.text.strip() if title_elem else ""
                title = title.replace('[Free]', '').replace('[100% Off]', '').strip()
                
                if not is_relevant_course(title):
                    continue
                
                udemy_link = None
                for a in psoup.find_all('a', href=True):
                    href = a['href']
                    if 'udemy.com/course/' in href:
                        udemy_link = href
                        break
                
                if udemy_link:
                    courses.append({
                        'title': title,
                        'url': udemy_link,
                        'source': 'CouponScorpion'
                    })
                    print(f"   ✅ {title[:60]}")
                
                time.sleep(0.4)
            except:
                continue
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"   Total: {len(courses)} relevant courses")
    return courses

# ========== IDOWNLOADCOUPON ==========
def scrape_idownloadcoupon():
    """Scrape iDownloadCoupon"""
    print("\n🔍 iDownloadCoupon")
    courses = []
    
    search_terms = ["hacking", "security", "python", "linux"]
    
    try:
        for term in search_terms:
            url = f"https://idownloadcoupon.com/?s={term}&post_type=product"
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                soup = BeautifulSoup(r.text, 'html.parser')
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if 'idownloadcoupon.com' in href and '/product/' in href:
                        try:
                            pr = requests.get(href, headers=HEADERS, timeout=10)
                            psoup = BeautifulSoup(pr.text, 'html.parser')
                            
                            title_elem = psoup.find('h1', class_='product_title')
                            title = title_elem.text.strip() if title_elem else ""
                            
                            if not is_relevant_course(title):
                                continue
                            
                            for link in psoup.find_all('a', href=True):
                                if 'udemy.com/course/' in link['href']:
                                    courses.append({
                                        'title': title,
                                        'url': link['href'],
                                        'source': 'iDownloadCoupon'
                                    })
                                    print(f"   ✅ {title[:60]}")
                                    break
                            
                            time.sleep(0.3)
                        except:
                            continue
                
                time.sleep(0.4)
            except:
                continue
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"   Total: {len(courses)} relevant courses")
    return courses

# ========== UDEMY24 ==========
def scrape_udemy24():
    """Scrape Udemy24"""
    print("\n🔍 Udemy24")
    courses = []
    
    try:
        r = requests.get("https://www.udemy24.com/search?q=hacking", 
                        headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        post_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'udemy24.com/2' in href:
                if href not in post_links:
                    post_links.append(href)
        
        for post_url in post_links[:20]:
            try:
                pr = requests.get(post_url, headers=HEADERS, timeout=10)
                psoup = BeautifulSoup(pr.text, 'html.parser')
                
                title_elem = psoup.find('h1') or psoup.find('title')
                title = title_elem.text.strip() if title_elem else ""
                
                if not is_relevant_course(title):
                    continue
                
                content = psoup.find('div', class_='post-body') or psoup.find('article')
                if content:
                    for a in content.find_all('a', href=True):
                        if 'udemy.com/course/' in a['href']:
                            courses.append({
                                'title': title,
                                'url': a['href'],
                                'source': 'Udemy24'
                            })
                            print(f"   ✅ {title[:60]}")
                            break
                
                time.sleep(0.4)
            except:
                continue
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"   Total: {len(courses)} relevant courses")
    return courses

# ========== REALDISCOUNT ==========
def scrape_realdiscount():
    """Scrape Real.Discount"""
    print("\n🔍 Real.Discount")
    courses = []
    
    try:
        r = requests.get("https://www.real.discount/udemy-coupon-code/", 
                        headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'udemy.com/course/' in href:
                title = a.text.strip()
                if not title:
                    cid = extract_course_id(href)
                    if cid:
                        title = cid.replace('-', ' ').title()
                    else:
                        title = "Unknown"
                
                if is_relevant_course(title):
                    courses.append({
                        'title': title,
                        'url': href,
                        'source': 'RealDiscount'
                    })
                    print(f"   ✅ {title[:60]}")
                    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"   Total: {len(courses)} relevant courses")
    return courses

# ========== MEMORY ==========
def load_sent():
    try:
        with open('memory.json', 'r') as f:
            return set(json.load(f))
    except:
        return set()

def save_sent(sent):
    with open('memory.json', 'w') as f:
        json.dump(list(sent), f, indent=2)

# ========== MAIN ==========
def main():
    print("=" * 80)
    print("🚀 CouponHunter - FIXED VERSION")
    print("   Only: Hacking | Security | Bug Bounty | Coding | Networking")
    print("=" * 80)
    
    sent_courses = load_sent()
    all_courses = []
    
    # Run all scrapers
    all_courses.extend(scrape_coursefolder())
    all_courses.extend(scrape_couponscorpion())
    all_courses.extend(scrape_idownloadcoupon())
    all_courses.extend(scrape_udemy24())
    all_courses.extend(scrape_realdiscount())
    
    print(f"\n📊 Total found: {len(all_courses)} courses")
    
    # Send new courses
    new_count = 0
    dup_count = 0
    
    for course in all_courses:
        cid = extract_course_id(course['url'])
        if not cid:
            continue
        
        if cid in sent_courses:
            dup_count += 1
            continue
        
        if send_telegram(course['title'], course['url'], course.get('source', '')):
            sent_courses.add(cid)
            new_count += 1
            time.sleep(2)
    
    save_sent(sent_courses)
    
    print("\n" + "=" * 80)
    print(f"🏁 Complete!")
    print(f"   New: {new_count} | Duplicates: {dup_count} | Total tracked: {len(sent_courses)}")
    print("=" * 80)

if __name__ == "__main__":
    main()