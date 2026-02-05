#!/usr/bin/env python3
"""
CouponHunter - Fixed Version with Enhanced Scraping
Improved URL extraction, better keyword matching, and robust error handling
"""
import os
import re
import time
import json
import html
import base64
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote, parse_qs

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Optional dotenv for local testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------- Config ----------
HISTORY_FILE = "memory.json"
SENT_FILE = "sent_courses.txt"
LOG_FILE = "hunter.log"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PREMIUM_SOURCES = {
    "CouponScorpion_100": {"url": "https://couponscorpion.com/category/100-off-coupons/", "use_playwright": True},
    "RealDiscount_Udemy": {"url": "https://www.real.discount/udemy-coupon-code/", "use_playwright": False},
    "UdemyFreebies": {"url": "https://www.udemyfreebies.com/", "use_playwright": False},
    "CourseCouponClub": {"url": "https://coursecouponclub.com/", "use_playwright": True},
    "DiscUdemy": {"url": "https://www.discudemy.com/all", "use_playwright": False},
    "FreeWebinarDiscount": {"url": "https://freebiesglobal.com/", "use_playwright": False},
}

# Expanded keywords for better matching
KEYWORDS = [
    # Hacking & Security
    "hacking", "hack", "ethical hacking", "pentest", "pentesting", "penetration testing",
    "bug bounty", "cybersecurity", "cyber security", "security", "infosec", "information security",
    "red team", "blue team", "osint", "reconnaissance", "vulnerability", "exploit",
    "malware", "reverse engineering", "forensics", "incident response",
    
    # Tools & Frameworks
    "kali", "kali linux", "metasploit", "nmap", "burp suite", "burpsuite", "wireshark",
    "sqlmap", "hydra", "aircrack", "hashcat", "mimikatz", "nessus", "owasp",
    "john the ripper", "netcat", "tcpdump", "snort",
    
    # Programming & Scripting
    "python", "bash", "shell scripting", "powershell", "javascript", "go", "golang",
    "rust", "c++", "java", "assembly", "node.js", "php", "ruby", "perl",
    
    # Networking & Systems
    "networking", "network security", "firewall", "vpn", "tcp/ip", "dns", "http",
    "linux", "unix", "windows", "active directory", "ldap",
    
    # Cloud & DevOps
    "cloud security", "aws security", "azure security", "docker", "kubernetes",
    "container security", "devops", "devsecops", "ci/cd",
    
    # Web & Mobile
    "web security", "web application", "owasp top 10", "xss", "sql injection",
    "csrf", "api security", "mobile security", "android security", "ios security",
    
    # Certifications & Learning
    "ceh", "oscp", "cissp", "comptia", "security+", "ethical hacker",
    "certified ethical hacker", "offensive security",
]
KEYWORDS_SET = set(k.lower() for k in KEYWORDS)

DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

UDEMY_REGEX = re.compile(r'(https?://(?:www\.)?udemy\.com/course/[A-Za-z0-9\-\_]+(?:[/?#&][^\s"\'<>]*)?)', re.I)

PLAYWRIGHT_NAV_TIMEOUT = 45_000
PLAYWRIGHT_MAX_ARTICLES = 50

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8")]
)
log = logging.getLogger("hunter").info

# ---------- Utilities ----------
def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def setup_session():
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"sent_links": [], "sent_courses": []}
    return {"sent_links": [], "sent_courses": []}

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        log(f"❌ Error saving history: {e}")

