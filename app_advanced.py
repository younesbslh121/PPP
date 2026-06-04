import streamlit as st
import tensorflow as tf
import keras
import numpy as np
from PIL import Image
import json
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import cv2
import pandas as pd
from fpdf import FPDF
import io
import os

# =========================
# KERAS VERSION COMPATIBILITY PATCH
# =========================
original_dense_from_config = keras.layers.Dense.from_config
keras.layers.Dense.from_config = lambda config: original_dense_from_config(
    {k: v for k, v in config.items() if k != 'quantization_config'}
)

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Allergy AI Pro - Moroccan Food Intelligence",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# LOAD CONFIG, MODEL & DATA
# =========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(filename):
    return os.path.join(SCRIPT_DIR, filename)

@st.cache_resource
def load_all_resources():
    # Load keras model
    try:
        model = tf.keras.models.load_model(get_path("moroccan_food_model.keras"))
    except Exception as e:
        # Fallback to .h5 if keras fails
        try:
            model = tf.keras.models.load_model(get_path("moroccan_food_model.h5"))
        except Exception as e2:
            st.error(f"Error loading model: {e2}")
            model = None

    # Load JSON resources
    with open(get_path("class_names.json"), "r", encoding="utf-8") as f:
        class_names = {int(k): v for k, v in json.load(f).items()}
    
    with open(get_path("allergens_db.json"), "r", encoding="utf-8") as f:
        allergens_db = json.load(f)
        
    with open(get_path("translations.json"), "r", encoding="utf-8") as f:
        translations = json.load(f)
        
    return model, class_names, allergens_db, translations

model, class_names, allergens_db, translations = load_all_resources()

# =========================
# STATE INITIALIZATION
# =========================
if 'scan_history' not in st.session_state:
    st.session_state.scan_history = []

if 'user_stats' not in st.session_state:
    st.session_state.user_stats = {
        'total_scans': 0,
        'safe_dishes': 0,
        'dangerous_dishes': 0,
        'most_scanned': {}
    }

# =========================
# MULTILINGUAL TRANSLATION HELPER
# =========================
# We support 'fr', 'en', 'ar'
if 'lang' not in st.session_state:
    st.session_state.lang = 'fr'

def t(key):
    lang = st.session_state.lang
    lang_dict = translations.get(lang, translations.get('fr', {}))
    return lang_dict.get(key, translations.get('fr', {}).get(key, key))

# RTL layout direction helper for Arabic
is_rtl = st.session_state.lang == 'ar'
align_style = "right" if is_rtl else "left"
dir_style = "rtl" if is_rtl else "ltr"

