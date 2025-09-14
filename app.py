import streamlit as st
import urllib.request
import csv
import io
import zipfile
import requests
import pandas as pd
from pathlib import Path

CORRECT_PWD = "spider888"

st.set_page_config(page_title="手机爬虫 V5", layout="centered")
st.title("📱 手机爬虫 V5（CSV + 壁纸 + 股票）")

pwd = st.text_input("🔑 全局密码", type="password")
if pwd != CORRECT_PWD:
    st.error("❌ 密码错误"); st.stop()

# 三栏切换
tab1, tab2, tab3 = st.tabs(["📄 CSV 直链模式", "🖼️ 壁纸批量模式", "📈 股票数据模式"])

# -------------------------------------------------
# ① CSV 直链模式（V4 原样保留）
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
# ② 壁纸批量模式（V4 原样保留）
# -------------------------------------------------
with tab2:
    st.header("壁纸/图片 批量 ZIP")
    API_WH = "https://wallhaven.cc/api/v1/search"
    key_media = st.text_input("🔍 壁纸关键词（英文）", value="landscape")
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
# ③ 新增：股票数据模式（实时行情 + 历史日线）
# -------------------------------------------------
with tab3:
    st.header("📈 股票数据抓取")
    import akshare as ak
    code = st.text_input("股票代码（支持 600519 / 000858 / AAPL / 00700）",
                         placeholder="600519")
    market = st.selectbox("市场", ["auto", "沪深", "港股", "美股"])
    period = st.selectbox("数据类型", ["实时行情", "近一年日线"])
    if st.button("获取股票数据"):
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

st.caption("💡 提示：CSV 模式维持旧版；壁纸模式抓 Wallhaven；股票模式使用 AkShare 公开接口，无需登录。")
