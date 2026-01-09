import streamlit as st
import pandas as pd
import math

# --- 頁面設定 ---
st.set_page_config(
    page_title="新標準工期算出工具 (台灣客製版)",
    page_icon="🏗️",
    layout="wide"
)

# --- CSS樣式優化 ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏗️ 新標準工期算出工具 (Ver 2.5 台灣客製版)")
st.caption("基於 Takenaka 2010 邏輯核心，針對台灣行事曆與工時進行優化")
st.markdown("---")

# ==========================================
# 側邊欄：參數輸入
# ==========================================
with st.sidebar:
    st.header("1. 專案基本資料")
    project_name = st.text_input("工事名", "某商業大樓新建工程")
    
    # 結構係數 (參考原始 Excel)
    structure_map = {"RC": 1.0, "SRC": 2.0, "S": 3.0}
    ug_struct = st.selectbox("地下結構", options=structure_map.keys(), index=1)
    ag_struct = st.selectbox("地上結構", options=structure_map.keys(), index=2)
    
    col1, col2 = st.columns(2)
    floors_under = col1.number_input("地下階數", value=4.0, step=0.5)
    floors_above = col2.number_input("地上階數", value=16.0, step=0.5)
    
    total_area = st.number_input("總樓地板面積 (㎡)", value=28224.0, step=100.0)
    has_pile = st.checkbox("包含基樁工程 (杭)", value=True)

    st.markdown("---")
    
    # ------------------------------------------
    # 重點修改：動態稼動率計算機
    # ------------------------------------------
    st.header("2. 施工效率設定 (台灣模式)")
    st.info("請根據實際勞務狀況設定，系統將自動計算係數。")
    
    # 輸入參數
    days_off_per_week = st.slider("每週休假天數 (天)", 0.0, 2.0, 2.0, step=0.5, help="1.0=週休一日, 1.5=隔週休二日, 2.0=週休二日")
    national_holidays = st.number_input("年國定假日/颱風等 (天)", value=12, help="台灣勞基法約12天，可自行增加颱風假預估")
    daily_hours = st.number_input("每日實際工時 (小時)", value=8.0, step=0.5, help="竹中原版預設為7小時，台灣常為8小時")
    
    # --- 核心邏輯：係數計算 ---
    # 1. 計算年總工時
    total_days_year = 365
    annual_work_days = total_days_year - (days_off_per_week * 52) - national_holidays
    annual_work_hours = annual_work_days * daily_hours
    
    # 2. 竹中公式基準常數 (從原始 CSV 反推：2184小時 / 0.85係數)
    BASE_CONSTANT = 2569.41176
    
    # 3. 算出係數
    work_coef = annual_work_hours / BASE_CONSTANT
    
    # 顯示計算結果
    st.markdown(f"""
    <div style="background-color:#e6f3ff; padding:10px; border-radius:5px;">
        <b>📊 自動計算稼動率係數:</b> <code style="font-size:1.2em; color:blue">{work_coef:.4f}</code><br>
        <small>(年工時: {annual_work_hours:.1f} 小時)</small>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.header("3. 特殊條件")
    special_delay = st.number_input("特殊因素延遲 (個月)", value=0.0)

# ==========================================
# 核心計算邏輯 (請在此填入 Excel 公式)
# ==========================================

def calculate_schedule(f_u, f_a, area, coef, pile, is_top_down):
    """
    計算工期主函數
    """
    # -------------------------------------------------------------------------
    # ⚠️【待辦事項】請打開您的 .xls 檔案，將下列變數的計算方式替換為真實公式
    # 目前使用 "模擬公式" 讓程式能跑出接近範例的數字
    # -------------------------------------------------------------------------
    
    # [模擬] 地下室工期基準 (月)
    # 假設：跟面積開根號成正比，跟樓層數成正比，有樁再加時
    base_under_months = (math.sqrt(area) * 0.05 + f_u * 1.2) 
    if pile:
        base_under_months += 2.5
        
    # [模擬] 地上層工期基準 (月)
    # 假設：每層樓約 0.7 個月
    base_above_months = f_a * 0.75 + 0.5
    
    # [模擬] 收尾工程 (月)
    finishing_months = 3.25
    
    # [模擬] 逆打縮短時間 (月)
    # 假設：逆打可以讓地上層提早開始，縮短約 20% 的總時間
    reduction = 0.0
    if is_top_down:
        reduction = (base_under_months * 0.3) # 模擬值
    
    # -------------------------------------------------------------------------
    # 應用稼動率係數 (Coefficient Application)
    # 邏輯：係數越低(假越多)，工期需要越長。
    # 標準工期 = 基準工期 / 係數
    # -------------------------------------------------------------------------
    
    real_under = base_under_months / coef
    real_above = base_above_months / coef
    real_finish = finishing_months  # 收尾通常較不受重型機具稼動率影響，或可選擇是否除以係數
    
    total = (real_under + real_above + real_finish) - reduction + special_delay
    
    return {
        "underground": real_under,
        "above": real_above,
        "finish": real_finish,
        "reduction": reduction,
        "total": total
    }

# 執行計算
res_bu = calculate_schedule(floors_under, floors_above, total_area, work_coef, has_pile, is_top_down=False)
res_td = calculate_schedule(floors_under, floors_above, total_area, work_coef, has_pile, is_top_down=True)

# ==========================================
# 主畫面：結果展示
# ==========================================

# 1. KPI 指標區
col1, col2, col3 = st.columns(3)
col1.metric("順打工法 (Bottom-Up) 總工期", f"{res_bu['total']:.1f} 個月")
col2.metric("逆打工法 (Top-Down) 總工期", f"{res_td['total']:.1f} 個月", 
            delta=f"{res_td['total'] - res_bu['total']:.1f} 個月", delta_color="inverse")
col3.metric("逆打節省時間", f"{res_bu['total'] - res_td['total']:.1f} 個月")

st.markdown("### 📅 工期詳細比較表")

# 2. 數據視覺化
tab1, tab2 = st.tabs(["📊 圖表分析", "📝 詳細數據"])

with tab1:
    # 準備繪圖資料
    chart_data = pd.DataFrame({
        "工項": ["杭/地下結構", "地上結構", "裝修/機電/收尾", "特殊因素", "逆打節省"],
        "順打 (月)": [res_bu['underground'], res_bu['above'], res_bu['finish'], special_delay, 0],
        "逆打 (月)": [res_td['underground'], res_td['above'], res_td['finish'], special_delay, -res_td['reduction']]
    })
    
    # 轉置資料以符合 st.bar_chart 堆疊需求
    st.bar_chart(chart_data.set_index("工項"), color=["#FF9999", "#9999FF"])
    
    if res_td['total'] < res_bu['total']:
        st.success(f"💡 分析結論：在此條件下，採用**逆打工法**預計可比順打提早 **{res_bu['total'] - res_td['total']:.1f} 個月** 完工。")

with tab2:
    st.write("#### 計算明細 (單位：日曆月)")
    comparison_df = pd.DataFrame({
        "項目": ["基礎/地下工程", "地上結構工程", "受電/竣工收尾", "特殊條件", "逆打扣減", "<b>總工期</b>"],
        "順打工法": [
            f"{res_bu['underground']:.2f}", 
            f"{res_bu['above']:.2f}", 
            f"{res_bu['finish']:.2f}",
            f"{special_delay:.2f}",
            "0.00",
            f"<b>{res_bu['total']:.2f}</b>"
        ],
        "逆打工法": [
            f"{res_td['underground']:.2f}", 
            f"{res_td['above']:.2f}", 
            f"{res_td['finish']:.2f}",
            f"{special_delay:.2f}",
            f"-{res_td['reduction']:.2f}",
            f"<b>{res_td['total']:.2f}</b>"
        ]
    })
    # 顯示 HTML 表格以支援粗體
    st.write(comparison_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# ==========================================
# 頁尾說明
# ==========================================
st.markdown("---")
st.warning("⚠️ **注意**：本工具工期基準計算公式目前為模擬值。請務必將 Excel 內的真實物理公式填入 `calculate_schedule` 函數中以獲得正確結果。")