from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

import json
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras import layers, models
import tensorflow as tf

# =========================
# DATA GENERATOR
# =========================
datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2
)

train_data = datagen.flow_from_directory(
    "dataset/train",
    target_size=(224, 224),
    batch_size=32,
    class_mode="categorical",
    subset="training",
    shuffle=True
)

val_data = datagen.flow_from_directory(
    "dataset/train",
    target_size=(224, 224),
    batch_size=32,
    class_mode="categorical",
    subset="validation",
    shuffle=False
)

# =========================
# MODEL
# =========================
base_model = MobileNetV2(
    weights="imagenet",
    include_top=False,
    input_shape=(224, 224, 3)
)

base_model.trainable = False  # geler le backbone

num_classes = train_data.num_classes

model = models.Sequential([
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.BatchNormalization(),
    layers.Dense(128, activation="relu"),
    layers.Dropout(0.5),
    layers.Dense(num_classes, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

# =========================
# TRAINING
# =========================
history = model.fit(
    train_data,
    epochs=10,
    validation_data=val_data
)

# =========================
# SAVE CLASS NAMES (CORRECT)
# =========================
class_indices = train_data.class_indices
class_names = {v: k for k, v in class_indices.items()}

with open("class_names.json", "w") as f:
    json.dump(class_names, f)

print("✅ Classes sauvegardées :", class_names)

# =========================
# SAVE MODEL (RECOMMANDÉ)
# =========================
model.save("moroccan_food_model.keras")

print("✅ Modèle sauvegardé")
