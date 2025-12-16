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
        # 搜尋 Imgur 或直接圖片網址
        match = re.search(r'https?://(?:i\.)?imgur\.com/([A-Za-z0-9]+)', res.text)
        if match:
            return f"https://i.imgur.com/{match.group(1)}.jpg"
    except: pass
    return ""

def fetch_data():
    global gossiping_logs, beauty_images
    cookies = {"over18": "1"}
    while True:
        try:
            # 1. 快速抓取八卦版最新
            print(">>> 正在同步八卦版最新消息...")
            res = requests.get("https://www.ptt.cc/bbs/Gossiping/index.html", cookies=cookies, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            g_content = f"<div class='section-title'>八卦版最新動態 ({time.strftime('%H:%M:%S')})</div>"
            for art in soup.select("div.r-ent")[:10]:
                t_tag = art.select_one("div.title a")
                if t_tag:
                    g_content += f"<div class='post'>· <a href='https://www.ptt.cc{t_tag['href']}' target='_blank'>{t_tag.text}</a></div>"
            gossiping_logs = [g_content]

            # 2. 深度考古表特爆文
            temp_beauty = []
            print(">>> 開始挖掘表特 1000 則爆文...")
            for page in range(1, 51):
                search_url = f"https://www.ptt.cc/bbs/Beauty/search?page={page}&q=recommend%3A100"
                res_b = requests.get(search_url, cookies=cookies, timeout=10)
                soup_b = BeautifulSoup(res_b.text, "html.parser")
                arts = soup_b.select("div.r-ent")
                if not arts: break
                
                for art in arts:
                    t_tag = art.select_one("div.title a")
                    if t_tag and "[正妹]" in t_tag.text:
                        temp_beauty.append({
                            "title": t_tag.text,
                            "link": "https://www.ptt.cc" + t_tag["href"],
                            "date": art.select_one("div.date").text,
                            "img": "" # 初始不抓圖，加快速度
                        })
                
                if page % 5 == 0:
                    print(f"已掃描 {page} 頁...")
                    # 先更新一部分資料到網頁上，讓使用者看到標題
                    beauty_images = list(temp_beauty) 
            
            # 3. 針對前 50 則補充圖片 (這步最慢)
            print(">>> 正在為前 50 則爆文提取預覽圖...")
            for i in range(min(50, len(temp_beauty))):
                if not temp_beauty[i]["img"]:
                    temp_beauty[i]["img"] = get_img_url(temp_beauty[i]["link"], cookies)
                # 抓幾張就更新幾張，讓網頁有感
                if i % 5 == 0: beauty_images = list(temp_beauty)
            
            beauty_images = temp_beauty
            print(f">>> 全部完成！目前庫存 {len(beauty_images)} 則爆文")

        except Exception as e:
            print(f">>> 錯誤: {e}")
        time.sleep(1800) # 每 30 分鐘大更新一次

@app.route('/')
def home():
    style = """
    <style>
        body { font-family: sans-serif; background: #0a0a0a; color: #fff; padding: 20px; }
        .container { max-width: 1200px; margin: auto; }
        .section-title { font-size: 1.5em; color: #ff2d55; border-bottom: 2px solid #ff2d55; margin: 30px 0 15px; padding-bottom: 5px; }
        .post { padding: 8px; border-bottom: 1px solid #222; font-size: 0.9em; }
        .post a { color: #4dabf5; text-decoration: none; }
        .beauty-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
        .card { background: #1a1a1a; border-radius: 12px; overflow: hidden; border: 1px solid #333; transition: 0.3s; height: 380px; }
        .card:hover { border-color: #ff2d55; transform: translateY(-5px); }
        .card img { width: 100%; height: 75%; object-fit: cover; background: #222; }
        .card-info { padding: 10px; font-size: 0.85em; }
        .date { color: #ff2d55; font-weight: bold; }
    </style>
    """
    g_html = "".join(gossiping_logs) if gossiping_logs else "<p>正在連線八卦版...</p>"
    
    b_html = "<div class='section-title'>💎 表特版 1000 則爆文名人堂</div>"
    if not beauty_images:
        b_html += "<p>機器人正在挖掘 1000 則爆文中... 請稍候刷新頁面</p>"
    else:
        b_html += "<div class='beauty-grid'>"
        for p in beauty_images:
            img_tag = f"<img src='{p['img']}' loading='lazy'>" if p['img'] else "<div style='height:75%; display:flex; align-items:center; justify-content:center; color:#555;'>載入圖中或無圖</div>"
            b_html += f"""
            <div class='card'>
                <a href='{p['link']}' target='_blank' style='text-decoration:none; color:inherit;'>
                    {img_tag}
                    <div class='card-info'>
                        <span class='date'>{p['date']}</span><br>{p['title']}
                    </div>
                </a>
            </div>
            """
        b_html += "</div>"
    
    return f"<html><head><title>PTT 考古工具</title><meta http-equiv='refresh' content='30'><meta name='viewport' content='width=device-width, initial-scale=1'>{style}</head><body><div class='container'>{g_html}{b_html}</div></body></html>"

if __name__ == "__main__":
    threading.Thread(target=fetch_data, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
