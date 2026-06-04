import os
import io
import json
import base64
import numpy as np
from datetime import datetime
from PIL import Image
import cv2

# =========================
# KERAS VERSION COMPATIBILITY PATCH
# =========================
import keras
original_dense_from_config = keras.layers.Dense.from_config
keras.layers.Dense.from_config = lambda config: original_dense_from_config(
    {k: v for k, v in config.items() if k != 'quantization_config'}
)

import tensorflow as tf
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF

app = FastAPI(title="Allergy AI Pro API", version="2.0")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(filename):
    return os.path.join(SCRIPT_DIR, filename)

# Load configurations and model
try:
    model = tf.keras.models.load_model(get_path("moroccan_food_model.keras"))
except Exception as e:
    try:
        model = tf.keras.models.load_model(get_path("moroccan_food_model.h5"))
    except Exception as e2:
        print(f"Error loading model: {e2}")
        model = None

with open(get_path("class_names.json"), "r", encoding="utf-8") as f:
    class_names = {int(k): v for k, v in json.load(f).items()}

with open(get_path("allergens_db.json"), "r", encoding="utf-8") as f:
    allergens_db = json.load(f)

with open(get_path("translations.json"), "r", encoding="utf-8") as f:
    translations = json.load(f)

# =========================
# NUTRITION DATABASE
# =========================
def get_nutrition_data(food_name):
    food = food_name.lower()
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
# GRAD-CAM HEATMAP GENERATOR
# =========================
def get_grad_cam_heatmap(model, img_array):
    try:
        base_model = model.layers[0]
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
        print("Grad-CAM error:", e)
        return None

def overlay_heatmap(original_img, heatmap):
    try:
        heatmap_resized = cv2.resize(heatmap, (original_img.width, original_img.height))
        heatmap_resized = np.uint8(255 * heatmap_resized)
        heatmap_color = cv2.applyColorMap(heatmap_resized, cv2.COLORMAP_JET)
        heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
        
        original_arr = np.array(original_img)
        superimposed = cv2.addWeighted(original_arr, 0.6, heatmap_color, 0.4, 0)
        return Image.fromarray(superimposed)
    except Exception as e:
        print("Overlay error:", e)
        return None

# =========================
# ENDPOINTS
# =========================
@app.get("/api/config")
def get_config():
    return {
        "class_names": class_names,
        "allergens_db": allergens_db,
        "translations": translations
    }

@app.post("/api/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    allergies: str = Form("[]")
):
    if not model:
        raise HTTPException(status_code=500, detail="Model not loaded on backend.")
    
    try:
        user_allergies = json.loads(allergies)
    except Exception:
        user_allergies = []
        
    try:
        contents = await file.read()
        image_pil = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")
    
    # Preprocess image
    img_resized = image_pil.resize((224, 224))
    img_array = np.array(img_resized) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    
    # Run Inference
    predictions = model.predict(img_array)[0]
    top_indices = np.argsort(predictions)[::-1][:3]
    
    top_predictions = []
    for idx in top_indices:
        food_name = class_names.get(int(idx), "Inconnu")
        confidence = float(predictions[idx]) * 100
        top_predictions.append({
            "index": int(idx),
            "name": food_name,
            "confidence": confidence
        })
    
    top_dish = top_predictions[0]["name"]
    top_confidence = top_predictions[0]["confidence"]
    
    # Get Allergen Details
    dish_info = allergens_db.get(top_dish, {
        "ingredients": ["Inconnu"],
        "allergens": [],
        "alternatives": []
    })
    
    user_allergies_lower = [alg.lower().strip() for alg in user_allergies]
    detected_allergens = []
    for alg in dish_info.get("allergens", []):
        alg_clean = alg.lower().strip()
        if alg_clean in user_allergies_lower:
            # Match the original user-selected capitalized allergen string
            idx = user_allergies_lower.index(alg_clean)
            detected_allergens.append(user_allergies[idx])
            
    is_safe = len(detected_allergens) == 0
    
    # Grad-CAM Heatmap
    heatmap = get_grad_cam_heatmap(model, img_array)
    overlay_pil = None
    if heatmap is not None:
        overlay_pil = overlay_heatmap(image_pil, heatmap)
        
    # Convert images to base64
    def pil_to_base64(img, format="JPEG"):
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    original_b64 = pil_to_base64(image_pil)
    overlay_b64 = pil_to_base64(overlay_pil) if overlay_pil else original_b64
    
    nutrition = get_nutrition_data(top_dish)
    
    return {
        "success": True,
        "top_predictions": top_predictions,
        "is_safe": is_safe,
        "user_allergies": user_allergies,
        "detected_allergens": detected_allergens,
        "all_dish_allergens": dish_info.get("allergens", []),
        "ingredients": dish_info.get("ingredients", []),
        "alternatives": dish_info.get("alternatives", []),
        "nutrition": nutrition,
        "images": {
            "original": original_b64,
            "overlay": overlay_b64
        }
    }

