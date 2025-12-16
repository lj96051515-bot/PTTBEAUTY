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

        # 進入文章抓取圖片

        res = requests.get(link, cookies=cookies, timeout=5)

        # 尋找 imgur 連結

        match = re.search(r'https?://(?:i\.)?imgur\.com/[A-Za-z0-9]+', res.text)

        if match:

            url = match.group(0)

            # 轉換為直接圖檔網址

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

            # 1. 抓取八卦版最新 (保持原本邏輯)

            res = requests.get("https://www.ptt.cc/bbs/Gossiping/index.html", cookies=cookies, timeout=10)

            soup = BeautifulSoup(res.text, "html.parser")

            g_content = f"<div class='section-title'>八卦版最新 ({time.strftime('%H:%M:%S')})</div>"

            for art in soup.select("div.r-ent")[:10]:

                t_tag = art.select_one("div.title a")

                if t_tag:

                    g_content += f"<div class='post'>· <a href='https://www.ptt.cc{t_tag['href']}' target='_blank'>{t_tag.text}</a></div>"

            gossiping_logs = [g_content]



            # 2. 抓取表特版 (往回掃描 3 頁，確保有資料)

            temp_beauty = []

            res_b = requests.get("https://www.ptt.cc/bbs/Beauty/index.html", cookies=cookies, timeout=10)

            soup_b = BeautifulSoup(res_b.text, "html.parser")

            # 取得上一頁連結來推算頁碼

            prev_link = soup_b.select("div.btn-group-paging a")[1]["href"]

            latest_page = int(re.search(r'index(\055?\d+)\.html', prev_link).group(1)) + 1

            

            # 掃描最近 3 頁

            for p in range(latest_page, latest_page - 3, -1):

                p_res = requests.get(f"https://www.ptt.cc/bbs/Beauty/index{p}.html", cookies=cookies)

                p_soup = BeautifulSoup(p_res.text, "html.parser")

                for art in p_soup.select("div.r-ent"):

                    push = art.select_one("div.nrec span")

                    push_num = 100 if push and push.text == "爆" else int(push.text) if (push and push.text.isdigit()) else 0

                    

                    t_tag = art.select_one("div.title a")

                    if t_tag and "[正妹]" in t_tag.text and push_num >= 30:

                        art_url = "https://www.ptt.cc" + t_tag["href"]

                        img = get_img_url(art_url, cookies)

                        if img:

                            temp_beauty.append({"title": t_tag.text, "link": art_url, "push": push_num, "img": img})

            

            beauty_images = temp_beauty

            print(f"更新完成: 抓到 {len(beauty_images)} 篇優質正妹貼文")



        except Exception as e:

            print(f"抓取失敗: {e}")

        

        time.sleep(60)



@app.route('/')

def home():

    style = """

    <style>

        body { font-family: sans-serif; background: #1a1a1a; color: #eee; padding: 20px; }

        .container { max-width: 1000px; margin: auto; }

        .section-title { font-size: 1.4em; color: #ff4081; border-bottom: 2px solid #ff4081; margin: 30px 0 15px; padding-bottom: 5px; }

        .post { padding: 8px; border-bottom: 1px solid #333; font-size: 0.95em; }

        .post a { color: #4dabf5; text-decoration: none; }

        .beauty-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 20px; }

        .beauty-card { background: #252525; border-radius: 12px; overflow: hidden; transition: 0.3s; border: 1px solid #444; }

        .beauty-card:hover { transform: translateY(-5px); border-color: #ff4081; }

        .beauty-card img { width: 100%; height: 200px; object-fit: cover; }

        .info { padding: 12px; }

        .push { color: #ff5252; font-weight: bold; margin-right: 5px; }

    </style>

    """

    g_html = "".join(gossiping_logs) if gossiping_logs else "八卦版加載中..."

    

    b_html = "<div class='section-title'>🔥 表特精選 (30推以上)</div>"

    if not beauty_images:

        b_html += "<p>此時段尚無高推文正妹，掃描中...</p>"

    else:

        b_html += "<div class='beauty-grid'>"

        for item in beauty_images:

            b_html += f"""

            <div class='beauty-card'>

                <a href='{item['link']}' target='_blank'>

                    <img src='{item['img']}'>

                    <div class='info'><span class='push'>{item['push']}推</span>{item['title']}</div>

                </a>

            </div>

            """

        b_html += "</div>"

    

    return f"<html><head><meta http-equiv='refresh' content='60'>{style}</head><body><div class='container'>{g_html}{b_html}</div></body></html>"



if __name__ == "__main__":

    threading.Thread(target=fetch_data, daemon=True).start()

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
