import streamlit as st
import urllib.request
import csv
import io
import zipfile
import requests
import pandas as pd
import m3u8  # 新增：解析m3u8
import subprocess  # 新增：调用ffmpeg
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

CORRECT_PWD = "123456"

st.set_page_config(page_title="手机爬虫 V6", layout="centered")
st.title("📱 手机爬虫 V6（CSV + 壁纸 + 股票 + 视频）")

pwd = st.text_input("🔑 全局密码", type="password")
if pwd != CORRECT_PWD:
    st.error("❌ 密码错误"); st.stop()

# 四栏切换（新增视频标签）
tab1, tab2, tab3, tab4 = st.tabs([
    "📄 CSV 直链模式", 
    "🖼️ 壁纸批量模式", 
    "📈 股票数据模式",
    "🎬 视频抓取模式"  # 新增
])

# -------------------------------------------------
# ① CSV 直链模式（原样保留）
# -------------------------------------------------
with tab1:
    st.header("CSV 过滤下载")
    url_csv = st.text_input("🔗 CSV 直链", placeholder="https://example.com/data.csv", key="csv_url")
    key_csv = st.text_input("🔍 关键词过滤（可选）", key="csv_key")
    if st.button("开始爬取 CSV", key="csv_btn"):
        if not url_csv:
            st.error("❌ 请输入 CSV 直链"); st.stop()
        try:
            req = urllib.request.Request(url_csv, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 11)"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8", errors="ignore")
            rows = list(csv.reader(data.splitlines()))
            if not rows: st.error("❌ CSV 为空"); st.stop()
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
            st.download_button("📥 下载结果 CSV", data=csv_buf.getvalue(),
                               file_name="result.csv", mime="text/csv")
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
                        if min_res != "any" and item["resolution"] < min_res: continue
                        img_url = item["path"]
                        fname = img_url.split("/")[-1]
                        img_resp = requests.get(img_url, headers={"referer": "https://wallhaven.cc"}, timeout=30)
                        zf.writestr(fname, img_resp.content); total += 1
                if total == 0: st.warning("未找到符合条件的图片"); st.stop()
            zip_buffer.seek(0)
            st.success(f"✅ 打包完成！共 {total} 张"); st.download_button("📥 下载 ZIP 包",
                               data=zip_buffer.getvalue(), file_name=f"wallhaven_{key_media}_{pages}p.zip",
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
                if code.startswith("6"): code += ".SS"
                elif code.startswith("0") or code.startswith("3"): code += ".SZ"
                elif code.isdigit() and len(code) == 5: code += ".HK"   # 港股 5 位
                else: code = code.upper()                              # 美股直接大写
            elif market == "沪深" and not code.endswith((".SS", ".SZ")):
                code += ".SS" if code.startswith("6") else ".SZ"
            elif market == "港股" and not code.endswith(".HK"):
                code += ".HK"
            elif market == "美股":
                code = code.upper()

            if period == "实时行情":
                df = ak.stock_individual_info_em(symbol=code)          # 东财快照
            else:
                df = ak.stock_zh_a_hist(symbol=code.split(".")[0], period="daily",
                                        start_date="20240101", end_date=pd.Timestamp.today().strftime("%Y%m%d"))
            if df.empty: st.warning("未获取到数据"); st.stop()
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False, encoding="utf-8")
            st.success(f"✅ 股票数据已获取 {len(df)} 条")
            st.download_button("📥 下载 CSV", data=csv_buf.getvalue(),
                               file_name=f"{code}_{period}.csv", mime="text/csv")
            with st.expander("预览前 20 行"):
                st.dataframe(df.head(20))
        except Exception as e:
            st.error(f"❌ 错误：{str(e)}")

