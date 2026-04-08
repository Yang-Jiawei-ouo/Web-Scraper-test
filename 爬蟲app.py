import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import html
import io

st.set_page_config(page_title="評論爬蟲", layout="centered")
st.title("阿呆婉瑄要的評論爬蟲 📝")

def crawl_internal(target_url, page_num, link_class, detail_content_class):
    base_url = "https://www.cosme.net.tw"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    full_reviews = []
    progress_bar = st.progress(0)
    
    for page in range(1, page_num + 1):
        url = f"{target_url}?page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            links = [l['href'] for l in soup.select(link_class) if l.has_attr('href')]
            
            for i, link in enumerate(links):
                detail_url = base_url + link if link.startswith("/") else link
                try:
                    detail_res = requests.get(detail_url, headers=headers, timeout=5)
                    detail_soup = BeautifulSoup(detail_res.text, "html.parser")
                    
                    # 🏠 1. 先抓到評論的主體大房子
                    content_tag = detail_soup.select_one(detail_content_class)
                    
                    if content_tag:
                        # 🌟 2. 核心大絕招：根據妳的截圖，直接拆除所有 other-attributes 的盒子
                        # 這樣裡面不管是「・效果：」還是「補充膠原蛋白」都會整組消失！
                        for junk in content_tag.select(".other-attributes, .review-attributes, .review-info"):
                            junk.decompose() 
                        
                        # 📝 3. 抓取文字，使用分隔符號保留段落感
                        text = content_tag.get_text(separator="\n", strip=True)
                        text = html.unescape(text)
                        
                        # 🧹 4. 清理多餘的空白行或奇怪的符號
                        lines = [line.strip() for line in text.split('\n') if line.strip() and line.strip() != "--"]
                        
                        # 用雙換行重新拼起來，排版才會漂亮
                        final_text = "\n\n".join(lines)
                        full_reviews.append(final_text)
                except:
                    continue 
                time.sleep(random.uniform(0.5, 1.0))
            progress_bar.progress(page / page_num)
        except:
            break
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
        with pd.ExcelWriter(output) as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()

# ==========================================
# UI 介面
# ==========================================
user_url = st.text_input("🔗 產品評論列表網址：", value="https://www.cosme.net.tw/products/106877/reviews")
pages = st.number_input("📄 爬取頁數", min_value=1, value=1)

if st.button("開始精準執行 🚀"):
    with st.spinner('正在精準拆除標籤並整理排版中...'):
        # 直接鎖定妳截圖中的 class
        results = crawl_internal(user_url, pages, ".review-content-top", ".review-content")
        
        if results:
            st.success(f"搞定！已成功移除屬性資料，共抓到 {len(results)} 則評論。")
            df = pd.DataFrame(results, columns=["評論內容"])
            st.dataframe(df, use_container_width=True, height=400)
            
            excel_data = to_excel(df)
            st.download_button(
                label="📥 下載 Excel 檔案",
                data=excel_data,
                file_name="clean_reviews_perfect.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("沒抓到資料，請檢查 Class 標籤！")