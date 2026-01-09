import streamlit as st
import pandas as pd
import math

# ==========================================
# 1. 系統設定
# ==========================================
st.set_page_config(
    page_title="台日雙軌工期評估系統 (Ver 5.1 獨立參數版)",
    page_icon="🏗️",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stAlert { padding: 10px; }
    /* 優化側邊欄標題 */
    .css-17lntkn { font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ 台日雙軌工期評估系統 (Ver 5.1)")
st.caption("雙獨立參數設定 | 竹中 (Takenaka) vs 鹿島 (Kajima)")
st.markdown("---")

try:
    # ==========================================
    # 2. 參數設定 (側邊欄)
    # ==========================================
    with st.sidebar:
        st.header("📝 1. 專案規模")
        project_name = st.text_input("專案名稱", "台北商辦大樓案")
        
        c1, c2, c3 = st.columns(3)
        floors_under = c1.number_input("地下F", value=4.0, step=0.5)
        floors_above = c2.number_input("地上F", value=20.0, step=0.5)
        ph_floors = c3.number_input("屋突PH", value=2.0, step=1.0)
        
        total_area = st.number_input("總樓地板面積 (FA ㎡)", value=35000.0)
        building_area = st.number_input("建築面積 (單層 ㎡)", value=1500.0)

        st.markdown("---")
        st.header("🏗️ 2. 結構與用途")
        
        # 結構共用 (會自動映射)
        struct_options = ["S (鋼骨)", "SRC (鋼骨鋼筋混凝土)", "RC (鋼筋混凝土)"]
        structure_type = st.selectbox("主要結構 (共用)", struct_options, index=0)
        
        st.markdown("#### 🏢 用途設定 (獨立選單)")
        # --- 修改重點：將用途拆分為左右兩欄 ---
        u_col1, u_col2 = st.columns(2)
        
        with u_col1:
            st.markdown("<small><b>竹中用途</b></small>", unsafe_allow_html=True)
            takenaka_opts = [
                "事務施設 (辦公)", "店舗", "購物中心", "住宅", "宿泊施設 (飯店)", 
                "医療・福祉", "教育研究施設", "工場", "倉庫・物流・駐車場", 
                "娯楽・集会施設", "その他建築"
            ]
            # 竹中用途選擇
            tak_usage = st.selectbox("竹中用途", takenaka_opts, index=0, label_visibility="collapsed")
            
        with u_col2:
            st.markdown("<small><b>鹿島用途</b></small>", unsafe_allow_html=True)
            kajima_opts = ["辦公室 (事務所)", "住宅", "飯店/醫院", "學校", "工廠/倉庫"]
            # 鹿島用途選擇
            kaj_usage = st.selectbox("鹿島用途", kajima_opts, index=0, label_visibility="collapsed")

        # 鹿島專用參數
        location_type = st.selectbox("基地位置 (鹿島專用)", ["市區", "郊外"], index=0)

        st.markdown("---")
        st.header("⚙️ 3. 施工效率")
        
        calc_mode = st.radio("稼動率模式", ["台灣行事曆自動計算", "手動輸入係數"], index=0)
        if calc_mode == "台灣行事曆自動計算":
            days_off = st.slider("週休天數", 0.0, 2.0, 1.5, step=0.5)
            nat_hol = st.number_input("國定假日", value=12)
            hrs = st.number_input("日工時", value=8.0)
            work_coef = ((365 - days_off*52 - nat_hol) * hrs) / 2569.41
            st.info(f"計算係數: **{work_coef:.4f}**")
        else:
            work_coef = st.number_input("係數", value=0.7574, format="%.4f")

    # ==========================================
    # 3. 核心運算：竹中 (Takenaka)
    # ==========================================
    def run_takenaka():
        # 結構速率調整 (S最快, RC最慢)
        if "RC" in structure_type:
            speed_factor = 1.4
            u_speed_factor = 1.1
        elif "SRC" in structure_type:
            speed_factor = 1.15
            u_speed_factor = 1.05
        else: # S
            speed_factor = 1.0
            u_speed_factor = 1.0
            
        base_rate_u = 2.80 * u_speed_factor
        base_rate_a = 0.59 * speed_factor 
        base_pile = 1.76
        
        # 用途影響 (使用 tak_usage)
        finish_base = 3.25
        if "住宅" in tak_usage or "宿泊" in tak_usage:
            finish_base *= 1.2
        elif "工場" in tak_usage or "倉庫" in tak_usage:
            finish_base *= 0.8
            
        # 顯示竹中速率資訊
        with st.sidebar:
            st.caption(f"ℹ️ 竹中速率 ({structure_type}):")
            st.caption(f"- 地下: {base_rate_u:.2f} 月/層")
            st.caption(f"- 地上: {base_rate_a:.2f} 月/層")
        
        t_pile = base_pile / work_coef
        t_under = (floors_under * base_rate_u) / work_coef
        t_above = (floors_above * base_rate_a) / work_coef
        
        total_bu = t_pile + t_under + t_above + finish_base
        
        reduction_ratio = 0.35 if "S" in structure_type else 0.25
        reduction = t_under * reduction_ratio
        total_td = total_bu - reduction
        
        return total_bu, total_td, reduction

    # ==========================================
    # 4. 核心運算：鹿島 (Kajima)
    # ==========================================
    def run_kajima():
        is_high = floors_above >= 18
        
        # 結構映射 (S -> SS)
        k_str_key = "SS (鋼骨)"
        if "RC" in structure_type: k_str_key = "RC"
        if "SRC" in structure_type: k_str_key = "SRC"

        # 係數庫 (直接使用 kaj_usage)
        if is_high: # 18F+
            const = 8.4
            c_use = {"辦公室 (事務所)": -2.5, "住宅": 10.0, "飯店/醫院": 8.0, "學校": 0.5, "工廠/倉庫": 1.0}.get(kaj_usage, 0)
            c_loc = {"市區": 2.0, "郊外": -3.0}.get(location_type, 0)
            c_str = {"SRC": -3.5, "SS (鋼骨)": 2.0, "RC": 0.0}.get(k_str_key, 0)
            
            val = (const + c_use + c_loc + c_str + 
                   (building_area * 0.002) + (total_area * -0.00007) + 
                   (floors_under * 1.7) + (floors_above * 0.5) + (ph_floors * 1.3))
        else: # 17F-
            const = 9.5
            c_use = {"辦公室 (事務所)": 0.0, "住宅": 0.0, "飯店/醫院": 0.5, "學校": 0.5, "工廠/倉庫": 1.0}.get(kaj_usage, 0)
            c_loc = {"市區": 0.0, "郊外": -0.7}.get(location_type, 0)
            c_str = {"SRC": 1.0, "SS (鋼骨)": -1.0, "RC": 0.0}.get(k_str_key, 0)
            
            val = (const + c_use + c_loc + c_str + 
                   (building_area * 0.0002) + (total_area * -0.000001) + 
                   (floors_under * 2.2) + (floors_above * 1.0) + (ph_floors * -0.4))
            
        return val * 0.9, is_high

    # ==========================================
    # 5. 執行與結果呈現
    # ==========================================
    res_tak_bu, res_tak_td, tak_red = run_takenaka()
    res_kaj, is_high_kaj = run_kajima()

    st.subheader(f"📊 專案評估：{project_name}")
    
    # KPI
    k1, k2, k3 = st.columns(3)
    k1.metric("竹中 (順打)", f"{res_tak_bu:.1f} 個月", f"用途: {tak_usage[:4]}...")
    k2.metric("竹中 (逆打)", f"{res_tak_td:.1f} 個月", f"結構: {structure_type.split(' ')[0]}")
    k3.metric("鹿島 (公式)", f"{res_kaj:.1f} 個月", f"用途: {kaj_usage}")

    # 圖表
    st.markdown("### 📈 工期模型比較")
    tab1, tab2 = st.tabs(["甘特圖模擬", "詳細參數表"])
    
    with tab1:
        chart_data = pd.DataFrame({
            "模型": ["竹中(順打)", "竹中(逆打)", "鹿島(公式)"],
            "工期 (月)": [res_tak_bu, res_tak_td, res_kaj]
        })
        st.bar_chart(chart_data.set_index("模型"))
        
        diff = res_kaj - res_tak_bu
        if abs(diff) < 5:
            st.success("✅ **一致性高**：兩大營造廠模型估算結果接近。")
        else:
            reason = "鹿島對該結構/用途有特殊加權"
            st.info(f"ℹ️ **差異顯著**：兩者相差 {abs(diff):.1f} 個月。")

    with tab2:
        st.table(pd.DataFrame({
            "比較項目": ["用途設定", "結構設定", "地上/地下/PH", "總樓地板/建築面積"],
            "竹中模型 (Takenaka)": [tak_usage, structure_type, f"{floors_above}/{floors_under}/-", "-"],
            "鹿島模型 (Kajima)": [kaj_usage, structure_type, f"{floors_above}/{floors_under}/{ph_floors}", f"{total_area:,.0f}/{building_area:,.0f}"]
        }))
        st.caption("註：竹中模型不直接使用面積參數與PH層參數，而是依賴結構別速率與樓層數。")

except Exception as e:
    st.error(f"運算發生錯誤: {e}")