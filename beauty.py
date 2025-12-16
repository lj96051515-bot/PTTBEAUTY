import requests
from bs4 import BeautifulSoup
import time
import threading
from flask import Flask
import os
import re

app = Flask(__name__)

gossiping_logs = []
beauty_images = []

def get_img_url(link, cookies):
    try:
        res = requests.get(link, cookies=cookies, timeout=5)
        # 尋找 imgur 連結
        match = re.search(r'https?://(?:i\.)?imgur\.com/[A-Za-z0-9]+', res.text)
        if match:
            url = match.group(0)
            if "i.imgur.com" not in url:
                url = url.replace("imgur.com", "i.imgur.com") + ".jpg"
            return url
    except:
        pass
    return None

def fetch_data():
    global gossiping_logs, beauty_images
    cookies = {"over18": "1"}
    
    while True:
        try:
            # 1. 八卦版：保持抓取最新 10 則 (即時性)
            res = requests.get("https://www.ptt.cc/bbs/Gossiping/index.html", cookies=cookies, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            g_content = f"<div class='section-title'>八卦版最新動態 ({time.strftime('%H:%M:%S')})</div>"
            for art in soup.select("div.r-ent")[:10]:
                t_tag = art.select_one("div.title a")
                if t_tag:
                    g_content += f"<div class='post'>· <a href='https://www.ptt.cc{t_tag['href']}' target='_blank'>{t_tag.text}</a></div>"
            gossiping_logs = [g_content]

            # 2. 表特版：切換為 1000 則爆文模式 (歷史深度)
            temp_beauty = []
            print("正在挖掘表特版 1000 則爆文...")
            
            # 翻 50 頁搜尋結果 (每頁約 20 則)
            for page in range(1, 51):
                search_url = f"https://www.ptt.cc/bbs/Beauty/search?page={page}&q=recommend%3A100"
                res_b = requests.get(search_url, cookies=cookies, timeout=10)
                soup_b = BeautifulSoup(res_b.text, "html.parser")
                
                arts = soup_b.select("div.r-ent")
                if not arts: break # 沒資料了就跳出
                
                for art in arts:
                    t_tag = art.select_one("div.title a")
                    if t_tag and "[正妹]" in t_tag.text:
                        art_url = "https://www.ptt.cc" + t_tag["href"]
                        # 為了效能：前 50 則才抓圖，剩下的顯示標題 (避免啟動太慢)
                        img = ""
                        if len(temp_beauty) < 50:
                            img = get_img_url(art_url, cookies)
                        
                        temp_beauty.append({
                            "title": t_tag.text, 
                            "link": art_url, 
                            "push": "爆", 
                            "img": img,
                            "date": art.select_one("div.date").text
                        })
                
                if page % 10 == 0: time.sleep(0.5) # 稍微休息防封鎖
            
            beauty_images = temp_beauty
            print(f"1000 則爆文同步完成！實際取得: {len(beauty_images)} 則")

        except Exception as e:
            print(f"抓取失敗: {e}")
        
        time.sleep(1800) # 爆文庫不常變動，每 30 分鐘更新一次即可

@app.route('/')
def home():
    style = """
    <style>
        body { font-family: sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1200px; margin: auto; }
        .section-title { font-size: 1.5em; color: #03dac6; border-bottom: 2px solid #03dac6; margin: 30px 0 15px; padding-bottom: 5px; }
        .post { padding: 10px; border-bottom: 1px solid #333; }
        .post a { color: #bb86fc; text-decoration: none; }
        .beauty-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }
        .beauty-card { background: #1e1e1e; border-radius: 8px; overflow: hidden; border: 1px solid #333; position: relative; }
        .beauty-card img { width: 100%; height: 300px; object-fit: cover; background: #222; }
        .info { padding: 10px; font-size: 0.9em; background: rgba(0,0,0,0.7); position: absolute; bottom: 0; width: 100%; box-sizing: border-box;}
        .date { color: #03dac6; font-size: 0.8em; }
    </style>
    """
    g_html = "".join(gossiping_logs) if gossiping_logs else "八卦版資料加載中..."
    
    b_html = "<div class='section-title'>💎 表特版 1000 則爆文名人堂 (前 50 則含預覽圖)</div>"
    if not beauty_images:
        b_html += "<p>正在挖掘 1000 則爆文中，請稍候約 30 秒後刷新...</p>"
    else:
        b_html += "<div class='beauty-grid'>"
        for item in beauty_images:
            # 如果有圖顯示圖，沒圖顯示標題卡片
            img_tag = f"<img src='{item['img']}'>" if item['img'] else "<div style='height:300px; display:flex; align-items:center; justify-content:center; color:#555;'>點擊查看原文</div>"
            b_html += f"""
            <div class='beauty-card'>
                <a href='{item['link']}' target='_blank'>
                    {img_tag}
                    <div class='info'>
                        <span class='date'>{item['date']}</span><br>
                        {item['title']}
                    </div>
                </a>
            </div>
            """
        b_html += "</div>"
    
    return f"<html><head><title>PTT 爆文庫</title><meta name='viewport' content='width=device-width, initial-scale=1'>{style}</head><body><div class='container'>{g_html}{b_html}</div></body></html>"

if __name__ == "__main__":
    threading.Thread(target=fetch_data, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
