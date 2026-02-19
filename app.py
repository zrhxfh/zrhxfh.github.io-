import streamlit as st
import urllib.request
import csv
import io
import zipfile
import requests
import pandas as pd
import os
import re
import random
import string
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ========== 新增导入 ==========
# 文章抓取
try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except:
    NEWSPAPER_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except:
    GTTS_AVAILABLE = False

# 二维码
try:
    import qrcode
    from PIL import Image
    import pyzbar.pyzbar as pyzbar
    QRCODE_AVAILABLE = True
except:
    QRCODE_AVAILABLE = False

# PDF处理
try:
    import PyPDF2
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False

# ===============================

CORRECT_PWD = "123456"

st.set_page_config(page_title="手机万能工具箱 V7", layout="centered")
st.title("📱 手机万能工具箱 V7")

pwd = st.text_input("🔑 全局密码", type="password")
if pwd != CORRECT_PWD:
    st.error("❌ 密码错误"); st.stop()

# 七栏切换（原有3个+新增4个）
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📄 CSV 直链模式", 
    "🖼️ 壁纸批量模式", 
    "📈 股票数据模式",
    "📥 通用下载",      # 新增
    "📰 文章朗读",      # 新增
    "🔲 二维码工具",    # 新增
    "📄 PDF工具"       # 新增
])

# -------------------------------------------------
# ① CSV 直链模式（原样保留，优化请求头）
# -------------------------------------------------
with tab1:
    st.header("CSV 过滤下载")
    url_csv = st.text_input("🔗 CSV 直链", placeholder="https://example.com/data.csv", key="csv_url")
    
    # 自动转换GitHub blob链接
    if url_csv and "github.com" in url_csv and "/blob/" in url_csv:
        url_csv = url_csv.replace("/blob/", "/raw/")
        st.info(f"🔄 已自动转换为Raw链接")
    
    key_csv = st.text_input("🔍 关键词过滤（可选）", key="csv_key")
    
    if st.button("开始爬取 CSV", key="csv_btn"):
        if not url_csv:
            st.error("❌ 请输入 CSV 直链"); st.stop()
        try:
            # 使用requests替代urllib，更稳定
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            resp = requests.get(url_csv, headers=headers, timeout=15)
            resp.raise_for_status()
            
            # 自动检测编码
            data = resp.text
            
            rows = list(csv.reader(data.splitlines()))
            if not rows: 
                st.error("❌ CSV 为空"); 
                st.stop()
                
            header, *body = rows
            hits = []
            for row in body:
                line = ",".join(row).lower()
                if not key_csv or key_csv.lower() in line:
                    hits.append([row[0] if row else "", ",".join(row), url_csv])
            
            df = pd.DataFrame(hits, columns=["第一列", "整行文本", "来源链接"])
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False, encoding="utf-8")
            st.success(f"✅ 完成！共 {len(hits)} 条")
            st.download_button("📥 下载结果 CSV", 
                             data=csv_buf.getvalue(),
                             file_name="result.csv", 
                             mime="text/csv")
        except Exception as e:
            st.error(f"❌ 错误：{str(e)}")

