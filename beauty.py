import requests
from bs4 import BeautifulSoup
import time
import threading
from flask import Flask, request
import os
import re
import math

app = Flask(__name__)

# 每頁顯示 30 張
PER_PAGE = 30

# 存所有圖片
ALL_IMAGES = []

# 抓文章內所有 imgur 圖片
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

        # 1️⃣ 抓 i.imgur.com 直接連
        direct = re.findall(
            r'https?://i\.imgur\.com/[A-Za-z0-9]+\.(?:jpg|jpeg|png|gif)',
            html,
            re.IGNORECASE
        )
        imgs.update(direct)

        # 2️⃣ 抓 imgur.com/xxxx → 轉直連 jpg
        pages = re.findall(r'https?://imgur\.com/([A-Za-z0-9]+)', html)
        for img_id in pages:
            imgs.add(f"https://i.imgur.com/{img_id}.jpg")

        # 3️⃣ 抓 imgur.com/a/ 相簿（轉為直接連結）
        album_pages = re.findall(r'https?://imgur\.com/a/([A-Za-z0-9]+)', html)
        for album_id in album_pages:
            # 嘗試常見圖片格式
            for ext in ['.jpg', '.png', '.gif']:
                imgs.add(f"https://i.imgur.com/{album_id}{ext}")

        # 4️⃣ 抓其他常見圖床
        # flickr
        flickr_imgs = re.findall(
            r'https?://[a-z0-9\.]*flickr\.com/[^\s\'"]+\.(?:jpg|jpeg|png|gif)',
            html,
            re.IGNORECASE
        )
        imgs.update(flickr_imgs)
        
        # pbs.twimg.com (Twitter圖片)
        twitter_imgs = re.findall(
            r'https?://pbs\.twimg\.com/media/[^\s\'"]+\.(?:jpg|jpeg|png|gif)',
            html,
            re.IGNORECASE
        )
        imgs.update(twitter_imgs)

        return list(imgs)

    except Exception as e:
        print("抓圖錯誤:", e, flush=True)
        return []

# 後台爬蟲 - 增強版
def fetch_data():
    global ALL_IMAGES
    print(">>> 啟動圖片抓取模式", flush=True)

    # 先設定一些預設圖片，讓網站立即有內容
    default_images = [
        "https://i.imgur.com/8Wr9FgB.jpg",
        "https://i.imgur.com/Vd2fGQ7.jpg",
        "https://i.imgur.com/s9dYb9M.jpg",
        "https://i.imgur.com/m6y2GzZ.jpg",
        "https://i.imgur.com/5Z3Q2Q9.jpg",
    ]
    ALL_IMAGES = default_images.copy()
    print(f">>> 載入預設圖片: {len(ALL_IMAGES)} 張")

    while True:
        try:
            imgs_pool = []
            articles_processed = 0
            pages_without_images = 0

            print(">>> 開始抓取 Beauty 爆文", flush=True)

            # 抓取更多頁，增加不同推薦數的文章
            for recommend in [100, 50, 30, 10]:  # 不同推薦門檻
                print(f">>> 抓取推薦數 {recommend}+ 的文章")
                
                for page in range(1, 31):  # 每種抓30頁
                    try:
                        url = f"https://www.ptt.cc/bbs/Beauty/search?page={page}&q=recommend%3A{recommend}"
                        r = requests.get(
                            url, 
                            cookies={"over18": "1"}, 
                            headers={"User-Agent": "Mozilla/5.0"},
                            timeout=10
                        )
                        soup = BeautifulSoup(r.text, "html.parser")
                        arts = soup.select("div.r-ent")

                        if not arts:
                            print(f">>> 推薦數{recommend}: 第 {page} 頁無文章，停止")
                            break

                        page_img_count = 0
                        for art in arts:
                            t = art.select_one("div.title a")
                            # 擴大抓取條件
                            if t and ("[正妹]" in t.text or 
                                     "[神人]" in t.text or 
                                     "[分享]" in t.text or 
                                     "正妹" in t.text.lower() or 
                                     "美女" in t.text.lower() or 
                                     "妹" in t.text.lower() or
                                     "girl" in t.text.lower()):
                                
                                link = "https://www.ptt.cc" + t["href"]
                                print(f">>> 處理文章: {t.text[:40]}...", flush=True)
                                
                                imgs = get_all_img_urls(link)
                                if imgs:
                                    imgs_pool.extend(imgs)
                                    page_img_count += len(imgs)
                                    articles_processed += 1
                                
                                time.sleep(0.2)  # 避免請求過快

                        print(f">>> 推薦數{recommend}: 第 {page} 頁完成，本頁圖片: {page_img_count} 張，累積: {len(imgs_pool)} 張")
                        
                        if page_img_count == 0:
                            pages_without_images += 1
                            if pages_without_images >= 5:  # 連續5頁無圖片就停止
                                print(f">>> 連續 {pages_without_images} 頁無圖片，停止抓取推薦數{recommend}的文章")
                                break
                        else:
                            pages_without_images = 0
                        
                        time.sleep(0.8)  # 頁面間隔
                        
                    except Exception as e:
                        print(f">>> 第 {page} 頁錯誤: {e}", flush=True)
                        continue

            # 去重並更新
            if imgs_pool:  # 如果有抓到新圖片
                # 先顯示預設圖片，再加入新圖片
                all_images = default_images + imgs_pool
                unique_imgs = list(dict.fromkeys(all_images))  # 去重
                ALL_IMAGES = unique_imgs
                
                # 嘗試保存到檔案（可選）
                try:
                    with open('images_list.txt', 'w', encoding='utf-8') as f:
                        for img in ALL_IMAGES[:500]:  # 保存前500張
                            f.write(img + '\n')
                except:
                    pass
                
                print(f">>> 更新完成！處理文章: {articles_processed} 篇，總圖片: {len(ALL_IMAGES)} 張", flush=True)
            else:
                print(">>> 本次未抓到新圖片", flush=True)

        except Exception as e:
            print(">>> 主流程錯誤:", e, flush=True)

        print(">>> 等待 20 分鐘後更新...", flush=True)
        time.sleep(1200)  # 20 分鐘更新一次

