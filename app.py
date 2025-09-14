# app.py  手机爬虫 v4  (CSV + 壁纸/图片/视频封面 双模式)
import streamlit as st
import urllib.request
import csv
import io
import os
import zipfile
import requests
import pandas as pd
from pathlib import Path

CORRECT_PWD = "spider888"

st.set_page_config(page_title="手机爬虫 v4", layout="centered")
st.title("📱 手机爬虫 v4（CSV + 图片/壁纸/视频）")

pwd = st.text_input("🔑 全局密码", type="password")
if pwd != CORRECT_PWD:
    st.error("❌ 密码错误，无法继续"); st.stop()

tab1, tab2 = st.tabs(["📄 CSV 直链模式", "🖼️ 媒体批量模式"])

# -------------------------------------------------
# ① CSV 直链模式（保留旧功能）
# -------------------------------------------------
with tab1:
    st.header("CSV 过滤下载")
    url_csv = st.text_input("🔗 CSV 直链", placeholder="https://example.com/data.csv")
    key_csv = st.text_input("🔍 关键词过滤（可选）")
    if st.button("开始爬取 CSV"):
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
# ② 媒体批量模式（壁纸/图片/视频封面）
# -------------------------------------------------
with tab2:
    st.header("壁纸/图片/视频封面 批量抓取")
    # 默认用 wallhaven 免费接口，国内可通
    API_WH = "https://wallhaven.cc/api/v1/search"
    key_media = st.text_input("🔍 关键词（英文）", value="landscape")
    pages = st.number_input("抓取页数", 1, 10, 2)
    min_res = st.selectbox("最低分辨率", ["any", "1920x1080", "2560x1440", "3840x2160"])
    if st.button("开始抓取并打包 ZIP"):
        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                total = 0
                for p in range(1, pages + 1):
                    params = {"q": key_media, "page": p}
                    r = requests.get(API_WH, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                    r.raise_for_status()
                    data = r.json().get("data", [])
                    if not data: continue
                    for item in data:
                        if min_res != "any" and item["resolution"] < min_res:
                            continue
                        img_url = item["path"]          # 原图直链
                        fname = img_url.split("/")[-1]  # wallhaven-xxx.jpg
                        img_resp = requests.get(img_url, headers={"referer": "https://wallhaven.cc"}, timeout=30)
                        zf.writestr(fname, img_resp.content)
                        total += 1
                if total == 0:
                    st.warning("未找到符合条件的图片"); st.stop()
            zip_buffer.seek(0)
            st.success(f"✅ 打包完成！共 {total} 张")
            st.download_button("📥 下载 ZIP 包", data=zip_buffer.getvalue(),
                               file_name=f"media_{key_media}_{pages}p.zip", mime="application/zip")
        except Exception as e:
            st.error(f"❌ 错误：{str(e)}")

# -------------------------------------------------
# 底部说明
# -------------------------------------------------
st.caption("💡 提示：CSV 模式支持任意公开 CSV；媒体模式默认 Wallhaven 高清壁纸，"
           "如需爬视频平台或 Unsplash/Pexels 可把接口换成官方 API。")