# -------------------------------------------------
# ② 壁纸批量模式（原样保留）
# -------------------------------------------------
with tab2:
    st.header("壁纸/图片 批量 ZIP")
    API_WH = "https://wallhaven.cc/api/v1/search"
    key_media = st.text_input("🔍 壁纸关键词（英文）", value="landscape", key="wall_key")
    pages = st.number_input("抓取页数", 1, 10, 2, key="wall_pages")
    min_res = st.selectbox("最低分辨率", ["any", "1920x1080", "2560x1440", "3840x2160"], key="wall_res")
    
    if st.button("开始抓取并打包 ZIP", key="wall_btn"):
        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                total = 0
                for p in range(1, pages + 1):
                    params = {"q": key_media, "page": p}
                    r = requests.get(API_WH, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                    r.raise_for_status()
                    data = r.json().get("data", [])
                    for item in data:
                        if min_res != "any" and item["resolution"] < min_res: 
                            continue
                        img_url = item["path"]
                        fname = img_url.split("/")[-1]
                        img_resp = requests.get(img_url, headers={"referer": "https://wallhaven.cc"}, timeout=30)
                        zf.writestr(fname, img_resp.content)
                        total += 1
                if total == 0: 
                    st.warning("未找到符合条件的图片"); 
                    st.stop()
            zip_buffer.seek(0)
            st.success(f"✅ 打包完成！共 {total} 张")
            st.download_button("📥 下载 ZIP 包",
                               data=zip_buffer.getvalue(), 
                               file_name=f"wallhaven_{key_media}_{pages}p.zip",
                               mime="application/zip")
        except Exception as e:
            st.error(f"❌ 错误：{str(e)}")

# -------------------------------------------------
# ③ 股票数据模式（原样保留）
# -------------------------------------------------
with tab3:
    st.header("📈 股票数据抓取")
    import akshare as ak
    code = st.text_input("股票代码（支持 600519 / 000858 / AAPL / 00700）",
                         placeholder="600519", key="stock_code")
    market = st.selectbox("市场", ["auto", "沪深", "港股", "美股"], key="stock_market")
    period = st.selectbox("数据类型", ["实时行情", "近一年日线"], key="stock_period")
    
    if st.button("获取股票数据", key="stock_btn"):
        try:
            # 自动加后缀
            if market == "auto":
                if code.startswith("6"): 
                    code += ".SS"
                elif code.startswith("0") or code.startswith("3"): 
                    code += ".SZ"
                elif code.isdigit() and len(code) == 5: 
                    code += ".HK"
                else: 
                    code = code.upper()
            elif market == "沪深" and not code.endswith((".SS", ".SZ")):
                code += ".SS" if code.startswith("6") else ".SZ"
            elif market == "港股" and not code.endswith(".HK"):
                code += ".HK"
            elif market == "美股":
                code = code.upper()

            if period == "实时行情":
                df = ak.stock_individual_info_em(symbol=code)
            else:
                df = ak.stock_zh_a_hist(symbol=code.split(".")[0], period="daily",
                                        start_date="20240101", 
                                        end_date=pd.Timestamp.today().strftime("%Y%m%d"))
            if df.empty: 
                st.warning("未获取到数据"); 
                st.stop()
                
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False, encoding="utf-8")
            st.success(f"✅ 股票数据已获取 {len(df)} 条")
            st.download_button("📥 下载 CSV", 
                             data=csv_buf.getvalue(),
                             file_name=f"{code}_{period}.csv", 
                             mime="text/csv")
            with st.expander("预览前 20 行"):
                st.dataframe(df.head(20))
        except Exception as e:
            st.error(f"❌ 错误：{str(e)}")

