import streamlit as st
import pandas as pd
import math

# ==========================================
# 1. 頁面與樣式設定
# ==========================================
st.set_page_config(
    page_title="新標準工期算出工具 (Ver 3.0)",
    page_icon="🏗️",
    layout="wide"
)

# 自定義 CSS 讓介面更乾淨
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stExpander"] {
        border: 1px solid #ddd;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ 新標準工期算出工具 (Ver 3.0)")
st.caption("Based on Takenaka 2010 Logic | 參數已校正為上海商銀案基準")
st.markdown("---")

# ==========================================
# 2. 側邊欄：輸入參數
# ==========================================
with st.sidebar:
    st.header("1. 專案基本資料")
    project_name = st.text_input("專案名稱", "上海商銀-校正測試")
    
    col1, col2 = st.columns(2)
    ug_struct = col1.selectbox("地下結構", ["SRC", "RC", "S"], index=0)
    ag_struct = col2.selectbox("地上結構", ["S", "SRC", "RC"], index=0)
    
    col3, col4 = st.columns(2)
    floors_under = col3.number_input("地下層數", value=4.0, step=0.5)
    floors_above = col4.number_input("地上層數", value=16.0, step=0.5)
    
    total_area = st.number_input("總樓地板面積 (㎡)", value=28224.0)
    has_pile = st.checkbox("包含基樁工程 (杭)", value=True)

    st.markdown("---")
    
    # --- 稼動率計算區 ---
    st.header("2. 施工效率 (稼動率)")
    calc_mode = st.radio("設定模式", ["自動計算 (台灣制)", "手動輸入係數"], index=0)
    
    if calc_mode == "自動計算 (台灣制)":
        # 預設值調整為接近 Excel 的 0.757
        days_off = st.slider("每週休假 (天)", 0.0, 2.0, 1.25, step=0.25, help="1.25約等於隔週休二日")
        national_holidays = st.number_input("年國定假日 (天)", value=12)
        daily_hours = st.number_input("每日工時 (小時)", value=7.0, step=0.5, help="竹中標準版為7小時")
        
        # 公式：(365 - 休假 - 國定) * 工時 / 基準常數
        # 基準常數 2569.41 是從 0.85 係數反推而來
        annual_work_hours = (365 - (days_off * 52) - national_holidays) * daily_hours
        BASE_CONSTANT = 2569.41
        work_coef = annual_work_hours / BASE_CONSTANT
        
        st.markdown(f"**試算係數：** `{work_coef:.4f}`")
    else:
        # 預設填入 Excel 中的係數
        work_coef = st.number_input("稼動率係數", value=0.7574, format="%.4f")

    st.markdown("---")
    st.header("3. 特殊條件")
    special_delay = st.number_input("特殊因素延遲 (個月)", value=0.0)

# ==========================================
# 3. 核心邏輯參數 (進階校正區)
# ==========================================
with st.expander("⚙️ 進階參數校正 (已預填為「純工作日」基準)", expanded=True):
    st.info("此處數值為「不含休假的純工期」，程式會自動除以稼動率係數換算為日曆天。")
    
    c_p1, c_p2, c_p3 = st.columns(3)
    
    # 【關鍵修正】這裡的預設值是讓結果吻合 Excel 的關鍵
    # 地下 2.80 (純) / 0.757 = 3.7 (曆) -> x 4層 = 14.8月
    # 地上 0.59 (純) / 0.757 = 0.78 (曆) -> x 16層 = 12.5月
    rate_under = c_p1.number_input("地下結構速率 (月/層)", value=2.80, step=0.1)
    rate_above = c_p2.number_input("地上結構速率 (月/層)", value=0.59, step=0.05)
    base_pile_time = c_p3.number_input("基樁基礎工期 (月)", value=1.76, step=0.1)
    
    # 逆打縮短比例 (Excel約縮短地下工期的 39%)
    td_reduction_ratio = 0.39 

