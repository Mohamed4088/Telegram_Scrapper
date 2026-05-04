import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from urllib.parse import urlparse, quote_plus

# استخدام Session لتقليل استهلاك الموارد وتسريع الاتصال (Connection Pooling)
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
})

SEARCH_TERMS = [
    "android",
    "ai tools",
    "machine learning"
]

PER_PAGE = 10
MAX_PAGES = 50
SAVE_FILE = "telegram_channels.csv"

def build_search_url(term, page):
    q = quote_plus(term)
    return f"https://lyzem.com/search?q={q}&f=all&l=&p={page}&per-page={PER_PAGE}"

def extract_username(url):
    try:
        path = urlparse(url).path.strip("/")
        return path.split("/")[0]
    except:
        return None

def fetch_with_retry(url, is_telegram=False):
    """دالة للتعامل مع الحظر المؤقت (Rate Limits) وأخطاء الاتصال"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = session.get(url, allow_redirects=is_telegram, timeout=15)
            
            if r.status_code == 429:
                print(f"  [!] Rate Limit (429) hit. Sleeping for 60 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(60)
                continue
                
            if r.status_code == 200:
                return r.text
            else:
                print(f"  [!] HTTP Error {r.status_code} for {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"  [!] Connection Error: {e}")
            time.sleep(5)
            
    return None

def get_channels(term, page):
    url = build_search_url(term, page)
    html_content = fetch_with_retry(url)
    
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    data = []

    for card in soup.select("li.search-result"):
        a = card.select_one("a[href*='t.me']")
        if not a:
            continue

        link = a["href"]
        username = extract_username(link)
        title_el = card.select_one(".search-result-title")
        title = title_el.text.strip() if title_el else "N/A"

        if username:
            data.append((title, username, term))

    return data

def get_subscribers(username):
    url = f"https://t.me/{username}"
    html_content = fetch_with_retry(url, is_telegram=True)
    
    if not html_content:
        return "error"

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        el = soup.select_one(".tgme_page_extra")
        if el:
            return el.text.strip()
        return "N/A"
    except:
        return "error"

def save_checkpoint(data_list):
    """حفظ البيانات بشكل دوري لتجنب ضياعها إذا تم فصل جلسة Colab"""
    df = pd.DataFrame(data_list)
    df.to_csv(SAVE_FILE, index=False, encoding="utf-8-sig")

def main():
    all_data = []
    seen = set()

    for term in SEARCH_TERMS:
        print(f"\n=== Searching: {term} ===")
        page = 1

        while page <= MAX_PAGES:
            print(f"[*] {term} - Page {page}")
            channels = get_channels(term, page)

            if not channels:
                print("[-] No more results or blocked.")
                break

            for title, username, term_used in channels:
                if username in seen:
                    continue

                seen.add(username)
                subs = get_subscribers(username)
                print(f"  -> {username}: {subs}")

                all_data.append({
                    "search_term": term_used,
                    "title": title,
                    "link": f"https://t.me/{username}",
                    "subscribers": subs
                })

                # توقف عشوائي لتجنب اكتشاف البوت
                time.sleep(random.uniform(1.5, 3.5))

            # حفظ نقطة تحقق كل صفحة لتأمين البيانات
            save_checkpoint(all_data)
            
            # توقف أطول قليلاً بين الصفحات
            time.sleep(random.uniform(3.0, 5.0))
            page += 1

    # الترتيب النهائي
    df = pd.read_csv(SAVE_FILE)
    
    def extract_number(text):
        try:
            return int(str(text).split()[0].replace(",", ""))
        except:
            return 0

    df["subs_num"] = df["subscribers"].apply(extract_number)
    df = df.sort_values(by="subs_num", ascending=False)
    
    # تنظيف العمود الإضافي قبل الحفظ النهائي
    df.drop(columns=["subs_num"], inplace=True)
    df.to_csv(SAVE_FILE, index=False, encoding="utf-8-sig")

    print(f"\n[+] Task Completed. Data saved to {SAVE_FILE}")

if __name__ == "__main__":
    main()
