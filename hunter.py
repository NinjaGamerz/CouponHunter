#!/usr/bin/env python3
"""
CouponHunter - MEGA VERSION v3.0
Sources: 27 websites scraped for 100% OFF Udemy coupons
Focus: Ethical Hacking | Bug Bounty | Cybersecurity | Coding | Networking | Pentesting
Runs on: GitHub Actions
Secrets: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""
import os
import re
import time
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode, quote_plus

# ============================================================
# TELEGRAM CONFIG (from GitHub Secrets)
# ============================================================
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ============================================================
# KEYWORD FILTERS
# ============================================================
SECURITY_KEYWORDS = [
    "hack", "hacking", "ethical hacking", "pentest", "penetration testing",
    "bug bounty", "cybersecurity", "cyber security", "infosec", "information security",
    "kali", "kali linux", "metasploit", "nmap", "burp suite", "wireshark",
    "oscp", "ceh", "cissp", "comptia security", "security+",
    "exploit", "exploitation", "vulnerability", "malware", "forensic",
    "red team", "blue team", "ctf", "reverse engineering",
    "social engineering", "phishing", "web hacking", "web application security",
    "owasp", "sql injection", "xss", "csrf", "ssrf", "idor",
    "network security", "web security", "application security", "appsec",
    "cyber attack", "cyber defense", "threat hunting", "incident response",
    "soc analyst", "security analyst", "security engineer", "security operations",
    "dark web", "tor", "anonymity", "privacy hacking", "osint",
    "reconnaissance", "enumeration", "privilege escalation", "post exploitation",
    "shellcode", "buffer overflow", "binary exploitation", "pwn",
    "mobile hacking", "android hacking", "ios hacking", "wireless hacking",
    "wifi hacking", "bluetooth hacking", "rfid hacking",
    "blockchain security", "smart contract audit", "web3 security",
    "active directory", "windows hacking", "linux privilege escalation",
    "cloud hacking", "aws security", "azure security", "gcp security",
    "docker security", "kubernetes security", "container security",
]

CODING_KEYWORDS = [
    "python", "javascript", "java", "c++", "c#", "golang", "go lang",
    "rust", "ruby", "php", "typescript", "kotlin", "swift",
    "bash", "shell script", "powershell", "batch script",
    "programming", "coding", "software development", "software engineering",
    "django", "flask", "fastapi", "react", "node.js", "nodejs", "angular", "vue",
    "api", "rest api", "graphql", "microservices",
    "git", "github", "gitlab", "version control",
    "docker", "kubernetes", "devops", "ci/cd", "devsecops",
    "aws", "azure", "gcp", "cloud computing", "terraform",
    "machine learning", "deep learning", "ai", "artificial intelligence",
    "data science", "data analysis", "data engineering",
    "blockchain", "smart contract", "solidity", "web3",
    "database", "sql", "nosql", "mongodb", "postgresql",
]

NETWORKING_KEYWORDS = [
    "network", "networking", "tcp/ip", "cisco", "ccna", "ccnp",
    "linux", "unix", "ubuntu", "centos", "debian", "server administration",
    "sysadmin", "system administration", "firewall", "vpn", "ipsec",
    "dns", "dhcp", "routing", "switching", "bgp", "ospf",
    "cloud", "virtualization", "vmware", "hyper-v",
    "siem", "ids", "ips", "waf", "proxy",
]

EXCLUDE_KEYWORDS = [
    "capcut", "video editing", "premiere pro", "after effects", "photoshop",
    "illustrator", "lightroom", "canva", "graphic design",
    "marketing", "digital marketing", "seo", "social media marketing",
    "business", "sales", "finance", "accounting", "bookkeeping",
    "excel", "powerpoint", "microsoft office", "productivity", "time management",
    "ui/ux", "figma", "sketch", "adobe xd", "music production",
    "photography", "lifestyle", "fitness", "yoga", "meditation",
    "cooking", "language", "english", "spanish", "french", "guitar",
    "drawing", "painting", "art", "animation", "3d modeling",
    "hr", "human resources", "project management", "pmp",
]

ALL_KEYWORDS = SECURITY_KEYWORDS + CODING_KEYWORDS + NETWORKING_KEYWORDS

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

SEARCH_TERMS = [
    "hacking", "cybersecurity", "ethical hacking", "penetration testing",
    "bug bounty", "python", "linux", "kali linux", "network security",
    "web security", "oscp", "ceh", "security", "exploit", "ctf",
    "devops", "docker", "aws", "javascript", "programming",
]

# ============================================================
# HELPERS
# ============================================================
def is_relevant_course(title, desc=""):
    text = (title + " " + desc).lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return False
    for kw in ALL_KEYWORDS:
        if kw in text:
            return True
    return False

def extract_course_id(url):
    match = re.search(r'/course/([^/?#]+)', url)
    return match.group(1).lower() if match else None

def extract_udemy_links(soup):
    """Extract all Udemy course links from a BeautifulSoup object. Prefer couponCode links."""
    found = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'udemy.com/course/' in href:
            found.append(href)
    # Prefer links with couponCode
    coupon_links = [u for u in found if 'couponCode=' in u]
    return coupon_links if coupon_links else found

def get_soup(url, timeout=15, retries=2):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return BeautifulSoup(r.text, 'html.parser')
        except Exception:
            time.sleep(1)
    return None

def clean_title(title):
    for remove in ['[Free]', '[100% Off]', '100% OFF', 'Free Course', 'Udemy Coupon', '–', '|']:
        title = title.replace(remove, '')
    return title.strip()

# ============================================================
# TELEGRAM
# ============================================================
def send_telegram(title, url, source=""):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram not configured")
        return False
    try:
        msg = (
            f"🔥 *FREE COURSE ALERT!*\n\n"
            f"📚 *{title}*\n\n"
            f"🌐 Source: `{source}`\n"
            f"🔗 {url}\n\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=10
        )
        if r.status_code == 200:
            print(f"   ✅ Sent: {title[:70]}")
            return True
        else:
            print(f"   ❌ Telegram error {r.status_code}: {r.text[:100]}")
            return False
    except Exception as e:
        print(f"   ❌ Telegram exception: {e}")
        return False

# ============================================================
# MEMORY (dedup)
# ============================================================
def load_sent():
    try:
        with open('memory.json', 'r') as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_sent(sent):
    with open('memory.json', 'w') as f:
        json.dump(list(sent), f, indent=2)

# ============================================================
# GENERIC SCRAPERS (reusable)
# ============================================================
def scrape_wordpress_api(site_name, base_url, categories=None, search_terms=None, max_posts=60):
    """
    Generic WordPress REST API scraper.
    Works for: tutorialbar, freecoursesite, freebiesglobal, freetutorials,
               paidcoursesforfree, freecoursesonline, techofide, etc.
    """
    print(f"\n🔍 {site_name} (WP API)")
    courses = []
    api_base = base_url.rstrip('/') + '/wp-json/wp/v2/posts'

    urls_to_check = []

    # Search by keywords
    if search_terms:
        for term in search_terms[:6]:  # limit API calls
            params = {'per_page': 20, 'search': term}
            api_url = api_base + '?' + urlencode(params)
            try:
                r = requests.get(api_url, headers=HEADERS, timeout=12)
                if r.status_code == 200:
                    posts = r.json()
                    for post in posts:
                        link = post.get('link', '')
                        if link and link not in urls_to_check:
                            urls_to_check.append(link)
            except Exception:
                pass
            time.sleep(0.3)
    else:
        # Just grab latest posts
        params = {'per_page': 50}
        api_url = api_base + '?' + urlencode(params)
        try:
            r = requests.get(api_url, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                posts = r.json()
                for post in posts:
                    link = post.get('link', '')
                    if link and link not in urls_to_check:
                        urls_to_check.append(link)
        except Exception:
            pass

    print(f"   Found {len(urls_to_check)} posts to check")

    for post_url in urls_to_check[:max_posts]:
        soup = get_soup(post_url, timeout=10)
        if not soup:
            continue

        title_elem = soup.find('h1')
        title = clean_title(title_elem.text.strip()) if title_elem else ""

        if not is_relevant_course(title):
            time.sleep(0.2)
            continue

        links = extract_udemy_links(soup)
        if links:
            courses.append({'title': title, 'url': links[0], 'source': site_name})
            print(f"   ✅ {title[:70]}")

        time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses


def scrape_category_listing(site_name, category_urls, max_pages=3, max_posts=40):
    """
    Generic category-listing scraper.
    Works for: discudemy, couponscorpion, coursevania, learnviral,
               udemyfreebies, givecoupon, onlinecourses, hitudemycoupons, etc.
    """
    print(f"\n🔍 {site_name} (Category)")
    courses = []
    post_urls = set()

    for cat_url in category_urls:
        for page in range(1, max_pages + 1):
            if page == 1:
                page_url = cat_url
            else:
                # Try common pagination patterns
                if cat_url.endswith('/'):
                    page_url = cat_url + f'page/{page}/'
                else:
                    page_url = cat_url + f'/page/{page}/'

            soup = get_soup(page_url, timeout=12)
            if not soup:
                break

            # Collect internal post links
            domain = re.sub(r'https?://(www\.)?', '', cat_url).split('/')[0]
            found_on_page = 0
            for a in soup.find_all('a', href=True):
                href = a['href']
                if domain in href and href not in post_urls:
                    # Filter out category/tag/page navigation links
                    skip = any(x in href for x in [
                        '/category/', '/tag/', '/page/', '/author/',
                        '#', 'mailto:', 'javascript:', '?', '/wp-',
                        '/feed', '/sitemap', '/about', '/contact',
                    ])
                    if not skip and len(href) > len(f'https://{domain}/') + 5:
                        post_urls.add(href)
                        found_on_page += 1

            if found_on_page == 0:
                break
            time.sleep(0.3)

    print(f"   Found {len(post_urls)} pages to check")

    for post_url in list(post_urls)[:max_posts]:
        soup = get_soup(post_url, timeout=10)
        if not soup:
            continue

        title_elem = soup.find('h1')
        title = clean_title(title_elem.text.strip()) if title_elem else ""

        if not is_relevant_course(title):
            time.sleep(0.2)
            continue

        links = extract_udemy_links(soup)
        if links:
            courses.append({'title': title, 'url': links[0], 'source': site_name})
            print(f"   ✅ {title[:70]}")

        time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 1: TutorialBar (WordPress REST API — very active)
# ============================================================
def scrape_tutorialbar():
    print("\n🔍 TutorialBar.com")
    courses = []
    api = "https://tutorialbar.com/wp-json/wp/v2/posts"

    for term in ["hacking", "security", "python", "linux", "bug bounty", "pentest"]:
        try:
            r = requests.get(api, headers=HEADERS, timeout=12,
                             params={'per_page': 20, 'search': term})
            if r.status_code != 200:
                continue
            for post in r.json():
                title = clean_title(BeautifulSoup(
                    post.get('title', {}).get('rendered', ''), 'html.parser').text)
                content_html = post.get('content', {}).get('rendered', '')
                csoup = BeautifulSoup(content_html, 'html.parser')
                if not is_relevant_course(title):
                    continue
                links = extract_udemy_links(csoup)
                if links:
                    courses.append({'title': title, 'url': links[0], 'source': 'TutorialBar'})
                    print(f"   ✅ {title[:70]}")
        except Exception as e:
            print(f"   ⚠️  {e}")
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 2: DiscUdemy
# ============================================================
def scrape_discudemy():
    print("\n🔍 DiscUdemy.com")
    courses = []
    cat_urls = [
        "https://www.discudemy.com/category/it-and-software",
        "https://www.discudemy.com/category/development",
        "https://www.discudemy.com/lang/english",
    ]

    for cat_url in cat_urls:
        for page in range(1, 4):
            url = cat_url if page == 1 else f"{cat_url}/{page}"
            soup = get_soup(url, timeout=12)
            if not soup:
                break

            cards = soup.find_all('div', class_=re.compile(r'card|course|post'))
            for card in cards:
                a = card.find('a', href=True)
                if not a:
                    continue
                href = a['href']
                if 'discudemy.com' not in href and not href.startswith('/'):
                    continue

                full_url = href if href.startswith('http') else f"https://www.discudemy.com{href}"
                if any(x in full_url for x in ['/category', '/lang', '/page']):
                    continue

                title = a.text.strip() or clean_title(
                    (card.find('h2') or card.find('h3') or card.find('p') or a
                     ).text.strip())

                if not is_relevant_course(title):
                    continue

                # Fetch the individual course page
                psoup = get_soup(full_url, timeout=10)
                if not psoup:
                    continue

                title_h1 = psoup.find('h1')
                if title_h1:
                    title = clean_title(title_h1.text.strip())

                links = extract_udemy_links(psoup)
                if not links:
                    # DiscUdemy uses a /go/ redirect; find it and follow
                    go_link = None
                    for al in psoup.find_all('a', href=True):
                        if '/go/' in al['href'] or 'discudemy.com/go' in al['href']:
                            go_link = al['href']
                            break
                    if go_link:
                        if go_link.startswith('/'):
                            go_link = 'https://www.discudemy.com' + go_link
                        try:
                            gr = requests.get(go_link, headers=HEADERS, timeout=10,
                                              allow_redirects=True)
                            if 'udemy.com/course/' in gr.url:
                                links = [gr.url]
                        except Exception:
                            pass

                if links:
                    courses.append({'title': title, 'url': links[0], 'source': 'DiscUdemy'})
                    print(f"   ✅ {title[:70]}")

                time.sleep(0.3)
            time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 3: Real.Discount (has public API!)
# ============================================================
def scrape_realdiscount():
    print("\n🔍 Real.Discount")
    courses = []

    for term in ["hacking", "security", "python", "linux", "pentest", "cyber", "coding"]:
        try:
            api_url = (
                "https://www.real.discount/api-web/all-courses/"
                f"?store=Udemy&page=1&per_page=30&orderby=date&free=1&search={quote_plus(term)}"
            )
            r = requests.get(api_url, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                data = r.json()
                items = data if isinstance(data, list) else data.get('results', data.get('courses', []))
                for item in items:
                    title = item.get('name', item.get('title', ''))
                    url   = item.get('url', item.get('link', ''))
                    if not url or 'udemy.com' not in url:
                        continue
                    if is_relevant_course(title):
                        courses.append({'title': clean_title(title), 'url': url, 'source': 'RealDiscount'})
                        print(f"   ✅ {title[:70]}")
        except Exception as e:
            print(f"   ⚠️  {e}")
        time.sleep(0.3)

    # Fallback HTML scrape
    soup = get_soup("https://www.real.discount/udemy-coupon-code/", timeout=12)
    if soup:
        for a in soup.find_all('a', href=True):
            if 'udemy.com/course/' in a['href']:
                title = a.text.strip()
                if not title:
                    cid = extract_course_id(a['href'])
                    title = cid.replace('-', ' ').title() if cid else "Unknown"
                if is_relevant_course(title):
                    courses.append({'title': title, 'url': a['href'], 'source': 'RealDiscount'})

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 4: CourseFolder (existing, kept & improved)
# ============================================================
def scrape_coursefolder():
    print("\n🔍 CourseFolder.net")
    courses = []
    category_urls = [
        "https://coursefolder.net/category/IT-and-Software",
        "https://coursefolder.net/category/Development",
        "https://coursefolder.net/category/IT-and-Software/Network-and-Security",
    ]

    all_course_urls = set()
    for cat_url in category_urls:
        for page in range(1, 4):
            url = cat_url if page == 1 else f"{cat_url}/page/{page}"
            soup = get_soup(url, timeout=12)
            if not soup:
                break
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'coursefolder.net' in href or href.startswith('/'):
                    if href.startswith('/'):
                        href = f"https://coursefolder.net{href}"
                    skip = any(x in href for x in [
                        '/category/', '/live', '/about', '/blog', '/contact',
                        '.php', '/compare', '/udemy', '/faq', '/privacy', '/terms',
                        '/page/', '#',
                    ])
                    if not skip:
                        path = href.replace('https://coursefolder.net/', '')
                        if '.' not in path.split('/')[-1] and len(path) > 8:
                            all_course_urls.add(href)
            time.sleep(0.3)

    print(f"   Found {len(all_course_urls)} course pages")
    for course_url in list(all_course_urls)[:80]:
        soup = get_soup(course_url, timeout=8)
        if not soup:
            continue
        title_elem = soup.find('h1')
        title = clean_title(title_elem.text.strip()) if title_elem else ""
        if not is_relevant_course(title):
            continue
        links = extract_udemy_links(soup)
        if links:
            courses.append({'title': title, 'url': links[0], 'source': 'CourseFolder'})
            print(f"   ✅ {title[:70]}")
        time.sleep(0.2)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 5: Courson.xyz
# ============================================================
def scrape_courson():
    print("\n🔍 Courson.xyz")
    courses = []

    search_terms = ["hacking", "security", "python", "linux", "pentest", "cyber"]
    for term in search_terms:
        for url in [
            f"https://courson.xyz/search/?q={quote_plus(term)}",
            f"https://courson.xyz/?s={quote_plus(term)}",
        ]:
            soup = get_soup(url, timeout=12)
            if not soup:
                continue

            # Find course links
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'courson.xyz' in href or href.startswith('/'):
                    if href.startswith('/'):
                        href = 'https://courson.xyz' + href
                    if any(x in href for x in ['/course/', '/courses/', '/deal/', '/coupon/']):
                        # Visit course page
                        psoup = get_soup(href, timeout=10)
                        if not psoup:
                            continue
                        title_elem = psoup.find('h1')
                        title = clean_title(title_elem.text.strip()) if title_elem else ""
                        if not is_relevant_course(title):
                            continue
                        links = extract_udemy_links(psoup)
                        if links:
                            courses.append({'title': title, 'url': links[0], 'source': 'Courson.xyz'})
                            print(f"   ✅ {title[:70]}")
                        time.sleep(0.3)
            time.sleep(0.4)

    # Also scrape main listing
    soup = get_soup("https://courson.xyz/", timeout=12)
    if soup:
        for a in soup.find_all('a', href=True):
            if 'udemy.com/course/' in a['href']:
                title = a.text.strip() or "Unknown"
                if is_relevant_course(title):
                    courses.append({'title': clean_title(title), 'url': a['href'], 'source': 'Courson.xyz'})

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 6: CouponScorpion (existing, improved)
# ============================================================
def scrape_couponscorpion():
    print("\n🔍 CouponScorpion.com")
    courses = []
    cat_urls = [
        "https://couponscorpion.com/category/100-off-coupons/it-software/",
        "https://couponscorpion.com/category/100-off-coupons/development/",
        "https://couponscorpion.com/category/100-off-coupons/",
    ]

    post_links = set()
    for cat_url in cat_urls:
        for page in range(1, 4):
            url = cat_url if page == 1 else f"{cat_url}page/{page}/"
            soup = get_soup(url, timeout=12)
            if not soup:
                break
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'couponscorpion.com' in href:
                    skip = any(x in href for x in ['/category/', '/page/', '/tag/', '/author/', '#'])
                    if not skip and len(href) > 35:
                        post_links.add(href)
            time.sleep(0.3)

    print(f"   Found {len(post_links)} posts")
    for post_url in list(post_links)[:50]:
        soup = get_soup(post_url, timeout=10)
        if not soup:
            continue
        title_elem = soup.find('h1')
        title = clean_title(title_elem.text.strip()) if title_elem else ""
        if not is_relevant_course(title):
            continue
        links = extract_udemy_links(soup)
        if links:
            courses.append({'title': title, 'url': links[0], 'source': 'CouponScorpion'})
            print(f"   ✅ {title[:70]}")
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 7: iDownloadCoupon (existing, improved)
# ============================================================
def scrape_idownloadcoupon():
    print("\n🔍 iDownloadCoupon.com")
    courses = []

    for term in ["hacking", "security", "python", "linux", "bug bounty"]:
        soup = get_soup(
            f"https://idownloadcoupon.com/?s={quote_plus(term)}&post_type=product",
            timeout=12
        )
        if not soup:
            continue
        for a in soup.find_all('a', href=True):
            if '/product/' in a['href']:
                psoup = get_soup(a['href'], timeout=10)
                if not psoup:
                    continue
                t_elem = psoup.find('h1', class_='product_title') or psoup.find('h1')
                title = clean_title(t_elem.text.strip()) if t_elem else ""
                if not is_relevant_course(title):
                    continue
                links = extract_udemy_links(psoup)
                if links:
                    courses.append({'title': title, 'url': links[0], 'source': 'iDownloadCoupon'})
                    print(f"   ✅ {title[:70]}")
                time.sleep(0.3)
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 8: UdemyFreebies
# ============================================================
def scrape_udemyfreebies():
    print("\n🔍 UdemyFreebies.com")
    courses = []
    urls = [
        "https://udemyfreebies.com/free-udemy-courses/it-software",
        "https://udemyfreebies.com/free-udemy-courses/development",
        "https://udemyfreebies.com/free-udemy-courses/network-security",
    ]

    post_links = set()
    for url in urls:
        soup = get_soup(url, timeout=12)
        if not soup:
            continue
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'udemyfreebies.com' in href:
                skip = any(x in href for x in ['/free-udemy-courses/', '/page/', '#', '/category/'])
                if not skip and len(href) > 30:
                    post_links.add(href)
        time.sleep(0.3)

    print(f"   Found {len(post_links)} posts")
    for post_url in list(post_links)[:50]:
        soup = get_soup(post_url, timeout=10)
        if not soup:
            continue
        title_elem = soup.find('h1')
        title = clean_title(title_elem.text.strip()) if title_elem else ""
        if not is_relevant_course(title):
            continue

        # UdemyFreebies uses a "Get Free Coupon" button that links to Udemy
        links = extract_udemy_links(soup)
        # Also check for redirect links
        if not links:
            for a in soup.find_all('a', href=True):
                if '/coupon/' in a['href'] or 'get-coupon' in a['href'].lower():
                    try:
                        r = requests.get(a['href'], headers=HEADERS, timeout=10, allow_redirects=True)
                        if 'udemy.com/course/' in r.url:
                            links = [r.url]
                            break
                    except Exception:
                        pass

        if links:
            courses.append({'title': title, 'url': links[0], 'source': 'UdemyFreebies'})
            print(f"   ✅ {title[:70]}")
        time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 9: CourseVania
# ============================================================
def scrape_coursevania():
    print("\n🔍 CourseVania.com")
    courses = []
    urls = [
        "https://coursevania.com/courses/it-software/",
        "https://coursevania.com/courses/development/",
        "https://coursevania.com/courses/network-security/",
    ]

    post_links = set()
    for url in urls:
        for page in range(1, 4):
            page_url = url if page == 1 else f"{url}page/{page}/"
            soup = get_soup(page_url, timeout=12)
            if not soup:
                break
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'coursevania.com/courses/' in href:
                    # Individual course page
                    path = href.replace('https://coursevania.com/courses/', '')
                    if path and '/' not in path.rstrip('/') and not any(
                            x in href for x in ['/it-software/', '/development/', '/network-security/', '/page/']):
                        post_links.add(href)
            time.sleep(0.3)

    print(f"   Found {len(post_links)} posts")
    for post_url in list(post_links)[:50]:
        soup = get_soup(post_url, timeout=10)
        if not soup:
            continue
        title_elem = soup.find('h1') or soup.find('h2')
        title = clean_title(title_elem.text.strip()) if title_elem else ""
        if not is_relevant_course(title):
            continue
        links = extract_udemy_links(soup)
        if links:
            courses.append({'title': title, 'url': links[0], 'source': 'CourseVania'})
            print(f"   ✅ {title[:70]}")
        time.sleep(0.3)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 10: LearnViral
# ============================================================
def scrape_learnviral():
    print("\n🔍 LearnViral.com")
    courses = []
    base_urls = [
        "https://learnviral.com/category/udemy-free-course/it-software/",
        "https://learnviral.com/category/udemy-free-course/development/",
    ]
    return scrape_category_listing("LearnViral", base_urls, max_pages=3, max_posts=40)

# ============================================================
# SOURCE 11: FreeCoursesSite
# ============================================================
def scrape_freecoursesite():
    return scrape_wordpress_api(
        "FreeCoursesSite",
        "https://freecoursesite.com",
        search_terms=["hacking", "security", "python", "linux", "pentest"]
    )

# ============================================================
# SOURCE 12: PaidCoursesForFree
# ============================================================
def scrape_paidcoursesforfree():
    return scrape_wordpress_api(
        "PaidCoursesForFree",
        "https://paidcoursesforfree.com",
        search_terms=["hacking", "security", "python", "linux", "network"]
    )

# ============================================================
# SOURCE 13: FreeBiesGlobal
# ============================================================
def scrape_freebiesglobal():
    return scrape_wordpress_api(
        "FreeBiesGlobal",
        "https://freebiesglobal.com",
        search_terms=["hacking", "security", "python", "linux"]
    )

# ============================================================
# SOURCE 14: FreeTutorials.us
# ============================================================
def scrape_freetutorials():
    print("\n🔍 FreeTutorials.us")
    courses = []
    base_urls = [
        "https://www.freetutorials.us/category/udemy/it-software/",
        "https://www.freetutorials.us/category/udemy/development/",
    ]
    return scrape_category_listing("FreeTutorials.us", base_urls, max_pages=3, max_posts=40)

# ============================================================
# SOURCE 15: TechOfide
# ============================================================
def scrape_techofide():
    return scrape_wordpress_api(
        "TechOfide",
        "https://techofide.com",
        search_terms=["hacking", "cybersecurity", "python", "kali linux"]
    )

# ============================================================
# SOURCE 16: OnlineCourses.ooo
# ============================================================
def scrape_onlinecourses_ooo():
    print("\n🔍 OnlineCourses.ooo")
    courses = []

    for term in ["hacking", "security", "python", "linux", "pentest"]:
        soup = get_soup(f"https://onlinecourses.ooo/?s={quote_plus(term)}", timeout=12)
        if not soup:
            continue
        for a in soup.find_all('a', href=True):
            if 'udemy.com/course/' in a['href']:
                title = a.text.strip() or extract_course_id(a['href'])
                if is_relevant_course(title):
                    courses.append({'title': clean_title(title), 'url': a['href'], 'source': 'OnlineCourses.ooo'})
                    print(f"   ✅ {title[:70]}")
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 17: GiveCoupon
# ============================================================
def scrape_givecoupon():
    print("\n🔍 GiveCoupon.com")
    courses = []
    base_urls = [
        "https://www.givecoupon.com/category/udemy/it-software/",
        "https://www.givecoupon.com/category/udemy/development/",
    ]
    return scrape_category_listing("GiveCoupon", base_urls, max_pages=3, max_posts=40)

# ============================================================
# SOURCE 18: InfoGnu
# ============================================================
def scrape_infognu():
    print("\n🔍 InfoGnu.com")
    courses = []

    for term in ["hacking", "security", "python", "linux"]:
        soup = get_soup(f"https://infognu.com/?s={quote_plus(term)}", timeout=12)
        if not soup:
            continue
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'infognu.com' in href and '/20' in href:
                psoup = get_soup(href, timeout=10)
                if not psoup:
                    continue
                t_elem = psoup.find('h1')
                title = clean_title(t_elem.text.strip()) if t_elem else ""
                if not is_relevant_course(title):
                    continue
                links = extract_udemy_links(psoup)
                if links:
                    courses.append({'title': title, 'url': links[0], 'source': 'InfoGnu'})
                    print(f"   ✅ {title[:70]}")
                time.sleep(0.3)
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 19: 100OffDeal
# ============================================================
def scrape_100offdeal():
    print("\n🔍 100OffDeal.com")
    courses = []
    base_urls = [
        "https://100offdeal.com/category/udemy/it-software/",
        "https://100offdeal.com/category/udemy/development/",
    ]
    return scrape_category_listing("100OffDeal", base_urls, max_pages=3, max_posts=40)

# ============================================================
# SOURCE 20: HitUdemyCoupons
# ============================================================
def scrape_hitudemycoupons():
    print("\n🔍 HitUdemyCoupons.com")
    courses = []

    soup = get_soup("https://hitudemycoupons.com/", timeout=12)
    if soup:
        for a in soup.find_all('a', href=True):
            if 'udemy.com/course/' in a['href']:
                title = a.text.strip()
                if is_relevant_course(title):
                    courses.append({'title': clean_title(title), 'url': a['href'], 'source': 'HitUdemyCoupons'})
                    print(f"   ✅ {title[:70]}")

    for term in ["hacking", "security", "python"]:
        soup = get_soup(f"https://hitudemycoupons.com/?s={quote_plus(term)}", timeout=12)
        if not soup:
            continue
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'hitudemycoupons.com' in href and not any(
                    x in href for x in ['/category/', '/tag/', '/page/', '#']):
                psoup = get_soup(href, timeout=10)
                if not psoup:
                    continue
                t_elem = psoup.find('h1')
                title = clean_title(t_elem.text.strip()) if t_elem else ""
                if not is_relevant_course(title):
                    continue
                links = extract_udemy_links(psoup)
                if links:
                    courses.append({'title': title, 'url': links[0], 'source': 'HitUdemyCoupons'})
                    print(f"   ✅ {title[:70]}")
                time.sleep(0.3)
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 21: CheapUdemy
# ============================================================
def scrape_cheapudemy():
    print("\n🔍 CheapUdemy.com")
    courses = []

    for term in ["hacking", "security", "python", "linux"]:
        soup = get_soup(f"https://cheapudemy.com/?s={quote_plus(term)}", timeout=12)
        if not soup:
            continue
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'cheapudemy.com' in href and not any(
                    x in href for x in ['/category/', '/tag/', '/page/', '#', '?']):
                psoup = get_soup(href, timeout=10)
                if not psoup:
                    continue
                t_elem = psoup.find('h1')
                title = clean_title(t_elem.text.strip()) if t_elem else ""
                if not is_relevant_course(title):
                    continue
                links = extract_udemy_links(psoup)
                if links:
                    courses.append({'title': title, 'url': links[0], 'source': 'CheapUdemy'})
                    print(f"   ✅ {title[:70]}")
                time.sleep(0.3)
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 22: FreeCourseUdemy
# ============================================================
def scrape_freecourseudemy():
    print("\n🔍 FreeCourseUdemy.com")
    courses = []
    base_urls = [
        "https://freecourseudemy.com/category/it-software/",
        "https://freecourseudemy.com/category/development/",
    ]
    return scrape_category_listing("FreeCourseUdemy", base_urls, max_pages=3, max_posts=40)

# ============================================================
# SOURCE 23: Comidoc
# ============================================================
def scrape_comidoc():
    print("\n🔍 Comidoc.net")
    courses = []

    for term in ["hacking", "security", "python", "linux", "pentest"]:
        for url in [
            f"https://comidoc.net/search?q={quote_plus(term)}&discount=100",
            f"https://comidoc.net/search?q={quote_plus(term)}&free=true",
        ]:
            soup = get_soup(url, timeout=12)
            if not soup:
                continue
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'comidoc.net/course/' in href or (href.startswith('/course/')):
                    if href.startswith('/'):
                        href = 'https://comidoc.net' + href
                    psoup = get_soup(href, timeout=10)
                    if not psoup:
                        continue
                    t_elem = psoup.find('h1')
                    title = clean_title(t_elem.text.strip()) if t_elem else ""
                    if not is_relevant_course(title):
                        continue
                    links = extract_udemy_links(psoup)
                    if links:
                        courses.append({'title': title, 'url': links[0], 'source': 'Comidoc'})
                        print(f"   ✅ {title[:70]}")
                    time.sleep(0.3)
            time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 24: FreeCourseOnline.me
# ============================================================
def scrape_freecoursesonline():
    return scrape_wordpress_api(
        "FreeCourseOnline.me",
        "https://freecoursesonline.me",
        search_terms=["hacking", "security", "python", "linux"]
    )

# ============================================================
# SOURCE 25: BestCouponHunter
# ============================================================
def scrape_bestcouponhunter():
    print("\n🔍 BestCouponHunter.com")
    courses = []
    base_urls = [
        "https://bestcouponhunter.com/category/udemy/it-software/",
        "https://bestcouponhunter.com/category/udemy/development/",
    ]
    return scrape_category_listing("BestCouponHunter", base_urls, max_pages=3, max_posts=40)

# ============================================================
# SOURCE 26: Udemy24 (existing, kept)
# ============================================================
def scrape_udemy24():
    print("\n🔍 Udemy24.com")
    courses = []

    for term in ["hacking", "security", "python", "linux"]:
        soup = get_soup(f"https://www.udemy24.com/search?q={quote_plus(term)}", timeout=12)
        if not soup:
            continue
        post_links = []
        for a in soup.find_all('a', href=True):
            if 'udemy24.com/2' in a['href'] and a['href'] not in post_links:
                post_links.append(a['href'])

        for post_url in post_links[:15]:
            psoup = get_soup(post_url, timeout=10)
            if not psoup:
                continue
            t_elem = psoup.find('h1') or psoup.find('title')
            title = clean_title(t_elem.text.strip()) if t_elem else ""
            if not is_relevant_course(title):
                continue
            content = psoup.find('div', class_='post-body') or psoup.find('article')
            if content:
                links = extract_udemy_links(content)
                if links:
                    courses.append({'title': title, 'url': links[0], 'source': 'Udemy24'})
                    print(f"   ✅ {title[:70]}")
            time.sleep(0.4)
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# SOURCE 27: UdemyCoupon.io
# ============================================================
def scrape_udemycoupon_io():
    print("\n🔍 UdemyCoupon.io")
    courses = []

    for url in [
        "https://udemycoupon.io/category/it-software/",
        "https://udemycoupon.io/category/development/",
        "https://udemycoupon.io/",
    ]:
        soup = get_soup(url, timeout=12)
        if not soup:
            continue
        for a in soup.find_all('a', href=True):
            if 'udemy.com/course/' in a['href']:
                title = a.text.strip()
                if is_relevant_course(title):
                    courses.append({'title': clean_title(title), 'url': a['href'], 'source': 'UdemyCoupon.io'})
                    print(f"   ✅ {title[:70]}")
            elif 'udemycoupon.io' in a['href'] and not any(
                    x in a['href'] for x in ['/category/', '/page/', '#', '/tag/']):
                psoup = get_soup(a['href'], timeout=10)
                if not psoup:
                    continue
                t_elem = psoup.find('h1')
                title = clean_title(t_elem.text.strip()) if t_elem else ""
                if not is_relevant_course(title):
                    continue
                links = extract_udemy_links(psoup)
                if links:
                    courses.append({'title': title, 'url': links[0], 'source': 'UdemyCoupon.io'})
                    print(f"   ✅ {title[:70]}")
                time.sleep(0.3)
        time.sleep(0.4)

    print(f"   Total: {len(courses)}")
    return courses

# ============================================================
# DEDUP within run
# ============================================================
def dedup_courses(all_courses):
    seen = set()
    unique = []
    for c in all_courses:
        cid = extract_course_id(c['url'])
        if cid and cid not in seen:
            seen.add(cid)
            unique.append(c)
    return unique

# ============================================================
# MAIN
# ============================================================
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
    print("🚀 CouponHunter MEGA v3.0 — 27 Sources")
    print("   Focus: Hacking | Bug Bounty | Cybersecurity | Coding | Networking")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)

    sent_courses = load_sent()
    all_courses  = []
    source_stats = {}

    for name, scraper in SCRAPERS:
        try:
            result = scraper()
            all_courses.extend(result)
            source_stats[name] = len(result)
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            source_stats[name] = 0
        time.sleep(1)

    # Dedup within this run
    all_courses = dedup_courses(all_courses)
    print(f"\n📊 Total unique courses found this run: {len(all_courses)}")

    # Send new ones to Telegram
    new_count = 0
    dup_count = 0
    fail_count = 0

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
            time.sleep(2)  # Respect Telegram rate limit
        else:
            fail_count += 1

    save_sent(sent_courses)

    # Summary
    print("\n" + "=" * 80)
    print("🏁 Run Complete!")
    print(f"   ✅ New sent   : {new_count}")
    print(f"   ⏭️  Duplicates : {dup_count}")
    print(f"   ❌ Failed     : {fail_count}")
    print(f"   📚 Total tracked: {len(sent_courses)}")
    print("\n📈 Per-source breakdown:")
    for name, count in source_stats.items():
        status = "✅" if count > 0 else "⚠️ "
        print(f"   {status} {name:<22} → {count} courses")
    print("=" * 80)

if __name__ == "__main__":
    main()