# ---------- Telegram ----------
def send_telegram(title, link, source=""):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log("⚠️ Telegram not configured (TOKEN/CHAT_ID missing)")
        return False
    try:
        text = (
            f"<b>🔥 100% FREE UDEMY COURSE!</b>\n\n"
            f"<b>{html.escape(title)}</b>\n\n"
            f"📚 Source: {html.escape(source)}\n"
            f"🔗 <a href=\"{html.escape(link)}\">Enroll Now (Click Here)</a>\n\n"
            f"⏰ Found: {now()}"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(
            url, 
            json={
                "chat_id": TELEGRAM_CHAT_ID, 
                "text": text, 
                "parse_mode": "HTML", 
                "disable_web_page_preview": False
            }, 
            timeout=15
        )
        if resp.status_code == 200:
            log(f"✅ Telegram sent: {title[:60]}")
            return True
        else:
            log(f"❌ Telegram error ({resp.status_code}): {resp.text[:200]}")
            return False
    except Exception as e:
        log(f"❌ Telegram exception: {e}")
        return False

# ---------- Extraction ----------
def extract_udemy_urls(text):
    """Extract all Udemy course URLs from text"""
    if not text:
        return set()
    
    found = set()
    
    # Direct regex matches
    for match in UDEMY_REGEX.finditer(text):
        url = match.group(1).rstrip('"\').,; ')
        found.add(url)
    
    # Escaped URLs (\\/)
    escaped_pattern = re.compile(r'https?:\\\\/\\\\/[^\s"\'<>]*udemy\.com\\/course\\/[A-Za-z0-9\-\_]+', re.I)
    for match in escaped_pattern.finditer(text):
        url = match.group(0).replace('\\\\/', '/').replace('\\/', '/')
        found.add(url)
    
    # Decode HTML entities
    cleaned = set()
    for url in found:
        try:
            decoded = html.unescape(unquote(url))
            # Clean query parameters that might break the URL
            if '?' in decoded:
                base_url = decoded.split('?')[0]
                cleaned.add(base_url)
            cleaned.add(decoded)
        except:
            cleaned.add(url)
    
    return cleaned

def matches_keywords(title, description=""):
    """Check if title or description matches our keywords"""
    text = (title + " " + description).lower()
    
    # Check for keyword matches
    for keyword in KEYWORDS_SET:
        if keyword in text:
            return True
    
    return False

def is_free_course(title, text=""):
    """Check if the course is actually 100% free"""
    combined = (title + " " + str(text)).lower()
    
    # Positive indicators
    free_indicators = [
        "100% off", "100%off", "100 off", "100off",
        "free", "free course", "free udemy",
        "$0", "0$", "free coupon"
    ]
    
    # Negative indicators (partial discounts)
    partial_discount = ["50%", "45%", "70%", "80%", "90%", "95%"]
    
    # Check for partial discounts first (reject them)
    for partial in partial_discount:
        if partial in combined and "100%" not in combined:
            return False
    
    # Check for free indicators
    for indicator in free_indicators:
        if indicator in combined:
            return True
    
    return False

# ---------- Requests-based Scraper ----------
def scrape_requests_source(session, source_name, source_url):
    results = []
    log(f"🔍 (requests) Scanning: {source_name}")
    
    try:
        resp = session.get(source_url, timeout=15)
        resp.encoding = resp.apparent_encoding or 'utf-8'
    except Exception as e:
        log(f"   ❌ GET failed: {e}")
        return results
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Extract all Udemy URLs from the entire page
    page_udemy_urls = extract_udemy_urls(resp.text)
    log(f"   📊 Found {len(page_udemy_urls)} Udemy URLs in page source")
    
    # Find all article/post containers
    containers = []
    
    # Try multiple container selectors
    selectors = [
        'article', '.post', '.course', '.deal', '.item',
        '[class*="post"]', '[class*="course"]', '[class*="item"]',
        '.entry', '.card', '[class*="card"]'
    ]
    
    for selector in selectors:
        found = soup.select(selector)
        if found:
            containers.extend(found)
            log(f"   Found {len(found)} containers with selector: {selector}")
    
    # Remove duplicates
    containers = list({id(c): c for c in containers}.values())
    log(f"   📦 Total unique containers: {len(containers)}")
    
    # Process containers
    processed_urls = set()
    
    for container in containers[:100]:  # Limit to 100 containers
        try:
            # Get title from container
            title = ""
            title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'a'])
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Get all links in container
            links = container.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '').strip()
                if not href:
                    continue
                
                # Make absolute URL
                full_url = urljoin(source_url, href)
                
                # Check if it's a Udemy URL
                if 'udemy.com/course/' in full_url.lower():
                    if full_url not in processed_urls:
                        # Extract course title
                        link_text = link.get_text(strip=True) or title
                        container_text = container.get_text(" ", strip=True)[:500]
                        
                        # Check if relevant AND free
                        if matches_keywords(link_text, container_text) and is_free_course(link_text, container_text):
                            results.append({
                                "title": link_text[:200],
                                "link": full_url,
                                "source": source_name,
                                "post_link": source_url
                            })
                            processed_urls.add(full_url)
                            log(f"   ✅ Found: {link_text[:60]}")
                        else:
                            log(f"   ⏭️ Skipped (not relevant): {link_text[:60]}")
                
                # Check if it's a redirect/intermediate link
                elif any(x in full_url.lower() for x in ['coupon', 'deal', 'offer', 'redirect', 'go']):
                    if full_url not in processed_urls:
                        processed_urls.add(full_url)
                        # Try to follow redirect
                        try:
                            redirect_resp = session.get(full_url, timeout=10, allow_redirects=True)
                            final_url = redirect_resp.url
                            
                            if 'udemy.com/course/' in final_url.lower():
                                link_text = link.get_text(strip=True) or title
                                container_text = container.get_text(" ", strip=True)[:500]
                                
                                if matches_keywords(link_text, container_text) and is_free_course(link_text, container_text):
                                    results.append({
                                        "title": link_text[:200],
                                        "link": final_url,
                                        "source": source_name,
                                        "post_link": full_url
                                    })
                                    log(f"   ✅ Found (redirect): {link_text[:60]}")
                                else:
                                    log(f"   ⏭️ Skipped redirect (not relevant): {link_text[:60]}")
                        except:
                            pass
                        
                        time.sleep(0.1)
        except Exception as e:
            log(f"   ⚠️ Container error: {e}")
            continue
    
    # Also check page-level URLs (but validate keywords)
    for udemy_url in page_udemy_urls:
        if udemy_url not in processed_urls:
            # Extract course slug for title
            match = re.search(r'/course/([^/?#]+)', udemy_url)
            course_slug = match.group(1).replace('-', ' ').title() if match else "Udemy Course"
            
            # Check if slug contains any keywords
            if matches_keywords(course_slug, page_title):
                processed_urls.add(udemy_url)
                results.append({
                    "title": course_slug[:200],
                    "link": udemy_url,
                    "source": source_name,
                    "post_link": source_url
                })
                log(f"   ✅ Found page-level: {course_slug[:60]}")
            else:
                log(f"   ⏭️ Skipped page-level (not relevant): {course_slug[:60]}")
    
    # Deduplicate results
    unique_results = {}
    for r in results:
        if r['link'] not in unique_results:
            unique_results[r['link']] = r
    
    final_results = list(unique_results.values())
    log(f"  ✅ {len(final_results)} courses found on {source_name}")
    return final_results

