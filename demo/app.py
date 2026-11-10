import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from fredapi import Fred
from google import genai

# ---------------------------------------------------------
# 1. 頁面基本配置
# ---------------------------------------------------------
st.set_page_config(page_title="總體經濟與資產觀測站", layout="wide")

st.title("📊 總體經濟與資產觀測站")
st.caption("整合美日總經數據、黃金現貨市場走勢、美債殖利率倒掛警示與 AI 自動化分析")

# ---------------------------------------------------------
# 2. 資料讀取與快取處理
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def load_dashboard_data():
    # 預設定備數據 (若 API 暫時無法連線時維護頁面運作)
    cpi, unemp, fed_rate, jp_10y = 2.40, 4.10, 4.75, 0.95
    gold_latest, gold_delta = 2750.00, 0.00
    df_gold = pd.DataFrame()
    df_jp_yield = pd.DataFrame()
    df_spread = pd.DataFrame()
    latest_spread = 0.50
    latest_spread_date = ""

    # --- A. yfinance 抓取黃金現貨 (GC=F) ---
    try:
        gold_data = yf.Ticker("GC=F").history(period="1y")
        if not gold_data.empty:
            df_gold = gold_data.reset_index()
            gold_latest = float(df_gold['Close'].iloc[-1])
            gold_prev = float(df_gold['Close'].iloc[-2])
            gold_delta = gold_latest - gold_prev
    except Exception:
        pass

    # --- B. FRED API 抓取總經與債券數據 ---
    if "FRED_API_KEY" in st.secrets and st.secrets["FRED_API_KEY"]:
        try:
            fred_key = str(st.secrets["FRED_API_KEY"]).strip()
            fred = Fred(api_key=fred_key)
            
            # 1. 通膨 (CPIAUCSL)、失業率 (UNRATE)、聯邦基金利率 (FEDFUNDS)
            cpi_series = fred.get_series('CPIAUCSL')
            unemp_series = fred.get_series('UNRATE')
            rate_series = fred.get_series('FEDFUNDS')
            
            cpi_pct = cpi_series.pct_change(12) * 100
            cpi = float(cpi_pct.dropna().iloc[-1])
            unemp = float(unemp_series.dropna().iloc[-1])
            fed_rate = float(rate_series.dropna().iloc[-1])

            # 2. 日本 10 年期國債殖利率 (IRLTLT01JPM156N)
            jp_series = fred.get_series('IRLTLT01JPM156N')
            if not jp_series.dropna().empty:
                jp_10y = float(jp_series.dropna().iloc[-1])
                df_jp_yield = jp_series.dropna().reset_index()
                df_jp_yield.columns = ['Date', 'Yield']

            # 3. 美債 10Y-2Y 利差 (DGS10 - DGS2)
            dgs10 = fred.get_series('DGS10')
            dgs2 = fred.get_series('DGS2')
            df_sp = pd.DataFrame({'10Y': dgs10, '2Y': dgs2}).dropna()
            df_sp['Spread'] = df_sp['10Y'] - df_sp['2Y']
            df_spread = df_sp.reset_index().rename(columns={'index': 'Date'})
            
            if not df_spread.empty:
                latest_spread = float(df_spread['Spread'].iloc[-1])
                latest_spread_date = df_spread['Date'].iloc[-1].strftime('%Y-%m-%d')
        except Exception:
            pass

    return {
        "cpi": cpi,
        "unemp": unemp,
        "fed_rate": fed_rate,
        "jp_10y": jp_10y,
        "gold_latest": gold_latest,
        "gold_delta": gold_delta,
        "df_gold": df_gold,
        "df_jp_yield": df_jp_yield,
        "df_spread": df_spread,
        "latest_spread": latest_spread,
        "latest_spread_date": latest_spread_date
    }

data = load_dashboard_data()

# ---------------------------------------------------------
# 3. 頂部關鍵指標列 (Metrics Bar)
# ---------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric(label="美國 CPI 年增率", value=f"{data['cpi']:.2f}%")
with m2:
    st.metric(label="美國失業率", value=f"{data['unemp']:.2f}%")
with m3:
    st.metric(label="聯邦基金利率", value=f"{data['fed_rate']:.2f}%")
with m4:
    st.metric(label="日債 10Y 殖利率", value=f"{data['jp_10y']:.2f}%")
with m5:
    st.metric(
        label="黃金現貨 (GC=F)", 
        value=f"${data['gold_latest']:.2f}", 
        delta=f"{data['gold_delta']:+.2f}"
    )

st.divider()

# ---------------------------------------------------------
# 4. 美債利差倒掛警示燈號
# ---------------------------------------------------------
if data['latest_spread'] < 0:
    st.error(
        f"🚨 **殖利率曲線倒掛警示（10Y - 2Y 利差小於 0）** | "
        f"最新數據（{data['latest_spread_date']}）：**{data['latest_spread']:.2f}%**。衰退預期警示燈號亮起。"
    )
