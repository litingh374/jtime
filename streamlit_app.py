import streamlit as st
import pandas as pd
import math

# --- 頁面設定 ---
st.set_page_config(
    page_title="竹中式標準工期算出工具 (Python復刻版)",
    page_icon="🏗️",
    layout="wide"
)

# --- CSS 優化 ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight:bold; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ 竹中式標準工期算出工具 (Python復刻版)")
st.markdown("**邏輯來源：** 基於您上傳的 `上海商銀-Ver2.5` 數據進行逆向工程反推。")
st.markdown("---")

# ==========================================
# 1. 側邊欄：基本參數
# ==========================================
with st.sidebar:
    st.header("1. 建案基本資料")
    project_name = st.text_input("專案名稱", "上海商銀-複刻測試")
    
    # 結構係數 (僅作標示，實際影響在下方的速度設定)
    st.caption("結構形式")
    c1, c2 = st.columns(2)
    ug_struct = c1.selectbox("地下", ["SRC", "RC", "S"], index=0)
    ag_struct = c2.selectbox("地上", ["S", "SRC", "RC"], index=0) # 預設 S
    
    st.caption("規模設定")
    c3, c4 = st.columns(2)
    floors_under = c3.number_input("地下層數", value=4.0, step=0.5)
    floors_above = c4.number_input("地上層數", value=16.0, step=0.5)
    
    total_area = st.number_input("總樓地板面積 (㎡)", value=28224.0)
    has_pile = st.checkbox("包含基樁工程 (杭)", value=True)

    st.markdown("---")
    
    # ==========================================
    # 2. 稼動率計算 (您之前的需求)
    # ==========================================
    st.header("2. 稼動率 (施工效率)")
    
    calc_method = st.radio("計算方式", ["自動計算 (台灣模式)", "手動輸入係數"], index=0)
    
    if calc_method == "自動計算 (台灣模式)":
        d_off = st.slider("每週休假 (天)", 0.0, 2.0, 2.0, step=0.5)
        d_hol = st.number_input("年國定假日 (天)", value=12)
        h_day = st.number_input("每日工時 (小時)", value=8.0, step=0.5)
        
        # 核心公式：(365-休假)*工時 / 竹中基準常數
        annual_hours = (365 - d_off*52 - d_hol) * h_day
        BASE_CONSTANT = 2569.41  # 從 CSV 反推的常數
        work_coef = annual_hours / BASE_CONSTANT
        
        st.info(f"年工時: {annual_hours} hr\n\n計算係數: **{work_coef:.4f}**")
    else:
        work_coef = st.number_input("直接輸入係數", value=0.7574, format="%.4f")

    st.markdown("---")
    st.header("3. 特殊調整")
    special_delay = st.number_input("特殊因素延遲 (月)", value=0.0)

# ==========================================
# 3. 進階參數校正 (核心反推區)
# ==========================================
with st.expander("⚙️ 進階參數校正 (基於 CSV 數據反推)", expanded=True):
    st.markdown("這裡的預設值是根據您上傳的 **上海商銀案 (地下SRC/地上S)** 反推出來的速率。")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    
    # 預設值說明：
    # 地下: (17.1-2.33)/4 = 3.69 個月/層
    # 地上: 12.54/16 = 0.78 個月/層
    # 基樁: 2.33 個月
    
    rate_under = col_p1.number_input("地下結構速度 (月/層)", value=3.70, step=0.1, help="包含開挖支撐。若為純RC可調低至2.5左右")
    rate_above = col_p2.number_input("地上結構速度 (月/層)", value=0.78, step=0.05, help="S結構約0.7-0.8，RC結構建議調高至1.2-1.5")
    base_pile_time = col_p3.number_input("基樁工程基礎時間 (月)", value=2.33, step=0.1)
    
    st.caption("注意：上述速度為「標準工時」，程式會再除以「稼動率係數」得到實際工期。")

