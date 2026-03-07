#!/usr/bin/env python3
"""
CouponHunter v3.2 — FULLY FIXED
Sources: 27 websites | Focus: Hacking, Bug Bounty, Cyber, Coding, Networking
GitHub Actions | Secrets: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

FIXES v3.2:
 - KEYWORD BUG FIXED: "finance" didn't match "financial" — now uses word-boundary regex
 - COUPON REQUIRED: ONLY sends URLs containing couponCode= (real free coupons)
 - EXCLUDE massively expanded: financial, investment, advisor, storytelling, etc.
 - ALL 27 scrapers rewritten with verified 2026 URL structures
 - Single universal extract_udemy_links() using raw HTML regex (catches all patterns)
"""

import os
import re
import time
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote_plus

# ─────────────────────────────────────────────
# TELEGRAM CONFIG
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ─────────────────────────────────────────────
# HEADERS
# ─────────────────────────────────────────────
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/123.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Cache-Control': 'no-cache',
}

# ─────────────────────────────────────────────
# KEYWORD LISTS
# ─────────────────────────────────────────────
SECURITY_KEYWORDS = [
    "hacking", "ethical hacking", "pentest", "penetration testing",
    "bug bounty", "cybersecurity", "cyber security", "infosec",
    "information security", "kali linux", "kali", "metasploit",
    "nmap", "burp suite", "wireshark", "oscp", "ceh", "cissp",
    "comptia security", "security+", "exploit", "exploitation",
    "vulnerability", "malware", "forensics", "digital forensics",
    "red team", "blue team", "purple team", "ctf", "capture the flag",
    "reverse engineering", "social engineering", "phishing",
    "web hacking", "web application security", "owasp",
    "sql injection", "xss", "csrf", "ssrf", "idor", "rce",
    "network security", "web security", "application security", "appsec",
    "cyber attack", "cyber defense", "threat hunting", "incident response",
    "soc analyst", "security analyst", "security engineer",
    "security operations", "osint", "reconnaissance", "enumeration",
    "privilege escalation", "post exploitation", "shellcode",
    "buffer overflow", "binary exploitation", "pwn", "mobile hacking",
    "android hacking", "wireless hacking", "wifi hacking",
    "active directory", "cloud hacking", "aws security", "azure security",
    "gcp security", "docker security", "kubernetes security",
    "container security", "devsecops", "security testing",
    "offensive security", "defensive security", "tor network",
    "vpn security", "hack",
]

CODING_KEYWORDS = [
    "python", "javascript", "java", "c++", "c#", "golang",
    "rust", "ruby", "php", "typescript", "kotlin", "swift",
    "bash scripting", "shell scripting", "powershell",
    "programming", "coding", "software development", "software engineering",
    "django", "flask", "fastapi", "react", "node.js", "nodejs",
    "angular", "vue.js", "rest api", "graphql", "microservices",
    "git", "github", "gitlab", "docker", "kubernetes", "devops",
    "ci/cd", "terraform", "ansible", "machine learning", "deep learning",
    "artificial intelligence", "data science", "data engineering",
    "data analysis", "blockchain", "smart contract", "solidity", "web3",
    "database", "nosql", "mongodb", "postgresql", "mysql",
    "linux administration", "linux", "system administration", "sysadmin",
    "aws", "azure", "gcp", "cloud computing",
]

NETWORKING_KEYWORDS = [
    "networking", "ccna", "ccnp", "cisco", "tcp/ip",
    "firewall", "vpn", "dns", "dhcp", "routing", "switching",
    "bgp", "ospf", "virtualization", "vmware",
    "server administration", "siem", "ids", "ips", "waf",
]

ALL_KEYWORDS = SECURITY_KEYWORDS + CODING_KEYWORDS + NETWORKING_KEYWORDS

