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
    """進入文章抓取 Imgur 圖片直接連結"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(ptt_link, cookies={"over18": "1"}, headers=headers, timeout=5)
        match = re.search(r'https?://(?:i\.)?imgur\.com/[A-Za-z0-9]+', res.text)
        if match:
            url = match.group(0)
            if "i.imgur.com" not in url:
                url = url.replace("imgur.com", "i.imgur.com") + ".jpg"
            elif not url.endswith(('.jpg', '.png', '.jpeg')):
                url += ".jpg"
            return url
    except:
        pass
    return None

def fetch_beauty_boom():
    global beauty_posts
    while True:
        try:
            cookies = {"over18": "1"}
            all_temp_posts = []
            
            print("正在開啟時空傳送門...抓取表特版 1000 則爆文...")
            # 搜尋 recommend:100，抓取 50 頁搜尋結果
            for i in range(1, 51):
                search_url = f"https://www.ptt.cc/bbs/Beauty/search?page={i}&q=recommend%3A100"
                res = requests.get(search_url, cookies=cookies, timeout=10)
                soup = BeautifulSoup(res.text, "html.parser")
                
                arts = soup.select("div.r-ent")
                if not arts: break
                
                for art in arts:
                    t_tag = art.select_one("div.title a")
                    if t_tag and "[正妹]" in t_tag.text:
                        art_url = "https://www.ptt.cc" + t_tag["href"]
                        # 先把基本資料存入，圖片等一下顯示時再由瀏覽器加載或預抓
                        all_temp_posts.append({
                            "title": t_tag.text,
                            "url": art_url,
                            "date": art.select_one("div.date").text,
                            "img": "" # 初始為空
                        })
                
                if i % 10 == 0:
                    time.sleep(0.5)
            
            # 為了效能，我們只幫前 100 則抓圖，其他的點進去再看，避免啟動太慢
            print("正在為前 100 則精選抓取預覽圖...")
            for post in all_temp_posts[:100]:
                post['img'] = get_real_image_url(post['url'])
            
            beauty_posts = all_temp_posts
            print(f"抓取完成！共存儲 {len(beauty_posts)} 則跨年分爆文")
            
        except Exception as e:
            print(f"錯誤: {e}")
        
        time.sleep(3600) # 每小時更新一次即可

@app.route('/')
def home():
    style = """
    <style>
        body { font-family: sans-serif; background: #000; color: #fff; margin: 0; text-align: center; }
        .header { background: linear-gradient(45deg, #6200ea, #03dac5); padding: 30px; position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .search-box { width: 80%; max-width: 600px; padding: 12px; margin-top: 15px; border-radius: 25px; border: none; font-size: 16px; outline: none; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; padding: 20px; }
        .card { background: #1a1a1a; border-radius: 15px; overflow: hidden; transition: 0.3s; position: relative; height: 400px; border: 1px solid #333; }
        .card:hover { transform: scale(1.03); border-color: #03dac5; }
        .card img { width: 100%; height: 100%; object-fit: cover; }
        .info { position: absolute; bottom: 0; background: rgba(0,0,0,0.8); width: 100%; padding: 15px; box-sizing: border-box; }
        .date { font-size: 12px; color: #03dac5; }
        a { color: white; text-decoration: none; display: block; height: 100%; }
        .no-img { display: flex; align-items: center; justify-content: center; height: 100%; background: #222; color: #555; }
    </style>
    """
    
    script = """
    <script>
    function searchPosts() {
        let input = document.getElementById('searchInput').value.toLowerCase();
        let cards = document.getElementsByClassName('card');
        for (let i = 0; i < cards.length; i++) {
            let title = cards[i].innerText.toLowerCase();
            cards[i].style.display = title.includes(input) ? "" : "none";
        }
    }
    </script>
    """
    
    cards_html = ""
    for p in beauty_posts:
        img_tag = f"<img src='{p['img']}' loading='lazy'>" if p['img'] else "<div class='no-img'>點擊查看原文圖片</div>"
        cards_html += f"""
        <div class='card'>
            <a href='{p['url']}' target='_blank'>
                {img_tag}
                <div class='info'>
                    <div class='date'>{p['date']}</div>
                    {p['title']}
                </div>
            </a>
        </div>
        """

    return f"""
    <html>
        <head>
            <title>表特 1000 爆文考古</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            {style}
        </head>
        <body>
            <div class='header'>
                <h1>💎 表特版千則爆文名人堂</h1>
                <input type="text" id="searchInput" onkeyup="searchPosts()" placeholder="搜尋關鍵字 (如: 氣質, 日系, 醫生)..." class="search-box">
            </div>
            <div class='grid'>{cards_html if cards_html else '<h2>考古學家正在挖掘資料中... 請等候約 60 秒後刷新網頁。</h2>'}</div>
            {script}
        </body>
    </html>
    """

if __name__ == "__main__":
    threading.Thread(target=fetch_beauty_boom, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
