import streamlit as st
from google import genai

# 假設這些變數是你從 FRED 取回並整理好的最新一筆數值
# latest_cpi = df_cpi.iloc[-1]['Value']
latest_cpi = 2.4
latest_unemployment = 4.1
latest_interest_rate = 4.75

st.subheader("💡 總經洞察")

# 按鈕觸發區塊
if st.button("產生 AI 總體經濟摘要"):
    # 確保已在 .streamlit/secrets.toml 中設定 API Key
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("請先在 secrets 中設定 GEMINI_API_KEY")
    else:
        # 使用 spinner 提供等待時的視覺回饋
        with st.spinner("正在推演總經局勢..."):
            try:
                # 1. 初始化最新的 google-genai Client
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                
                # 2. 建構 Prompt
                prompt = f"""
                請運用嚴謹的經濟學邏輯與第一性原理，基於以下最新數據撰寫約 200 字的短評：
                - CPI 年增率：{latest_cpi}%
                - 失業率：{latest_unemployment}%
                - 聯邦基金利率：{latest_interest_rate}%

                請以結構化的方式，拆解通膨與就業市場目前的連動關係，並推演後續可能的貨幣政策路徑與潛在影響。
                """
                
                # 3. 呼叫模型生成內容 (使用 flash 模型兼顧速度與品質)
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt
                )
                
                # 4. 顯示結果
                st.success("摘要生成完成！")
                st.markdown("### 🤖 數據解讀")
                st.info(response.text)
                
            except Exception as e:
                st.error(f"API 呼叫失敗，錯誤訊息：{e}")
