#!/usr/bin/env python3
"""
CouponHunter - Multi-Site Scraper
Works with: CouponScorpion, iDownloadCoupon, Udemy24, Discudemy, Real.Discount
"""
import os
import re
import time
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

KEYWORDS = [
    "hack", "hacking", "ethical", "pentest", "penetration", "security", "cyber",
    "bug bounty", "kali", "metasploit", "nmap", "burp", "wireshark", "python",
    "bash", "linux", "network", "web security", "sql injection", "xss", "oscp",
    "ceh", "exploit", "vulnerability", "malware", "forensic", "osint", "red team",
    "blue team", "ctf", "reverse engineering", "cybersecurity", "offensive security",
    "course", "training", "learning", "tutorial", "programming", "development"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ============= TELEGRAM =============
def send_telegram(title, url):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"⚠️  Telegram not configured")
        return False
    
    try:
        msg = f"🔥 100% FREE UDEMY COURSE!\n\n{title}\n\n🔗 {url}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10
        )
        if r.status_code == 200:
            print(f"✅ Sent: {title[:50]}")
            return True
        else:
            print(f"❌ Telegram error: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

# ============= HELPERS =============
def matches_keywords(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)

def extract_course_id(url):
    """Extract course ID from Udemy URL"""
    match = re.search(r'/course/([^/?#]+)', url)
    return match.group(1).lower() if match else None

def get_course_title_from_slug(slug):
    """Convert URL slug to readable title"""
    return slug.replace('-', ' ').replace('_', ' ').title()

def is_udemy_url(url):
    """Check if URL is a Udemy course link"""
    return bool(url and 'udemy.com/course/' in url.lower())

# ============= SITE-SPECIFIC SCRAPERS =============

def scrape_couponscorpion():
    """Scrape CouponScorpion - visits intermediate pages to get Udemy links"""
    print("\n🔍 Scanning: CouponScorpion")
    courses = []
    
    try:
        url = "https://couponscorpion.com/category/100-off-coupons/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find all course post links
        post_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'couponscorpion.com' in href and any(cat in href for cat in ['/it-software/', '/business/', '/development/']):
                if href not in post_links:
                    post_links.append(href)
        
        print(f"   Found {len(post_links)} course pages to check")

        # Visit each course page to extract Udemy link
        for post_url in post_links[:60]:  # Limit to 60 to get more courses
            try:
                pr = requests.get(post_url, headers=HEADERS, timeout=10)
                psoup = BeautifulSoup(pr.text, 'html.parser')
                
                # Get title from page
                title_elem = psoup.find('h1')
                title = title_elem.text.strip() if title_elem else "Unknown Course"
                title = title.replace('[Free]', '').replace('[100% Off]', '').strip()
                
                # Find the "FREE COURSE" button/link
                udemy_link = None
                for a in psoup.find_all('a', href=True):
                    href = a['href']
                    # Check for direct Udemy link
                    if 'udemy.com/course/' in href:
                        udemy_link = href
                        break
                    # Check for redirect scripts (common pattern)
                    if 'scripts/udemy/out.php' in href or 'go=' in href:
                        # Follow redirect
                        try:
                            redirect_url = urljoin(post_url, href)
                            rr = requests.get(redirect_url, headers=HEADERS, timeout=10, allow_redirects=True)
                            if 'udemy.com/course/' in rr.url:
                                udemy_link = rr.url
                                break
                        except:
                            continue
                
                if udemy_link and matches_keywords(title):
                    courses.append({'title': title, 'url': udemy_link})
                    print(f"   ✅ {title[:50]}")
                
                time.sleep(0.5)
            except Exception as e:
                print(f"   ⚠️  Error on {post_url}: {e}")
                continue
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return courses

def scrape_idownloadcoupon():
    """Scrape iDownloadCoupon"""
    print("\n🔍 Scanning: iDownloadCoupon")
    courses = []
    search_terms = ["hacking", "security", "python", "linux", "cybersecurity"]

    try:
        for search_term in search_terms:
            url = f"https://idownloadcoupon.com/?s={search_term}&post_type=product"
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')

            # Find product links
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'idownloadcoupon.com' in href and '/product/' in href:
                    try:
                        # Visit product page
                        pr = requests.get(href, headers=HEADERS, timeout=10)
                        psoup = BeautifulSoup(pr.text, 'html.parser')

                        # Get title
                        title_elem = psoup.find('h1', class_='product_title')
                        title = title_elem.text.strip() if title_elem else "Unknown"

                        # Find Udemy link
                        for link in psoup.find_all('a', href=True):
                            if 'udemy.com/course/' in link['href']:
                                if matches_keywords(title) and link['href'] not in [c['url'] for c in courses]:
                                    courses.append({'title': title, 'url': link['href']})
                                    print(f"   ✅ {title[:50]}")
                                break

                        time.sleep(0.3)
                    except:
                        continue

            time.sleep(1)

    except Exception as e:
        print(f"   ❌ Error: {e}")

    return courses

def scrape_udemy24():
    """Scrape Udemy24"""
    print("\n🔍 Scanning: Udemy24")
    courses = []
    search_terms = ["hacking", "security", "python", "linux", "ethical"]

    try:
        for search_term in search_terms:
            # Search page
            url = f"https://www.udemy24.com/search?q={search_term}"
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')

            # Find blog post links
            post_links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'udemy24.com/2' in href:  # Blog posts are dated like /2025/11/...
                    if href not in post_links:
                        post_links.append(href)

            # Visit each post
            for post_url in post_links[:50]:
                try:
                    pr = requests.get(post_url, headers=HEADERS, timeout=10)
                    psoup = BeautifulSoup(pr.text, 'html.parser')

                    # Get title
                    title_elem = psoup.find('h1') or psoup.find('title')
                    title = title_elem.text.strip() if title_elem else "Unknown"

                    # Find Udemy link in post content
                    content = psoup.find('div', class_='post-body') or psoup.find('article')
                    if content:
                        for a in content.find_all('a', href=True):
                            if 'udemy.com/course/' in a['href']:
                                if matches_keywords(title) and a['href'] not in [c['url'] for c in courses]:
                                    courses.append({'title': title, 'url': a['href']})
                                    print(f"   ✅ {title[:50]}")
                                break

                    time.sleep(0.3)
                except:
                    continue

            time.sleep(1)

    except Exception as e:
        print(f"   ❌ Error: {e}")

    return courses

def scrape_discudemy():
    """Scrape Discudemy"""
    print("\n🔍 Scanning: Discudemy")
    courses = []

    try:
        url = "https://www.discudemy.com/all"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find course cards
        for card in soup.find_all('div', class_='card'):
            try:
                title_elem = card.find('h3') or card.find('a')
                title = title_elem.text.strip() if title_elem else "Unknown"

                # Find the "Go to Course" button
                for a in card.find_all('a', href=True):
                    href = a['href']
                    if 'discudemy.com/go/' in href or 'out.php' in href:
                        # Follow redirect
                        try:
                            rr = requests.get(href, headers=HEADERS, timeout=10, allow_redirects=True)
                            if 'udemy.com/course/' in rr.url:
                                if matches_keywords(title) and rr.url not in [c['url'] for c in courses]:
                                    courses.append({'title': title, 'url': rr.url})
                                    print(f"   ✅ {title[:50]}")
                                break
                        except:
                            continue

                time.sleep(0.2)
            except:
                continue

    except Exception as e:
        print(f"   ❌ Error: {e}")

    return courses

def scrape_realdiscount():
    """Scrape Real.Discount"""
    print("\n🔍 Scanning: Real.Discount")
    courses = []

    try:
        url = "https://www.real.discount/udemy-coupon-code/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find all Udemy links directly
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'udemy.com/course/' in href:
                title = a.text.strip() or get_course_title_from_slug(extract_course_id(href) or "course")
                if matches_keywords(title) and href not in [c['url'] for c in courses]:
                    courses.append({'title': title, 'url': href})
                    print(f"   ✅ {title[:50]}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    return courses

# ============= MEMORY =============
def load_sent():
    try:
        with open('memory.json', 'r') as f:
            return set(json.load(f))
    except:
        return set()

def save_sent(sent):
    with open('memory.json', 'w') as f:
        json.dump(list(sent), f, indent=2)

# ============= MAIN =============
def main():
    print("="*70)
    print("🚀 CouponHunter - Multi-Site Scraper")
    print("="*70)
    
    sent_courses = load_sent()
    all_courses = []
    
    # Run all scrapers
    all_courses.extend(scrape_couponscorpion())
    all_courses.extend(scrape_idownloadcoupon())
    all_courses.extend(scrape_udemy24())
    all_courses.extend(scrape_discudemy())
    all_courses.extend(scrape_realdiscount())
    
    # Send new courses
    new_count = 0
    for course in all_courses:
        course_id = extract_course_id(course['url'])
        if not course_id:
            continue

        if course_id in sent_courses:
            print(f"⏭️  Duplicate: {course['title'][:50]}")
            continue

        send_telegram(course['title'], course['url'])
        sent_courses.add(course_id)
        new_count += 1
        time.sleep(2)

    save_sent(sent_courses)
    
    print("\n" + "="*70)
    print(f"🏁 Done! New courses: {new_count} | Total tracked: {len(sent_courses)}")
    print("="*70)

if __name__ == "__main__":
    main()