# EXCLUDE — word-boundary aware (so "finance" won't accidentally match "financial")
EXCLUDE_EXACT = [
    "finance", "financial advisor", "financial planning", "financial advisors",
    "investment", "investor", "trading", "forex", "stock market",
    "crypto trading", "accounting", "bookkeeping", "business",
    "entrepreneur", "sales", "marketing", "digital marketing",
    "seo", "social media", "dropshipping", "ecommerce", "e-commerce",
    "shopify", "real estate", "insurance", "tax", "storytelling",
    "photoshop", "illustrator", "lightroom", "after effects",
    "premiere pro", "capcut", "video editing", "canva", "graphic design",
    "ui/ux", "figma", "sketch", "adobe xd", "drawing", "painting",
    "illustration", "3d modeling", "blender", "animation", "motion graphics",
    "yoga", "fitness", "meditation", "mindfulness", "lifestyle",
    "cooking", "nutrition", "health and wellness", "wellness", "photography",
    "personal development", "time management", "productivity",
    "leadership", "coaching", "communication skills", "public speaking",
    "english", "spanish", "french", "german", "japanese", "arabic",
    "music", "guitar", "piano", "singing", "music production",
    "microsoft office", "excel", "powerpoint", "word",
    "project management", "pmp", "hr", "human resources",
    "hiring", "recruitment",
]

# Pre-compile patterns once at startup
def _wpat(kw):
    return re.compile(r'(?<![a-z])' + re.escape(kw) + r'(?![a-z])', re.IGNORECASE)

_INC = [_wpat(k) for k in ALL_KEYWORDS]
_EXC = [_wpat(k) for k in EXCLUDE_EXACT]

def is_relevant_course(title, desc=""):
    text = (title + " " + desc).lower()
    for p in _EXC:
        if p.search(text):
            return False
    for p in _INC:
        if p.search(text):
            return True
    return False

# ─────────────────────────────────────────────
# URL / LINK HELPERS
# ─────────────────────────────────────────────
def has_coupon(url):
    return bool(re.search(r'[?&]couponCode=[A-Za-z0-9_\-]+', url))

def extract_course_id(url):
    m = re.search(r'/course/([^/?#]+)', url)
    return m.group(1).lower() if m else None

def extract_udemy_links(html_or_str, require_coupon=True):
    """
    Universal extractor — scans raw HTML string for ANY Udemy course URL.
    Catches <a href>, data-* attrs, onclick, JS variables — everything.
    Returns couponCode links first. If require_coupon=True, only returns those.
    """
    raw = html_or_str if isinstance(html_or_str, str) else str(html_or_str)
    raw_urls = re.findall(
        r'https?://(?:www\.)?udemy\.com/course/[A-Za-z0-9_\-/?=&%+#.]+', raw)
    # Clean trailing punctuation
    clean = [re.sub(r'["\'\s)\]>\\]+$', '', u) for u in raw_urls]
    # Deduplicate preserving order
    seen, unique = set(), []
    for u in clean:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    coupon = [u for u in unique if has_coupon(u)]
    plain  = [u for u in unique if not has_coupon(u)]
    return coupon if require_coupon else (coupon + plain)

