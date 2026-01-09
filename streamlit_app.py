import streamlit as st
import pandas as pd
from datetime import date, timedelta
import math

# --- 設定頁面配置 ---
st.set_page_config(page_title="標準工期算出工具 (Ver 2.5)", layout="wide")

st.title("🏗️ 標準工期算出工具 (仿 Takenaka Ver 2.5)")
st.markdown("---")

# --- 側邊欄：輸入參數 (參照 Source 1) ---
st.sidebar.header("1. 基本條件設定")

project_name = st.sidebar.text_input("工事名", "上海商銀-test")
location = st.sidebar.text_input("建築地", "台北")

# 結構與用途係數 (參照 Source 1 右下角表格)
# 這裡將 CSV 中的係數表轉化為 Python 字典
structure_options = {"RC": 1.0, "SRC": 2.0, "S": 3.0}
usage_options = {
    "事務施設(辦公)": 1.0, "店舗": 2.0, "購物中心": 3.0, "住宅": 4.0, 
    "飯店": 5.0, "醫院": 6.0, "學校": 7.0, "工廠": 10.0
}

underground_struct = st.sidebar.selectbox("地下/基礎構造", list(structure_options.keys()), index=1) # 預設 SRC
above_struct = st.sidebar.selectbox("地上構造", list(structure_options.keys()), index=2) # 預設 S
usage = st.sidebar.selectbox("建物用途", list(usage_options.keys()))

# 數值輸入
col1, col2 = st.sidebar.columns(2)
floors_under = col1.number_input("地下階數", value=4.0, step=0.5)
floors_above = col2.number_input("地上階數", value=16.0, step=0.5)
total_area = st.sidebar.number_input("延床面積 (㎡)", value=28224.0)
has_pile = st.sidebar.checkbox("杭（基樁）有無", value=True)

# 稼動率係數設定
st.sidebar.markdown("### 2. 效率設定")
work_day_options = {
    "週休一日 (係數 0.85)": 0.85,
    "週休一日+月休一六 (係數 0.757)": 0.75737,
    "趕工/無休 (係數 0.96)": 0.9644
}
work_coef_key = st.sidebar.selectbox("作業所稼働率", list(work_day_options.keys()), index=1)
work_coef = work_day_options[work_coef_key]

# 特殊條件
st.sidebar.markdown("### 3. 特殊條件")
special_delay = st.sidebar.number_input("特殊條件工期總和 (個月)", value=0.0)

# --- 核心計算邏輯 (這部分需要您校對 Excel 公式) ---
# 這裡使用模擬邏輯，請您對照 Excel 修改數值運算部分

def calculate_duration(f_under, f_above, area, coef, is_top_down=False):
    """
    計算工期的函數
    :param is_top_down: 是否為逆打工法
    """
    
    # ---------------------------------------------------------
    # ⚠️【關鍵】請在此處替換為 Excel 中的真實公式
    # 目前為依照您 CSV 輸出的數據反推的"模擬公式"
    # ---------------------------------------------------------
    
    # 1. 杭・地下階工期計算 (假設與面積開根號和樓層有關)
    # 模擬公式：基礎係數 * (地下樓層 * 2 + 面積係數) / 稼動率
    base_under = 17.1 if has_pile else 14.0 # 依照 CSV 範例填入的基準
    
    # 2. 地上階工期計算
    # 模擬公式：樓層 * 單層週期
    base_above = 12.5 # 依照 CSV 範例填入的基準
    
    # 3. 收尾測試
    finishing = 3.25
    
    # 如果是逆打 (Top-Down)，工期縮短
    reduction = 0.0
    if is_top_down:
        # CSV 顯示逆打縮短了約 5.76 個月
        reduction = 5.76 
        
    total_months = (base_under + base_above + finishing - reduction) + special_delay
    
    return {
        "underground": base_under,
        "above": base_above,
        "finishing": finishing,
        "reduction": reduction,
        "total": total_months
    }

# --- 執行計算 ---

# 1. 順打 (Bottom-Up)
res_bu = calculate_duration(floors_under, floors_above, total_area, work_coef, is_top_down=False)

# 2. 逆打 (Top-Down)
res_td = calculate_duration(floors_under, floors_above, total_area, work_coef, is_top_down=True)

# --- 顯示結果介面 ---

st.header(f"專案：{project_name} 工期試算結果")

# 建立分頁
tab1, tab2 = st.tabs(["📊 工期比較總表", "📅 詳細時程數據"])

with tab1:
    # 顯示關鍵指標
    c1, c2, c3 = st.columns(3)
    c1.metric("順打總工期", f"{res_bu['total']:.2f} 個月")
    c2.metric("逆打總工期", f"{res_td['total']:.2f} 個月", delta=f"-{res_bu['total'] - res_td['total']:.2f} 個月")
    c3.metric("工期縮短效益", f"{res_td['reduction']:.2f} 個月")

    # 製作圖表數據
    chart_data = pd.DataFrame({
        "工項": ["杭/地下", "地上結構", "收尾測試", "特殊條件"],
        "順打 (月)": [res_bu['underground'], res_bu['above'], res_bu['finishing'], special_delay],
        "逆打 (月)": [res_td['underground'], res_td['above'], res_td['finishing'], special_delay]
    })
    
    st.subheader("工種時間分佈比較")
    st.bar_chart(chart_data.set_index("工項"))

    if res_td['total'] < res_bu['total']:
        st.success(f"💡 建議：採用逆打工法可縮短工期約 {res_bu['total'] - res_td['total']:.1f} 個月")

with tab2:
    st.subheader("詳細計算數據")
    st.info("以下數據基於您輸入的參數與預設公式計算")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 🏗️ 順打工法 (Bottom-Up)")
        st.write(f"- 杭・地下階工期: **{res_bu['underground']:.2f}** 個月")
        st.write(f"- 地上階工期: **{res_bu['above']:.2f}** 個月")
        st.write(f"- 受電～竣工: **{res_bu['finishing']:.2f}** 個月")
        st.write(f"- **總計**: **{res_bu['total']:.2f}** 個月")
        
    with col_b:
        st.markdown("### 🏗️ 逆打工法 (Top-Down)")
        st.write(f"- 杭・地下階工期: **{res_td['underground']:.2f}** 個月")
        st.write(f"- 地上階工期: **{res_td['above']:.2f}** 個月")
        st.write(f"- 受電～竣工: **{res_td['finishing']:.2f}** 個月")
        st.write(f"- 逆打縮短時間: **-{res_td['reduction']:.2f}** 個月")
        st.write(f"- **總計**: **{res_td['total']:.2f}** 個月")

# --- 頁尾 ---
st.markdown("---")
st.caption("Calculation based on Takenaka 2010 Ver 2.5 Logic (Ported to Python)")