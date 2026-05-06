import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
from urllib.parse import urlparse, quote_plus

# إعداد الجلسة والمتصفح
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
})

# قائمة الكلمات المفتاحية الضخمة الخاصة بك
SEARCH_TERMS = [
    "premium apk", "pro apps", "modded apps", "unlocked apk", "android mod", "cracked software", "nova launcher setup",
    "android apps paid free", "mod apk download", "apk hacks", "تطبيقات مهكرة", "برامج برو", "أندرويد مدفوع",
    "ألعاب مهكرة", "تطبيقات معدلة", "نسخة احترافية", "machine learning", "best ai tools", "gpt4", "ai automation",
    "chatgpt tools", "ai prompts", "openai tools", "llm tools", "ذكاء اصطناعي", "أدوات الذكاء", "بوتات تليجرام",
    "تقنيات حديثة", "شروحات تقنية", "free courses", "udemy coupons", "programming scripts", "github repos",
    "python coding", "excel tutorials", "data analysis python", "automation scripts", "كورسات مجانية", 
    "دورة برمجية", "تعليم إكسيل", "تعلم البرمجة", "مكتبات بايثون", "كتب تقنية", "uae offers", "dubai discounts",
    "coupon codes", "amazon deals uae", "noon coupons", "uae promo codes", "dubai deals today", "عروض الإمارات",
    "أكواد خصم", "تخفيضات دبي", "وفر فلوسك", "iptv links", "netflix premium", "movies hd", "live tv", "series hd",
    "arab movies", "قنوات مشفرة", "أفلام وثائقية", "بث مباشر", "سيرفرات iptv", "مسلسلات حصرية", "free api key",
    "free llm", "open source tools", "telegram bots", "automation tools", "مواقع مفيدة", "قنوات مفيدة",
    "معلومات عامة", "telegram search engine", "telegram directory", "telegram channels list", "telegram search bot",
    "محرك بحث تيليجرام", "بحث قنوات تيليجرام", "دليل قنوات تيليجرام", "اكتشاف قنوات"
]

PER_PAGE = 10
MAX_PAGES = 5 # لضمان عدم تجاوز وقت GitHub Actions (6 ساعات)
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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = session.get(url, allow_redirects=is_telegram, timeout=15)
            if r.status_code == 429:
                time.sleep(60)
                continue
            if r.status_code == 200:
                return r.text
        except:
            time.sleep(5)
    return None

def get_channels(term, page):
    url = build_search_url(term, page)
    html_content = fetch_with_retry(url)
    if not html_content: return []
    
    soup = BeautifulSoup(html_content, "html.parser")
    data = []
    for card in soup.select("li.search-result"):
        a = card.select_one("a[href*='t.me']")
        if a:
            username = extract_username(a["href"])
            title_el = card.select_one(".search-result-title")
            title = title_el.text.strip() if title_el else "N/A"
            if username: data.append((title, username, term))
    return data

def get_subscribers(username):
    url = f"https://t.me/{username}"
    html_content = fetch_with_retry(url, is_telegram=True)
    if not html_content: return "error"
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        el = soup.select_one(".tgme_page_extra")
        return el.text.strip() if el else "N/A"
    except: return "error"

def main():
    new_data = []
    seen = set()
    old_data_count = 0

    # 1. تحميل البيانات القديمة لتجنب التكرار وللإضافة عليها
    if os.path.exists(SAVE_FILE):
        try:
            old_df = pd.read_csv(SAVE_FILE)
            if not old_df.empty:
                # استخراج اليوزر نيم من اللينك لتخزينه في الـ seen
                seen = set(old_df['link'].apply(lambda x: x.split('/')[-1]).tolist())
                old_data_count = len(old_df)
                print(f"[*] Found {old_data_count} existing channels. I will only add new ones.")
        except Exception as e:
            print(f"[!] Warning: Could not read old file, starting fresh. {e}")

    # 2. بدء عملية السحب
    for term in SEARCH_TERMS:
        print(f"\n=== Searching: {term} ===")
        for page in range(1, MAX_PAGES + 1):
            print(f"[*] Page {page}")
            channels = get_channels(term, page)
            if not channels: break

            for title, username, term_used in channels:
                if username in seen:
                    continue # تخطي القناة لو كانت موجودة مسبقاً

                seen.add(username)
                subs = get_subscribers(username)
                print(f"  + New: {username} -> {subs}")

                new_data.append({
                    "search_term": term_used,
                    "title": title,
                    "link": f"https://t.me/{username}",
                    "subscribers": subs
                })
                time.sleep(random.uniform(1.5, 3.5))
            
            time.sleep(random.uniform(2, 4))

    # 3. الدمج والحفظ النهائي
    if new_data:
        new_df = pd.DataFrame(new_data)
        
        # لو فيه بيانات قديمة، ادمجهم مع بعض
        if old_data_count > 0:
            final_df = pd.concat([old_df, new_df], ignore_index=True)
        else:
            final_df = new_df

        # تنظيف وترتيب البيانات
        def extract_number(text):
            try:
                return int(str(text).split()[0].replace(",", ""))
            except:
                return 0

        final_df["subs_num"] = final_df["subscribers"].apply(extract_number)
        final_df = final_df.sort_values(by="subs_num", ascending=False).drop_duplicates(subset=['link'])
        final_df.drop(columns=["subs_num"], inplace=True)
        
        final_df.to_csv(SAVE_FILE, index=False, encoding="utf-8-sig")
        print(f"\n[+] Task Completed. Added {len(new_data)} new channels. Total: {len(final_df)}")
    else:
        print("\n[-] No new channels found in this run.")

if __name__ == "__main__":
    main()
