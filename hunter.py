#!/usr/bin/env python3
"""
Hybrid Ultra Scraper - Fixed (filters non-http candidates and reduces noisy errors)
Replace your old hunter.py with this file.
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
    "RealDiscount_Udemy": {"url": "https://www.real.discount/udemy", "use_playwright": False},
    "UdemyFreebies": {"url": "https://www.udemyfreebies.com/", "use_playwright": False},
    "CourseCouponClub": {"url": "https://coursecouponclub.com/", "use_playwright": True},
    "InfoGnu": {"url": "https://infognu.com/", "use_playwright": False},
}

KEYWORDS = ["hacking","hack","ethical hacking","pentest","pentesting","bug bounty","cybersecurity","security","kali","nmap"]
KEYWORDS_SET = set(k.lower() for k in KEYWORDS)

DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}

UDEMY_REGEX = re.compile(r'(https?://(?:www\.)?udemy\.com/course/[A-Za-z0-9\-\_]+(?:[/?#&][^\s"\'<>]*)?)', re.I)
UDEMY_ESCAPED = re.compile(r'(https?:\\\\/\\\\/[^\'"]*udemy\.com\\/course\\/[A-Za-z0-9\-\_]+)', re.I)
BASE64_TOKEN = re.compile(r'["\']([A-Za-z0-9+/=]{48,})["\']')

PLAYWRIGHT_NAV_TIMEOUT = 30_000
PLAYWRIGHT_MAX_ARTICLES = 200

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
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])
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
            f"<b>🔥 100% FREE UDEMY COURSE FOUND!</b>\n\n"
            f"<b>{html.escape(title)}</b>\n"
            f"Source: {html.escape(source)}\n"
            f"<a href=\"{html.escape(link)}\">Get it on Udemy — Click here</a>\n"
            f"Found: {now()}"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}, timeout=12)
        if resp.status_code == 200:
            log(f"✅ Telegram sent: {title[:80]}")
            return True
        else:
            log(f"❌ Telegram error ({resp.status_code}): {resp.text[:160]}")
            return False
    except Exception as e:
        log(f"❌ Telegram exception: {e}")
        return False

# ---------- Extraction helpers ----------
def extract_udemy_from_text(text):
    found = set()
    if not text:
        return found
    for m in UDEMY_REGEX.finditer(text):
        found.add(m.group(1).rstrip('"\').,; '))
    for m in UDEMY_ESCAPED.finditer(text):
        dec = m.group(1).replace('\\\\/','/').replace('\\/','/').replace('http:\\/\\/','http://').replace('https:\\/\\/','https://')
        found.add(dec)
    for tok in BASE64_TOKEN.findall(text):
        try:
            dec = base64.b64decode(tok + '===').decode('utf-8', errors='ignore')
            if 'udemy.com/course' in dec:
                found.add(dec)
        except:
            pass
    cleaned = set()
    for u in found:
        try:
            cleaned.add(unquote(html.unescape(u)))
        except:
            cleaned.add(u)
    return cleaned

def decode_targets_from_query(url):
    found = set()
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for k, vals in qs.items():
            if any(x in k.lower() for x in ('url','to','target','redirect','link','u')):
                for v in vals:
                    v2 = unquote(v)
                    if 'udemy.com/course' in v2:
                        found.add(v2)
                    if len(v2) > 40 and re.match(r'^[A-Za-z0-9+/=]+$', v2):
                        try:
                            dec = base64.b64decode(v2 + '===').decode('utf-8', errors='ignore')
                            if 'udemy.com/course' in dec:
                                found.add(dec)
                        except:
                            pass
    except:
        pass
    return found

def is_valid_http_url(u):
    if not u:
        return False
    u = u.strip()
    # AGGRESSIVE: reject any non-http schemes
    u_lower = u.lower()
    bad_schemes = ('javascript:', 'mailto:', 'tel:', 'data:', 'void', '#', 'ftp:')
    for scheme in bad_schemes:
        if u_lower.startswith(scheme):
            return False
    if '#' in u or u in ("/", ""):
        return False
    parsed = urlparse(u)
    # allow relative paths (start with /), or http/https absolute
    if parsed.scheme in ('http','https'):
        return True
    if not parsed.scheme and u.startswith("/"):
        return True
    return False

def is_probably_free(title, content=""):
    """Check if title/content indicates a free course."""
    combined = (title + " " + str(content)).lower()
    free_keywords = ("100% off", "free", "coupon", "$0", "free course", "free udemy", "no cost")
    return any(k in combined for k in free_keywords)

def resolve_and_extract(session, candidate_url):
    """Follow redirects and inspect body/params — but only for valid http urls."""
    found = set()
    try:
        if not is_valid_http_url(candidate_url):
            # Skip non-http URLs silently
            return found
        found |= decode_targets_from_query(candidate_url)
        try:
            r = session.get(candidate_url, timeout=12, allow_redirects=True)
            r.encoding = r.apparent_encoding or 'utf-8'
        except Exception as e:
            # Reduced logging noise - skip logging for non-fatal candidate errors
            return found
        try:
            chain_urls = [h.url for h in (r.history or [])] + [r.url]
        except:
            chain_urls = [getattr(r, 'url', candidate_url)]
        for u in chain_urls:
            if 'udemy.com/course' in u.lower():
                found.add(u)
        found |= extract_udemy_from_text(r.text)
        # base64 tokens in body
        for tok in BASE64_TOKEN.findall(r.text or ""):
            try:
                dec = base64.b64decode(tok + '===').decode('utf-8', errors='ignore')
                if 'udemy.com/course' in dec:
                    found.add(dec)
            except:
                pass
    except Exception as e:
        log(f"   ⚠️ resolve_and_extract unexpected error: {e}")
    return found

# ---------- Requests-based scraper ----------
def scrape_requests_source(session, source_name, source_url):
    results = []
    log(f"🔍 (requests) Scanning: {source_name} -> {source_url}")
    try:
        r = session.get(source_url, timeout=12)
        r.encoding = r.apparent_encoding or 'utf-8'
    except Exception as e:
        log(f"   ⚠️ GET failed for {source_url}: {e}")
        return results

    soup = BeautifulSoup(r.text, "html.parser")
    page_title = (soup.title.string or "").strip() if soup.title else source_name
    meta_desc = ""
    md = soup.find('meta', attrs={'name':'description'})
    if md and md.get('content'):
        meta_desc = md['content']

    # page-level direct udemy links
    page_found = extract_udemy_from_text(r.text)
    for u in page_found:
        results.append({"title": page_title, "link": u, "source": source_name, "post_link": source_url})
    if page_found:
        log(f"   ✓ Page-level direct: {len(page_found)}")

    # examine anchors + data- attributes
    processed = set()
    tags = soup.find_all(['a','button','input'])
    for tag in tags:
        try:
            cands = set()
            # common attrs
            href = tag.get('href') or tag.get('data-href') or tag.get('data-url') or ""
            if href:
                # normalize relative
                full = urljoin(source_url, href.strip())
                if is_valid_http_url(full):
                    cands.add(full)
            for attr in ('data-href','data-url','data-clipboard-text','data-link','data-redirect','value'):
                v = tag.get(attr)
                if v:
                    full = urljoin(source_url, str(v).strip())
                    if is_valid_http_url(full):
                        cands.add(full)
            onclick = tag.get('onclick') or ''
            if onclick:
                for m in re.findall(r'(https?://[^\)\'"]+)', onclick):
                    if is_valid_http_url(m):
                        cands.add(m.strip())
            text = (tag.get_text(" ", strip=True) or "")
            if 'http' in text:
                for u in extract_udemy_from_text(text):
                    if is_valid_http_url(u):
                        cands.add(u)

            for cand in list(cands):
                if not cand or cand in processed:
                    continue
                # Skip obviously invalid URLs early
                if not is_valid_http_url(cand):
                    continue
                processed.add(cand)

                if 'udemy.com/course' in cand.lower():
                    # direct Udemy link - accept if heuristics show free
                    title = (tag.get_text(" ", strip=True) or page_title)[:150]
                    if is_probably_free(title, meta_desc):
                        results.append({"title": title, "link": cand, "source": source_name, "post_link": source_url})
                        log(f"    ✓ Direct udemy href: {title[:80]}")
                    continue

                # otherwise resolve the candidate
                resolved = resolve_and_extract(session, cand)
                if resolved:
                    inner_title = (tag.get_text(" ", strip=True) or page_title)[:150]
                    for u in resolved:
                        if is_probably_free(inner_title, r.text[:1000]):
                            results.append({"title": inner_title, "link": u, "source": source_name, "post_link": cand})
                            log(f"    ✓ Resolved -> Udemy: {u}")
                time.sleep(0.05)
        except Exception as e:
            # keep single-line log to avoid spam
            log(f"   ⚠️ tag processing error (non-fatal): {e}")
            continue

    # dedupe
    uniq = {}
    for it in results:
        if it['link'] not in uniq:
            uniq[it['link']] = it
    final = list(uniq.values())
    log(f"  ✅ {len(final)} courses found (requests) on {source_name}")
    return final

# ---------- Playwright-based scraper ----------
def scrape_playwright_source(requests_session, source_name, source_url, max_articles=PLAYWRIGHT_MAX_ARTICLES, headless=True):
    results = []
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except Exception:
        log("⚠️ Playwright not installed - skipping Playwright sources (install playwright if needed).")
        return results

    log(f"🔍 (playwright) Scanning: {source_name} -> {source_url}")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto(source_url, timeout=PLAYWRIGHT_NAV_TIMEOUT, wait_until="domcontentloaded")
            except PWTimeout:
                log(f"   ⚠️ playwright page load timeout for {source_url}")
            except Exception as e:
                log(f"   ⚠️ playwright page load error: {e}")

            # gather candidate links (filtering out javascript:, fragments, etc.)
            candidates = set()
            try:
                anchors = page.query_selector_all("a[href]")
                for a in anchors:
                    try:
                        href = a.get_attribute("href") or ""
                        href_full = urljoin(source_url, href)
                        txt = (a.inner_text() or "").lower()
                        # heuristics: include likely article/coupon links or direct udemy
                        if is_valid_http_url(href_full) and any(x in href_full.lower() for x in ('coupon','free','udemy','course','deal','/free-')) or ('100%' in txt or 'free' in txt):
                            candidates.add(href_full)
                    except Exception:
                        continue

                # also check page HTML for direct udemy
                page_html = page.content()
                for u in UDEMY_REGEX.findall(page_html):
                    if is_valid_http_url(u):
                        candidates.add(u)
            except Exception as e:
                log(f"   ⚠️ playwright candidate gather error: {e}")

            candidates = list(candidates)[:max_articles]
            log(f"   Candidates to open: {len(candidates)}")

            for art in candidates:
                try:
                    # skip invalid URLs (javascript:, fragments, etc.)
                    if not is_valid_http_url(art):
                        continue
                    # extra safety: skip base64-looking URLs
                    if 'javascript' in art.lower() or 'void' in art.lower():
                        continue
                    art_page = context.new_page()
                    try:
                        art_page.goto(art, timeout=PLAYWRIGHT_NAV_TIMEOUT, wait_until="domcontentloaded")
                    except PWTimeout:
                        log(f"     ⚠️ Article load timeout: {art}")
                    except Exception:
                        pass

                    html_content = art_page.content()
                    found = extract_udemy_from_text(html_content)

                    # anchors in article page
                    try:
                        anchors = art_page.query_selector_all("a")
                        for a in anchors:
                            try:
                                href = a.get_attribute("href") or ""
                                if href and is_valid_http_url(href) and "udemy.com/course" in href.lower():
                                    found.add(urljoin(art_page.url, href))
                            except:
                                pass
                    except:
                        pass

                    # click coupon-like buttons (best effort)
                    if not found:
                        try:
                            btns = art_page.query_selector_all("a,button,input")
                            for b in btns:
                                try:
                                    label = ((b.inner_text() or "") + " " + (b.get_attribute("value") or "")).lower()
                                    if any(k in label for k in ('coupon','get coupon','claim','get it','grab','free')):
                                        # attempt to click and capture popup
                                        try:
                                            with context.expect_page(timeout=3000) as new_page_info:
                                                b.click(timeout=2000)
                                            newp = new_page_info.value
                                            found |= extract_udemy_from_text(newp.content())
                                            try:
                                                newp.close()
                                            except:
                                                pass
                                        except Exception:
                                            # fallback to href attr
                                            href = b.get_attribute("href") or ""
                                            if href and is_valid_http_url(href) and "udemy" in href.lower():
                                                found |= extract_udemy_from_text(href)
                                except Exception:
                                    continue
                        except Exception:
                            pass

                    # resolve relative/redirect links found in article DOM using requests_session
                    try:
                        for tag in art_page.query_selector_all("[href], [data-href], [data-url], [data-redirect], [onclick]"):
                            try:
                                h = tag.get_attribute("href") or tag.get_attribute("data-href") or tag.get_attribute("data-url") or ""
                                if h:
                                    full = urljoin(art_page.url, h)
                                    if is_valid_http_url(full):
                                        resolved = resolve_and_extract(requests_session, full)
                                        found |= resolved
                            except Exception:
                                pass
                    except Exception:
                        pass

                    for u in found:
                        results.append({"title": art_page.title() or art, "link": u, "source": source_name, "post_link": art})
                    try:
                        art_page.close()
                    except:
                        pass
                    time.sleep(0.08)
                except Exception as e:
                    log(f"     ⚠️ playwright article error (non-fatal): {e}")
                    continue

            try:
                page.close()
            except:
                pass
            browser.close()
    except Exception as e:
        log(f"   ⚠️ Playwright outer error (non-fatal): {e}")

    # dedupe
    uniq = {}
    for r in results:
        if r['link'] not in uniq:
            uniq[r['link']] = r
    final = list(uniq.values())
    log(f"  ✅ {len(final)} courses found (playwright) on {source_name}")
    return final

# ---------- Hybrid driver ----------
def start_scan():
    log("="*60)
    log("🚀 Starting Hybrid CouponHunter (Fixed)")
    log("="*60)
    session = setup_session()
    history = load_history()
    sent_links = set(history.get("sent_links", []))
    sent_courses = set(history.get("sent_courses", []))
    all_courses = []
    new_finds = 0

    for name, meta in PREMIUM_SOURCES.items():
        url = meta.get("url")
        use_play = bool(meta.get("use_playwright", False))
        if not url:
            log(f"⏭️ Skipping invalid source: {name}")
            continue
        try:
            if use_play:
                courses = scrape_playwright_source(session, name, url)
            else:
                courses = scrape_requests_source(session, name, url)
            all_courses.extend(courses)
        except Exception as e:
            log(f"❌ Error scanning {name}: {e}")
        time.sleep(0.6)

    # dedupe & send
    sent_this_run = set()
    for c in all_courses:
        try:
            m = re.search(r'/course/([A-Za-z0-9\-\_]+)', c['link'], re.I)
            cid = m.group(1).lower() if m else c['link']
            if c['link'] in sent_links or cid in sent_courses or cid in sent_this_run:
                log(f"⏭️ Duplicate: {c['title'][:50]}")
                continue
            if send_telegram(c['title'], c['link'], c.get('source','')):
                sent_links.add(c['link'])
                sent_courses.add(cid)
                sent_this_run.add(cid)
                new_finds += 1
                try:
                    with open(SENT_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{c['link']} | {c['title']} | {c.get('source','')}\n")
                except:
                    pass
        except Exception as e:
            log(f"❌ Error sending course (non-fatal): {e}")

    history["sent_links"] = list(sent_links)
    history["sent_courses"] = list(sent_courses)
    save_history(history)

    log("="*60)
    log(f"🏁 Scan complete! New finds: {new_finds}. Total tracked: {len(sent_courses)}")
    log("="*60)

if __name__ == "__main__":
    start_scan()