# -------------------------------------------------
# ④ 新增：视频抓取模式
# -------------------------------------------------
with tab4:
    st.header("🎬 视频抓取下载")
    
    video_type = st.radio("视频源类型", ["直链视频(.mp4等)", "M3U8流媒体", "yt-dlp万能解析"], horizontal=True)
    
    # 通用请求头设置
    headers_default = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "identity;q=1, *;q=0",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "",
        "Origin": ""
    }
    
    with st.expander("🔧 高级请求头设置（可选）"):
        referer = st.text_input("Referer", placeholder="https://example.com", key="vid_ref")
        origin = st.text_input("Origin", placeholder="https://example.com", key="vid_ori")
        cookie = st.text_input("Cookie（部分网站需要）", type="password", key="vid_cookie")
        custom_ua = st.text_input("自定义User-Agent", value=headers_default["User-Agent"], key="vid_ua")
    
    # 模式1: 直链视频
    if video_type == "直链视频(.mp4等)":
        video_url = st.text_input("🔗 视频直链URL", placeholder="https://example.com/video.mp4", key="direct_url")
        file_name = st.text_input("💾 保存文件名", value="video.mp4", key="direct_name")
        
        if st.button("⬇️ 开始下载直链视频", key="direct_btn"):
            if not video_url:
                st.error("❌ 请输入视频直链"); st.stop()
            
            # 构建请求头
            headers = headers_default.copy()
            headers["User-Agent"] = custom_ua
            if referer: headers["Referer"] = referer
            if origin: headers["Origin"] = origin
            if cookie: headers["Cookie"] = cookie
            
            try:
                with st.spinner("正在下载视频..."):
                    # 流式下载避免内存溢出
                    resp = requests.get(video_url, headers=headers, stream=True, timeout=60)
                    resp.raise_for_status()
                    
                    # 获取文件大小
                    total_size = int(resp.headers.get('content-length', 0))
                    
                    # 流式读取到内存
                    video_buffer = io.BytesIO()
                    downloaded = 0
                    progress_bar = st.progress(0)
                    
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            video_buffer.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = min(downloaded / total_size, 1.0)
                                progress_bar.progress(int(progress * 100))
                    
                    video_buffer.seek(0)
                    st.success(f"✅ 下载完成！大小: {len(video_buffer.getvalue()) / 1024 / 1024:.2f} MB")
                    st.download_button("📥 下载视频文件", 
                                     data=video_buffer.getvalue(),
                                     file_name=file_name,
                                     mime="video/mp4")
            except Exception as e:
                st.error(f"❌ 下载失败：{str(e)}")
    
    # 模式2: M3U8流媒体
    elif video_type == "M3U8流媒体":
        m3u8_url = st.text_input("🔗 M3U8链接", placeholder="https://example.com/playlist.m3u8", key="m3u8_url")
        merge_method = st.selectbox("合并方式", ["Python原生合并（较慢但稳定）", "ffmpeg（需系统安装，更快）"], key="m3u8_merge")
        custom_name = st.text_input("💾 保存文件名", value="output.mp4", key="m3u8_name")
        
        if st.button("⬇️ 开始解析并下载M3U8", key="m3u8_btn"):
            if not m3u8_url:
                st.error("❌ 请输入M3U8链接"); st.stop()
            
            try:
                with st.spinner("正在解析M3U8..."):
                    # 解析m3u8
                    playlist = m3u8.load(m3u8_url, headers={
                        "User-Agent": custom_ua,
                        "Referer": referer or m3u8_url,
                    })
                    
                    if not playlist.segments:
                        st.error("❌ 未找到视频片段，可能链接无效或需要认证"); st.stop()
                    
                    segments = playlist.segments
                    total_segments = len(segments)
                    st.info(f"📊 发现 {total_segments} 个视频片段")
                    
                    # 下载所有ts片段
                    ts_buffers = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    base_uri = playlist.base_uri or os.path.dirname(m3u8_url)
                    
                    for i, segment in enumerate(segments):
                        segment_url = urljoin(base_uri, segment.uri)
                        status_text.text(f"正在下载片段 {i+1}/{total_segments}...")
                        
                        seg_headers = {
                            "User-Agent": custom_ua,
                            "Referer": referer or m3u8_url,
                        }
                        if cookie: seg_headers["Cookie"] = cookie
                        
                        resp = requests.get(segment_url, headers=seg_headers, timeout=30)
                        resp.raise_for_status()
                        ts_buffers.append(resp.content)
                        progress_bar.progress(int((i + 1) / total_segments * 50))  # 前50%用于下载
                    
                    # 合并片段
                    status_text.text("正在合并视频片段...")
                    
                    if merge_method == "Python原生合并（较慢但稳定）":
                        # 纯Python合并（兼容性最好）
                        final_buffer = io.BytesIO()
                        for ts_data in ts_buffers:
                            final_buffer.write(ts_data)
                        final_buffer.seek(0)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ 合并完成")
                        
                        st.success(f"✅ M3U8下载完成！共 {total_segments} 个片段")
                        st.download_button("📥 下载合并后的视频", 
                                         data=final_buffer.getvalue(),
                                         file_name=custom_name,
                                         mime="video/mp4")
                    
                    else:  # ffmpeg方式
                        # 临时保存ts文件
                        temp_dir = "/tmp/m3u8_temp" if os.name != 'nt' else os.path.expanduser("~\\AppData\\Local\\Temp\\m3u8_temp")
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        ts_files = []
                        for i, ts_data in enumerate(ts_buffers):
                            ts_path = os.path.join(temp_dir, f"segment_{i:04d}.ts")
                            with open(ts_path, "wb") as f:
                                f.write(ts_data)
                            ts_files.append(ts_path)
                        
                        # 创建filelist
                        list_file = os.path.join(temp_dir, "filelist.txt")
                        with open(list_file, "w", encoding="utf-8") as f:
                            for ts_path in ts_files:
                                f.write(f"file '{ts_path}'\n")
                        
                        output_path = os.path.join(temp_dir, custom_name)
                        
                        # 调用ffmpeg
                        cmd = [
                            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                            "-i", list_file, "-c", "copy", output_path
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        if result.returncode == 0 and os.path.exists(output_path):
                            with open(output_path, "rb") as f:
                                video_data = f.read()
                            
                            # 清理临时文件
                            for f in ts_files + [list_file, output_path]:
                                try: os.remove(f)
                                except: pass
                            
                            progress_bar.progress(100)
                            st.success(f"✅ FFmpeg合并完成！")
                            st.download_button("📥 下载视频", 
                                             data=video_data,
                                             file_name=custom_name,
                                             mime="video/mp4")
                        else:
                            st.error(f"❌ FFmpeg合并失败：{result.stderr}")
                            
            except Exception as e:
                st.error(f"❌ M3U8处理失败：{str(e)}")
    
    # 模式3: yt-dlp万能解析（最强大）
    else:
        st.info("🚀 yt-dlp 支持 1000+ 视频网站（YouTube/Bilibili/抖音/优酷等）")
        yt_url = st.text_input("🔗 视频页面URL", placeholder="https://www.bilibili.com/video/BVxxxxx", key="yt_url")
        yt_quality = st.selectbox("画质偏好", ["best", "1080p", "720p", "480p", "worst"], key="yt_quality")
        audio_only = st.checkbox("仅下载音频（MP3）", key="yt_audio")
        
        if st.button("⬇️ 开始yt-dlp解析下载", key="yt_btn"):
            if not yt_url:
                st.error("❌ 请输入视频页面URL"); st.stop()
            
            try:
                import yt_dlp
                
                with st.spinner("yt-dlp正在解析，请稍候..."):
                    # 配置选项
                    ydl_opts = {
                        'format': 'bestaudio/best' if audio_only else f'bestvideo[height<={yt_quality.replace("p", "")}]+bestaudio/best',
                        'quiet': True,
                        'no_warnings': True,
                        'cookiefile': None,  # 如果需要登录，可以上传cookie文件
                    }
                    
                    if audio_only:
                        ydl_opts['postprocessors'] = [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }]
                        ext = "mp3"
                    else:
                        ext = "mp4"
                    
                    # 先获取信息
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(yt_url, download=False)
                        title = info.get('title', 'video')
                        st.success(f"✅ 解析成功：{title}")
                        st.json({
                            "标题": title,
                            "时长": f"{info.get('duration', 0)//60}分{info.get('duration', 0)%60}秒",
                            "上传者": info.get('uploader', '未知'),
                            "平台": info.get('extractor', '未知')
                        })
                        
                        # 实际下载到内存（注意：大视频可能内存不足，建议改为临时文件）
                        st.warning("⚠️ 注意：大视频建议直接使用yt-dlp命令行工具，避免内存溢出")
                        
                        # 这里提供下载链接生成（由于streamlit限制，大文件建议用外部下载）
                        download_url = info.get('url') or (info['formats'][-1]['url'] if info.get('formats') else None)
                        
                        if download_url:
                            st.code(f"直接视频流地址（可能有时效性）：\n{download_url}", language="text")
                            st.info("💡 提示：复制上方地址用IDM/Aria2下载，或在服务器运行 `yt-dlp {yt_url}`")
                        else:
                            st.info("该视频需要额外处理，建议复制链接到本地yt-dlp下载")
                            
            except ImportError:
                st.error("❌ 未安装yt-dlp，请运行：pip install yt-dlp")
            except Exception as e:
                st.error(f"❌ yt-dlp解析失败：{str(e)}")

st.caption("💡 V6更新：新增视频抓取功能，支持直链/M3U8/yt-dlp三种模式")
