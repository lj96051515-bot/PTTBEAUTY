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
    """
    強化版爬圖邏輯：進入文章抓取 Imgur 或其他圖片網址
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(ptt_link, cookies={"over18": "1"}, headers=headers, timeout=5)
        
        # 1. 優先搜尋 Imgur 的各種格式 (包含相簿 /a/ 或直接圖片)
        # Regex 會抓取含有 imgur.com 的字串
        imgur_match = re.search(r'https?://(?:i\.)?imgur\.com/([A-Za-z0-9]+)(?:\.[a-z]+)?', res.text)
        
        if imgur_match:
            img_id = imgur_match.group(1)
            # 強制轉換為 i.imgur.com/xxxx.jpg 格式，這是最穩定的直接顯圖網址
            return f"https://i.imgur.com/{img_id}.jpg"
        
        # 2. 如果沒找到 Imgur，尋找任何以 jpg, png, jpeg 結尾的網址
        other_match = re.search(r'https?://[^\s\'"]+\.(?:jpg|jpeg|png|gif)', res.text)
        if other_match:
            return other_match.group(0)
            
    except Exception as e:
        print(f"爬取圖片網址失敗 ({ptt_link}): {e}")
    return None

def fetch_beauty_boom():
    global beauty_posts
    while True:
        try:
            cookies = {"over18": "1"}
            all_temp_posts = []
            
            print("正在掃描表特版 1000 則爆文資料...")
            # 搜尋 recommend:100 (爆文)，抓取前 50 頁搜尋結果
            for i in range(1, 51):
                search_url = f"https://www.ptt.cc/bbs/Beauty/search?page={i}&q=recommend%3A100"
                res = requests.get(search_url, cookies=cookies, timeout=10)
                soup = BeautifulSoup(res.text, "html.parser")
                
                arts = soup.select("div.r-ent")
                if not arts: break
                
                for art in arts:
                    t_tag = art.select_one("div.title a")
                    # 只抓標題有 [正妹] 的文章，過濾掉 [公告] 或 [帥哥]
                    if t_tag and "[正妹]" in t_tag.text:
                        art_url = "https://www.ptt.cc" + t_tag["href"]
                        all_temp_posts.append({
                            "title": t_tag.text,
                            "url": art_url,
                            "date": art.select_one("div.date").text,
                            "img": "" 
                        })
                
                if i % 10 == 0:
                    time.sleep(0.5) # 防止被 PTT 暫時封鎖
            
            # 效能考量：僅幫前 100 則「最熱門/最新」的爆文抓取預覽圖
            # 這樣網站載入會快很多
            print("正在為前 100 則爆文提取圖片...")
            for post in all_temp_posts[:100]:
                if not post['img']:
                    post['img'] = get_real_image_url(post['url'])
            
            beauty_posts = all_temp_posts
            print(f"全部完成！目前庫存 {len(beauty_posts)} 則精選")
            
        except Exception as e:
            print(f"更新發生錯誤: {e}")
        
        time.sleep(3600) # 每小時自動更新一次

@app.route('/')
def home():
    style = """
    <style>
        body { font-family: "Microsoft JhengHei", sans-serif; background: #0a0a0a; color: #fff; margin: 0; }
        .header { background: linear-gradient(135deg, #1a1a1a 0%, #000 100%); padding: 30px; position: sticky; top: 0; z-index: 100; border-bottom: 2px solid #333; }
        .search-box { width: 90%; max-width: 500px; padding: 15px; border-radius: 30px; border: 1px solid #444; background: #222; color: #fff; font-size: 16px; margin-top: 15px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 25px; }
        .card { background: #161616; border-radius: 12px; overflow: hidden; transition: 0.4s; border: 1px solid #222; height: 450px; }
        .card:hover { transform: translateY(-10px); border-color: #ff2d55; box-shadow: 0 10px 20px rgba(255,45,85,0.2); }
        .card img { width: 100%; height: 75%; object-fit: cover; }
        .no-img { width: 100%; height: 75%; display: flex; align-items: center; justify-content: center; background: #222; color: #666; font-size: 14px; }
        .info { padding: 15px; text-align: left; }
        .date { font-size: 12px; color: #ff2d55; margin-bottom: 5px; }
        .title-text { font-size: 15px; font-weight: bold; line-height: 1.4; color: #eee; text-decoration: none; }
        a { text-decoration: none; }
    </style>
    """
    
    script = """
    <script>
    function searchPosts() {
        let input = document.getElementById('searchInput').value.toLowerCase();
        let cards = document.getElementsByClassName('card');
        for (let i = 0; i < cards.length; i++) {
            let title = cards[i].querySelector('.title-text').innerText.toLowerCase();
            cards[i].style.display = title.includes(input) ? "" : "none";
        }
    }
    </script>
    """
    
    cards_html = ""
    for p in beauty_posts:
        img_content = f"<img src='{p['img']}' loading='lazy'>" if p['img'] else "<div class='no-img'>點擊看原文圖</div>"
        cards_html += f"""
        <div class='card'>
            <a href='{p['url']}' target='_blank'>
                {img_content}
                <div class='info'>
                    <div class='date'>{p['date']}</div>
                    <div class='title-text'>{p['title']}</div>
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
                <h1 style='margin:0; color:#ff2d55;'>PTT Beauty 名人堂</h1>
                <input type="text" id="searchInput" onkeyup="searchPosts()" placeholder="搜尋正妹關鍵字..." class="search-box">
            </div>
            <div class='grid'>
                {cards_html if cards_html else '<h2 style="width:100%; text-align:center;">考古中...請稍候 30-60 秒後刷新網頁</h2>'}
            </div>
            {script}
        </body>
    </html>
    """

if __name__ == "__main__":
    threading.Thread(target=fetch_beauty_boom, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
