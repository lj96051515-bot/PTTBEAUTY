import requests
from bs4 import BeautifulSoup
import time
import threading
from flask import Flask, request, jsonify
import os
import re
import math
from urllib.parse import urljoin

app = Flask(__name__)

# 儲存所有圖片
ALL_IMAGES = {
    'urls': [],           # 圖片 URL 列表
    'last_updated': None, # 最後更新時間
    'count': 0,           # 總圖片數
    'per_page': 30        # 每頁顯示數量
}

def get_all_img_urls(link):
    """從文章取得所有圖片連結"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.ptt.cc"
        }
        res = requests.get(
            link,
            cookies={"over18": "1"},
            headers=headers,
            timeout=15
        )
        res.raise_for_status()
        
        html = res.text
        imgs = set()
        
        # 1️⃣ 抓取 i.imgur.com 圖片
        direct = re.findall(
            r'https?://i\.imgur\.com/[A-Za-z0-9]{5,}(?:\.(?:jpg|jpeg|png|gif|webp))?',
            html,
            re.IGNORECASE
        )
        imgs.update(direct)
        
        # 2️⃣ 處理 imgur.com/xxxx 連結
        pages = re.findall(
            r'https?://(?:www\.)?imgur\.com/(?:a/|gallery/)?([A-Za-z0-9]{5,})',
            html
        )
        for img_id in pages:
            # 嘗試常見圖片格式
            for ext in ['.jpg', '.png', '.gif', '.webp']:
                imgs.add(f"https://i.imgur.com/{img_id}{ext}")
        
        return list(imgs)
        
    except Exception as e:
        print(f"抓圖錯誤 {link}: {e}", flush=True)
        return []

def fetch_data():
    """背景執行抓取資料"""
    global ALL_IMAGES
    
    print(">>> 啟動圖片抓取服務", flush=True)
    
    # 先設定一些預設圖片
    default_images = [
        "https://i.imgur.com/8Wr9FgB.jpg",
        "https://i.imgur.com/Vd2fGQ7.jpg",
        "https://i.imgur.com/s9dYb9M.jpg",
        "https://i.imgur.com/m6y2GzZ.jpg",
        "https://i.imgur.com/5Z3Q2Q9.jpg",
    ]
    
    ALL_IMAGES = {
        'urls': default_images,
        'last_updated': time.strftime("%Y-%m-%d %H:%M:%S"),
        'count': len(default_images),
        'per_page': 30
    }
    
    while True:
        try:
            imgs_pool = []
            processed_count = 0
            article_count = 0
            
            print(">>> 開始抓取 Beauty 看板爆文", flush=True)
            
            # 抓取前3頁（可調整）
            for page in range(1, 4):
                try:
                    url = f"https://www.ptt.cc/bbs/Beauty/search?page={page}&q=recommend%3A100"
                    r = requests.get(
                        url, 
                        cookies={"over18": "1"}, 
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=10
                    )
                    r.raise_for_status()
                    
                    soup = BeautifulSoup(r.text, "html.parser")
                    arts = soup.select("div.r-ent")
                    
                    if not arts:
                        print(f">>> 第 {page} 頁無文章，停止抓取", flush=True)
                        break
                    
                    for art in arts:
                        title_elem = art.select_one("div.title a")
                        if title_elem and "[正妹]" in title_elem.text:
                            article_count += 1
                            link = urljoin("https://www.ptt.cc", title_elem["href"])
                            print(f">>> 處理文章: {title_elem.text[:30]}...", flush=True)
                            
                            imgs = get_all_img_urls(link)
                            imgs_pool.extend(imgs)
                            processed_count += len(imgs)
                            
                            time.sleep(0.3)  # 降低請求頻率
                    
                    print(f">>> 完成第 {page} 頁，累積圖片: {processed_count} 張", flush=True)
                    time.sleep(1)
                    
                except Exception as e:
                    print(f">>> 第 {page} 頁錯誤: {e}", flush=True)
                    continue
            
            # 去重並更新
            unique_imgs = list(dict.fromkeys(imgs_pool))
            if unique_imgs:  # 如果有抓到新圖片，才取代預設圖片
                ALL_IMAGES['urls'] = unique_imgs
                ALL_IMAGES['count'] = len(unique_imgs)
                ALL_IMAGES['last_updated'] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f">>> 更新完成！文章: {article_count} 篇，圖片: {ALL_IMAGES['count']} 張", flush=True)
            
        except Exception as e:
            print(f">>> 主流程錯誤: {e}", flush=True)
        
        # 每30分鐘更新一次
        print(f">>> 等待下次更新...", flush=True)
        time.sleep(1800)

def get_paginated_images(page=1, per_page=None):
    """取得分頁圖片數據"""
    if per_page is None:
        per_page = ALL_IMAGES['per_page']
    
    total_images = ALL_IMAGES['count']
    total_pages = math.ceil(total_images / per_page)
    
    # 確保頁數在合理範圍
    page = max(1, min(page, total_pages))
    
    # 計算起始和結束索引
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # 取得該頁圖片
    images = ALL_IMAGES['urls'][start_idx:end_idx]
    
    return {
        'images': images,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_images': total_images,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'last_updated': ALL_IMAGES['last_updated']
    }

@app.route('/')
def home():
    """首頁 - 自動重定向到第一頁"""
    return """
    <html>
        <head>
            <meta http-equiv="refresh" content="0;url=/page/1">
            <title>Redirecting...</title>
        </head>
        <body>
            <p>Redirecting to page 1...</p>
        </body>
    </html>
    """

@app.route('/page/<int:page>')
def gallery_page(page):
    """分頁圖片展示"""
    per_page = request.args.get('per_page', default=30, type=int)
    per_page = min(per_page, 100)  # 限制每頁最多100張
    
    # 取得分頁數據
    data = get_paginated_images(page, per_page)
    
    style = f"""
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            background: #0f0f0f;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: white;
        }}
        .header {{
            background: rgba(0, 0, 0, 0.9);
            padding: 1rem;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid #333;
        }}
        .gallery {{
            column-count: {3 if per_page <= 30 else 4};
            column-gap: 8px;
            padding: 8px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .image-container {{
            position: relative;
            margin-bottom: 8px;
            break-inside: avoid;
        }}
        .image-container img {{
            width: 100%;
            height: auto;
            border-radius: 8px;
            display: block;
            transition: transform 0.3s ease;
            cursor: pointer;
        }}
        .image-container img:hover {{
            transform: scale(1.02);
        }}
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 1.5rem;
            gap: 1rem;
            flex-wrap: wrap;
            background: rgba(0, 0, 0, 0.8);
            margin-top: 1rem;
        }}
        .pagination a, .pagination span {{
            padding: 0.5rem 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            color: white;
            text-decoration: none;
            transition: background 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        .pagination a:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}
        .pagination .current {{
            background: rgba(255, 255, 255, 0.3);
            font-weight: bold;
        }}
        .pagination .disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        .stats {{
            text-align: center;
            padding: 0.5rem;
            color: #aaa;
            font-size: 0.9rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            margin: 0 1rem 1rem 1rem;
        }}
        .controls {{
            display: flex;
            justify-content: center;
            gap: 1rem;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.7);
            border-bottom: 1px solid #333;
        }}
        .controls select, .controls input {{
            padding: 0.5rem;
            border-radius: 4px;
            border: 1px solid #555;
            background: #222;
            color: white;
        }}
        .controls button {{
            padding: 0.5rem 1rem;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .controls button:hover {{
            background: #45a049;
        }}
        .loading {{
            text-align: center;
            color: #888;
            padding: 50px;
            font-size: 1.2rem;
        }}
        
        @media (max-width: 1200px) {{
            .gallery {{ column-count: {2 if per_page <= 30 else 3}; }}
        }}
        @media (max-width: 900px) {{
            .gallery {{ column-count: {1 if per_page <= 30 else 2}; }}
        }}
        @media (max-width: 600px) {{
            .gallery {{ column-count: 1; }}
            .pagination {{ gap: 0.5rem; }}
            .pagination a, .pagination span {{
                padding: 0.3rem 0.6rem;
                font-size: 0.9rem;
            }}
        }}
    </style>
    """
    
    # 生成圖片 HTML
    if not data['images']:
        images_html = "<div class='loading'>暫時沒有圖片，正在抓取中...</div>"
    else:
        images_html = ""
        for idx, img_url in enumerate(data['images']):
            img_number = (data['page'] - 1) * data['per_page'] + idx + 1
            images_html += f"""
            <div class="image-container">
                <img src="{img_url}" 
                     loading="lazy" 
                     alt="圖片 {img_number}"
                     onclick="window.open('{img_url}', '_blank')"
                     onerror="this.src='https://via.placeholder.com/300x200/333/ccc?text=Image+Error'">
                <div style="position: absolute; bottom: 5px; right: 5px; background: rgba(0,0,0,0.7); color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px;">
                    #{img_number}
                </div>
            </div>
            """
    
    # 生成分頁按鈕 HTML
    pagination_html = ""
    
    # 上一頁按鈕
    if data['has_prev']:
        pagination_html += f'<a href="/page/{data["page"]-1}?per_page={data["per_page"]}">← 上一頁</a>'
    else:
        pagination_html += '<span class="disabled">← 上一頁</span>'
    
    # 頁碼按鈕（顯示當前頁前後各2頁）
    start_page = max(1, data['page'] - 2)
    end_page = min(data['total_pages'], data['page'] + 2)
    
    if start_page > 1:
        pagination_html += f'<a href="/page/1?per_page={data["per_page"]}">1</a>'
        if start_page > 2:
            pagination_html += '<span>...</span>'
    
    for p in range(start_page, end_page + 1):
        if p == data['page']:
            pagination_html += f'<span class="current">{p}</span>'
        else:
            pagination_html += f'<a href="/page/{p}?per_page={data["per_page"]}">{p}</a>'
    
    if end_page < data['total_pages']:
        if end_page < data['total_pages'] - 1:
            pagination_html += '<span>...</span>'
        pagination_html += f'<a href="/page/{data["total_pages"]}?per_page={data["per_page"]}">{data["total_pages"]}</a>'
    
    # 下一頁按鈕
    if data['has_next']:
        pagination_html += f'<a href="/page/{data["page"]+1}?per_page={data["per_page"]}">下一頁 →</a>'
    else:
        pagination_html += '<span class="disabled">下一頁 →</span>'
    
    # 控制表單
    controls_html = f"""
    <div class="controls">
        <form method="get" action="/page/{data['page']}" style="display: flex; gap: 0.5rem; align-items: center;">
            <label>每頁顯示：</label>
            <select name="per_page" onchange="this.form.submit()">
                <option value="15" {"selected" if data['per_page'] == 15 else ""}>15 張</option>
                <option value="30" {"selected" if data['per_page'] == 30 else ""}>30 張</option>
                <option value="50" {"selected" if data['per_page'] == 50 else ""}>50 張</option>
                <option value="100" {"selected" if data['per_page'] == 100 else ""}>100 張</option>
            </select>
        </form>
        <form method="get" action="/page/1" style="display: flex; gap: 0.5rem; align-items: center;">
            <label>跳轉到：</label>
            <input type="number" name="page" min="1" max="{data['total_pages']}" placeholder="頁碼" style="width: 80px;">
            <input type="hidden" name="per_page" value="{data['per_page']}">
            <button type="submit">前往</button>
        </form>
    </div>
    """
    
    return f"""
    <html>
        <head>
            <title>PTT 正妹圖片 - 第 {data['page']} 頁 (共 {data['total_pages']} 頁)</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta name="description" content="PTT Beauty 看板爆文正妹圖片自動彙整 - 第 {data['page']} 頁">
            {style}
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0; font-size: 1.5rem;">📸 PTT Beauty 正妹圖片精選</h1>
                <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #ccc;">
                    最後更新: {data['last_updated'] or '抓取中...'}
                </div>
            </div>
            
            {controls_html}
            
            <div class="stats">
                第 {data['page']} 頁 / 共 {data['total_pages']} 頁 | 
                顯示 {len(data['images'])} 張圖片 / 總計 {data['total_images']} 張 | 
                排序: 最新抓取優先
            </div>
            
            <div class="gallery">
                {images_html}
            </div>
            
            <div class="pagination">
                {pagination_html}
            </div>
            
            <div style="text-align: center; padding: 1rem; color: #666; font-size: 0.8rem;">
                自動抓取 PTT Beauty 看板推薦數 100 以上且標題含 [正妹] 的文章圖片 | 每30分鐘自動更新
            </div>
            
            <script>
                // 圖片錯誤處理
                document.addEventListener('DOMContentLoaded', function() {{
                    document.querySelectorAll('img').forEach(img => {{
                        img.onerror = function() {{
                            this.src = 'https://via.placeholder.com/300x200/333/ccc?text=Image+Load+Failed';
                            this.style.opacity = '0.5';
                        }};
                    }});
                }});
                
                // 鍵盤快捷鍵
                document.addEventListener('keydown', function(e) {{
                    if (e.key === 'ArrowLeft' && {str(data['has_prev']).lower()}) {{
                        window.location.href = '/page/{data['page']-1}?per_page={data['per_page']}';
                    }}
                    if (e.key === 'ArrowRight' && {str(data['has_next']).lower()}) {{
                        window.location.href = '/page/{data['page']+1}?per_page={data['per_page']}';
                    }}
                }});
                
                // 無限滾動（可選功能）
                let isLoading = false;
                window.addEventListener('scroll', function() {{
                    if ({str(data['has_next']).lower()} && !isLoading && 
                        window.innerHeight + window.scrollY >= document.body.offsetHeight - 1000) {{
                        // 可以在此實作 AJAX 加載更多
                        console.log('加載下一頁...');
                    }}
                }});
            </script>
        </body>
    </html>
    """

@app.route('/api/images')
def api_images():
    """API 接口：獲取圖片數據"""
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=30, type=int)
    per_page = min(per_page, 100)
    
    data = get_paginated_images(page, per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'images': data['images'],
            'pagination': {
                'page': data['page'],
                'per_page': data['per_page'],
                'total_pages': data['total_pages'],
                'total_images': data['total_images'],
                'has_next': data['has_next'],
                'has_prev': data['has_prev']
            },
            'meta': {
                'last_updated': data['last_updated']
            }
        }
    })

@app.route('/status')
def status():
    """狀態檢查頁面"""
    data = get_paginated_images(1)
    return jsonify({
        'status': 'running',
        'image_count': data['total_images'],
        'last_updated': data['last_updated'],
        'total_pages': data['total_pages'],
        'current_page': data['page'],
        'images_per_page': data['per_page']
    })

@app.route('/search')
def search():
    """搜尋功能（未來擴展）"""
    query = request.args.get('q', '')
    return f"搜尋功能開發中... 關鍵字: {query}"

if __name__ == "__main__":
    # 啟動背景抓取執行緒
    fetch_thread = threading.Thread(target=fetch_data, daemon=True)
    fetch_thread.start()
    
    # 取得連接埠
    port = int(os.environ.get("PORT", 5000))
    
    # 啟動 Flask
    print(f">>> 伺服器啟動在連接埠 {port}", flush=True)
    print(f">>> 首頁網址: http://localhost:{port}/", flush=True)
    print(f">>> API 網址: http://localhost:{port}/api/images", flush=True)
    
    app.run(
        host="0.0.0.0", 
        port=port,
        debug=False,
        threaded=True
    )
