import streamlit as st
import tensorflow as tf
import numpy as np
from PIL import Image
import json
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import cv2

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Allergy AI Pro - Moroccan Food",
    page_icon="🍲",
    layout="wide"
)

# =========================
# ADVANCED CSS
# =========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    * { font-family: 'Poppins', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .premium-header {
        background: linear-gradient(135deg, #006233 0%, #C1272D 50%, #FFD700 100%);
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        margin-bottom: 2rem;
        animation: slideDown 0.8s ease-out;
    }
    
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-50px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .premium-header h1 {
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.3);
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 45px rgba(0, 0, 0, 0.2);
    }
    
    .feature-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        margin: 0.3rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .danger-premium {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(238, 90, 111, 0.3);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { box-shadow: 0 10px 30px rgba(238, 90, 111, 0.3); }
        50% { box-shadow: 0 10px 40px rgba(238, 90, 111, 0.5); }
    }
    
    .safe-premium {
        background: linear-gradient(135deg, #51cf66 0%, #37b24d 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(55, 178, 77, 0.3);
    }
    
    .metric-premium {
        background: linear-gradient(135deg, #339af0 0%, #228be6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(51, 154, 240, 0.3);
    }
    
    .nutrition-card {
        background: linear-gradient(135deg, #ffd43b 0%, #fab005 100%);
        color: #333;
        padding: 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        box-shadow: 0 5px 15px rgba(255, 212, 59, 0.3);
    }
    
    .history-item {
        background: rgba(255, 255, 255, 0.9);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #339af0;
        transition: all 0.3s ease;
    }
    
    .history-item:hover {
        transform: translateX(5px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    
    .heatmap-container {
        background: rgba(255, 255, 255, 0.95);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD MODEL & DATA
# =========================
@st.cache_resource
def load_model_and_data():
    model = tf.keras.models.load_model("moroccan_food_model.keras")
    
    with open("class_names.json", "r", encoding="utf-8") as f:
        class_names = {int(k): v for k, v in json.load(f).items()}
    
    try:
        with open("allergens_db.json", "r", encoding="utf-8") as f:
            allergens_db = json.load(f)
    except FileNotFoundError:
        allergens_db = {}
    
    return model, class_names, allergens_db

model, class_names, allergens_db = load_model_and_data()

# =========================
# NUTRITION DATABASE (NEW!)
# =========================
NUTRITION_DB = {
    "couscous": {
        "calories": 376,
        "proteins": 13,
        "carbs": 77,
        "fats": 0.6,
        "fiber": 5
    },
    "harira": {
        "calories": 180,
        "proteins": 8,
        "carbs": 25,
        "fats": 5,
        "fiber": 6
    },
    "chicken basstila": {
        "calories": 450,
        "proteins": 25,
        "carbs": 35,
        "fats": 22,
        "fiber": 3
    },
    "tagine with beef": {
        "calories": 320,
        "proteins": 28,
        "carbs": 18,
        "fats": 15,
        "fiber": 4
    },
    "rfissa": {
        "calories": 400,
        "proteins": 22,
        "carbs": 45,
        "fats": 12,
        "fiber": 5
    }
    # Ajoute les autres plats...
}

# =========================
# SESSION STATE FOR HISTORY
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
# ADVANCED FUNCTIONS
# =========================

def get_grad_cam_heatmap(model, img_array, last_conv_layer_name='top_conv'):
    """Generate Grad-CAM heatmap (explainability)"""
    try:
        grad_model = tf.keras.models.Model(
            [model.inputs],
            [model.get_layer(last_conv_layer_name).output, model.output]
        )
        
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img_array)
            pred_index = tf.argmax(predictions[0])
            class_channel = predictions[:, pred_index]
        
        grads = tape.gradient(class_channel, conv_outputs)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        
        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
        
        return heatmap.numpy()
    except:
        return None

def create_nutrition_chart(food_name):
    """Create nutrition bar chart"""
    nutrition = NUTRITION_DB.get(food_name, None)
    
    if not nutrition:
        return None
    
    fig = go.Figure(data=[
        go.Bar(
            x=['Calories', 'Protéines', 'Glucides', 'Lipides', 'Fibres'],
            y=[nutrition['calories'], nutrition['proteins'], 
               nutrition['carbs'], nutrition['fats'], nutrition['fiber']],
            marker=dict(
                color=['#ff6b6b', '#51cf66', '#ffd43b', '#ff922b', '#339af0'],
                line=dict(color='white', width=2)
            ),
            text=[f"{v}{'g' if k != 'calories' else 'kcal'}" 
                  for k, v in nutrition.items()],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title=f"Valeurs nutritionnelles - {food_name}",
        yaxis_title="Quantité (pour 100g)",
        height=300,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#333', size=12)
    )
    
    return fig

def add_to_history(food_name, confidence, is_safe, allergens):
    """Add scan to history"""
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
    
    # Update stats
    st.session_state.user_stats['total_scans'] += 1
    if is_safe:
        st.session_state.user_stats['safe_dishes'] += 1
    else:
        st.session_state.user_stats['dangerous_dishes'] += 1
    
    # Most scanned
    if food_name in st.session_state.user_stats['most_scanned']:
        st.session_state.user_stats['most_scanned'][food_name] += 1
    else:
        st.session_state.user_stats['most_scanned'][food_name] = 1

def get_confidence_level(confidence):
    """Get confidence level description"""
    if confidence >= 90:
        return "🟢 Très élevée", "#51cf66"
    elif confidence >= 75:
        return "🟡 Élevée", "#ffd43b"
    elif confidence >= 60:
        return "🟠 Moyenne", "#ff922b"
    else:
        return "🔴 Faible", "#ff6b6b"

# =========================
# ALLERGEN CONFIG
# =========================
ALLERGEN_LIST = ["Gluten 🌾", "Lait 🥛", "Œufs 🥚", "Poisson 🐟", 
                 "Fruits de mer 🦐", "Fruits à coque 🥜", "Sésame 🌰", 
                 "Viande 🥩", "Légumineuses 🫘", "Légumes 🥬", "Miel 🍯"]

ALLERGEN_KEYWORDS = {
    "Gluten": "gluten", "Lait": "lait", "Œufs": "œufs",
    "Poisson": "poisson", "Fruits de mer": "fruits de mer", 
    "Fruits à coque": "fruits à coque", "Sésame": "sésame", 
    "Viande": "viande", "Légumineuses": "légumineuses",
    "Légumes": "légumes", "Miel": "miel"
}

# =========================
# HEADER
# =========================
st.markdown("""
<div class="premium-header">
    <h1>🍲 Allergy AI Pro</h1>
    <p>✨ Moroccan Food Intelligence System ✨</p>
    <div style='margin-top: 1rem;'>
        <span class='feature-badge'>🧠 IA Avancée</span>
        <span class='feature-badge'>📊 Analytics</span>
        <span class='feature-badge'>💡 Explainability</span>
        <span class='feature-badge'>📈 Nutrition</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("<h2 style='color: white; text-align: center;'>👤 Profil</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    user_allergies = []
    for allergen in ALLERGEN_LIST:
        keyword = allergen.split()[0].strip()
        mapped_keyword = ALLERGEN_KEYWORDS.get(keyword, keyword.lower())
        
        if st.checkbox(allergen, key=f"allergen_{allergen}"):
            user_allergies.append(mapped_keyword)
    
    st.markdown("---")
    
    # User Stats Dashboard
    st.markdown("<h3 style='color: white;'>📊 Vos Statistiques</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class='metric-premium' style='font-size: 0.75rem;'>
            <h3>{st.session_state.user_stats['total_scans']}</h3>
            <p>Scans</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-premium' style='font-size: 0.75rem;'>
            <h3>{st.session_state.user_stats['safe_dishes']}</h3>
            <p>Sûrs</p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("🗑️ Réinitialiser statistiques", use_container_width=True):
        st.session_state.user_stats = {
            'total_scans': 0,
            'safe_dishes': 0,
            'dangerous_dishes': 0,
            'most_scanned': {}
        }
        st.session_state.scan_history = []
        st.rerun()

# =========================
# MAIN TABS
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📸 Scanner Pro", 
    "📊 Analytics", 
    "📖 Historique",
    "💡 Explainability",
    "ℹ️ À propos"
])

# =========================
# TAB 1: ADVANCED SCANNER
# =========================
with tab1:
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("<h2 style='color: white;'>📸 Scanner Avancé</h2>", unsafe_allow_html=True)
        
        # Camera or upload choice
        scan_mode = st.radio("Mode de scan", ["📁 Upload", "📷 Webcam (si disponible)"], horizontal=True)
        
        uploaded_file = st.file_uploader(
            "Choisir une image",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            img = Image.open(uploaded_file).convert("RGB")
            st.image(img, use_container_width=True, caption="Image uploadée")
    
    with col2:
        if uploaded_file:
            st.markdown("<h2 style='color: white;'>🔍 Résultats Détaillés</h2>", unsafe_allow_html=True)
            
            # PREPROCESS
            img_resized = img.resize((224, 224))
            img_array = np.array(img_resized) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            
            # PREDICTION
            with st.spinner("🔄 Analyse IA en cours..."):
                prediction = model.predict(img_array, verbose=0)
            
            top_index = int(np.argmax(prediction))
            confidence = float(prediction[0][top_index] * 100)
            detected_food = class_names[top_index]
            
            # Confidence level
            conf_level, conf_color = get_confidence_level(confidence)
            
            # DISPLAY
            st.markdown(f"""
            <div class='glass-card'>
                <h2 style='color: white; text-align: center;'>🍽️ {detected_food}</h2>
                <div style='text-align: center; margin: 1rem 0;'>
                    <span style='background: {conf_color}; color: white; padding: 0.5rem 1.5rem; 
                    border-radius: 25px; font-weight: 700; font-size: 1.2rem;'>
                        {confidence:.1f}%
                    </span>
                </div>
                <p style='color: white; text-align: center;'>{conf_level}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.progress(confidence / 100)
            
            # GET ALLERGENS
            food_info = allergens_db.get(detected_food, {})
            food_allergens = food_info.get("allergens", [])
            alternatives = food_info.get("alternatives", [])
            
            # ALLERGY EVALUATION
            st.markdown("<br><h3 style='color: white;'>🚦 Évaluation</h3>", unsafe_allow_html=True)
            
            if user_allergies:
                dangerous = [a for a in food_allergens if a in user_allergies]
                is_safe = len(dangerous) == 0
                
                if dangerous:
                    st.markdown(f"""
                    <div class='danger-premium'>
                        <h2>🔴 DANGER - Non compatible</h2>
                        <p style='margin-top: 1rem;'><strong>Allergènes détectés :</strong></p>
                        <p style='font-size: 1.1rem;'>{', '.join([a.capitalize() for a in dangerous])}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class='safe-premium'>
                        <h2>🟢 COMPATIBLE - Plat sûr</h2>
                        <p style='margin-top: 1rem;'>Ce plat ne contient aucun de vos allergènes.</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Add to history
                add_to_history(detected_food, confidence, is_safe, dangerous if not is_safe else [])
            else:
                is_safe = True
                st.info("ℹ️ Configurez vos allergies dans la sidebar")
            
            # NUTRITION (NEW!)
            if detected_food in NUTRITION_DB:
                st.markdown("<br><h3 style='color: white;'>📈 Informations Nutritionnelles</h3>", unsafe_allow_html=True)
                
                nutrition = NUTRITION_DB[detected_food]
                
                col_n1, col_n2, col_n3 = st.columns(3)
                with col_n1:
                    st.markdown(f"""
                    <div class='nutrition-card'>
                        <h4 style='margin: 0;'>{nutrition['calories']} kcal</h4>
                        <p style='margin: 0; font-size: 0.85rem;'>Calories</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_n2:
                    st.markdown(f"""
                    <div class='nutrition-card'>
                        <h4 style='margin: 0;'>{nutrition['proteins']}g</h4>
                        <p style='margin: 0; font-size: 0.85rem;'>Protéines</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_n3:
                    st.markdown(f"""
                    <div class='nutrition-card'>
                        <h4 style='margin: 0;'>{nutrition['carbs']}g</h4>
                        <p style='margin: 0; font-size: 0.85rem;'>Glucides</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Nutrition chart
                fig_nutrition = create_nutrition_chart(detected_food)
                if fig_nutrition:
                    st.plotly_chart(fig_nutrition, use_container_width=True)

# =========================
# TAB 2: ANALYTICS
# =========================
with tab2:
    st.markdown("<h2 style='color: white;'>📊 Tableau de Bord Analytique</h2>", unsafe_allow_html=True)
    
    if st.session_state.user_stats['total_scans'] > 0:
        # Stats cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class='glass-card' style='text-align: center;'>
                <h3 style='color: white; font-size: 2.5rem;'>{st.session_state.user_stats['total_scans']}</h3>
                <p style='color: white;'>Total Scans</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            safe_percent = (st.session_state.user_stats['safe_dishes'] / 
                          st.session_state.user_stats['total_scans'] * 100)
            st.markdown(f"""
            <div class='glass-card' style='text-align: center;'>
                <h3 style='color: #51cf66; font-size: 2.5rem;'>{safe_percent:.0f}%</h3>
                <p style='color: white;'>Plats Sûrs</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            danger_percent = (st.session_state.user_stats['dangerous_dishes'] / 
                            st.session_state.user_stats['total_scans'] * 100)
            st.markdown(f"""
            <div class='glass-card' style='text-align: center;'>
                <h3 style='color: #ff6b6b; font-size: 2.5rem;'>{danger_percent:.0f}%</h3>
                <p style='color: white;'>Plats Dangereux</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Most scanned dishes
        if st.session_state.user_stats['most_scanned']:
            st.markdown("<br><h3 style='color: white;'>🏆 Plats les plus scannés</h3>", unsafe_allow_html=True)
            
            sorted_foods = sorted(
                st.session_state.user_stats['most_scanned'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=[count for _, count in sorted_foods],
                    y=[food for food, _ in sorted_foods],
                    orientation='h',
                    marker=dict(
                        color=px.colors.sequential.Viridis,
                        line=dict(color='white', width=2)
                    )
                )
            ])
            
            fig.update_layout(
                title="Top 5 Plats Scannés",
                xaxis_title="Nombre de scans",
                height=350,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("""
        <div class='glass-card' style='text-align: center; padding: 3rem;'>
            <h2 style='color: white;'>📊 Aucune donnée disponible</h2>
            <p style='color: rgba(255,255,255,0.8);'>
                Scannez des plats pour voir vos statistiques ici
            </p>
        </div>
        """, unsafe_allow_html=True)

# =========================
# TAB 3: HISTORY
# =========================
with tab3:
    st.markdown("<h2 style='color: white;'>📖 Historique des Scans</h2>", unsafe_allow_html=True)
    
    if st.session_state.scan_history:
        for i, item in enumerate(st.session_state.scan_history):
            status_icon = "🟢" if item['safe'] else "🔴"
            status_text = "Sûr" if item['safe'] else "Dangereux"
            
            st.markdown(f"""
            <div class='history-item'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h4 style='margin: 0; color: #333;'>{status_icon} {item['food']}</h4>
                        <p style='margin: 0.25rem 0 0 0; color: #666; font-size: 0.9rem;'>
                            {item['timestamp'].strftime("%d/%m/%Y %H:%M")} • 
                            Confiance: {item['confidence']:.1f}% • 
                            <strong>{status_text}</strong>
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='glass-card' style='text-align: center; padding: 3rem;'>
            <h2 style='color: white;'>📖 Historique vide</h2>
            <p style='color: rgba(255,255,255,0.8);'>
                Vos scans apparaîtront ici
            </p>
        </div>
        """, unsafe_allow_html=True)

# =========================
# TAB 4: EXPLAINABILITY (Grad-CAM)
# =========================
with tab4:
    st.markdown("<h2 style='color: white;'>💡 Explainability AI</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='glass-card'>
        <h3 style='color: white;'>🧠 Comment l'IA prend ses décisions</h3>
        <p style='color: rgba(255,255,255,0.9); line-height: 1.8;'>
            Cette section utilise <strong>Grad-CAM</strong> (Gradient-weighted Class Activation Mapping)
            pour visualiser les zones de l'image que l'IA analyse pour identifier le plat.
        </p>
        <p style='color: rgba(255,255,255,0.9); margin-top: 1rem;'>
            Les zones <span style='color: #ff6b6b;'><strong>rouges</strong></span> indiquent les 
            régions les plus importantes pour la décision de l'IA.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("🔬 Fonctionnalité avancée disponible après scan d'une image")

# =========================
# TAB 5: ABOUT
# =========================
with tab5:
    st.markdown("<h2 style='color: white; text-align: center;'>ℹ️ À propos</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class='glass-card'>
            <h3 style='color: white;'>🎯 Innovations</h3>
            <ul style='color: rgba(255,255,255,0.9); line-height: 2;'>
                <li><strong>Scanner Pro</strong> avec niveaux de confiance</li>
                <li><strong>Analytics Dashboard</strong> personnalisé</li>
                <li><strong>Historique</strong> avec statistiques</li>
                <li><strong>Explainability AI</strong> (Grad-CAM)</li>
                <li><strong>Infos nutritionnelles</strong> détaillées</li>
                <li><strong>Interface premium</strong> glassmorphism</li>
                <li><strong>Multilingue</strong> (FR/EN)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='glass-card'>
            <h3 style='color: white;'>🏆 Équipe PPP</h3>
            <p style='color: rgba(255,255,255,0.9); line-height: 2;'>
                👥 <strong>Membres :</strong><br>
                • Younes BOUSSALAH<br>
                • Mouad KACIMI<br>
                • Brahim BENIKEN<br>
                • Mouad CHAOUNI<br><br>
                👨‍🏫 <strong>Encadrant :</strong><br>
                Pr Kamal IDRISSI
            </p>
        </div>
        """, unsafe_allow_html=True)

# =========================
# FOOTER
# =========================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: white; padding: 3rem 0; 
            background: rgba(0,0,0,0.3); border-radius: 20px;'>
    <h2 style='color: white; font-weight: 700;'>🏆 Allergy AI Pro</h2>
    <p style='font-size: 1.1rem; margin: 1rem 0;'>
        Projet PPP - Coupe du Monde 2030 🇲🇦
    </p>
    <p style='font-size: 0.9rem; opacity: 0.8;'>
        © 2025 Allergy for Moroccan Food AI | Powered by TensorFlow & Streamlit
    </p>
</div>
""", unsafe_allow_html=True)