else:
    st.success(
        f"✅ **殖利率曲線斜率正常（10Y - 2Y 利差維持零軸上方）** | "
        f"最新數據（{data['latest_spread_date']}）：**{data['latest_spread']:.2f}%**。"
    )

# ---------------------------------------------------------
# 5. 圖表分頁 (Tabs Layout)
# ---------------------------------------------------------
tab_spread, tab_gold, tab_jp = st.tabs([
    "📉 美債 10Y-2Y 利差走勢", 
    "🥇 黃金現貨歷史價格", 
    "🇯🇵 日本 10 年期國債殖利率"
])

with tab_spread:
    if not data['df_spread'].empty:
        fig_spread = px.line(
            data['df_spread'], 
            x='Date', 
            y='Spread', 
            title="美債 10 年期與 2 年期殖利率歷史利差 (DGS10 - DGS2)",
            labels={'Spread': '利差 (%)', 'Date': '日期'}
        )
        fig_spread.add_hline(
            y=0, 
            line_dash="dash", 
            line_color="red", 
            annotation_text="倒掛警戒線 (0%)",
            annotation_position="bottom right"
        )
        fig_spread.update_layout(template="plotly_white", hovermode="x unified")
        st.plotly_chart(fig_spread, use_container_width=True)
    else:
        st.info("💡 請在 Secrets 中設定 `FRED_API_KEY` 以載入利差歷史資料。")

with tab_gold:
    if not data['df_gold'].empty:
        fig_gold = px.line(
            data['df_gold'], 
            x='Date', 
            y='Close', 
            title="黃金現貨價格走勢 (USD/oz)",
            labels={'Close': '價格 (美元)', 'Date': '日期'}
        )
        fig_gold.update_layout(template="plotly_white", hovermode="x unified")
        st.plotly_chart(fig_gold, use_container_width=True)
    else:
        st.info("💡 正在讀取 yfinance 黃金歷史資料...")

with tab_jp:
    if not data['df_jp_yield'].empty:
        fig_jp = px.line(
            data['df_jp_yield'], 
            x='Date', 
            y='Yield', 
            title="日本 10 年期國債殖利率歷史走勢 (FRED: IRLTLT01JPM156N)",
            labels={'Yield': '殖利率 (%)', 'Date': '日期'}
        )
        fig_jp.update_layout(template="plotly_white", hovermode="x unified")
        st.plotly_chart(fig_jp, use_container_width=True)
    else:
        st.info("💡 請在 Secrets 中設定 `FRED_API_KEY` 以載入日本國債資料。")

st.divider()

# ---------------------------------------------------------
# 6. AI 總經與資產洞察模組 (Google GenAI)
# ---------------------------------------------------------
st.subheader("💡 AI 跨市場總經洞察")

if st.button("產生 AI 總體經濟摘要", type="primary"):
    if "GEMINI_API_KEY" not in st.secrets or not st.secrets["GEMINI_API_KEY"]:
        st.error("❌ 請先在 Streamlit Secrets 中設定 `GEMINI_API_KEY`。")
    else:
        with st.spinner("🤖 正在綜合美日利差、通膨、利率與黃金走勢推演總經局勢..."):
            try:
                api_key = str(st.secrets["GEMINI_API_KEY"]).strip()
                client = genai.Client(api_key=api_key)
                
                prompt = f"""
                請運用嚴謹的經濟學邏輯與第一性原理，基於以下最新數據撰寫約 250 字的總體經濟與資產短評：
                - 美國 CPI 年增率：{data['cpi']:.2f}%
                - 美國失業率：{data['unemp']:.2f}%
                - 美國聯邦基金利率：{data['fed_rate']:.2f}%
                - 美債 10Y-2Y 利差：{data['latest_spread']:.2f}%
                - 日本 10 年期國債殖利率：{data['jp_10y']:.2f}%
                - 黃金現貨價格：${data['gold_latest']:.2f}

                請以結構化方式拆解：
                1. 總體需求視角下的美國通膨與就業連動關係，並推演央行後續貨幣政策路徑。
                2. 美債利差倒掛狀態與美日利差變化對國際資金流向及避險資產（黃金）的連動關係。
                """
                
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt
                )
                
                if response and hasattr(response, 'text') and response.text:
                    st.success("✅ 摘要生成完成！")
                    st.markdown("### 🤖 數據解讀與觀點")
                    st.info(response.text)
                else:
                    st.warning("⚠️ 模型未回傳有效內容，請重新點擊嘗試。")
                    
            except Exception as e:
                st.error(f"❌ API 呼叫失敗：{e}")    