# -------------------------------------------------
# ④ 新增：通用文件下载（任何文件直链）
# -------------------------------------------------
with tab4:
    st.header("📥 通用文件下载器")
    st.info("支持任意文件：PDF、ZIP、MP3、MP4、EXE等")
    
    file_url = st.text_input("🔗 文件直链URL", placeholder="https://example.com/file.zip", key="file_url")
    custom_name = st.text_input("💾 保存文件名（可选，留空自动识别）", key="file_name")
    
    # 高级选项
    with st.expander("🔧 高级设置"):
        referer = st.text_input("Referer", placeholder="https://example.com", key="file_ref")
        use_stream = st.checkbox("流式下载（大文件推荐）", value=True, key="file_stream")
    
    if st.button("⬇️ 开始下载", key="file_btn"):
        if not file_url:
            st.error("❌ 请输入文件直链"); st.stop()
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
            }
            if referer:
                headers["Referer"] = referer
            
            with st.spinner("正在下载..."):
                if use_stream:
                    # 流式下载，适合大文件
                    resp = requests.get(file_url, headers=headers, stream=True, timeout=60)
                    resp.raise_for_status()
                    
                    # 获取文件名
                    if not custom_name:
                        # 从Content-Disposition或URL提取
                        cd = resp.headers.get('content-disposition', '')
                        fname = re.findall('filename="?([^"]+)"?', cd)
                        if fname:
                            custom_name = fname[0]
                        else:
                            custom_name = file_url.split("/")[-1].split("?")[0] or "download.bin"
                    
                    # 流式读取
                    file_buffer = io.BytesIO()
                    total_size = int(resp.headers.get('content-length', 0))
                    downloaded = 0
                    
                    progress_bar = st.progress(0)
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            file_buffer.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress_bar.progress(min(downloaded / total_size, 1.0))
                    
                    file_buffer.seek(0)
                else:
                    # 直接下载，适合小文件
                    resp = requests.get(file_url, headers=headers, timeout=30)
                    resp.raise_for_status()
                    file_buffer = io.BytesIO(resp.content)
                    
                    if not custom_name:
                        custom_name = file_url.split("/")[-1].split("?")[0] or "download.bin"
                
                # 自动识别MIME类型
                mime_types = {
                    '.pdf': 'application/pdf',
                    '.zip': 'application/zip',
                    '.mp3': 'audio/mpeg',
                    '.mp4': 'video/mp4',
                    '.txt': 'text/plain',
                    '.csv': 'text/csv',
                    '.json': 'application/json',
                }
                ext = os.path.splitext(custom_name)[1].lower()
                mime = mime_types.get(ext, 'application/octet-stream')
                
                st.success(f"✅ 下载完成！大小: {len(file_buffer.getvalue()) / 1024 / 1024:.2f} MB")
                st.download_button("📥 保存文件", 
                                 data=file_buffer.getvalue(),
                                 file_name=custom_name,
                                 mime=mime)
        except Exception as e:
            st.error(f"❌ 下载失败：{str(e)}")

# -------------------------------------------------
# ⑤ 新增：文章抓取+朗读
# -------------------------------------------------
with tab5:
    st.header("📰 文章抓取与朗读")
    
    if not NEWSPAPER_AVAILABLE:
        st.warning("⚠️ 未安装 newspaper3k，文章抓取功能不可用")
        st.code("pip install newspaper3k", language="bash")
    
    if not GTTS_AVAILABLE:
        st.warning("⚠️ 未安装 gTTS，语音朗读功能不可用")
        st.code("pip install gtts", language="bash")
    
    article_url = st.text_input("🔗 文章链接", placeholder="https://example.com/news.html", key="article_url")
    max_chars = st.slider("朗读字数限制", 100, 2000, 500, key="article_limit")
    
    col1, col2 = st.columns(2)
    with col1:
        fetch_btn = st.button("📄 抓取文章", key="article_fetch", disabled=not NEWSPAPER_AVAILABLE)
    with col2:
        tts_btn = st.button("🔊 生成语音", key="article_tts", disabled=not (NEWSPAPER_AVAILABLE and GTTS_AVAILABLE))
    
    if 'article_text' not in st.session_state:
        st.session_state.article_text = ""
    
    if fetch_btn and article_url:
        try:
            with st.spinner("正在抓取文章..."):
                article = Article(article_url, language='zh')
                article.download()
                article.parse()
                
                st.session_state.article_text = article.text
                st.success(f"✅ 抓取成功：{article.title}")
                st.write(f"**标题：** {article.title}")
                st.write(f"**作者：** {article.authors}")
                if article.publish_date:
                    st.write(f"**发布时间：** {article.publish_date}")
                
                with st.expander("查看正文"):
                    st.write(article.text[:2000] + "..." if len(article.text) > 2000 else article.text)
        except Exception as e:
            st.error(f"❌ 抓取失败：{str(e)}")
    
    if tts_btn and st.session_state.article_text:
        try:
            with st.spinner("正在生成语音..."):
                text_to_read = st.session_state.article_text[:max_chars]
                tts = gTTS(text=text_to_read, lang='zh-cn', slow=False)
                mp3_buffer = io.BytesIO()
                tts.write_to_fp(mp3_buffer)
                mp3_buffer.seek(0)
                
                st.success(f"✅ 语音生成完成（前{max_chars}字）")
                st.audio(mp3_buffer, format="audio/mp3")
                st.download_button("📥 下载MP3", 
                                 data=mp3_buffer.getvalue(),
                                 file_name="article_read.mp3",
                                 mime="audio/mpeg")
        except Exception as e:
            st.error(f"❌ 语音生成失败：{str(e)}")

