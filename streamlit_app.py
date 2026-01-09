import streamlit as st
import pandas as pd
import math

# ==========================================
# 1. 系統設定
# ==========================================
st.set_page_config(
    page_title="台日雙軌工期評估系統 (Ver 5.0 完整版)",
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
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ 台日雙軌工期評估系統 (Ver 5.0)")
st.caption("整合竹中工務店 (Menu參數連動版) 與 鹿島建設 (回歸公式版)")
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
        st.header("🏗️ 2. 結構與用途 (竹中參數)")
        
        # 竹中 Menu 定義的 11 種用途
        # 邏輯：用途主要影響裝修與收尾時間，結構影響軀體時間
        usage_options = [
            "事務施設 (辦公)", "店舗", "購物中心", "住宅", "宿泊施設 (飯店)", 
            "医療・福祉", "教育研究施設", "工場", "倉庫・物流・駐車場", 
            "娯楽・集会施設", "その他建築"
        ]
        usage_type = st.selectbox("建物用途", usage_options, index=0)
        
        # 竹中 Menu 定義的結構
        struct_options = ["S (鋼骨)", "SRC (鋼骨鋼筋混凝土)", "RC (鋼筋混凝土)"]
        structure_type = st.selectbox("主要結構", struct_options, index=0)
        
        location_type = st.selectbox("基地位置 (鹿島用)", ["市區", "郊外"], index=0)

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
    # 3. 核心運算：竹中 (Takenaka) - 動態修正版
    # ==========================================
    def run_takenaka():
        # --- 根據結構自動調整「純工作速率」 ---
        # 基準(S): 地上 0.6月/層, 地下 2.8月/層
        # 係數邏輯：RC 最慢 (x1.4), SRC 次之 (x1.15), S 最快 (x1.0)
        
        if "RC" in structure_type:
            speed_factor = 1.4
            u_speed_factor = 1.1 # 地下室 RC 與 SRC 差異較小
        elif "SRC" in structure_type:
            speed_factor = 1.15
            u_speed_factor = 1.05
        else: # S
            speed_factor = 1.0
            u_speed_factor = 1.0
            
        # 基礎速率 (Base Rate) - 可在此微調
        base_rate_u = 2.80 * u_speed_factor
        base_rate_a = 0.59 * speed_factor 
        base_pile = 1.76
        
        # 用途對裝修期的影響 (簡單加權)
        finish_base = 3.25
        if "住宅" in usage_type or "宿泊" in usage_type:
            finish_base *= 1.2 # 隔間多，收尾慢
        elif "工場" in usage_type or "倉庫" in usage_type:
            finish_base *= 0.8 # 收尾快
            
        # 顯示目前的速率給使用者看
        with st.sidebar:
            st.caption(f"ℹ️ 竹中速率設定 ({structure_type}):")
            st.caption(f"- 地下: {base_rate_u:.2f} 月/層")
            st.caption(f"- 地上: {base_rate_a:.2f} 月/層")
        
        # 計算 (除以稼動率)
        t_pile = base_pile / work_coef
        t_under = (floors_under * base_rate_u) / work_coef
        t_above = (floors_above * base_rate_a) / work_coef
        
        total_bu = t_pile + t_under + t_above + finish_base
        
        # 逆打縮短 (SRC/S 效果較好)
        reduction_ratio = 0.35 if "S" in structure_type else 0.25
        reduction = t_under * reduction_ratio
        total_td = total_bu - reduction
        
        return total_bu, total_td, reduction

    # ==========================================
    # 4. 核心運算：鹿島 (Kajima) - 完整公式版
    # ==========================================
    def run_kajima():
        is_high = floors_above >= 18
        
        # 映射用途字串到鹿島係數 key
        k_use_map = {
            "事務施設 (辦公)": "辦公室 (事務所)", 
            "住宅": "住宅", 
            "宿泊施設 (飯店)": "飯店/醫院",
            "医療・福祉": "飯店/醫院",
            "教育研究施設": "學校",
            "工場": "工廠/倉庫",
            "倉庫・物流・駐車場": "工廠/倉庫"
        }
        k_use_key = k_use_map.get(usage_type, "辦公室 (事務所)") # 預設辦公
        
        # 映射結構字串
        k_str_key = "SS (鋼骨)" # 預設
        if "RC" in structure_type: k_str_key = "RC"
        if "SRC" in structure_type: k_str_key = "SRC"
        if "S (" in structure_type: k_str_key = "SS (鋼骨)"

        # 係數庫
        if is_high: # 18F+
            const = 8.4
            c_use = {"辦公室 (事務所)": -2.5, "住宅": 10.0, "飯店/醫院": 8.0, "學校": 0.5, "工廠/倉庫": 1.0}.get(k_use_key, 0)
            c_loc = {"市區": 2.0, "郊外": -3.0}.get(location_type, 0)
            c_str = {"SRC": -3.5, "SS (鋼骨)": 2.0, "RC": 0.0}.get(k_str_key, 0)
            
            val = (const + c_use + c_loc + c_str + 
                   (building_area * 0.002) + (total_area * -0.00007) + 
                   (floors_under * 1.7) + (floors_above * 0.5) + (ph_floors * 1.3))
        else: # 17F-
            const = 9.5
            c_use = {"辦公室 (事務所)": 0.0, "住宅": 0.0, "飯店/醫院": 0.5, "學校": 0.5, "工廠/倉庫": 1.0}.get(k_use_key, 0)
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
    k1.metric("竹中 (順打)", f"{res_tak_bu:.1f} 個月", f"結構: {structure_type}")
    k2.metric("竹中 (逆打)", f"{res_tak_td:.1f} 個月", f"節省 {tak_red:.1f} 月", delta_color="inverse")
    k3.metric("鹿島 (公式)", f"{res_kaj:.1f} 個月", f"{'高層' if is_high_kaj else '低層'}公式")

    # 圖表
    st.markdown("### 📈 工期模型比較")
    tab1, tab2 = st.tabs(["甘特圖模擬", "詳細參數表"])
    
    with tab1:
        chart_data = pd.DataFrame({
            "模型": ["竹中(順打)", "竹中(逆打)", "鹿島(公式)"],
            "工期 (月)": [res_tak_bu, res_tak_td, res_kaj]
        })
        st.bar_chart(chart_data.set_index("模型"))
        
        # 智慧建議
        if abs(res_kaj - res_tak_bu) < 5:
            st.success("✅ **一致性高**：兩大營造廠模型估算結果接近。")
        else:
            diff = res_kaj - res_tak_bu
            reason = "鹿島對高層S造效率假設極高" if diff < 0 else "鹿島對特定用途/結構有加權懲罰"
            st.info(f"ℹ️ **差異顯著**：兩者相差 {abs(diff):.1f} 個月 ({reason})。")

    with tab2:
        st.table(pd.DataFrame({
            "參數項目": ["地上/地下/PH", "總樓地板/建築面積", "結構設定", "用途設定", "稼動率係數"],
            "設定值": [
                f"{floors_above} / {floors_under} / {ph_floors}",
                f"{total_area:,.0f} / {building_area:,.0f}",
                structure_type,
                usage_type,
                f"{work_coef:.4f}"
            ]
        }))
        st.caption("註：竹中模型已根據選擇的結構別 (RC/S) 自動調整標準層施工速率。")

except Exception as e:
    st.error(f"運算發生錯誤: {e}")