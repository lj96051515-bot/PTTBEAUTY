import requests
from bs4 import BeautifulSoup
import time
import threading
from flask import Flask
import os
import re

app = Flask(__name__)
beauty_posts = []

def get_real_image_url(ptt_link):
    """強化版：進入文章抓取 Imgur 或圖片網址"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(ptt_link, cookies={"over18": "1"}, headers=headers, timeout=5)
        # 尋找 Imgur ID
        imgur_match = re.search(r'https?://(?:i\.)?imgur\.com/([A-Za-z0-9]+)', res.text)
        if imgur_match:
            return f"https://i.imgur.com/{imgur_match.group(1)}.jpg"
        # 尋找直接連結
        other_match = re.search(r'https?://[^\s\'"]+\.(?:jpg|jpeg|png|gif)', res.text)
        if other_match:
            return other_match.group(0)
    except: pass
    return None

def fetch_beauty_boom():
    global beauty_posts
    cookies = {"over18": "1"}
    while True:
        try:
            all_temp_posts = []
            print("開始抓取前 10 則爆文...")
            
            # 第一階段：先抓第 1 頁（快速顯示）
            search_url = "https://www.ptt.cc/bbs/Beauty/search?page=1&q=recommend%3A100"
            res = requests.get(search_url, cookies=cookies, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            arts = soup.select("div.r-ent")
            
            for art in arts:
                t_tag = art.select_one("div.title a")
                if t_tag and "[正妹]" in t_tag.text:
                    url = "https://www.ptt.cc" + t_tag["href"]
                    # 直接抓圖
                    img = get_real_image_url(url)
                    all_temp_posts.append({
                        "title": t_tag.text, "url": url, 
                        "date": art.select_one("div.date").text, "img": img
                    })
            
            # 存入前 10 則讓網頁先有東西看
            beauty_posts = all_temp_posts[:10]
            print("前 10 則已上線！開始挖掘後續 990 則...")

            # 第二階段：挖掘剩下的 49 頁 (背景執行)
            for i in range(2, 51):
                search_url = f"https://www.ptt.cc/bbs/Beauty/search?page={i}&q=recommend%3A100"
                res = requests.get(search_url, cookies=cookies, timeout=10)
                soup = BeautifulSoup(res.text, "html.parser")
                for art in soup.select("div.r-ent"):
                    t_tag = art.select_one("div.title a")
                    if t_tag and "[正妹]" in t_tag.text:
                        url = "https://www.ptt.cc" + t_tag["href"]
                        all_temp_posts.append({
                            "title": t_tag.text, "url": url, 
                            "date": art.select_one("div.date").text, "img": ""
                        })
                if i % 5 == 0: time.sleep(0.3)
            
            # 更新完整清單
            beauty_posts = all_temp_posts
            print("1000 則爆文資料庫同步完畢")
            
        except Exception as e:
            print(f"錯誤: {e}")
        time.sleep(3600)

@app.route('/')
def home():
    style = """
    <style>
        body { font-family: sans-serif; background: #000; color: #fff; margin: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; padding: 20px; }
        .card { background: #111; border-radius: 10px; overflow: hidden; height: 450px; border: 1px solid #333; }
        .card img { width: 100%; height: 80%; object-fit: cover; }
        .info { padding: 10px; font-size: 14px; }
        a { color: #eee; text-decoration: none; }
    </style>
    """
    cards = "".join([f"""
        <div class='card'>
            <a href='{p['url']}' target='_blank'>
                <img src='{p['img'] if p['img'] else "https://placehold.co/400x600/222/555?text=Click+to+View"}'>
                <div class='info'>[{p['date']}] {p['title']}</div>
            </a>
        </div>
    """ for p in beauty_posts])

    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{style}</head><body><h2 style='text-align:center; color:pink;'>PTT 表特爆文精選</h2><div class='grid'>{cards if cards else '挖掘中...請稍候刷新'}</div></body></html>"

if __name__ == "__main__":
    threading.Thread(target=fetch_beauty_boom, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