# 前端頁面 - 增強版
@app.route('/')
def home():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", PER_PAGE))
    
    # 限制每頁最多100張
    per_page = min(per_page, 100)
    
    start = (page - 1) * per_page
    end = start + per_page

    total_images = len(ALL_IMAGES)
    total_pages = max(1, math.ceil(total_images / per_page))
    
    # 確保頁數在合理範圍
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
    
    start = (page - 1) * per_page
    end = start + per_page
    images = ALL_IMAGES[start:end]

    style = f"""
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{ 
            margin:0; 
            background:#0a0a0a;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        .header {{
            background: rgba(0, 0, 0, 0.95);
            padding: 1.2rem 1rem;
            text-align: center;
            border-bottom: 1px solid #333;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .controls {{
            background: rgba(20, 20, 20, 0.9);
            padding: 1rem;
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
            border-bottom: 1px solid #333;
        }}
        
        .control-group {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .control-group label {{
            color: #ccc;
            font-size: 0.9rem;
        }}
        
        .control-group select, .control-group input {{
            padding: 0.4rem 0.8rem;
            border-radius: 4px;
            border: 1px solid #555;
            background: #222;
            color: #fff;
        }}
        
        .control-group button {{
            padding: 0.4rem 1rem;
            background: #0084ff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .control-group button:hover {{
            background: #0073e6;
        }}
        
        .stats {{
            text-align: center;
            padding: 0.8rem;
            color: #aaa;
            font-size: 0.9rem;
            background: rgba(255, 255, 255, 0.05);
            margin: 0 1rem;
            border-radius: 6px;
            margin-top: 1rem;
        }}
        
        .gallery {{
            column-count: {3 if per_page <= 30 else 4};
            column-gap: 10px;
            padding: 10px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .image-container {{
            position: relative;
            margin-bottom: 10px;
            break-inside: avoid;
        }}
        
        img {{
            width:100%;
            height: auto;
            border-radius:8px;
            display: block;
            transition: transform 0.3s ease;
            cursor: pointer;
        }}
        
        img:hover {{
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 1.5rem;
            gap: 0.8rem;
            flex-wrap: wrap;
            background: rgba(0, 0, 0, 0.9);
            margin-top: 1rem;
        }}
        
        .pagination a, .pagination span {{
            padding: 0.5rem 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            color: white;
            text-decoration: none;
            transition: all 0.2s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
            font-size: 0.95rem;
        }}
        
        .pagination a:hover {{
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }}
        
        .pagination .current {{
            background: rgba(0, 132, 255, 0.8);
            font-weight: bold;
        }}
        
        .pagination .disabled {{
            opacity: 0.4;
            cursor: not-allowed;
            pointer-events: none;
        }}
        
        .image-number {{
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .footer {{
            text-align: center;
            padding: 1.5rem;
            color: #666;
            font-size: 0.85rem;
            background: rgba(0, 0, 0, 0.95);
            border-top: 1px solid #333;
            margin-top: 2rem;
        }}
        
        @media (max-width: 1200px) {{
            .gallery {{ column-count: {2 if per_page <= 30 else 3}; }}
        }}
        
        @media (max-width: 768px) {{
            .gallery {{ column-count: 1; }}
            .controls {{ 
                flex-direction: column; 
                align-items: center;
                gap: 0.8rem;
            }}
            .pagination {{ 
                gap: 0.4rem;
                padding: 1rem;
            }}
            .pagination a, .pagination span {{
                padding: 0.4rem 0.7rem;
                font-size: 0.9rem;
            }}
        }}
    </style>
    """

    # 生成圖片 HTML
    if not images:
        imgs_html = """
        <div style="text-align:center; padding: 60px 20px; color: #888;">
            <h2>圖片載入中...</h2>
            <p>正在抓取最新圖片，請稍候幾秒鐘</p>
        </div>
        """
    else:
        imgs_html = ""
        for idx, img_url in enumerate(images):
            img_num = start + idx + 1
            imgs_html += f"""
            <div class="image-container">
                <img src='{img_url}' 
                     loading='lazy' 
                     alt='圖片 {img_num}'
                     onerror="this.onerror=null; this.src='https://via.placeholder.com/400x300/333/ccc?text=圖片載入失敗';">
                <div class="image-number">#{img_num}</div>
            </div>
            """

    # 生成分頁按鈕
    pagination_html = '<div class="pagination">'
    
    # 上一頁按鈕
    if page > 1:
        pagination_html += f'<a href="/?page={page-1}&per_page={per_page}">⬅ 上一頁</a>'
    else:
        pagination_html += '<span class="disabled">⬅ 上一頁</span>'
    
    # 頁碼按鈕
    start_page = max(1, page - 3)
    end_page = min(total_pages, page + 3)
    
    if start_page > 1:
        pagination_html += f'<a href="/?page=1&per_page={per_page}">1</a>'
        if start_page > 2:
            pagination_html += '<span>...</span>'
    
    for p in range(start_page, end_page + 1):
        if p == page:
            pagination_html += f'<span class="current">{p}</span>'
        else:
            pagination_html += f'<a href="/?page={p}&per_page={per_page}">{p}</a>'
    
    if end_page < total_pages:
        if end_page < total_pages - 1:
            pagination_html += '<span>...</span>'
        pagination_html += f'<a href="/?page={total_pages}&per_page={per_page}">{total_pages}</a>'
    
    # 下一頁按鈕
    if page < total_pages:
        pagination_html += f'<a href="/?page={page+1}&per_page={per_page}">下一頁 ➡</a>'
    else:
        pagination_html += '<span class="disabled">下一頁 ➡</span>'
    
    pagination_html += '</div>'

    # 控制面板
    controls_html = f"""
    <div class="controls">
        <div class="control-group">
            <label>每頁顯示：</label>
            <select id="perPageSelect" onchange="changePerPage(this.value)">
                <option value="15" {"selected" if per_page == 15 else ""}>15 張</option>
                <option value="30" {"selected" if per_page == 30 else ""}>30 張</option>
                <option value="50" {"selected" if per_page == 50 else ""}>50 張</option>
                <option value="100" {"selected" if per_page == 100 else ""}>100 張</option>
            </select>
        </div>
        
        <div class="control-group">
            <label>跳轉到：</label>
            <input type="number" id="jumpPage" min="1" max="{total_pages}" value="{page}" style="width: 70px;">
            <button onclick="jumpToPage()">前往</button>
        </div>
    </div>
    """

    # 統計資訊
    stats_html = f"""
    <div class="stats">
        📊 第 <strong>{page}</strong> 頁 / 共 <strong>{total_pages}</strong> 頁 | 
        🖼️ 總計 <strong>{total_images}</strong> 張圖片 | 
        🔄 自動更新中...
    </div>
    """

    return f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PTT 正妹圖片精選 ({total_images} 張圖片)</title>
        <meta name="description" content="自動抓取 PTT Beauty 看板的正妹圖片，每日更新">
        {style}
    </head>
    <body>
        <div class="header">
            <h1 style="margin: 0; font-size: 1.8rem;">📸 PTT 正妹圖片精選</h1>
            <p style="margin: 0.5rem 0 0 0; color: #ccc; font-size: 0.95rem;">
                自動抓取 PTT Beauty 看板爆文的正妹圖片
            </p>
        </div>
        
        {controls_html}
        {stats_html}
        
        <div class="gallery">
            {imgs_html}
        </div>
        
        {pagination_html}
        
        <div class="footer">
            <p>🤖 自動抓取系統 | 🔄 每 20 分鐘更新一次 | 📱 支援手機/平板/電腦瀏覽</p>
            <p style="margin-top: 0.5rem; color: #888; font-size: 0.8rem;">
                本網站僅用於技術展示，圖片版權屬於原作者
            </p>
        </div>

        <script>
            // 改變每頁顯示數量
            function changePerPage(value) {{
                const url = new URL(window.location);
                url.searchParams.set('per_page', value);
                url.searchParams.set('page', 1); // 回到第一頁
                window.location.href = url.toString();
            }}
            
            // 跳轉到指定頁面
            function jumpToPage() {{
                const pageInput = document.getElementById('jumpPage');
                let pageNum = parseInt(pageInput.value);
                const totalPages = {total_pages};
                
                if (isNaN(pageNum) || pageNum < 1) pageNum = 1;
                if (pageNum > totalPages) pageNum = totalPages;
                
                const url = new URL(window.location);
                url.searchParams.set('page', pageNum);
                window.location.href = url.toString();
            }}
            
            // 圖片點擊放大
            document.addEventListener('DOMContentLoaded', function() {{
                document.querySelectorAll('.gallery img').forEach(img => {{
                    img.addEventListener('click', function() {{
                        window.open(this.src, '_blank');
                    }});
                }});
                
                // 鍵盤快捷鍵
                document.addEventListener('keydown', function(e) {{
                    if (e.key === 'ArrowLeft' && {page > 1}) {{
                        window.location.href = '/?page={page-1}&per_page={per_page}';
                    }}
                    if (e.key === 'ArrowRight' && {page < total_pages}) {{
                        window.location.href = '/?page={page+1}&per_page={per_page}';
                    }}
                }});
                
                // 圖片載入錯誤處理
                document.querySelectorAll('img').forEach(img => {{
                    img.onerror = function() {{
                        if (!this.src.includes('placeholder.com')) {{
                            this.src = 'https://via.placeholder.com/400x300/333/ccc?text=圖片載入失敗';
                        }}
                    }};
                }});
            }});
        </script>
    </body>
    </html>
    """

# 狀態檢查頁面
@app.route('/status')
def status():
    return f"""
    <html>
    <body style="background:#000;color:#fff;padding:30px;font-family:monospace;">
        <h1>系統狀態</h1>
        <p>📊 圖片總數: {len(ALL_IMAGES)}</p>
        <p>🕐 當前時間: {time.ctime()}</p>
        <p>⚙️ 每頁顯示: {PER_PAGE} 張</p>
        <p>📄 總頁數: {math.ceil(len(ALL_IMAGES) / PER_PAGE) if ALL_IMAGES else 0}</p>
        <hr>
        <h3>前 5 張圖片預覽:</h3>
        {"<br>".join(ALL_IMAGES[:5]) if ALL_IMAGES else "無圖片"}
        <hr>
        <p><a href="/" style="color:#0af;">返回首頁</a></p>
    </body>
    </html>
    """

if __name__ == "__main__":
    # 啟動背景抓取執行緒
    fetch_thread = threading.Thread(target=fetch_data, daemon=True)
    fetch_thread.start()
    
    # 讓執行緒先跑一下
    time.sleep(2)
    
    # 啟動 Flask
    port = int(os.environ.get("PORT", 5000))
    print(f">>> 伺服器啟動在連接埠 {port}", flush=True)
    print(f">>> 當前圖片數量: {len(ALL_IMAGES)}", flush=True)
    print(f">>> 網站網址: http://localhost:{port}/", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
