import requests
from bs4 import BeautifulSoup
import time
import threading
from flask import Flask
import os
import re

app = Flask(__name__)

# 全部圖片存在這（單純 img url list）
ALL_IMAGES = []

def get_all_img_urls(link):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.ptt.cc"
        }
        res = requests.get(
            link,
            cookies={"over18": "1"},
            headers=headers,
            timeout=10
        )

        html = res.text
        imgs = set()

        # 1️⃣ 直接抓 i.imgur.com 圖片
        direct = re.findall(
            r'https?://i\.imgur\.com/[A-Za-z0-9]+\.(?:jpg|jpeg|png|gif)',
            html,
            re.IGNORECASE
        )
        imgs.update(direct)

        # 2️⃣ imgur.com/xxxx → 轉直連
        pages = re.findall(
            r'https?://imgur\.com/([A-Za-z0-9]+)',
            html
        )
        for img_id in pages:
            imgs.add(f"https://i.imgur.com/{img_id}.jpg")

        return list(imgs)

    except Exception as e:
        print("抓圖錯誤:", e, flush=True)
        return []

def fetch_data():
    global ALL_IMAGES
    print(">>> 啟動只看圖片模式", flush=True)

    while True:
        try:
            imgs_pool = []

            print(">>> 開始抓 Beauty 爆文", flush=True)

            for page in range(1, 51):
                url = f"https://www.ptt.cc/bbs/Beauty/search?page={page}&q=recommend%3A100"
                r = requests.get(url, cookies={"over18": "1"}, timeout=10)
                soup = BeautifulSoup(r.text, "html.parser")
                arts = soup.select("div.r-ent")

                if not arts:
                    break

                for art in arts:
                    t = art.select_one("div.title a")
                    if t and "[正妹]" in t.text:
                        link = "https://www.ptt.cc" + t["href"]
                        imgs = get_all_img_urls(link)
                        imgs_pool.extend(imgs)

                time.sleep(0.5)

            # 去重
            ALL_IMAGES = list(dict.fromkeys(imgs_pool))
            print(f">>> 完成，共 {len(ALL_IMAGES)} 張圖片", flush=True)

        except Exception as e:
            print(">>> 主流程錯誤:", e, flush=True)

        time.sleep(1800)  # 30 分鐘更新一次

@app.route('/')
def home():
    style = """
    <style>
        body {
            margin: 0;
            background: #000;
        }
        .gallery {
            column-count: 3;
            column-gap: 8px;
            padding: 8px;
        }
        img {
            width: 100%;
            margin-bottom: 8px;
            border-radius: 6px;
            break-inside: avoid;
        }
        @media (max-width: 900px) {
            .gallery { column-count: 2; }
        }
        @media (max-width: 600px) {
            .gallery { column-count: 1; }
        }
    </style>
    """

    if not ALL_IMAGES:
        imgs_html = "<h2 style='color:#555;text-align:center;padding:50px;'>圖片載入中…</h2>"
    else:
        imgs_html = "".join(
            f"<img src='{img}' loading='lazy'>" for img in ALL_IMAGES
        )

    return f"""
    <html>
        <head>
            <title>Images Only</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            {style}
        </head>
        <body>
            <div class="gallery">
                {imgs_html}
            </div>
        </body>
    </html>
    """

if __name__ == "__main__":
    threading.Thread(target=fetch_data, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