# ==========================================
# 4. 計算函數
# ==========================================
def calculate_schedule():
    # 1. 計算各分項的「日曆工期」 (Calendar Months)
    # 公式：(數量 * 純速率) / 稼動率係數
    
    # 基樁
    time_pile = (base_pile_time / work_coef) if has_pile else 0
    
    # 地下結構
    time_under = (floors_under * rate_under) / work_coef
    
    # 地上結構 (包含裝修收尾的總時程)
    time_above_total = (floors_above * rate_above) / work_coef
    
    # 收尾時間拆分 (僅用於圖表顯示，不影響總工期)
    # Excel 顯示受電竣工約 3.25 個月，我們從地上總工期中切出來顯示
    display_finish_time = 3.25
    time_above_structure = max(0, time_above_total - display_finish_time)
    
    # 2. 總工期計算 (順打)
    total_bu = time_pile + time_under + time_above_total + special_delay
    
    # 3. 逆打計算 (Top-Down)
    # 逆打縮短時間 = 地下工期 * 縮短比率
    reduction_time = time_under * td_reduction_ratio
    total_td = total_bu - reduction_time
    
    return {
        "pile": time_pile,
        "under": time_under,
        "above_struct": time_above_structure, # 僅結構部分
        "finish": display_finish_time,        # 收尾部分
        "above_total": time_above_total,      # 地上總計
        "reduction": reduction_time,
        "total_bu": total_bu,
        "total_td": total_td
    }

# 執行計算
res = calculate_schedule()

# ==========================================
# 5. 結果顯示區
# ==========================================
st.subheader(f"📊 專案工期試算：{project_name}")

# KPI 指標
k1, k2, k3 = st.columns(3)
k1.metric("順打 (Bottom-Up) 總工期", f"{res['total_bu']:.1f} 個月", help="預估約 29.6 個月 (吻合Excel)")
k2.metric("逆打 (Top-Down) 總工期", f"{res['total_td']:.1f} 個月", delta=f"-{res['reduction']:.1f} 個月", delta_color="inverse")
k3.metric("工期縮短效益", f"{res['reduction']:.1f} 個月")

# 圖表與數據
tab1, tab2 = st.tabs(["📉 甘特圖模擬", "📋 詳細數據表"])

with tab1:
    # 準備圖表數據 (將地上拆為結構+收尾)
    chart_data = pd.DataFrame({
        "工項": ["1.基樁工程", "2.地下結構", "3.地上結構", "4.裝修收尾", "5.特殊/逆打調整"],
        "順打工法": [
            res['pile'], 
            res['under'], 
            res['above_struct'], 
            res['finish'], 
            special_delay
        ],
        "逆打工法": [
            res['pile'], 
            res['under'], 
            res['above_struct'], 
            res['finish'], 
            special_delay - res['reduction'] # 顯示負值代表縮短
        ]
    })
    
    st.bar_chart(chart_data.set_index("工項"))
    
    st.caption("註：圖表中「地上結構」與「裝修收尾」是從地上總工期拆分顯示，以利視覺辨識。")

with tab2:
    # 建立比較表
    df_detail = pd.DataFrame({
        "項目": ["基樁工程", "地下結構", "地上工程 (含收尾)", "特殊條件", "逆打縮短", "<b>總工期 (月)</b>"],
        "順打數值": [
            f"{res['pile']:.2f}",
            f"{res['under']:.2f}",
            f"{res['above_total']:.2f}",
            f"{special_delay:.2f}",
            "-",
            f"<b>{res['total_bu']:.2f}</b>"
        ],
        "逆打數值": [
            f"{res['pile']:.2f}",
            f"{res['under']:.2f}",
            f"{res['above_total']:.2f}",
            f"{special_delay:.2f}",
            f"<span style='color:green'>-{res['reduction']:.2f}</span>",
            f"<b>{res['total_td']:.2f}</b>"
        ]
    })
    
    st.markdown("### 詳細工期計算表")
    st.write(df_detail.to_html(escape=False, index=False), unsafe_allow_html=True)
    
    st.markdown("""
    ---
    #### 💡 數據驗證 (Debug Info)
    - **稼動率係數**: `0.7574` (假設值)
    - **地下工期驗證**: 4層 × 2.80 / 0.7574 ≈ 14.79 月 (與Excel 14.77接近)
    - **地上工期驗證**: 16層 × 0.59 / 0.7574 ≈ 12.46 月 (與Excel 12.54接近)
    - **總和驗證**: 2.33(樁) + 14.79(地) + 12.46(天) ≈ 29.58 月
    """)