class PDFRequest(BaseModel):
    food_name: str
    confidence: float
    is_safe: bool
    user_allergies: list
    detected_allergens: list
    nutrition: dict
    alternatives: list

@app.post("/api/export-pdf")
def export_pdf(req: PDFRequest):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        pdf.set_font("helvetica", "B", 22)
        pdf.set_text_color(0, 98, 51)
        pdf.cell(0, 15, "ALLERGY AI PRO REPORT", ln=True, align="C")
        
        pdf.set_font("helvetica", "I", 11)
        pdf.set_text_color(107, 114, 128)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        pdf.ln(5)
        
        pdf.set_draw_color(229, 231, 235)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(17, 24, 39)
        pdf.cell(0, 10, f"Detected Dish: {req.food_name.upper()}", ln=True)
        
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 8, f"Prediction Confidence: {req.confidence:.2f}%", ln=True)
        pdf.ln(5)
        
        pdf.set_font("helvetica", "B", 14)
        if req.is_safe:
            pdf.set_fill_color(209, 250, 229)
            pdf.set_text_color(6, 95, 70)
            pdf.cell(0, 12, "STATUS: COMPATIBLE / SAFE DISH", fill=True, ln=True, align="C")
        else:
            pdf.set_fill_color(254, 226, 226)
            pdf.set_text_color(153, 27, 27)
            pdf.cell(0, 12, "STATUS: DANGER / INCOMPATIBLE DISH", fill=True, ln=True, align="C")
            
        pdf.ln(5)
        pdf.set_text_color(17, 24, 39)
        
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "Allergy Profile Context:", ln=True)
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 6, f"Declared User Allergies: {', '.join(req.user_allergies) if req.user_allergies else 'None'}", ln=True)
        pdf.cell(0, 6, f"Detected Allergens in Dish: {', '.join(req.detected_allergens) if req.detected_allergens else 'None'}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "Nutritional Profile (per 100g estimate):", ln=True)
        
        pdf.set_font("helvetica", "", 11)
        pdf.cell(45, 7, f"Calories: {req.nutrition.get('calories', 0)} kcal", border=1)
        pdf.cell(45, 7, f"Proteins: {req.nutrition.get('proteins', 0)} g", border=1)
        pdf.cell(45, 7, f"Carbohydrates: {req.nutrition.get('carbs', 0)} g", border=1)
        pdf.cell(45, 7, f"Fats: {req.nutrition.get('fats', 0)} g", border=1)
        pdf.ln(7)
        pdf.cell(45, 7, f"Dietary Fiber: {req.nutrition.get('fiber', 0)} g", border=1)
        pdf.ln(12)
        
        if req.alternatives:
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, "Recommended Alternatives:", ln=True)
            pdf.set_font("helvetica", "", 11)
            for alt in req.alternatives:
                pdf.cell(0, 6, f"- {alt}", ln=True)
                
        pdf.ln(15)
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(156, 163, 175)
        pdf.multi_cell(0, 5, "Disclaimer: Allergy AI Pro is an assistive tool using deep learning. Always consult restaurant staff or medical personnel before consuming foods to verify exact ingredient sourcing.")
        
        pdf_bytes = pdf.output()
        return Response(content=pdf_bytes, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=allergy_ai_pro_report.pdf"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation error: {e}")

# Mount static folder
app.mount("/", StaticFiles(directory=get_path("static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