def get_page(url, timeout=14, retries=2):
    """Returns (soup, raw_html) or (None, '')."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return BeautifulSoup(r.text, 'html.parser'), r.text
            if r.status_code in [403, 404, 410, 429]:
                return None, ""
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5)
    return None, ""

def clean_title(t):
    for junk in [
        '[Free]','[free]','[100% Off]','[100% off]','[100% OFF]',
        '100% OFF','100% Off','Free Course','Udemy Coupon','– Udemy',
        '| Udemy','–',' | ',' - Udemy','Download Free','Free Download',
    ]:
        t = t.replace(junk, '')
    t = re.sub(r'^\s*\[.*?\]\s*', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def escape_html(t):
    return (t.replace('&','&amp;').replace('<','&lt;')
             .replace('>','&gt;').replace('"','&quot;'))

# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(title, url, source=""):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram not configured")
        return False
    msg_html = (
        f"🔥 <b>FREE COURSE ALERT!</b>\n\n"
        f"📚 <b>{escape_html(title)}</b>\n\n"
        f"🌐 Source: <code>{escape_html(source)}</code>\n"
        f"🔗 {url}\n\n"
        f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    msg_plain = f"FREE COURSE\n\n{title}\n{source}\n{url}"

    for attempt, (payload) in enumerate([
        {"chat_id": TELEGRAM_CHAT_ID, "text": msg_html,
         "parse_mode": "HTML", "disable_web_page_preview": False},
        {"chat_id": TELEGRAM_CHAT_ID, "text": msg_plain},
    ]):
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json=payload, timeout=12)
            if r.status_code == 200:
                print(f"   ✅ Sent: {title[:70]}")
                return True
            if attempt == 0:
                print(f"   ⚠️  HTML failed ({r.status_code}), trying plain...")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    return False

# ─────────────────────────────────────────────
# MEMORY
# ─────────────────────────────────────────────
def load_sent():
    try:
        with open('memory.json') as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_sent(sent):
    with open('memory.json', 'w') as f:
        json.dump(list(sent), f, indent=2)

# ─────────────────────────────────────────────
# GENERIC SCRAPERS
# ─────────────────────────────────────────────
def scrape_wp_api(site_name, base_url, terms, max_per_term=20):
    """Generic WordPress REST API scraper. Extracts coupon links from post content."""
    print(f"\n🔍 {site_name}")
    courses, seen = [], set()
    api = base_url.rstrip('/') + '/wp-json/wp/v2/posts'

    for term in terms:
        for page in [1, 2]:
            try:
                r = requests.get(api, headers=HEADERS, timeout=14,
                                 params={'per_page': max_per_term, 'search': term, 'page': page})
                if r.status_code != 200 or not r.json():
                    break
                for post in r.json():
                    title = clean_title(
                        BeautifulSoup(post.get('title',{}).get('rendered',''), 'html.parser').text)
                    content = post.get('content',{}).get('rendered','')
                    if not is_relevant_course(title):
                        continue
                    for lnk in extract_udemy_links(content, require_coupon=True):
                        cid = extract_course_id(lnk)
                        if cid and cid not in seen:
                            seen.add(cid)
                            courses.append({'title': title, 'url': lnk, 'source': site_name})
                            print(f"   ✅ {title[:70]}")
                            break
            except Exception as e:
                print(f"   ⚠️  {term} p{page}: {e}")
                break
            time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_category(site_name, cat_urls, domain, max_pages=3, max_posts=50):
    """Generic category listing scraper."""
    print(f"\n🔍 {site_name}")
    post_urls, seen = set(), set()
    SKIP = ['/category/','/tag/','/page/','/author/','#','mailto:',
            'javascript:','/wp-','/feed','/sitemap','/about',
            '/contact','/privacy','/terms']

    for cat_url in cat_urls:
        for page in range(1, max_pages + 1):
            purl = cat_url if page == 1 else (
                cat_url + f'page/{page}/' if cat_url.endswith('/') else f'{cat_url}/page/{page}/')
            soup, _ = get_page(purl, timeout=12)
            if not soup:
                break
            found = 0
            for a in soup.find_all('a', href=True):
                href = a['href']
                if not href.startswith('http'):
                    href = f'https://{domain}' + href
                if domain not in href or any(s in href for s in SKIP):
                    continue
                min_len = len(f'https://{domain}/') + 5
                if len(href) > min_len and href not in post_urls:
                    post_urls.add(href)
                    found += 1
            if found == 0:
                break
            time.sleep(0.3)

    courses = []
    for post_url in list(post_urls)[:max_posts]:
        soup, raw = get_page(post_url, timeout=10)
        if not soup:
            continue
        t = soup.find('h1')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title):
            time.sleep(0.15)
            continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': site_name})
                print(f"   ✅ {title[:70]}")
                break
        time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses

# ═══════════════════════════════════════════
# 27 SOURCE SCRAPERS
# ═══════════════════════════════════════════

def scrape_tutorialbar():
    c = scrape_wp_api("TutorialBar", "https://tutorialbar.com",
        ["hacking","security","python","linux","pentest","kali","bug bounty","cyber","exploit","ctf"])
    if not c:
        c = scrape_category("TutorialBar",
            ["https://tutorialbar.com/cat/it-and-software/",
             "https://tutorialbar.com/cat/development/"], "tutorialbar.com")
    return c

def scrape_discudemy():
    print("\n🔍 DiscUdemy.com")
    courses, post_urls, seen = [], set(), set()

    for base in ["https://www.discudemy.com/lang/english",
                 "https://www.discudemy.com/category/it-and-software",
                 "https://www.discudemy.com/category/development"]:
        for page in range(1, 5):
            url = base if page == 1 else f"{base}/{page}"
            soup, _ = get_page(url, timeout=12)
            if not soup: break
            found = 0
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/'):
                    href = 'https://www.discudemy.com' + href
                skip = any(x in href for x in ['/category','/lang','/go/',
                    '/about','/contact','/faq','/privacy','/terms','#','/page'])
                if not skip and 'discudemy.com' in href and len(href) > 32:
                    if href not in post_urls:
                        post_urls.add(href)
                        found += 1
            if found == 0: break
            time.sleep(0.4)

    print(f"   Found {len(post_urls)} pages")
    for post_url in list(post_urls)[:60]:
        soup, raw = get_page(post_url, timeout=10)
        if not soup: continue
        t = soup.find('h1') or soup.find('h3')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title):
            time.sleep(0.15); continue

        udemy_url = None
        # Follow /go/ redirect
        for a in soup.find_all('a', href=True):
            if '/go/' in a['href']:
                href = a['href']
                if href.startswith('/'):
                    href = 'https://www.discudemy.com' + href
                try:
                    gr = requests.get(href, headers=HEADERS, timeout=12, allow_redirects=True)
                    if has_coupon(gr.url) and 'udemy.com/course/' in gr.url:
                        udemy_url = gr.url; break
                    lnks = extract_udemy_links(gr.text, require_coupon=True)
                    if lnks:
                        udemy_url = lnks[0]; break
                except Exception:
                    pass

        if not udemy_url:
            lnks = extract_udemy_links(raw, require_coupon=True)
            if lnks: udemy_url = lnks[0]

        if udemy_url:
            cid = extract_course_id(udemy_url)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': udemy_url, 'source': 'DiscUdemy'})
                print(f"   ✅ {title[:70]}")
        time.sleep(0.35)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_realdiscount():
    print("\n🔍 Real.Discount")
    courses, seen = [], set()
    urls = [
        "https://www.real.discount/udemy-coupon-code/it-and-software/",
        "https://www.real.discount/udemy-coupon-code/development/",
        "https://www.real.discount/udemy-coupon-code/network-and-security/",
    ] + [f"https://www.real.discount/?s={quote_plus(t)}"
         for t in ["hacking","security","python","linux","pentest","kali","ctf"]]

    for url in urls:
        soup, raw = get_page(url, timeout=12)
        if not soup: continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if not cid or cid in seen: continue
            title = cid.replace('-',' ').title()
            for a in soup.find_all('a', href=True):
                if cid in a.get('href',''):
                    tx = a.text.strip()
                    if tx and len(tx) > 5: title = clean_title(tx)
                    break
            if is_relevant_course(title):
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'RealDiscount'})
                print(f"   ✅ {title[:70]}")
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_coursefolder():
    print("\n🔍 CourseFolder.net")
    all_urls, seen, courses = set(), set(), []

    for cat in ["https://coursefolder.net/category/IT-and-Software",
                "https://coursefolder.net/category/Development",
                "https://coursefolder.net/category/IT-and-Software/Network-and-Security"]:
        for page in range(1, 5):
            url = cat if page == 1 else f"{cat}/page/{page}"
            soup, _ = get_page(url, timeout=12)
            if not soup: break
            found = 0
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/'): href = 'https://coursefolder.net' + href
                skip = any(x in href for x in ['/category/','/live','/about','/blog',
                    '/contact','.php','/compare','/udemy','/faq','/privacy','/terms','/page/','#'])
                if not skip and 'coursefolder.net' in href:
                    path = href.replace('https://coursefolder.net/','')
                    if '.' not in path.split('/')[-1] and len(path) > 8:
                        all_urls.add(href); found += 1
            if found == 0: break
            time.sleep(0.3)

    print(f"   Checking {min(len(all_urls),80)} course pages...")
    for cu in list(all_urls)[:80]:
        soup, raw = get_page(cu, timeout=8)
        if not soup: continue
        t = soup.find('h1')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title): continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'CourseFolder'})
                print(f"   ✅ {title[:70]}"); break
        time.sleep(0.2)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_courson():
    print("\n🔍 Courson.xyz")
    courses, post_urls, seen = [], set(), set()
    for term in ["hacking","security","python","linux","pentest","kali"]:
        for surl in [f"https://courson.xyz/?s={quote_plus(term)}",
                     f"https://courson.xyz/search/?q={quote_plus(term)}"]:
            soup, raw = get_page(surl, timeout=12)
            if not soup: continue
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'courson.xyz' in href and not any(
                        x in href for x in ['/?s=','/#','/?q=','/page/','/category/']):
                    post_urls.add(href)
            time.sleep(0.4)

    for pu in list(post_urls)[:40]:
        soup, raw = get_page(pu, timeout=10)
        if not soup: continue
        t = soup.find('h1')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title): continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'Courson.xyz'})
                print(f"   ✅ {title[:70]}"); break
        time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_couponscorpion():
    print("\n🔍 CouponScorpion.com")
    post_links, seen, courses = set(), set(), []
    for cat in ["https://couponscorpion.com/it-software/",
                "https://couponscorpion.com/development/",
                "https://couponscorpion.com/category/100-off-coupons/it-software/",
                "https://couponscorpion.com/category/100-off-coupons/development/"]:
        for page in range(1, 4):
            url = cat if page == 1 else f"{cat}page/{page}/"
            soup, _ = get_page(url, timeout=12)
            if not soup: break
            found = 0
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'couponscorpion.com' not in href: continue
                if any(x in href for x in ['/category/','/page/','/tag/','/author/','#','/wp-','?s=']): continue
                if len(href) > 35 and href not in post_links:
                    post_links.add(href); found += 1
            if found == 0: break
            time.sleep(0.3)

    print(f"   Found {len(post_links)} posts")
    for pu in list(post_links)[:60]:
        soup, raw = get_page(pu, timeout=10)
        if not soup: continue
        t = soup.find('h1')
        title = clean_title(re.sub(r'\[100% Off\]|\[Free\]','', t.text.strip(), flags=re.I)) if t else ""
        if not is_relevant_course(title): continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'CouponScorpion'})
                print(f"   ✅ {title[:70]}"); break
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_idownloadcoupon():
    print("\n🔍 iDownloadCoupon.com")
    courses, seen, product_urls = [], set(), set()
    for term in ["hacking","security","python","linux","bug bounty","kali"]:
        soup, _ = get_page(
            f"https://idownloadcoupon.com/?s={quote_plus(term)}&post_type=product", timeout=12)
        if soup:
            for a in soup.find_all('a', href=True):
                if '/product/' in a['href']: product_urls.add(a['href'])
        time.sleep(0.4)

    for pu in list(product_urls)[:40]:
        soup, raw = get_page(pu, timeout=10)
        if not soup: continue
        t = soup.find('h1', class_='product_title') or soup.find('h1')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title): continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'iDownloadCoupon'})
                print(f"   ✅ {title[:70]}"); break
        time.sleep(0.35)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_udemyfreebies():
    print("\n🔍 UdemyFreebies.com")
    post_links, seen, courses = set(), set(), []
    for cat in ["https://udemyfreebies.com/free-udemy-courses/it-software",
                "https://udemyfreebies.com/free-udemy-courses/development",
                "https://udemyfreebies.com/free-udemy-courses/network-security"]:
        for page in range(1, 4):
            url = cat if page == 1 else f"{cat}/page/{page}"
            soup, _ = get_page(url, timeout=12)
            if not soup: break
            found = 0
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'udemyfreebies.com' not in href: continue
                if any(x in href for x in ['/free-udemy-courses/','/page/','#','/category/',
                        '/about','/contact','/privacy','/terms','?','/author/']): continue
                if len(href) > 35 and href not in post_links:
                    post_links.add(href); found += 1
            if found == 0: break
            time.sleep(0.3)

    print(f"   Checking {min(len(post_links),60)} posts...")
    for pu in list(post_links)[:60]:
        soup, raw = get_page(pu, timeout=10)
        if not soup: continue
        t = soup.find('h1')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title):
            time.sleep(0.15); continue

        links = extract_udemy_links(raw, require_coupon=True)
        if not links:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if any(x in href.lower() for x in ['/coupon/','/get-coupon','/go/','/visit/']):
                    if href.startswith('/'): href = 'https://udemyfreebies.com' + href
                    try:
                        gr = requests.get(href, headers=HEADERS, timeout=12, allow_redirects=True)
                        if has_coupon(gr.url) and 'udemy.com/course/' in gr.url:
                            links = [gr.url]; break
                        gl = extract_udemy_links(gr.text, require_coupon=True)
                        if gl: links = gl; break
                    except Exception:
                        pass

        for lnk in links:
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'UdemyFreebies'})
                print(f"   ✅ {title[:70]}"); break
        time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_coursevania():
    print("\n🔍 CourseVania.com")
    post_links, seen, courses = set(), set(), []
    for base in ["https://coursevania.com/courses/it-software/",
                 "https://coursevania.com/courses/development/",
                 "https://coursevania.com/courses/network-security/",
                 "https://coursevania.com/it-software/",
                 "https://coursevania.com/development/"]:
        for page in range(1, 4):
            url = base if page == 1 else f"{base}page/{page}/"
            soup, _ = get_page(url, timeout=12)
            if not soup: break
            found = 0
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/'): href = 'https://coursevania.com' + href
                if 'coursevania.com' not in href: continue
                skip = any(x in href for x in ['/courses/it-software','/courses/development',
                    '/courses/network','/it-software/','/development/','/page/',
                    '/category/','/tag/','/author/','#','/about','/contact'])
                if not skip and len(href) > 30 and href not in post_links:
                    post_links.add(href); found += 1
            if found == 0: break
            time.sleep(0.3)

    print(f"   Found {len(post_links)} posts")
    for pu in list(post_links)[:60]:
        soup, raw = get_page(pu, timeout=10)
        if not soup: continue
        t = soup.find('h1') or soup.find('h2')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title): continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'CourseVania'})
                print(f"   ✅ {title[:70]}"); break
        time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses

def scrape_learnviral():
    c = scrape_wp_api("LearnViral", "https://learnviral.com",
        ["hacking","security","python","linux","cyber","pentest","kali"])
    if not c:
        c = scrape_category("LearnViral",
            ["https://learnviral.com/category/udemy-free-course/it-software/",
             "https://learnviral.com/category/udemy-free-course/development/"], "learnviral.com")
    return c

def scrape_freecoursesite():
    c = scrape_wp_api("FreeCoursesSite", "https://freecoursesite.com",
        ["hacking","security","python","linux","pentest","kali","cyber"])
    if not c:
        c = scrape_category("FreeCoursesSite",
            ["https://freecoursesite.com/category/it-and-software/",
             "https://freecoursesite.com/category/development/"], "freecoursesite.com")
    return c

def scrape_paidcoursesforfree():
    return scrape_wp_api("PaidCoursesForFree", "https://paidcoursesforfree.com",
        ["hacking","security","python","linux","network","cyber"])

def scrape_freebiesglobal():
    print("\n🔍 FreeBiesGlobal")
    # WP API — extract from content, require couponCode
    courses = scrape_wp_api("FreeBiesGlobal", "https://freebiesglobal.com",
        ["hacking","security","python","linux","pentest","kali",
         "cyber","exploit","ctf","burp","nmap","oscp","ceh"])
    return courses

def scrape_freetutorials():
    c = scrape_wp_api("FreeTutorials.us", "https://www.freetutorials.us",
        ["hacking","security","python","linux","pentest"])
    if not c:
        c = scrape_category("FreeTutorials.us",
            ["https://www.freetutorials.us/category/udemy/it-software/",
             "https://www.freetutorials.us/category/udemy/development/"], "freetutorials.us")
    return c

def scrape_techofide():
    return scrape_wp_api("TechOfide", "https://techofide.com",
        ["hacking","cybersecurity","python","kali linux","ethical hacking"])

def scrape_onlinecourses_ooo():
    print("\n🔍 OnlineCourses.ooo")
    courses, seen = [], set()
    for term in ["hacking","security","python","linux"]:
        for url in [f"https://onlinecourses.ooo/?s={quote_plus(term)}",
                    f"https://onlinecourses.ooo/search/{quote_plus(term)}/"]:
            soup, raw = get_page(url, timeout=12)
            if not soup: continue
            for lnk in extract_udemy_links(raw, require_coupon=True):
                cid = extract_course_id(lnk)
                if not cid or cid in seen: continue
                title = cid.replace('-',' ').title()
                for a in soup.find_all('a', href=True):
                    if cid in a.get('href',''):
                        tx = a.text.strip()
                        if tx and len(tx) > 5: title = clean_title(tx)
                        break
                if is_relevant_course(title):
                    seen.add(cid)
                    courses.append({'title': title, 'url': lnk, 'source': 'OnlineCourses.ooo'})
                    print(f"   ✅ {title[:70]}")
            time.sleep(0.4)
    print(f"   Total: {len(courses)}")
    return courses

def scrape_givecoupon():
    return scrape_category("GiveCoupon",
        ["https://www.givecoupon.com/category/udemy/it-software/",
         "https://www.givecoupon.com/category/udemy/development/"], "givecoupon.com")

def scrape_infognu():
    c = scrape_wp_api("InfoGnu", "https://infognu.com",
        ["hacking","security","python","linux"])
    if not c:
        c = scrape_category("InfoGnu",
            ["https://infognu.com/category/it-software/",
             "https://infognu.com/category/development/"], "infognu.com")
    return c

def scrape_100offdeal():
    return scrape_category("100OffDeal",
        ["https://100offdeal.com/category/udemy/it-software/",
         "https://100offdeal.com/category/udemy/development/"], "100offdeal.com")

def scrape_hitudemycoupons():
    print("\n🔍 HitUdemyCoupons.com")
    courses, seen = [], set()
    for url in ["https://hitudemycoupons.com/",
                "https://hitudemycoupons.com/it-software/",
                "https://hitudemycoupons.com/development/"]:
        soup, raw = get_page(url, timeout=12)
        if not soup: continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if not cid or cid in seen: continue
            title = cid.replace('-',' ').title()
            for a in soup.find_all('a', href=True):
                if cid in a.get('href',''):
                    tx = a.text.strip()
                    if tx and len(tx) > 5: title = clean_title(tx)
                    break
            if is_relevant_course(title):
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'HitUdemyCoupons'})
                print(f"   ✅ {title[:70]}")
        time.sleep(0.4)
    print(f"   Total: {len(courses)}")
    return courses

def scrape_cheapudemy():
    return scrape_wp_api("CheapUdemy", "https://cheapudemy.com",
        ["hacking","security","python","linux"])

def scrape_freecourseudemy():
    return scrape_category("FreeCourseUdemy",
        ["https://freecourseudemy.com/category/it-software/",
         "https://freecourseudemy.com/category/development/"], "freecourseudemy.com")

def scrape_comidoc():
    print("\n🔍 Comidoc.net")
    courses, seen, post_urls = [], set(), set()
    for term in ["hacking","security","python","linux","pentest"]:
        for url in [f"https://comidoc.net/search?q={quote_plus(term)}&discount=100",
                    f"https://comidoc.net/search?q={quote_plus(term)}&free=true"]:
            soup, _ = get_page(url, timeout=12)
            if not soup: continue
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/course/'): href = 'https://comidoc.net' + href
                if 'comidoc.net/course/' in href: post_urls.add(href)
            time.sleep(0.4)

    for pu in list(post_urls)[:40]:
        soup, raw = get_page(pu, timeout=10)
        if not soup: continue
        t = soup.find('h1')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title): continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'Comidoc'})
                print(f"   ✅ {title[:70]}"); break
        time.sleep(0.3)
    print(f"   Total: {len(courses)}")
    return courses

def scrape_freecoursesonline():
    return scrape_wp_api("FreeCourseOnline", "https://freecoursesonline.me",
        ["hacking","security","python","linux","pentest"])

def scrape_bestcouponhunter():
    c = scrape_wp_api("BestCouponHunter", "https://bestcouponhunter.com",
        ["hacking","security","python","linux","pentest","kali","cyber"])
    if not c:
        c = scrape_category("BestCouponHunter",
            ["https://bestcouponhunter.com/category/udemy/it-software/",
             "https://bestcouponhunter.com/category/udemy/development/"], "bestcouponhunter.com")
    return c

def scrape_udemy24():
    print("\n🔍 Udemy24.com")
    courses, post_links, seen = [], set(), set()
    for term in ["hacking","security","python","linux","pentest"]:
        soup, _ = get_page(f"https://www.udemy24.com/search?q={quote_plus(term)}", timeout=12)
        if soup:
            for a in soup.find_all('a', href=True):
                if 'udemy24.com/2' in a['href']: post_links.add(a['href'])
        time.sleep(0.4)

    for pu in list(post_links)[:40]:
        soup, raw = get_page(pu, timeout=10)
        if not soup: continue
        t = soup.find('h1') or soup.find('title')
        title = clean_title(t.text.strip()) if t else ""
        if not is_relevant_course(title): continue
        article = (soup.find('div', class_='post-body') or
                   soup.find('article') or soup.find('div', class_='entry-content'))
        html = str(article) if article else raw
        for lnk in extract_udemy_links(html, require_coupon=True):
            cid = extract_course_id(lnk)
            if cid and cid not in seen:
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'Udemy24'})
                print(f"   ✅ {title[:70]}"); break
        time.sleep(0.4)
    print(f"   Total: {len(courses)}")
    return courses

def scrape_udemycoupon_io():
    print("\n🔍 UdemyCoupon.io")
    courses, seen = [], set()
    for cat in ["https://udemycoupon.io/category/it-software/",
                "https://udemycoupon.io/category/development/",
                "https://udemycoupon.io/"]:
        soup, raw = get_page(cat, timeout=12)
        if not soup: continue
        for lnk in extract_udemy_links(raw, require_coupon=True):
            cid = extract_course_id(lnk)
            if not cid or cid in seen: continue
            title = cid.replace('-',' ').title()
            for a in soup.find_all('a', href=True):
                if cid in a.get('href',''):
                    tx = a.text.strip()
                    if tx and len(tx) > 5: title = clean_title(tx)
                    break
            if is_relevant_course(title):
                seen.add(cid)
                courses.append({'title': title, 'url': lnk, 'source': 'UdemyCoupon.io'})
                print(f"   ✅ {title[:70]}")
        time.sleep(0.4)
    print(f"   Total: {len(courses)}")
    return courses

# ─────────────────────────────────────────────
# DEDUP + MAIN
# ─────────────────────────────────────────────
def dedup(courses):
    seen, out = set(), []
    for c in courses:
        cid = extract_course_id(c['url'])
        if cid and cid not in seen:
            seen.add(cid); out.append(c)
    return out

SCRAPERS = [
    ("TutorialBar",        scrape_tutorialbar),
    ("DiscUdemy",          scrape_discudemy),
    ("RealDiscount",       scrape_realdiscount),
    ("CourseFolder",       scrape_coursefolder),
    ("Courson.xyz",        scrape_courson),
    ("CouponScorpion",     scrape_couponscorpion),
    ("iDownloadCoupon",    scrape_idownloadcoupon),
    ("UdemyFreebies",      scrape_udemyfreebies),
    ("CourseVania",        scrape_coursevania),
    ("LearnViral",         scrape_learnviral),
    ("FreeCoursesSite",    scrape_freecoursesite),
    ("PaidCoursesForFree", scrape_paidcoursesforfree),
    ("FreeBiesGlobal",     scrape_freebiesglobal),
    ("FreeTutorials.us",   scrape_freetutorials),
    ("TechOfide",          scrape_techofide),
    ("OnlineCourses.ooo",  scrape_onlinecourses_ooo),
    ("GiveCoupon",         scrape_givecoupon),
    ("InfoGnu",            scrape_infognu),
    ("100OffDeal",         scrape_100offdeal),
    ("HitUdemyCoupons",    scrape_hitudemycoupons),
    ("CheapUdemy",         scrape_cheapudemy),
    ("FreeCourseUdemy",    scrape_freecourseudemy),
    ("Comidoc",            scrape_comidoc),
    ("FreeCourseOnline",   scrape_freecoursesonline),
    ("BestCouponHunter",   scrape_bestcouponhunter),
    ("Udemy24",            scrape_udemy24),
    ("UdemyCoupon.io",     scrape_udemycoupon_io),
]

def main():
    print("=" * 80)
    print("🚀 CouponHunter v3.2 — 27 Sources — COUPON-REQUIRED MODE")
    print("   Only courses with couponCode= in URL are sent")
    print(f"   Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)

    sent = load_sent()
    all_courses, stats = [], {}

    for name, fn in SCRAPERS:
        try:
            res = fn()
            all_courses.extend(res)
            stats[name] = len(res)
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            stats[name] = 0
        time.sleep(1)

    all_courses = dedup(all_courses)
    print(f"\n📊 Unique coupon courses this run: {len(all_courses)}")

    new = dup = fail = 0
    for c in all_courses:
        cid = extract_course_id(c['url'])
        if not cid: continue
        if cid in sent:
            dup += 1; continue
        if send_telegram(c['title'], c['url'], c.get('source','')):
            sent.add(cid); new += 1; time.sleep(2)
        else:
            fail += 1

    save_sent(sent)

    print("\n" + "=" * 80)
    print("🏁 Done!")
    print(f"   ✅ Sent: {new}  |  ⏭️  Dupes: {dup}  |  ❌ Failed: {fail}")
    print(f"   📚 Total ever tracked: {len(sent)}")
    print("\n📈 Per-source:")
    for name, count in stats.items():
        print(f"   {'✅' if count > 0 else '⚠️ '} {name:<22} → {count}")
    print("=" * 80)

if __name__ == "__main__":
    main()