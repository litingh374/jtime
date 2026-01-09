import streamlit as st
import pandas as pd
import math

# ==========================================
# 1. 頁面與樣式設定
# ==========================================
st.set_page_config(
    page_title="雙標準工期評估工具 (竹中 + 鹿島)",
    page_icon="🏗️",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric {
        background-color: white;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    h3 { color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ 雙標準工期評估工具 (Takenaka & Kajima)")
st.caption("整合日本兩大營造廠工期估算邏輯：竹中工務店 (累積法) vs 鹿島建設 (回歸公式法)")
st.markdown("---")

# ==========================================
# 2. 側邊欄：共用參數輸入
# ==========================================
with st.sidebar:
    st.header("1. 建案基本資料")
    project_name = st.text_input("專案名稱", "台北商辦大樓案")
    
    # 共用參數
    col1, col2 = st.columns(2)
    floors_under = col1.number_input("地下層數", value=4.0, step=0.5)
    floors_above = col2.number_input("地上層數", value=20.0, step=0.5) # 預設改高一點以測試高層公式
    
    total_area = st.number_input("總樓地板面積 (㎡)", value=35000.0)
    
    # 鹿島專用參數
    st.markdown("---")
    st.caption("👇 鹿島公式專用參數")
    building_area = st.number_input("建築面積 (單層投影 ㎡)", value=1500.0, help="鹿島公式需要此參數 (Building Footprint)")
    ph_floors = st.number_input("屋突層數 (PH)", value=2.0, step=1.0)
    
    # 地點與用途 (影響鹿島係數)
    location_type = st.selectbox("基地位置", ["市區", "郊外"], index=0)
    usage_type = st.selectbox("建物用途", ["辦公室 (事務所)", "住宅", "飯店/醫院", "學校", "工廠/倉庫"], index=0)
    structure_type = st.selectbox("主要結構", ["SRC", "SS (鋼骨)", "RC"], index=1)

    st.markdown("---")
    
    # 稼動率設定
    st.header("2. 施工效率設定")
    calc_mode = st.radio("模式", ["自動計算 (台灣制)", "手動係數"], index=0)
    
    if calc_mode == "自動計算 (台灣制)":
        days_off = st.slider("週休天數", 0.0, 2.0, 1.5, step=0.5)
        nat_hol = st.number_input("年國定假", value=12)
        hrs = st.number_input("日工時", value=8.0)
        # 係數計算
        annual_hrs = (365 - days_off*52 - nat_hol) * hrs
        K_CONST = 2569.41
        work_coef = annual_hrs / K_CONST
        st.write(f"係數: `{work_coef:.4f}`")
    else:
        work_coef = st.number_input("係數", value=0.7574)

# ==========================================
# 3. 核心邏輯 A：竹中工務店 (Takenaka)
# ==========================================
def calc_takenaka():
    # 預設參數 (基於上一版反推結果)
    rate_u = 2.80  # 純工作月/層
    rate_a = 0.59  # 純工作月/層
    base_pile = 1.76
    finish = 3.25
    
    # 計算 (需除以稼動率)
    t_pile = base_pile / work_coef
    t_under = (floors_under * rate_u) / work_coef
    t_above = (floors_above * rate_a) / work_coef
    
    # 總工期
    total_bu = t_pile + t_under + t_above + finish
    
    # 逆打縮短 (假設 35%)
    reduction = t_under * 0.35
    total_td = total_bu - reduction
    
    return total_bu, total_td, t_under, t_above

# ==========================================
# 4. 核心邏輯 B：鹿島建設 (Kajima)
# ==========================================
def calc_kajima():
    # 判斷適用公式 (低層 vs 中高層)
    is_high_rise = floors_above >= 18
    
    # --- 係數庫 (基於 CSV 解析) ---
    coeffs = {
        "high": { # 18F 以上
            "const": 8.4,
            "usage": {"辦公室 (事務所)": -2.5, "住宅": 10.0, "飯店/醫院": 8.0, "學校": 0.5, "工廠/倉庫": 1.0},
            "loc": {"市區": 2.0, "郊外": -3.0},
            "struc": {"SRC": -3.5, "SS (鋼骨)": 2.0, "RC": 0.0}, # 高層 SRC 反而快
            "area_factor": 0.002,      # 建築面積係數
            "total_area_factor": -0.00007, # 總面積係數
            "u_factor": 1.7,  # 地下層權重
            "a_factor": 0.5,  # 地上層權重 (極快)
            "ph_factor": 1.3
        },
        "low": { # 17F 以下
            "const": 9.5,
            "usage": {"辦公室 (事務所)": 0.0, "住宅": 0.0, "飯店/醫院": 0.5, "學校": 0.5, "工廠/倉庫": 1.0},
            "loc": {"市區": 0.0, "郊外": -0.7},
            "struc": {"SRC": 1.0, "SS (鋼骨)": -1.0, "RC": 0.0},
            "area_factor": 0.0002,
            "total_area_factor": -0.000001,
            "u_factor": 2.2,
            "a_factor": 1.0,
            "ph_factor": -0.4
        }
    }
    
    c = coeffs["high"] if is_high_rise else coeffs["low"]
    
    # 取得對應係數 (若找不到 key 則給 0)
    val_use = c["usage"].get(usage_type, 0)
    val_loc = c["loc"].get(location_type, 0)
    val_str = c["struc"].get(structure_type, 0)
    
    # === 鹿島核心公式 ===
    # Y = (常數 + 用途 + 地域 + 構造 + 面積項 + 樓層項) * 0.9 (折減係數)
    
    sum_val = (
        c["const"] + 
        val_use + 
        val_loc + 
        val_str +
        (building_area * c["area_factor"]) + 
        (total_area * c["total_area_factor"]) +
        (floors_under * c["u_factor"]) + 
        (floors_above * c["a_factor"]) + 
        (ph_floors * c["ph_factor"])
    )
    
    total_months = sum_val * 0.9
    
    return total_months, is_high_rise

# ==========================================
# 5. 執行運算與結果呈現
# ==========================================

# 執行兩套運算
tak_bu, tak_td, tak_u_detail, tak_a_detail = calc_takenaka()
kaj_total, is_high = calc_kajima()

# 顯示區
st.subheader("📊 工期評估結果對比")

# KPI 比較
col1, col2, col3 = st.columns(3)
col1.metric("竹中 (順打)", f"{tak_bu:.1f} 個月", f"約 {tak_bu*30:.0f} 天")
col2.metric("竹中 (逆打)", f"{tak_td:.1f} 個月", f"節省 {tak_bu - tak_td:.1f} 月")
col3.metric("鹿島 (公式法)", f"{kaj_total:.1f} 個月", 
            f"{'中高層公式' if is_high else '低層公式'}", delta_color="off")

# 視覺化比較
tab1, tab2 = st.tabs(["📉 綜合比較圖表", "📝 詳細數據解析"])

with tab1:
    # 準備繪圖資料
    data = {
        "工法模型": ["竹中 (順打)", "竹中 (逆打)", "鹿島 (標準公式)"],
        "總工期 (月)": [tak_bu, tak_td, kaj_total]
    }
    df_chart = pd.DataFrame(data)
    
    # 使用 Altair 或 Streamlit 原生圖表
    st.bar_chart(df_chart.set_index("工法模型"))
    
    # 差異分析文字
    diff = kaj_total - tak_bu
    if abs(diff) < 3:
        st.success("✅ **分析結論**：兩套系統估算結果相當接近（誤差 3 個月內），具備高度參考價值。")
    elif diff > 0:
        st.info(f"ℹ️ **分析結論**：鹿島公式估算較長 (+{diff:.1f}月)。\n可能是因為鹿島公式對「{location_type}」或「{structure_type}」有額外的加權係數。")
    else:
        st.info(f"ℹ️ **分析結論**：鹿島公式估算較短 ({diff:.1f}月)。\n鹿島在高層建築 (18F+) 對地上層施工速度有非常積極的假設 (0.5月/層)。")

with tab2:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 🏗️ 竹中工務店 (Takenaka)")
        st.write("**邏輯：累積疊加法**")
        st.markdown(f"""
        - 地下工期: `{tak_u_detail:.1f}` 月
        - 地上工期: `{tak_a_detail:.1f}` 月
        - 裝修收尾: `3.25` 月 (固定)
        - **總計**: `{tak_bu:.1f}` 月
        """)
        st.caption("特色：邏輯透明，易於繪製甘特圖，能明確反映逆打工法優勢。")

    with col_b:
        st.markdown("### 🦌 鹿島建設 (Kajima)")
        st.write(f"**邏輯：多項式回歸 ({'18F以上' if is_high else '17F以下'})**")
        
        # 顯示鹿島係數細節 (Debug用)
        # 重新抓一次係數以顯示
        coeffs = {
            "const": 8.4 if is_high else 9.5,
            "u_factor": 1.7 if is_high else 2.2,
            "a_factor": 0.5 if is_high else 1.0
        }
        
        st.markdown(f"""
        - 基準常數: `{coeffs['const']}`
        - 地下權重: `{floors_under}層 × {coeffs['u_factor']}`
        - 地上權重: `{floors_above}層 × {coeffs['a_factor']}` (關鍵差異)
        - 結構修正: `{structure_type}`
        - **計算結果**: `{kaj_total:.1f}` 月
        """)
        st.caption("特色：基於大數據統計，能快速反應建築形狀(面積)與地點對工期的影響。")
        
    st.markdown("---")
    st.warning("**注意**：竹中模型會隨您設定的「稼動率」連動；鹿島模型則是基於日本標準統計，較不受手動稼動率設定影響(已內含折減係數 0.9)。")