import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from fredapi import Fred
from google import genai

# 1. 頁面基本配置
st.set_page_config(page_title="總體經濟與資產觀測站", layout="wide")

st.title("📊 總體經濟與資產觀測站")

# 2. 數據讀取與快取處理
@st.cache_data(ttl=3600)
def get_macro_data():
    # 預設基準值 (若 FRED API 尚未設定時備用)
    cpi, unemployment, interest_rate = 2.4, 4.1, 4.75
    
    # 若在 Secrets 中有設定 FRED_API_KEY，則動態抓取最新數據
    if "FRED_API_KEY" in st.secrets and st.secrets["FRED_API_KEY"]:
        try:
            fred = Fred(api_key=st.secrets["FRED_API_KEY"])
            # 抓取 CPI (CPIAUCSL)、失業率 (UNRATE)、聯邦基金利率 (FEDFUNDS)
            cpi_series = fred.get_series('CPIAUCSL')
            unemp_series = fred.get_series('UNRATE')
            rate_series = fred.get_series('FEDFUNDS')
            
            # 計算 CPI 年增率 (%)
            cpi_pct = cpi_series.pct_change(12) * 100
            
            cpi = float(cpi_pct.dropna().iloc[-1])
            unemployment = float(unemp_series.dropna().iloc[-1])
            interest_rate = float(rate_series.dropna().iloc[-1])
        except Exception:
            pass # 若抓取失敗則自動降級使用預設值
            
    return cpi, unemployment, interest_rate

latest_cpi, latest_unemployment, latest_interest_rate = get_macro_data()

# 3. 頂部關鍵指標卡片 (Metrics)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="CPI 年增率", value=f"{latest_cpi:.2f}%")
with col2:
    st.metric(label="失業率", value=f"{latest_unemployment:.2f}%")
with col3:
    st.metric(label="聯邦基金利率", value=f"{latest_interest_rate:.2f}%")

st.divider()

# 4. AI 總體經濟摘要模組
st.subheader("💡 AI 總經洞察")

if st.button("產生 AI 總體經濟摘要", type="primary"):
    # 檢查是否設定 GEMINI_API_KEY
    if "GEMINI_API_KEY" not in st.secrets or not st.secrets["GEMINI_API_KEY"]:
        st.error("❌ 請先在 Secrets 中設定 `GEMINI_API_KEY`。")
    else:
        with st.spinner("🤖 正在推演總經局勢..."):
            try:
                # 初始化 google-genai Client
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                
                # 建構 Prompt
                prompt = f"""
                請運用嚴謹的經濟學邏輯與第一性原理，基於以下最新數據撰寫約 200 字的短評：
                - CPI 年增率：{latest_cpi:.2f}%
                - 失業率：{latest_unemployment:.2f}%
                - 聯邦基金利率：{latest_interest_rate:.2f}%

                請以結構化的方式，拆解通膨與就業市場目前的連動關係，並推演後續可能的貨幣政策路徑與潛在影響。
                """
                
                # 呼叫官方標準 Flash 模型
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt
                )
                
                st.success("✅ 摘要生成完成！")
                st.markdown("### 🤖 數據解讀與觀點")
                st.info(response.text)
                
            except Exception as e:
                st.error(f"❌ API 呼叫失敗，錯誤訊息：{e}")
