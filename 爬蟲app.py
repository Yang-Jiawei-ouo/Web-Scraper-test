import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import html
import io
from concurrent.futures import ThreadPoolExecutor # 🚀 新增：並行處理工具

st.set_page_config(page_title="高效評論爬蟲版本⚡", layout="centered")
st.title("呆瓜婉瑄要的評論爬蟲 📝")

# --- 詳細頁抓取單元 (供並行使用) ---
def fetch_detail(session, base_url, link, detail_content_class, min_wait, max_wait):
    detail_url = base_url + link if link.startswith("/") else link
    try:
        # 模擬人類點擊前的猶豫 (在並行模式下仍保有隨機性)
        time.sleep(random.uniform(min_wait, max_wait))
        
        res = session.get(detail_url, timeout=5)
        # 🚀 使用更快的 lxml 解析器
        soup = BeautifulSoup(res.text, "lxml")
        
        content_tag = soup.select_one(detail_content_class)
        if content_tag:
            # 移除雜訊
            for junk in content_tag.select(".other-attributes, .review-attributes, .review-info"):
                junk.decompose()
            
            text = content_tag.get_text(separator="\n", strip=True)
            text = html.unescape(text)
            lines = [line.strip() for line in text.split('\n') if line.strip() and line.strip() != "--"]
            return "\n\n".join(lines)
    except:
        return None
    return None

# --- 主抓取函數 ---
def crawl_internal(target_url, page_num, link_class, detail_content_class):
    base_url = "https://www.cosme.net.tw"
    # 🚀 使用 Session 保持連線，效能提升關鍵
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    
    full_reviews = []
    progress_bar = st.progress(0)
    
    # 動態延遲邏輯 (維持原有的聰明設定)
    if page_num <= 2:
        min_wait, max_wait, workers = 0.5, 1.2, 5  # 頁數少，並行數可稍多
    elif page_num <= 10:
        min_wait, max_wait, workers = 1.0, 2.0, 3  # 頁數中等，降速保平安
    else:
        min_wait, max_wait, workers = 1.5, 3.5, 2  # 大量抓取，嚴防封鎖
    
    st.info(f"⚙️ 效能優化中：開啟 {workers} 個並行通道抓取...")

    for page in range(1, page_num + 1):
        url = f"{target_url}?page={page}"
        try:
            res = session.get(url, timeout=10)
            soup = BeautifulSoup(res.text, "lxml")
            links = [l['href'] for l in soup.select(link_class) if l.has_attr('href')]
            
            # 🚀 核心優化：使用 ThreadPoolExecutor 同時抓取詳細頁
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # 建立任務清單
                futures = [
                    executor.submit(fetch_detail, session, base_url, link, detail_content_class, min_wait, max_wait) 
                    for link in links
                ]
                # 蒐集結果
                for f in futures:
                    result = f.result()
                    if result:
                        full_reviews.append(result)
            
            progress_bar.progress(page / page_num)
        except Exception as e:
            st.warning(f"第 {page} 頁抓取遇到點狀況，已自動跳過。")
            continue
            
    return full_reviews

# --- Excel 轉換函數 ---
def to_excel(df):
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='評論內容')
            workbook = writer.book
            worksheet = writer.sheets['評論內容']
            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            worksheet.set_column('A:A', 100, wrap_format) 
        return output.getvalue()
    except:
        return None

# --- UI 介面 ---
user_url = st.text_input("🔗 產品評論列表網址：", value="https://www.cosme.net.tw/products/106877/reviews")
pages = st.number_input("📄 爬取頁數", min_value=1, value=1)

if st.button("開始高效抓取 🚀"):
    start_time = time.time() # 計時開始
    with st.spinner('正在使用並行引擎抓取中...'):
        results = crawl_internal(user_url, pages, ".review-content-top", ".review-content")
        
        if results:
            end_time = time.time()
            st.success(f"搞定！共抓到 {len(results)} 則評論，耗時 {round(end_time - start_time, 1)} 秒。")
            df = pd.DataFrame(results, columns=["評論內容"])
            st.dataframe(df, use_container_width=True, height=400)
            
            excel_data = to_excel(df)
            if excel_data:
                st.download_button(
                    label="📥 下載 Excel 檔案",
                    data=excel_data,
                    file_name="fast_reviews.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )