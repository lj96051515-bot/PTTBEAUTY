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

def get_img_url(link):
    try:
        res = requests.get(link, cookies={"over18": "1"}, timeout=5)
        match = re.search(r'https?://(?:i\.)?imgur\.com/([A-Za-z0-9]+)', res.text)
        if match:
            return f"https://i.imgur.com/{match.group(1)}.jpg"
    except: pass
    return ""

def fetch_data():
    global gossiping_logs, beauty_images
    time.sleep(5)  # 延遲啟動，確保 Flask 已經完全跑起來
    
    while True:
        try:
            print(">>> [開始更新] 八卦版...")
            res = requests.get("https://www.ptt.cc/bbs/Gossiping/index.html", cookies={"over18": "1"}, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            g_content = f"<div class='section-title'>八卦最新 ({time.strftime('%H:%M:%S')})</div>"
            for art in soup.select("div.r-ent")[:10]:
                t_tag = art.select_one("div.title a")
                if t_tag:
                    g_content += f"<div class='post'>· <a href='https://www.ptt.cc{t_tag['href']}' target='_blank'>{t_tag.text}</a></div>"
            gossiping_logs = [g_content]

            print(">>> [開始挖掘] 表特爆文...")
            temp_list = []
            for page in range(1, 31): # 先縮減到 30 頁確保穩定
                url = f"https://www.ptt.cc/bbs/Beauty/search?page={page}&q=recommend%3A100"
                r = requests.get(url, cookies={"over18": "1"}, timeout=10)
                s = BeautifulSoup(r.text, "html.parser")
                arts = s.select("div.r-ent")
                if not arts: break
                
                for art in arts:
                    t = art.select_one("div.title a")
                    if t and "[正妹]" in t.text:
                        temp_list.append({
                            "title": t.text,
                            "link": "https://www.ptt.cc" + t["href"],
                            "date": art.select_one("div.date").text,
                            "img": ""
                        })
                
                # 每抓 5 頁就更新一次畫面，不要讓使用者乾等
                if page % 5 == 0:
                    beauty_images = list(temp_list)
                    print(f"進度：已載入 {len(beauty_images)} 則文章...")
                time.sleep(0.5)

            # 補圖 (只補前 30 張最熱門的)
            for i in range(min(30, len(temp_list))):
                if not temp_list[i]["img"]:
                    temp_list[i]["img"] = get_img_url(temp_list[i]["link"])
                if i % 5 == 0: beauty_images = list(temp_list)

            beauty_images = temp_list
            print(">>> [完成] 全部資料同步完畢")
            
        except Exception as e:
            print(f">>> [警告] 發生錯誤: {e}")
        
        time.sleep(1200)

@app.route('/')
def home():
    style = "<style>body{background:#111;color:#eee;font-family:sans-serif;padding:20px;}.section-title{color:pink;border-bottom:1px solid pink;margin:20px 0;}.post{margin:5px 0;}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px;}.card{background:#222;border-radius:8px;overflow:hidden;height:350px;border:1px solid #444;}.card img{width:100%;height:70%;object-fit:cover;}</style>"
    
    g_html = "".join(gossiping_logs) if gossiping_logs else "八卦版連線中..."
    b_html = "<div class='section-title'>💎 表特爆文庫</div>"
    
    if not beauty_images:
        b_html += "<p>正在深度挖掘中，請稍候 30 秒後刷新網頁...</p>"
    else:
        b_html += "<div class='grid'>"
        for p in beauty_images:
            img = f"<img src='{p['img']}'>" if p['img'] else "<div style='height:70%;display:flex;align-items:center;justify-content:center;background:#333;'>點擊看原文</div>"
            b_html += f"<div class='card'><a href='{p['link']}' target='_blank' style='color:#fff;text-decoration:none;'>{img}<div style='padding:10px;'>[{p['date']}]<br>{p['title']}</div></a></div>"
        b_html += "</div>"
        
    return f"<html><head><meta http-equiv='refresh' content='30'><meta name='viewport' content='width=device-width, initial-scale=1'>{style}</head><body>{g_html}{b_html}</body></html>"

if __name__ == "__main__":
    t = threading.Thread(target=fetch_data)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
