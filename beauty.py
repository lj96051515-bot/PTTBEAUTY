import requests
from bs4 import BeautifulSoup
import time
import threading
from flask import Flask
import os
import re

app = Flask(__name__)
# 存放抓到的資料
beauty_images = []

def get_img_url(link):
    try:
        # 模擬真人瀏覽器，避免被 PTT 拒絕
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(link, cookies={"over18": "1"}, headers=headers, timeout=5)
        # 尋找 Imgur 圖片
        match = re.search(r'https?://(?:i\.)?imgur\.com/([A-Za-z0-9]+)', res.text)
        if match:
            return f"https://i.imgur.com/{match.group(1)}.jpg"
    except: pass
    return ""

def fetch_data():
    global beauty_images
    # 強制在 Logs 顯示啟動訊息
    print(">>> [系統] 啟動表特考古模式...", flush=True)
    while True:
        try:
            temp_list = []
            print(">>> [爬蟲] 開始挖掘 50 頁爆文資料...", flush=True)
            
            for page in range(1, 51):
                # 搜尋推薦數 100 以上的文章
                url = f"https://www.ptt.cc/bbs/Beauty/search?page={page}&q=recommend%3A100"
                r = requests.get(url, cookies={"over18": "1"}, timeout=10)
                s = BeautifulSoup(r.text, "html.parser")
                arts = s.select("div.r-ent")
                
                if not arts:
                    print(f"第 {page} 頁無資料，停止搜尋。", flush=True)
                    break
                
                for art in arts:
                    t = art.select_one("div.title a")
                    if t and "[正妹]" in t.text:
                        temp_list.append({
                            "title": t.text,
                            "link": "https://www.ptt.cc" + t["href"],
                            "date": art.select_one("div.date").text,
                            "img": ""
                        })
                
                # 每抓 10 頁更新一次，讓使用者有感
                if page % 10 == 0:
                    beauty_images = list(temp_list)
                    print(f">>> [進度] 已取得 {len(beauty_images)} 則標題...", flush=True)
                
                time.sleep(0.5) # 安全間隔

            # 抓取前 40 則的圖片
            print(">>> [圖片] 開始抓取前 40 則預覽圖...", flush=True)
            for i in range(min(40, len(temp_list))):
                if not temp_list[i]["img"]:
                    temp_list[i]["img"] = get_img_url(temp_list[i]["link"])
                if i % 10 == 0:
                    beauty_images = list(temp_list)

            beauty_images = temp_list
            print(f">>> [完成] 考古完畢，共庫存 {len(beauty_images)} 則爆文", flush=True)
            
        except Exception as e:
            print(f">>> [錯誤] {e}", flush=True)
        
        time.sleep(1800) # 每 30 分鐘大更新一次

@app.route('/')
def home():
    style = """
    <style>
        body { background:#000; color:#eee; font-family:sans-serif; text-align:center; padding:20px; }
        .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:20px; padding:20px; }
        .card { background:#111; border-radius:12px; overflow:hidden; border:1px solid #333; height:420px; transition:0.3s; }
        .card:hover { border-color:#ff4081; transform:translateY(-5px); }
        .card img { width:100%; height:75%; object-fit:cover; background:#222; }
        .info { padding:15px; text-align:left; font-size:14px; }
        .date { color:#ff4081; font-weight:bold; }
        a { text-decoration:none; color:inherit; }
    </style>
    """
    
    html = "<h1>💎 PTT 表特版 1000 則爆文庫</h1>"
    
    if not beauty_images:
        html += "<div style='padding:50px;'><h3>🛸 機器人正在深度挖掘中...</h3><p>請稍候約 1 分鐘，網頁會自動刷新</p></div>"
    else:
        html += "<div class='grid'>"
        for p in beauty_images:
            img_src = p['img'] if p['img'] else "https://placehold.co/400x600/222/555?text=Click+to+View"
            html += f"""
            <div class='card'>
                <a href='{p['link']}' target='_blank'>
                    <img src='{img_src}' loading='lazy'>
                    <div class='info'>
                        <span class='date'>[{p['date']}]</span><br>
                        {p['title']}
                    </div>
                </a>
            </div>
            """
        html += "</div>"
        
    return f"<html><head><title>表特 1000 爆</title><meta http-equiv='refresh' content='60'><meta name='viewport' content='width=device-width, initial-scale=1'>{style}</head><body>{html}</body></html>"

if __name__ == "__main__":
    t = threading.Thread(target=fetch_data, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
