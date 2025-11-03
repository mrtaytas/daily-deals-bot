# deals.py
import os, re, time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

AMAZON_TAG   = os.getenv("AMAZON_TAG", "")      # ör: murataytas-21
HEPSI_AFF_ID = os.getenv("HEPSI_AFF_ID", "")    # ör: 1234
TRENDYOL_AFF = os.getenv("TRENDYOL_AFF", "")    # ör: senin-partner-param

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"}

def clean(s): return re.sub(r"\s+", " ", (s or "")).strip()

def send_telegram(text: str):
    if not (BOT_TOKEN and CHAT_ID):
        print("Telegram secrets eksik.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }, timeout=60)
    if r.status_code != 200:
        print("Telegram hata:", r.text)

def add_affiliates(url: str) -> str:
    u = url
    if "amazon.com.tr" in u and "tag=" not in u and AMAZON_TAG:
        u += ("&" if "?" in u else "?") + f"tag={AMAZON_TAG}"
    if "hepsiburada.com" in u and "aff_id=" not in u and HEPSI_AFF_ID:
        u += ("&" if "?" in u else "?") + f"aff_id={HEPSI_AFF_ID}&utm_source=affiliate"
    if "trendyol.com" in u and TRENDYOL_AFF and "utm_source=" not in u:
        u += ("&" if "?" in u else "?") + f"utm_source=affiliate&utm_medium=partner&utm_campaign={TRENDYOL_AFF}"
    return u

def fetch_html(url: str):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    return r.text

def get_amazon_deals(limit=5):
    items = []
    try:
        url = "https://www.amazon.com.tr/gp/goldbox"
        soup = BeautifulSoup(fetch_html(url), "html.parser")
        cards = soup.select("[data-component-type='s-deal-card'], .DealGridItem-module__dealItem")
        for c in cards:
            a = c.find("a", href=True)
            if not a: 
                continue
            link = a["href"]
            link = "https://www.amazon.com.tr" + link if link.startswith("/") else link
            title = clean(c.get_text(" "))
            price_el = c.select_one(".a-price .a-offscreen, .a-price-whole")
            price = clean(price_el.get_text()) if price_el else ""
            if title and len(title) > 20:
                items.append({"title": title[:120], "price": price, "link": add_affiliates(link)})
                if len(items) >= limit:
                    break
    except Exception as e:
        print("Amazon hata:", e)
    return items

def get_hepsiburada_deals(limit=5):
    items = []
    try:
        url = "https://www.hepsiburada.com/indirimler"
        soup = BeautifulSoup(fetch_html(url), "html.parser")
        anchors = soup.select("a[href*='/urun/'], a[href*='/kampanya/']")
        for a in anchors:
            t = clean(a.get_text())
            if len(t) < 20:
                continue
            href = a.get("href", "")
            link = "https://www.hepsiburada.com" + href if href.startswith("/") else href
            items.append({"title": t[:120], "price": "", "link": add_affiliates(link)})
            if len(items) >= limit:
                break
    except Exception as e:
        print("Hepsiburada hata:", e)
    return items

def get_trendyol_deals(limit=5):
    items = []
    try:
        url = "https://www.trendyol.com/sr?sst=BEST_SELLER"
        soup = BeautifulSoup(fetch_html(url), "html.parser")
        cards = soup.select("div.p-card-wrppr a[href*='-p-']")
        for a in cards:
            href = a.get("href", "")
            link = "https://www.trendyol.com" + href if href.startswith("/") else href
            title = clean(a.get_text())
            price_el = a.select_one(".prc-box-dscntd, .prc-box-sllng")
            price = clean(price_el.get_text()) if price_el else ""
            if len(title) > 15:
                items.append({"title": title[:120], "price": price, "link": add_affiliates(link)})
                if len(items) >= limit:
                    break
    except Exception as e:
        print("Trendyol hata:", e)
    return items

def format_message(results: dict) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"<b>Günlük İndirim Özeti</b> ({ts})"]
    for site, arr in results.items():
        lines.append(f"\n<b>— {site} —</b>")
        if not arr:
            lines.append("• Bugün sonuç yok veya erişim kısıtlı.")
            continue
        for it in arr:
            p = f" — <b>{it['price']}</b>" if it.get("price") else ""
            lines.append(f"• {it['title']}{p}\n{it['link']}")
    msg = "\n".join(lines)
    return msg[:4000]  # Telegram sınırı

def main():
    amazon = get_amazon_deals(5)
    trendy  = get_trendyol_deals(5)
    hepsi   = get_hepsiburada_deals(5)
    msg = format_message({"Amazon": amazon, "Trendyol": trendy, "Hepsiburada": hepsi})
    send_telegram(msg)

if __name__ == "__main__":
    main()