# ---------- Playwright Scraper ----------
def scrape_playwright_source(session, source_name, source_url, max_articles=PLAYWRIGHT_MAX_ARTICLES):
    results = []
    
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except Exception:
        log("⚠️ Playwright not installed - skipping")
        return results
    
    log(f"🔍 (playwright) Scanning: {source_name}")
    
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=DEFAULT_HEADERS['User-Agent']
            )
            page = context.new_page()
            
            try:
                page.goto(source_url, timeout=PLAYWRIGHT_NAV_TIMEOUT, wait_until="networkidle")
            except PWTimeout:
                log(f"   ⚠️ Page load timeout, continuing anyway...")
                pass
            except Exception as e:
                log(f"   ⚠️ Page load error: {e}")
            
            # Wait a bit for dynamic content
            time.sleep(2)
            
            # Get page HTML
            html_content = page.content()
            
            # Extract Udemy URLs from page
            page_udemy_urls = extract_udemy_urls(html_content)
            log(f"   📊 Found {len(page_udemy_urls)} Udemy URLs in page")
            
            # Find all article links
            article_links = set()
            try:
                anchors = page.query_selector_all("a[href]")
                log(f"   📎 Found {len(anchors)} total links")
                
                for anchor in anchors:
                    try:
                        href = anchor.get_attribute("href")
                        if not href:
                            continue
                        
                        full_url = urljoin(source_url, href)
                        text = (anchor.inner_text() or "").lower()
                        
                        # Include links that look like course pages or have relevant keywords
                        if any(x in full_url.lower() for x in ['/course', '/coupon', '/deal', 'udemy']) or \
                           any(x in text for x in ['free', '100%', 'course', 'udemy']):
                            article_links.add(full_url)
                    except:
                        continue
                
                log(f"   📰 Candidate article links: {len(article_links)}")
            except Exception as e:
                log(f"   ⚠️ Error gathering links: {e}")
            
            # Process article links
            processed = set()
            found_urls = set()  # Track URLs to prevent duplicates
            
            for article_url in list(article_links)[:max_articles]:
                if article_url in processed:
                    continue
                processed.add(article_url)
                
                try:
                    # Check if it's already a Udemy URL
                    if 'udemy.com/course/' in article_url.lower():
                        match = re.search(r'/course/([^/?#]+)', article_url)
                        title = match.group(1).replace('-', ' ').title() if match else "Udemy Course"
                        
                        results.append({
                            "title": title,
                            "link": article_url,
                            "source": source_name,
                            "post_link": article_url
                        })
                        log(f"   ✅ Direct Udemy link: {title[:60]}")
                        continue
                    
                    # Open article page
                    article_page = context.new_page()
                    try:
                        article_page.goto(article_url, timeout=15000, wait_until="domcontentloaded")
                        time.sleep(1)
                        
                        article_html = article_page.content()
                        article_title = article_page.title() or "Course"
                        
                        # Extract Udemy URLs from article
                        article_udemy_urls = extract_udemy_urls(article_html)
                        
                        for udemy_url in article_udemy_urls:
                            # Skip if already found this URL
                            if udemy_url in found_urls:
                                continue
                            
                            # Check if course matches keywords AND is free
                            if is_free_course(article_title, article_html[:2000]):
                                # Also check the article content for keywords
                                if matches_keywords(article_title, article_html[:3000]):
                                    found_urls.add(udemy_url)
                                    results.append({
                                        "title": article_title[:200],
                                        "link": udemy_url,
                                        "source": source_name,
                                        "post_link": article_url
                                    })
                                    log(f"   ✅ Found in article: {article_title[:60]}")
                                else:
                                    log(f"   ⏭️ Skipped (not relevant): {article_title[:60]}")
                        
                        article_page.close()
                    except:
                        try:
                            article_page.close()
                        except:
                            pass
                    
                    time.sleep(0.2)
                except Exception as e:
                    log(f"   ⚠️ Article processing error: {str(e)[:100]}")
                    continue
            
            # Add page-level Udemy URLs (but validate keywords)
            for udemy_url in page_udemy_urls:
                if udemy_url not in found_urls:
                    match = re.search(r'/course/([^/?#]+)', udemy_url)
                    title = match.group(1).replace('-', ' ').title() if match else "Udemy Course"
                    
                    # Check if matches keywords
                    if matches_keywords(title, html_content[:2000]):
                        found_urls.add(udemy_url)
                        results.append({
                            "title": title,
                            "link": udemy_url,
                            "source": source_name,
                            "post_link": source_url
                        })
                        log(f"   ✅ Found page-level: {title[:60]}")
                    else:
                        log(f"   ⏭️ Skipped page-level (not relevant): {title[:60]}")
            
            page.close()
            browser.close()
            
    except Exception as e:
        log(f"   ❌ Playwright error: {e}")
    
    # Deduplicate
    unique_results = {}
    for r in results:
        if r['link'] not in unique_results:
            unique_results[r['link']] = r
    
    final_results = list(unique_results.values())
    log(f"  ✅ {len(final_results)} courses found on {source_name}")
    return final_results