# =========================
# PREMIUM CSS DESIGN SYSTEM
# =========================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * {{
        font-family: 'Outfit', -apple-system, sans-serif;
    }}
    
    /* Premium Dark Theme */
    .stApp {{
        background: #090d16;
        color: #f0f4ff;
    }}
    
    /* Top Header Card */
    .premium-header {{
        background: linear-gradient(135deg, rgba(0, 98, 51, 0.9) 0%, rgba(193, 39, 45, 0.9) 50%, rgba(255, 215, 0, 0.9) 100%);
        padding: 2.5rem;
        border-radius: 24px;
        text-align: center;
        box-shadow: 0 20px 40px rgba(0,0,0,0.4);
        margin-bottom: 2.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }}
    
    .premium-header::after {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(rgba(255,255,255,0.05), transparent);
        pointer-events: none;
    }}
    
    .premium-header h1 {{
        color: white !important;
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        text-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        letter-spacing: -0.03em !important;
    }}
    
    .premium-header p {{
        font-size: 1.25rem !important;
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 500 !important;
        margin-top: 0.5rem !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
    }}
    
    /* Glass Cards */
    .glass-card {{
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 1.5rem;
    }}
    
    .glass-card:hover {{
        transform: translateY(-4px);
        border-color: rgba(0, 242, 254, 0.3);
        box-shadow: 0 20px 40px rgba(0, 242, 254, 0.1);
    }}
    
    /* Feature Badge */
    .feature-badge {{
        display: inline-block;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        color: #090d16 !important;
        padding: 0.4rem 1.2rem;
        margin: 0.3rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 700;
        box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    /* Danger & Safe Verdict Banners */
    .danger-premium {{
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        color: white;
        padding: 2rem;
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(255, 75, 43, 0.3);
        border: 1px solid rgba(255,255,255,0.15);
    }}
    
    .safe-premium {{
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 2rem;
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(56, 239, 125, 0.3);
        border: 1px solid rgba(255,255,255,0.15);
    }}
    
    /* Metric Pill */
    .metric-premium {{
        background: linear-gradient(145deg, #1f2937, #111827);
        border: 1px solid rgba(255,255,255,0.06);
        color: white;
        padding: 1.5rem;
        border-radius: 18px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease;
    }}
    .metric-premium:hover {{
        transform: scale(1.03);
    }}
    .metric-premium h3 {{
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    
    /* Nutrition Card Pill */
    .nutrition-card {{
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 1rem;
        border-radius: 14px;
        text-align: center;
        box-shadow: 0 6px 18px rgba(245, 158, 11, 0.25);
    }}
    
    /* History List Items */
    .history-item {{
        background: rgba(31, 41, 55, 0.6);
        padding: 1.25rem;
        border-radius: 14px;
        margin: 0.75rem 0;
        border-left: 5px solid #4facfe;
        border-top: 1px solid rgba(255,255,255,0.05);
        border-right: 1px solid rgba(255,255,255,0.05);
        border-bottom: 1px solid rgba(255,255,255,0.05);
        transition: all 0.25s ease;
    }}
    .history-item:hover {{
        transform: translateX(6px);
        background: rgba(31, 41, 55, 0.85);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }}
    
    /* Allergen Badge Pills */
    .allergen-badge {{
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 8px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 0.25rem;
        color: white;
    }}
    .allergen-danger {{
        background: rgba(239, 68, 68, 0.2);
        border: 1px solid rgb(239, 68, 68);
        color: #f87171;
    }}
    .allergen-safe {{
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgb(16, 185, 129);
        color: #34d399;
    }}
    .allergen-neutral {{
        background: rgba(107, 114, 128, 0.2);
        border: 1px solid rgb(107, 114, 128);
        color: #d1d5db;
    }}
    
    /* Custom Alert Panel */
    .emergency-card {{
        background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
        border: 1px solid #b91c1c;
        border-radius: 16px;
        padding: 1.5rem;
        color: #fca5a5;
        box-shadow: 0 10px 25px rgba(220, 38, 38, 0.2);
    }}
    
    /* Custom Sidebar styling */
    section[data-testid="stSidebar"] {{
        background-color: #0c1220 !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }}
    
    /* RTL adjustments */
    .rtl-text {{
        direction: rtl;
        text-align: right;
    }}
</style>
""", unsafe_allow_html=True)

# =========================
# NUTRITION DATABASE GENERATOR
# =========================
def get_nutrition_data(food_name):
    food = food_name.lower()
    # Programmatic mapping to cover all 70 dishes accurately
    if any(x in food for x in ["tagine", "tajine"]):
        return {"calories": 320, "proteins": 25, "carbs": 15, "fats": 18, "fiber": 4}
    elif "couscous" in food:
        return {"calories": 380, "proteins": 12, "carbs": 78, "fats": 1.2, "fiber": 5}
    elif any(x in food for x in ["salad", "salade", "taktouka", "zaalouk", "zitoun"]):
        return {"calories": 110, "proteins": 1.8, "carbs": 8, "fats": 8.5, "fiber": 3}
    elif any(x in food for x in ["bahla", "basbousa", "briouate", "chebakia", "gazelle horn", "fekkas", "mhancha", "macaroon", "snowballs", "cake", "nougat"]):
        return {"calories": 440, "proteins": 5.8, "carbs": 62, "fats": 19.5, "fiber": 2.2}
    elif any(x in food for x in ["batbout", "beghrir", "croissant", "harcha", "msamen", "rghayf", "sfenje", "bread"]):
        return {"calories": 275, "proteins": 7.5, "carbs": 54, "fats": 3.8, "fiber": 2.8}
    elif any(x in food for x in ["apple", "banana", "pear", "orange", "dates"]):
        return {"calories": 95, "proteins": 1.1, "carbs": 23, "fats": 0.2, "fiber": 2.9}
    elif any(x in food for x in ["fish", "calamari", "salmon", "paella"]):
        return {"calories": 240, "proteins": 21, "carbs": 14, "fats": 11.5, "fiber": 1.8}
    elif any(x in food for x in ["beef", "chicken", "meat", "liver", "nuggets", "hamburger", "rfissa", "tkalya"]):
        return {"calories": 340, "proteins": 27, "carbs": 9, "fats": 21.2, "fiber": 0.8}
    elif any(x in food for x in ["bissara", "feves", "harira", "lentils", "beans"]):
        return {"calories": 185, "proteins": 9.2, "carbs": 27, "fats": 3.2, "fiber": 5.8}
    else:
        return {"calories": 280, "proteins": 9, "carbs": 38, "fats": 9.5, "fiber": 2.5}

# =========================
# HELPER FUNCTIONS
# =========================
def add_to_history(food_name, confidence, is_safe, allergens):
    st.session_state.scan_history.insert(0, {
        'timestamp': datetime.now(),
        'food': food_name,
        'confidence': confidence,
        'safe': is_safe,
        'allergens': allergens
    })
    
    # Keep only last 10
    if len(st.session_state.scan_history) > 10:
        st.session_state.scan_history = st.session_state.scan_history[:10]
    
    # Update Stats
    st.session_state.user_stats['total_scans'] += 1
    if is_safe:
        st.session_state.user_stats['safe_dishes'] += 1
    else:
        st.session_state.user_stats['dangerous_dishes'] += 1
    
    # Increment most scanned
    scanned_dict = st.session_state.user_stats['most_scanned']
    scanned_dict[food_name] = scanned_dict.get(food_name, 0) + 1

def get_confidence_status(confidence):
    if confidence >= 90:
        return "🟢 " + t("confidence") + " : " + f"{confidence:.1f}% (" + t("green_light") + ")", "#10b981"
    elif confidence >= 70:
        return "🟡 " + t("confidence") + " : " + f"{confidence:.1f}% (" + t("advice") + ")", "#fbbf24"
    else:
        return "🔴 " + t("confidence") + " : " + f"{confidence:.1f}% (" + t("important_warning") + ")", "#f43f5e"

# =========================
# GRAD-CAM GRADIENT EXPLAINABILITY HELPER
# =========================
def get_grad_cam_heatmap(model, img_array):
    try:
        # MobilNetV2 structure inspection
        base_model = model.layers[0]
        
        # Look for the last Conv2D or BatchNormalization in the base model
        last_conv = None
        for layer in reversed(base_model.layers):
            if isinstance(layer, tf.keras.layers.Conv2D) or 'conv' in layer.name.lower() or 'project' in layer.name.lower():
                last_conv = layer
                break
        
        if not last_conv:
            return None
            
        grad_model = tf.keras.models.Model(
            inputs=[base_model.inputs],
            outputs=[last_conv.output, base_model.output]
        )
        
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img_array)
            # Find matching class index
            main_predictions = model(img_array)
            pred_index = tf.argmax(main_predictions[0])
            class_channel = predictions[:, pred_index]
            
        grads = tape.gradient(class_channel, conv_outputs)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        
        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
        return heatmap.numpy()
    except Exception as e:
        return None

def overlay_heatmap(original_img, heatmap):
    try:
        # Resize heatmap
        heatmap_resized = cv2.resize(heatmap, (original_img.width, original_img.height))
        heatmap_resized = np.uint8(255 * heatmap_resized)
        
        # Colorize
        heatmap_color = cv2.applyColorMap(heatmap_resized, cv2.COLORMAP_JET)
        heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
        
        # Superimpose
        original_arr = np.array(original_img)
        superimposed = cv2.addWeighted(original_arr, 0.6, heatmap_color, 0.4, 0)
        return Image.fromarray(superimposed)
    except:
        return None

# =========================
# PDF REPORT EXPORTER
# =========================
def generate_pdf_report(food_name, confidence, is_safe, user_allergies, detected_allergens, nutrition, alternatives):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Colors & Fonts
        pdf.set_font("helvetica", "B", 22)
        pdf.set_text_color(0, 98, 51) # Green
        pdf.cell(0, 15, "ALLERGY AI PRO REPORT", ln=True, align="C")
        
        pdf.set_font("helvetica", "I", 11)
        pdf.set_text_color(107, 114, 128)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        pdf.ln(5)
        
        # Divider Line
        pdf.set_draw_color(229, 231, 235)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        # Dish Info
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(17, 24, 39)
        pdf.cell(0, 10, f"Detected Dish: {food_name.upper()}", ln=True)
        
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 8, f"Prediction Confidence: {confidence:.2f}%", ln=True)
        pdf.ln(5)
        
        # Safety Status Block
        pdf.set_font("helvetica", "B", 14)
        if is_safe:
            pdf.set_fill_color(209, 250, 229)
            pdf.set_text_color(6, 95, 70)
            pdf.cell(0, 12, "STATUS: COMPATIBLE / SAFE DISH", fill=True, ln=True, align="C")
        else:
            pdf.set_fill_color(254, 226, 226)
            pdf.set_text_color(153, 27, 27)
            pdf.cell(0, 12, "STATUS: DANGER / INCOMPATIBLE DISH", fill=True, ln=True, align="C")
            
        pdf.ln(5)
        pdf.set_text_color(17, 24, 39)
        
        # Allergens Section
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "Allergy Profile Context:", ln=True)
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 6, f"Declared User Allergies: {', '.join(user_allergies) if user_allergies else 'None'}", ln=True)
        pdf.cell(0, 6, f"Detected Allergens in Dish: {', '.join(detected_allergens) if detected_allergens else 'None'}", ln=True)
        pdf.ln(5)
        
        # Nutrition Table
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "Nutritional Profile (per 100g estimate):", ln=True)
        
        pdf.set_font("helvetica", "", 11)
        pdf.cell(45, 7, f"Calories: {nutrition['calories']} kcal", border=1)
        pdf.cell(45, 7, f"Proteins: {nutrition['proteins']} g", border=1)
        pdf.cell(45, 7, f"Carbohydrates: {nutrition['carbs']} g", border=1)
        pdf.cell(45, 7, f"Fats: {nutrition['fats']} g", border=1)
        pdf.ln(7)
        pdf.cell(45, 7, f"Dietary Fiber: {nutrition['fiber']} g", border=1)
        pdf.ln(12)
        
        # Alternatives
        if alternatives:
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, "Recommended Alternatives:", ln=True)
            pdf.set_font("helvetica", "", 11)
            for alt in alternatives:
                pdf.cell(0, 6, f"- {alt}", ln=True)
                
        pdf.ln(15)
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(156, 163, 175)
        pdf.multi_cell(0, 5, "Disclaimer: Allergy AI Pro is an assistive tool using deep learning. Always consult restaurant staff or medical personnel before consuming foods to verify exact ingredient sourcing.")
        
        # Return PDF bytes
        return pdf.output()
    except Exception as e:
        return None

# =========================
# SIDEBAR PANEL
# =========================
with st.sidebar:
    st.markdown(f"<div class='rtl-text' style='direction: {dir_style};'><h2 style='color: white; font-weight: 700; margin-bottom:0.25rem;'>🌐 Language / Langue</h2></div>", unsafe_allow_html=True)
    lang_choice = st.selectbox(
        "Select Language",
        options=["fr", "en", "ar"],
        format_func=lambda x: "Français 🇫🇷" if x == 'fr' else ("English 🇬🇧" if x == 'en' else "العربية 🇲🇦"),
        index=0 if st.session_state.lang == 'fr' else (1 if st.session_state.lang == 'en' else 2),
        label_visibility="collapsed"
    )
    if lang_choice != st.session_state.lang:
        st.session_state.lang = lang_choice
        st.rerun()
        
    st.markdown("---")
    st.markdown(f"<div class='rtl-text' style='direction: {dir_style}; text-align: {align_style};'><h2 style='color: white; font-weight: 700;'>👤 {t('sidebar_title')}</h2></div>", unsafe_allow_html=True)
    st.write(t("select_allergies"))
    
    # Active Allergen List
    ALLERGEN_LIST = [
        ("Gluten 🌾", "gluten"),
        ("Lait 🥛", "lait"),
        ("Œufs 🥚", "œufs"),
        ("Poisson 🐟", "poisson"),
        ("Fruits de mer 🦐", "fruits de mer"),
        ("Fruits à coque 🥜", "fruits à coque"),
        ("Sésame 🌰", "sésame"),
        ("Viande 🥩", "viande"),
        ("Légumineuses 🫘", "légumineuses"),
        ("Légumes 🥬", "légumes"),
        ("Miel 🍯", "miel")
    ]
    
    user_allergies = []
    for allergen_label, key in ALLERGEN_LIST:
        if st.checkbox(allergen_label, key=f"user_allergen_{key}"):
            user_allergies.append(key)
            
    st.markdown("---")
    
    # Stats Summary
    st.markdown(f"<div class='rtl-text' style='direction: {dir_style}; text-align: {align_style};'><h3 style='color: white; font-weight: 700;'>📊 {t('statistics')}</h3></div>", unsafe_allow_html=True)
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.markdown(f"""
        <div class="metric-premium">
            <p style="margin: 0; font-size: 0.8rem; color: #9ca3af;">{t('dishes_recognized')}</p>
            <h3>{st.session_state.user_stats['total_scans']}</h3>
        </div>
        """, unsafe_allow_html=True)
    with col_stat2:
        st.markdown(f"""
        <div class="metric-premium">
            <p style="margin: 0; font-size: 0.8rem; color: #9ca3af;">{t('accuracy')} (model)</p>
            <h3 style="color:#34d399 !important;">87%</h3>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Reset Stats", use_container_width=True):
        st.session_state.user_stats = {
            'total_scans': 0,
            'safe_dishes': 0,
            'dangerous_dishes': 0,
            'most_scanned': {}
        }
        st.session_state.scan_history = []
        st.rerun()

# =========================
# HEADER BANNER
# =========================
st.markdown(f"""
<div class="premium-header">
    <h1>🍲 {t('app_title')}</h1>
    <p>✨ {t('app_subtitle')} ✨</p>
    <div style="margin-top: 1rem;">
        <span class="feature-badge">🧠 Deep Learning IA</span>
        <span class="feature-badge">📊 Heatmaps Grad-CAM</span>
        <span class="feature-badge">📈 Nutrition 100%</span>
        <span class="feature-badge">📄 Export PDF</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================
# MAIN SECTION TABS
# =========================
tab_scan, tab_explain, tab_stats, tab_history, tab_emergency, tab_about = st.tabs([
    "📸 " + t("tab_scanner"),
    "💡 Explainability",
    "📊 " + t("statistics"),
    "📖 " + t("dishes_recognized"),
    "🚨 Emergency Info",
    "ℹ️ " + t("tab_about")
])

# =========================
# TAB 1: SCANNER PRO
# =========================
with tab_scan:
    col_input, col_results = st.columns([1, 1], gap="large")
    
    with col_input:
        st.markdown(f"<div class='rtl-text' style='direction: {dir_style}; text-align: {align_style};'><h3 style='color: white; font-weight:700;'>📸 {t('tab_scanner')}</h3></div>", unsafe_allow_html=True)
        
        # Toggle camera vs upload file
        input_mode = st.radio("Source Image", [t("upload_image"), "Camera Input 📷"], horizontal=True)
        
        uploaded_file = None
        if input_mode == t("upload_image"):
            uploaded_file = st.file_uploader(
                t("choose_photo"),
                type=["jpg", "jpeg", "png"],
                label_visibility="collapsed"
            )
        else:
            uploaded_file = st.camera_input("Capture Food Photo")
            
        # Draw image preview
        if uploaded_file:
            original_img = Image.open(uploaded_file).convert("RGB")
            st.image(original_img, use_container_width=True, caption="Food Scan Preview")
            
    with col_results:
        st.markdown(f"<div class='rtl-text' style='direction: {dir_style}; text-align: {align_style};'><h3 style='color: white; font-weight:700;'>🔍 {t('results')}</h3></div>", unsafe_allow_html=True)
        
        if uploaded_file and model:
            # 1. Preprocess
            img_resized = original_img.resize((224, 224))
            img_array = np.array(img_resized) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            
            # 2. Prediction
            with st.spinner(t("analysis_in_progress")):
                predictions = model.predict(img_array, verbose=0)[0]
                
            top_indices = np.argsort(predictions)[::-1][:3]
            top1_index = top_indices[0]
            top1_conf = float(predictions[top1_index] * 100)
            top1_name = class_names[top1_index]
            
            # Display confidence level
            conf_desc, conf_color = get_confidence_status(top1_conf)
            
            st.markdown(f"""
            <div class="glass-card" style="border-left: 6px solid {conf_color};">
                <h2 style="color: white; margin: 0; font-size: 2rem;">{top1_name.upper()}</h2>
                <p style="color: {conf_color}; font-weight: 700; margin-top: 0.5rem; font-size: 1.1rem;">{conf_desc}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Allow manual override if top-1 is wrong
            st.markdown(f"<div class='rtl-text' style='direction: {dir_style}; text-align: {align_style};'><h5 style='color: #9ca3af;'>{t('top_3_predictions')}</h5></div>", unsafe_allow_html=True)
            
            selected_food = top1_name
            override_options = [class_names[idx] for idx in top_indices]
            
            selected_override = st.selectbox(
                "Confirm Dish Name (Select correct if prediction is off)",
                options=override_options,
                format_func=lambda name: f"{name} ({predictions[[k for k, v in class_names.items() if v == name][0]] * 100:.1f}%)"
            )
            selected_food = selected_override
            
            # Save the index of the selected food for Grad-CAM
            selected_index = [k for k, v in class_names.items() if v == selected_food][0]
            
            # 3. Allergen Analysis
            food_info = allergens_db.get(selected_food, {})
            food_allergens = food_info.get("allergens", [])
            alternatives = food_info.get("alternatives", [])
            
            # Evaluate against user allergies
            dangerous_allergens = [a for a in food_allergens if a in user_allergies]
            is_compatible = len(dangerous_allergens) == 0
            
            st.markdown(f"<br><div class='rtl-text' style='direction: {dir_style}; text-align: {align_style};'><h4 style='color: white; font-weight: 700;'>🚦 {t('allergy_evaluation')}</h4></div>", unsafe_allow_html=True)
            
            if user_allergies:
                if not is_compatible:
                    st.markdown(f"""
                    <div class="danger-premium">
                        <h3 style="margin: 0; color: white; font-weight:700;">{t('warning_incompatible')}</h3>
                        <p style="margin-top: 0.5rem;">{t('dangerous_allergens')}</p>
                        <p style="font-size: 1.25rem; font-weight: 800; text-transform: uppercase;">
                            {", ".join([a.capitalize() for a in dangerous_allergens])}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="safe-premium">
                        <h3 style="margin: 0; color: white; font-weight:700;">{t('compatible_safe')}</h3>
                        <p style="margin-top: 0.5rem;">{t('no_allergens_declared')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Auto add to session history
                add_to_history(selected_food, top1_conf, is_compatible, dangerous_allergens)
            else:
                st.info(t("configure_profile"))
                
            # 4. Interactive Ingredients & Alternatives
            st.markdown("<br>", unsafe_allow_html=True)
            st.write(t("allergens_in_dish"))
            
            if food_allergens:
                for alg in food_allergens:
                    badge_class = "allergen-danger" if alg in user_allergies else "allergen-neutral"
                    st.markdown(f"<span class='allergen-badge {badge_class}'>{alg.upper()}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='allergen-badge allergen-safe'>{t('no_major_allergens').upper()}</span>", unsafe_allow_html=True)
                
            # Alternative suggestions
            if not is_compatible and alternatives:
                st.markdown(f"<br><div class='rtl-text' style='direction: {dir_style}; text-align: {align_style};'><h5 style='color: white; font-weight:700;'>🍲 {t('suggested_alternatives')}</h5></div>", unsafe_allow_html=True)
                st.write(t("similar_dishes"))
                for alt in alternatives:
                    st.markdown(f"<span class='allergen-badge allergen-safe'>{alt.upper()}</span>", unsafe_allow_html=True)
                    
            # 5. Full Nutrition display
            st.markdown("<br><h4 style='color: white; font-weight: 700;'>📈 Nutritional Breakdown</h4>", unsafe_allow_html=True)
            nut = get_nutrition_data(selected_food)
            
            nut_col1, nut_col2, nut_col3, nut_col4 = st.columns(4)
            with nut_col1:
                st.markdown(f"<div class='nutrition-card'><h4>{nut['calories']}</h4><p style='margin:0;font-size:0.8rem;'>Calories (kcal)</p></div>", unsafe_allow_html=True)
            with nut_col2:
                st.markdown(f"<div class='nutrition-card' style='background: linear-gradient(135deg, #10b981 0%, #059669 100%);'><h4>{nut['proteins']}g</h4><p style='margin:0;font-size:0.8rem;'>Proteins</p></div>", unsafe_allow_html=True)
            with nut_col3:
                st.markdown(f"<div class='nutrition-card' style='background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);'><h4>{nut['carbs']}g</h4><p style='margin:0;font-size:0.8rem;'>Carbs</p></div>", unsafe_allow_html=True)
            with nut_col4:
                st.markdown(f"<div class='nutrition-card' style='background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);'><h4>{nut['fats']}g</h4><p style='margin:0;font-size:0.8rem;'>Fats</p></div>", unsafe_allow_html=True)
                
            # Export report download button
            st.markdown("<br>", unsafe_allow_html=True)
            pdf_bytes = generate_pdf_report(
                selected_food, 
                top1_conf, 
                is_compatible, 
                user_allergies, 
                dangerous_allergens, 
                nut, 
                alternatives
            )
            
            if pdf_bytes:
                st.download_button(
                    label="📄 " + t("export_pdf"),
                    data=pdf_bytes,
                    file_name=f"Allergy_AI_Report_{selected_food.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; padding: 4rem;">
                <p style="font-size: 1.5rem; color: #9ca3af; margin:0;">{t('upload_to_start')}</p>
            </div>
            """, unsafe_allow_html=True)

# =========================
# TAB 2: EXPLAINABILITY (Grad-CAM)
# =========================
with tab_explain:
    st.markdown("<h3 style='color: white; font-weight:700;'>💡 Explainability AI (Grad-CAM Activation Mapping)</h3>", unsafe_allow_html=True)
    st.write("Understand which features the neural network analyzed to determine the dish prediction. Regions highlighted in Red represent the key visual features (texture, colors, ingredients) driving the AI prediction.")
    
    if uploaded_file and model:
        # Load and compute heatmap
        heatmap = get_grad_cam_heatmap(model, img_array)
        if heatmap is not None:
            col_orig, col_grad = st.columns(2)
            with col_orig:
                st.image(original_img, use_container_width=True, caption="Original Image")
            with col_grad:
                overlayed = overlay_heatmap(original_img, heatmap)
                if overlayed:
                    st.image(overlayed, use_container_width=True, caption="Grad-CAM Hotspots Overlay")
                else:
                    st.error("Failed to generate heatmap overlay")
        else:
            st.info("Explainability mapping could not determine convolution features for this target image.")
    else:
        st.info("Upload an image in the 'Scanner' tab to visualize the model's inner decision-making features.")

# =========================
# TAB 3: ANALYTICS DASHBOARD
# =========================
with tab_stats:
    st.markdown("<h3 style='color: white; font-weight:700;'>📊 Analytics Dashboard</h3>", unsafe_allow_html=True)
    
    if st.session_state.user_stats['total_scans'] > 0:
        col_an1, col_an2, col_an3 = st.columns(3)
        with col_an1:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center;">
                <h4>Total Scans</h4>
                <h1 style="color: #4facfe; margin:0;">{st.session_state.user_stats['total_scans']}</h1>
            </div>
            """, unsafe_allow_html=True)
        with col_an2:
            safe_perc = (st.session_state.user_stats['safe_dishes'] / st.session_state.user_stats['total_scans']) * 100
            st.markdown(f"""
            <div class="glass-card" style="text-align: center;">
                <h4>Safe Verdicts</h4>
                <h1 style="color: #10b981; margin:0;">{safe_perc:.0f}%</h1>
            </div>
            """, unsafe_allow_html=True)
        with col_an3:
            danger_perc = (st.session_state.user_stats['dangerous_dishes'] / st.session_state.user_stats['total_scans']) * 100
            st.markdown(f"""
            <div class="glass-card" style="text-align: center;">
                <h4>Dangerous Verdicts</h4>
                <h1 style="color: #f43f5e; margin:0;">{danger_perc:.0f}%</h1>
            </div>
            """, unsafe_allow_html=True)
            
        # Draw analytics charts
        st.markdown("<br>", unsafe_allow_html=True)
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Top scanned foods chart
            scanned_data = st.session_state.user_stats['most_scanned']
            if scanned_data:
                df_scan = pd.DataFrame(list(scanned_data.items()), columns=["Dish", "Scans"]).sort_values(by="Scans", ascending=False).head(5)
                fig_bar = px.bar(
                    df_scan, 
                    x="Scans", 
                    y="Dish", 
                    orientation='h',
                    title="Top 5 Scanned Foods",
                    color="Scans",
                    color_continuous_scale=px.colors.sequential.Viridis
                )
                fig_bar.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="white"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
        with chart_col2:
            # Donut chart safety
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Safe', 'Dangerous'], 
                values=[st.session_state.user_stats['safe_dishes'], st.session_state.user_stats['dangerous_dishes']],
                hole=.4,
                marker_colors=['#10b981', '#f43f5e']
            )])
            fig_pie.update_layout(
                title="Dish Safety Overview",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No stats available yet. Go ahead and scan some Moroccan food items!")

# =========================
# TAB 4: HISTORIQUE
# =========================
with tab_history:
    st.markdown("<h3 style='color: white; font-weight:700;'>📖 Scan History Log</h3>", unsafe_allow_html=True)
    
    if st.session_state.scan_history:
        for idx, item in enumerate(st.session_state.scan_history):
            status_icon = "🟢" if item['safe'] else "🔴"
            status_label = "SAFE" if item['safe'] else "DANGEROUS"
            st.markdown(f"""
            <div class="history-item">
                <div style="display:flex; justify-content: space-between; align-items:center;">
                    <div>
                        <h4 style="margin:0; color:white;">{status_icon} {item['food'].upper()}</h4>
                        <p style="margin:0.2rem 0; font-size:0.85rem; color:#9ca3af;">
                            {item['timestamp'].strftime('%d/%m/%Y %H:%M')} &bull; Confidence: {item['confidence']:.1f}% &bull; Verdict: <strong>{status_label}</strong>
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Your scan history is currently empty.")

# =========================
# TAB 5: EMERGENCY INFORMATION
# =========================
with tab_emergency:
    st.markdown("<h3 style='color: white; font-weight:700;'>🚨 Emergency / Urgence - Allergy Reaction</h3>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="emergency-card">
        <h4 style="margin-top:0; color:#fca5a5; font-size:1.3rem;">If you suspect a severe allergic reaction (Anaphylaxis):</h4>
        <ol style="margin-bottom:0; line-height: 1.6;">
            <li><strong>Use your Adrenaline Auto-Injector (EpiPen) immediately</strong> if prescribed.</li>
            <li><strong>Call emergency services</strong> right away. Do not wait for symptoms to get better.</li>
            <li>Lie flat on your back. If breathing is difficult, sit up. Do not stand or walk.</li>
            <li>Stay with the person until medical assistance arrives.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: white; font-weight: 700;'>📞 Emergency Contacts in Morocco</h4>", unsafe_allow_html=True)
    
    em_col1, em_col2, em_col3 = st.columns(3)
    with em_col1:
        st.markdown("""
        <div class="glass-card" style="text-align: center; border-color:#b91c1c;">
            <h1 style="color:#ef4444; margin:0;">15</h1>
            <p style="font-weight: 700; margin-top:0.5rem;">Ambulance / Protection Civile</p>
        </div>
        """, unsafe_allow_html=True)
    with em_col2:
        st.markdown("""
        <div class="glass-card" style="text-align: center; border-color:#b91c1c;">
            <h1 style="color:#ef4444; margin:0;">19</h1>
            <p style="font-weight: 700; margin-top:0.5rem;">Police Secours</p>
        </div>
        """, unsafe_allow_html=True)
    with em_col3:
        st.markdown("""
        <div class="glass-card" style="text-align: center; border-color:#b91c1c;">
            <h1 style="color:#ef4444; margin:0;">177</h1>
            <p style="font-weight: 700; margin-top:0.5rem;">Gendarmerie Royale</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("⚕️ Morocco Poison Control & Pharmacovigilance Center (CAPM) Hotline: **0801 000 180**")

# =========================
# TAB 6: ABOUT PAGE
# =========================
with tab_about:
    st.markdown(f"<h3 style='color: white; font-weight:700;'>ℹ️ {t('about_project')}</h3>", unsafe_allow_html=True)
    
    ab_col1, ab_col2 = st.columns(2)
    with ab_col1:
        st.markdown(f"""
        <div class="glass-card">
            <h4 style="color:#4facfe; font-weight:700;">🚀 Innovations & Features</h4>
            <ul style="line-height:2.0; margin-bottom:0; color:#d1d5db;">
                <li><strong>Scanner Pro:</strong> Top-3 Predictions with override mechanism</li>
                <li><strong>Explainability AI:</strong> Live Grad-CAM heatmap feature highlighting</li>
                <li><strong>Multilingual Framework:</strong> French, English, and Arabic support</li>
                <li><strong>PDF Exporting:</strong> Instant downloadable reports</li>
                <li><strong>Morocco 2030 World Cup Ready:</strong> Fast scanning tool for international tourists</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with ab_col2:
        st.markdown(f"""
        <div class="glass-card">
            <h4 style="color:#34d399; font-weight:700;">🏆 PPP Development Team</h4>
            <p style="color:#d1d5db; line-height: 1.8;">
                <strong>Membres de l'équipe :</strong><br>
                &bull; Younes BOUSSALAH<br>
                &bull; Mouad KACIMI<br>
                &bull; Brahim BENIKEN<br>
                &bull; Mouad CHAOUNI<br><br>
                <strong>Encadrant :</strong><br>
                &bull; Pr. Kamal IDRISSI
            </p>
        </div>
        """, unsafe_allow_html=True)

# =========================
# FOOTER
# =========================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; color: #9ca3af; padding: 2rem 0; border-top: 1px solid rgba(255,255,255,0.06);">
    <h3 style="color: white; margin:0; font-weight:700;">🏆 Allergy AI Pro</h3>
    <p style="font-size: 0.95rem; margin-top:0.5rem;">
        Allergy for Moroccan Food AI &bull; World Cup 2030 Morocco 🇲🇦
    </p>
    <p style="font-size: 0.8rem; color:#6b7280;">
        &copy; 2026 Powered by MobileNetV2 Transfer Learning, Streamlit & FPDF2
    </p>
</div>
""", unsafe_allow_html=True)