# -------------------------------------------------
# ⑥ 新增：二维码工具
# -------------------------------------------------
with tab6:
    st.header("🔲 二维码工具")
    
    if not QRCODE_AVAILABLE:
        st.warning("⚠️ 未安装二维码依赖")
        st.code("pip install qrcode[pil] pyzbar pillow", language="bash")
        st.stop()
    
    qr_mode = st.radio("选择功能", ["生成二维码", "识别二维码"], horizontal=True)
    
    if qr_mode == "生成二维码":
        qr_content = st.text_area("输入内容", placeholder="https://example.com 或任意文本", key="qr_gen")
        qr_size = st.slider("尺寸", 5, 20, 10, key="qr_size")
        
        if st.button("生成二维码", key="qr_gen_btn"):
            if not qr_content:
                st.error("❌ 请输入内容"); st.stop()
            
            try:
                qr = qrcode.QRCode(version=1, box_size=qr_size, border=2)
                qr.add_data(qr_content)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # 转换为bytes
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="PNG")
                img_buffer.seek(0)
                
                st.image(img_buffer, caption="生成的二维码")
                st.download_button("📥 下载PNG", 
                                 data=img_buffer.getvalue(),
                                 file_name="qrcode.png",
                                 mime="image/png")
            except Exception as e:
                st.error(f"❌ 生成失败：{str(e)}")
    
    else:  # 识别二维码
        uploaded_qr = st.file_uploader("上传二维码图片", type=["png", "jpg", "jpeg", "gif"], key="qr_upload")
        
        if uploaded_qr:
            try:
                img = Image.open(uploaded_qr)
                st.image(img, caption="上传的图片", width=300)
                
                # 识别
                decoded = pyzbar.decode(img)
                if decoded:
                    st.success("✅ 识别成功")
                    for i, d in enumerate(decoded):
                        st.write(f"**内容 {i+1}：**")
                        st.code(d.data.decode('utf-8'))
                        
                        # 如果是URL，提供跳转
                        data_str = d.data.decode('utf-8')
                        if data_str.startswith(('http://', 'https://')):
                            st.markdown(f"[🔗 打开链接]({data_str})")
                else:
                    st.warning("未识别到二维码，请确保图片清晰")
            except Exception as e:
                st.error(f"❌ 识别失败：{str(e)}")

# -------------------------------------------------
# ⑦ 新增：PDF工具
# -------------------------------------------------
with tab7:
    st.header("📄 PDF合并工具")
    
    if not PDF_AVAILABLE:
        st.warning("⚠️ 未安装 PyPDF2")
        st.code("pip install PyPDF2", language="bash")
        st.stop()
    
    st.info("上传多个PDF文件，按顺序合并为一个")
    
    uploaded_pdfs = st.file_uploader("上传PDF文件（可多选）", 
                                     type=["pdf"], 
                                     accept_multiple_files=True,
                                     key="pdf_upload")
    
    if uploaded_pdfs:
        st.write(f"已上传 {len(uploaded_pdfs)} 个文件：")
        for i, pdf in enumerate(uploaded_pdfs, 1):
            st.write(f"{i}. {pdf.name}")
        
        if st.button("📎 合并PDF", key="pdf_merge_btn"):
            if len(uploaded_pdfs) < 2:
                st.warning("请至少上传2个PDF文件"); st.stop()
            
            try:
                merger = PyPDF2.PdfMerger()
                
                for pdf in uploaded_pdfs:
                    merger.append(pdf)
                
                # 输出到内存
                output_buffer = io.BytesIO()
                merger.write(output_buffer)
                output_buffer.seek(0)
                merger.close()
                
                st.success(f"✅ 合并完成！共 {len(uploaded_pdfs)} 个文件")
                st.download_button("📥 下载合并后的PDF",
                                 data=output_buffer.getvalue(),
                                 file_name="merged.pdf",
                                 mime="application/pdf")
            except Exception as e:
                st.error(f"❌ 合并失败：{str(e)}")

st.caption("💡 V7更新：新增通用下载、文章朗读、二维码、PDF工具，打造手机端全能工具箱")