# ---------- Main Scanner ----------
def start_scan():
    log("=" * 70)
    log("🚀 CouponHunter - Starting Scan")
    log("=" * 70)
    
    session = setup_session()
    history = load_history()
    sent_links = set(history.get("sent_links", []))
    sent_courses = set(history.get("sent_courses", []))
    
    all_courses = []
    new_finds = 0
    
    for name, config in PREMIUM_SOURCES.items():
        url = config.get("url")
        use_playwright = config.get("use_playwright", False)
        
        if not url:
            continue
        
        try:
            if use_playwright:
                courses = scrape_playwright_source(session, name, url)
            else:
                courses = scrape_requests_source(session, name, url)
            
            all_courses.extend(courses)
        except Exception as e:
            log(f"❌ Error scanning {name}: {e}")
        
        time.sleep(1)  # Rate limiting
    
    log(f"\n📊 Total courses found: {len(all_courses)}")
    
    # Send to Telegram
    sent_this_run = set()
    
    for course in all_courses:
        try:
            # Extract course ID
            match = re.search(r'/course/([A-Za-z0-9\-\_]+)', course['link'], re.I)
            course_id = match.group(1).lower() if match else course['link']
            
            # Check if already sent
            if course['link'] in sent_links or course_id in sent_courses or course_id in sent_this_run:
                continue
            
            # Send to Telegram
            if send_telegram(course['title'], course['link'], course.get('source', '')):
                sent_links.add(course['link'])
                sent_courses.add(course_id)
                sent_this_run.add(course_id)
                new_finds += 1
                
                # Log to file
                try:
                    with open(SENT_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{now()} | {course['link']} | {course['title']} | {course.get('source', '')}\n")
                except:
                    pass
                
                time.sleep(1)  # Don't spam Telegram
        except Exception as e:
            log(f"❌ Error processing course: {e}")
            continue
    
    # Save history
    history["sent_links"] = list(sent_links)
    history["sent_courses"] = list(sent_courses)
    save_history(history)
    
    log("=" * 70)
    log(f"🏁 Scan Complete! New courses sent: {new_finds}")
    log(f"📚 Total courses tracked: {len(sent_courses)}")
    log("=" * 70)

if __name__ == "__main__":
    start_scan()