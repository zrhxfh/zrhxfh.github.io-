import streamlit as st
import urllib.request
import csv
import os
from pathlib import Path
import pandas as pd
import io

CORRECT_PWD = "spider888"

st.set_page_config(page_title="手机爬虫", layout="centered")
st.title("📱 手机爬虫 v3（网页版）")

pwd = st.text_input("🔑 密码", type="password")
url = st.text_input("🔗 CSV直链")
key = st.text_input("🔍 关键词（可选）")

if st.button("开始爬取"):
    if pwd != CORRECT_PWD:
        st.error("❌ 密码错误")
    elif not url:
        st.error("❌ 请输入CSV直链")
    else:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 11)"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8", errors="ignore")

            rows = list(csv.reader(data.splitlines()))
            if not rows:
                st.error("❌ CSV为空")
                st.stop()

            header, *body = rows
            hits = []
            for row in body:
                line = ",".join(row).lower()
                if not key or key.lower() in line:
                    hits.append([row[0] if row else "", ",".join(row), url])

            df = pd.DataFrame(hits, columns=["第一列", "整行文本", "来源链接"])
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding="utf-8")
            csv_data = csv_buffer.getvalue()

            st.success(f"✅ 完成！共 {len(hits)} 条")
            st.download_button("📥 下载结果CSV", data=csv_data, file_name="result.csv", mime="text/csv")
        except Exception as e:
            st.error(f"❌ 错误：{str(e)}")