# ==========================================
# 4. 運算邏輯
# ==========================================
def calculate_project():
    # 1. 基礎計算 (Base Duration)
    # 邏輯：層數 * 單層速度
    t_pile = base_pile_time if has_pile else 0
    t_under_base = floors_under * rate_under
    t_above_base = floors_above * rate_above
    t_finish_base = 3.25 # 收尾工程通常固定
    
    # 2. 逆打縮短邏輯 (Top-Down Logic)
    # 根據 CSV，逆打縮短了約 5.76 個月。
    # 邏輯推測：逆打時，地上層可以提早開始。
    # 假設：地上層在地下室做到 1/3 時即可開始
    reduction_td = 0
    # 簡易模擬：逆打可節省「地下室總工期」的 30% ~ 40%
    reduction_td = t_under_base * 0.35 

    # 3. 應用稼動率 (Apply Coefficient)
    # 公式：實際工期 = 基礎工期 / 係數
    # 注意：收尾期通常較有彈性，這裡假設也受係數影響
    
    res_bu = {
        "pile": t_pile / work_coef,
        "under": t_under_base / work_coef,
        "above": t_above_base / work_coef,
        "finish": t_finish_base, # 收尾不除以係數(依經驗)或可除
        "total": 0
    }
    res_bu["total"] = res_bu["pile"] + res_bu["under"] + res_bu["above"] + res_bu["finish"] + special_delay

    res_td = {
        "pile": res_bu["pile"],
        "under": res_bu["under"],
        "above": res_bu["above"],
        "finish": res_bu["finish"],
        "reduction": reduction_td / work_coef,
        "total": 0
    }
    res_td["total"] = res_bu["total"] - res_td["reduction"]
    
    return res_bu, res_td

bu, td = calculate_project()

# ==========================================
# 5. 結果顯示
# ==========================================
st.subheader(f"📊 專案試算結果：{project_name}")

# KPI 卡片
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("順打總工期", f"{bu['total']:.1f} 個月", f"約 {bu['total']*30:.0f} 天")
kpi2.metric("逆打總工期", f"{td['total']:.1f} 個月", delta=f"-{bu['total']-td['total']:.1f} 個月", delta_color="inverse")
kpi3.metric("結構體完成時間 (地上)", f"{(bu['total'] - bu['finish']):.1f} 個月")

# 詳細圖表
tab1, tab2 = st.tabs(["工期甘特圖模擬", "詳細數據表"])

with tab1:
    # 製作簡單的堆疊長條圖數據
    df_chart = pd.DataFrame({
        "工項": ["1.基樁", "2.地下結構", "3.地上結構", "4.裝修收尾", "5.逆打節省"],
        "順打 (Bottom-Up)": [bu['pile'], bu['under'], bu['above'], bu['finish'], 0],
        "逆打 (Top-Down)": [td['pile'], td['under'], td['above'], td['finish'], -td['reduction']]
    })
    st.bar_chart(df_chart.set_index("工項"))
    
    if td['total'] < bu['total']:
        st.success(f"💡 採用逆打工法，預計可讓地上結構提早 **{td['reduction']:.1f} 個月** 進行，總工期縮短至 **{td['total']:.1f} 個月**。")

with tab2:
    # 顯示精確數據
    st.write("### 計算明細 (單位：月)")
    st.markdown(f"""
    | 工項 | 順打工期 | 逆打工期 | 備註 |
    | :--- | :---: | :---: | :--- |
    | **稼動率係數** | `{work_coef:.4f}` | `{work_coef:.4f}` | 依設定自動計算 |
    | 基樁工程 | {bu['pile']:.2f} | {td['pile']:.2f} |  |
    | 地下結構 | {bu['under']:.2f} | {td['under']:.2f} | 基準速度: {rate_under} 月/層 |
    | 地上結構 | {bu['above']:.2f} | {td['above']:.2f} | 基準速度: {rate_above} 月/層 |
    | 裝修收尾 | {bu['finish']:.2f} | {td['finish']:.2f} | 固定 {3.25} 月 |
    | **逆打扣減** | - | <span style="color:red">-{td['reduction']:.2f}</span> | 同步施工效益 |
    | 特殊延遲 | {special_delay} | {special_delay} | |
    | **總計** | **{bu['total']:.2f}** | **{td['total']:.2f}** | |
    """, unsafe_allow_html=True)
    
    st.warning("註：此為基於 2010 年版數據反推之估算值，實際工期需考量缺工、缺料及地質變異。")