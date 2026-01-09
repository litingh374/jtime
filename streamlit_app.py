import streamlit as st
import pandas as pd
import math

# ==========================================
# 1. 系統設定 (必須放在第一行)
# ==========================================
st.set_page_config(
    page_title="台日雙軌工期評估系統 (竹中+鹿島)",
    page_icon="🏗️",
    layout="wide"
)

# 介面樣式優化
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ 台日雙軌工期評估系統 (Ver 4.6)")
st.caption("已修正圖表顯示錯誤 | 整合 Takenaka 與 Kajima 邏輯")
st.markdown("---")

try:
    # ==========================================
    # 2. 側邊欄：詳細參數設定
    # ==========================================
    with st.sidebar:
        st.header("📝 1. 專案規模設定")
        project_name = st.text_input("專案名稱", "台北商辦大樓案")
        
        # --- 關鍵規模參數 ---
        col_f1, col_f2, col_f3 = st.columns(3)
        floors_under = col_f1.number_input("地下層數", value=4.0, step=0.5)
        floors_above = col_f2.number_input("地上層數", value=20.0, step=0.5)
        ph_floors = col_f3.number_input("屋突(PH)", value=2.0, step=1.0, help="鹿島公式關鍵參數")
        
        total_area = st.number_input("總樓地板面積 (FA ㎡)", value=35000.0)
        building_area = st.number_input("建築面積 (單層投影 ㎡)", value=1500.0, help="鹿島公式專用 (Building Area)")

        st.markdown("---")
        st.header("🏗️ 2. 結構與用途")
        
        # 結構與用途 (影響鹿島係數)
        structure_type = st.selectbox("主要結構", ["SRC", "SS (鋼骨)", "RC"], index=1)
        location_type = st.selectbox("基地位置", ["市區", "郊外"], index=0)
        usage_type = st.selectbox("建物用途", ["辦公室 (事務所)", "住宅", "飯店/醫院", "學校", "工廠/倉庫"], index=0)

        st.markdown("---")
        st.header("⚙️ 3. 施工效率 (稼動率)")
        
        calc_mode = st.radio("計算模式", ["台灣行事曆自動計算", "手動輸入係數"], index=0)
        if calc_mode == "台灣行事曆自動計算":
            days_off = st.slider("週休天數", 0.0, 2.0, 1.5, step=0.5, help="1.5=隔週休二日")
            nat_hol = st.number_input("國定假日/颱風 (天)", value=12)
            hrs = st.number_input("每日工時 (hr)", value=8.0)
            
            # 係數計算 (基於竹中基準 2569.41)
            annual_hours = (365 - days_off*52 - nat_hol) * hrs
            CONST_BASE = 2569.41
            work_coef = annual_hours / CONST_BASE
            st.info(f"自動計算係數: **{work_coef:.4f}**")
        else:
            work_coef = st.number_input("稼動率係數", value=0.7574, format="%.4f")

    # ==========================================
    # 3. 核心運算：竹中工務店 (Takenaka)
    # ==========================================
    def run_takenaka():
        # 參數設定 (基於反推數據)
        rate_u = 2.80  # 地下純工期 (月/層)
        rate_a = 0.59  # 地上純工期 (月/層)
        base_pile = 1.76 # 基樁純工期
        finish = 3.25    # 收尾
        
        # 計算日曆天 (除以係數)
        t_pile = base_pile / work_coef
        t_under = (floors_under * rate_u) / work_coef
        t_above = (floors_above * rate_a) / work_coef
        
        # 總工期 (順打)
        total_bu = t_pile + t_under + t_above + finish
        
        # 逆打縮短 (假設縮短地下工期的 35%)
        reduction = t_under * 0.35
        total_td = total_bu - reduction
        
        return total_bu, total_td

    # ==========================================
    # 4. 核心運算：鹿島建設 (Kajima)
    # ==========================================
    def run_kajima():
        # 判斷適用公式 (18層為分界)
        is_high_rise = floors_above >= 18
        
        # 係數定義
        if is_high_rise:
            # --- 中高層公式 (18F+) ---
            c_const = 8.4
            c_use = {"辦公室 (事務所)": -2.5, "住宅": 10.0, "飯店/醫院": 8.0, "學校": 0.5, "工廠/倉庫": 1.0}.get(usage_type, 0)
            c_loc = {"市區": 2.0, "郊外": -3.0}.get(location_type, 0)
            c_str = {"SRC": -3.5, "SS (鋼骨)": 2.0, "RC": 0.0}.get(structure_type, 0)
            
            # 規模係數
            v_area = building_area * 0.002
            v_total_area = total_area * -0.00007
            v_under = floors_under * 1.7
            v_above = floors_above * 0.5
            v_ph = ph_floors * 1.3
            
        else:
            # --- 低層公式 (17F-) ---
            c_const = 9.5
            c_use = {"辦公室 (事務所)": 0.0, "住宅": 0.0, "飯店/醫院": 0.5, "學校": 0.5, "工廠/倉庫": 1.0}.get(usage_type, 0)
            c_loc = {"市區": 0.0, "郊外": -0.7}.get(location_type, 0)
            c_str = {"SRC": 1.0, "SS (鋼骨)": -1.0, "RC": 0.0}.get(structure_type, 0)
            
            v_area = building_area * 0.0002
            v_total_area = total_area * -0.000001
            v_under = floors_under * 2.2
            v_above = floors_above * 1.0
            v_ph = ph_floors * -0.4 

        # 原始公式計算
        raw_sum = c_const + c_use + c_loc + c_str + v_area + v_total_area + v_under + v_above + v_ph
        
        # 鹿島公式內建折減係數 0.9
        kajima_standard = raw_sum * 0.9
        
        return kajima_standard, is_high_rise

    # ==========================================
    # 5. 執行與顯示
    # ==========================================
    res_tak_bu, res_tak_td = run_takenaka()
    res_kaj, is_high = run_kajima()

    st.subheader(f"📊 評估結果：{project_name}")

    # KPI 區塊
    col1, col2, col3 = st.columns(3)

    col1.metric("竹中 (Takenaka) - 順打", f"{res_tak_bu:.1f} 個月", 
                f"累積法 | 地上{floors_above}F / 地下{floors_under}F")

    col2.metric("竹中 (Takenaka) - 逆打", f"{res_tak_td:.1f} 個月", 
                f"工期縮短 {res_tak_bu - res_tak_td:.1f} 個月", delta_color="inverse")

    col3.metric("鹿島 (Kajima) - 公式法", f"{res_kaj:.1f} 個月", 
                f"{'中高層' if is_high else '低樓層'}公式 | PH:{ph_floors}層")

    # 圖表區塊
    st.markdown("### 📈 雙工法模型比較")

    tab1, tab2 = st.tabs(["綜合甘特圖", "詳細數據比較"])

    with tab1:
        chart_df = pd.DataFrame({
            "模型": ["竹中(順打)", "竹中(逆打)", "鹿島(公式)"],
            "工期 (月)": [res_tak_bu, res_tak_td, res_kaj]
        })
        # 修正：移除 color 參數以避免錯誤
        st.bar_chart(chart_df.set_index("模型"))
        
        diff = res_kaj - res_tak_bu
        if diff > 5:
            st.warning(f"⚠️ **差異過大提醒**：鹿島公式算出的工期比竹中多了 {diff:.1f} 個月。")
        elif diff < -5:
            st.success(f"💡 **差異分析**：鹿島公式比竹中少了 {-diff:.1f} 個月。")
        else:
            st.info("✅ **結果一致**：兩套模型估算結果相近，數據可信度高。")

    with tab2:
        st.markdown("#### 參數驗證表")
        
        compare_df = pd.DataFrame({
            "輸入參數": ["地上層數", "地下層數", "屋突層數 (PH)", "總樓地板面積", "建築面積 (單層)", "結構", "用途"],
            "數值": [
                f"{floors_above}", 
                f"{floors_under}", 
                f"**{ph_floors}**", 
                f"{total_area:,.0f}", 
                f"{building_area:,.0f}", 
                structure_type, 
                usage_type
            ]
        })
        st.table(compare_df)
        
        st.markdown("""
        #### 公式邏輯備註
        1. **竹中工務店**：`(層數 × 單層速率) ÷ 稼動率係數`
        2. **鹿島建設**：回歸公式 (含屋突、面積、用途修正)
        """)

except Exception as e:
    st.error(f"發生未預期的錯誤: {e}")
    st.write("請檢查輸入數值是否正確（例如樓層數不可為負值）。")