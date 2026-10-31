import json
import uuid

import numpy as np
import paho.mqtt.client as paho
import streamlit as st
from PIL import Image, ImageOps
from keras.models import load_model

# Debe coincidir con el tema al que se suscribe el ESP32 en Wokwi (sketch.ino)
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "cerradura_tm_7c3f"
UMBRAL = 0.6  # confianza mínima para actuar sobre la cerradura

st.set_page_config(page_title="Cerradura Inteligente", page_icon="🔒")


@st.cache_resource
def cargar_modelo():
    model = load_model("keras_model.h5", compile=False)
    with open("labels.txt", encoding="utf-8") as f:
        # Cada línea es "0 Abre", "1 Cierra", ... -> nos quedamos con el nombre
        labels = [line.strip().split(" ", 1)[1] for line in f if line.strip()]
    return model, labels


@st.cache_resource
def conectar_mqtt():
    # ID único para no chocar con otros clientes en el broker público
    client = paho.Client(f"APP_CERR_{uuid.uuid4().hex[:6]}")
    client.connect(BROKER, PORT)
    client.loop_start()
    return client


def preparar_imagen(img_file):
    img = Image.open(img_file).convert("RGB")
    img = ImageOps.fit(img, (224, 224), Image.Resampling.LANCZOS)
    arr = (np.asarray(img).astype(np.float32) / 127.5) - 1
    return arr[np.newaxis, ...]


model, labels = cargar_modelo()
client = conectar_mqtt()

if "estado" not in st.session_state:
    st.session_state.estado = "Desconocido"

with st.sidebar:
    st.header("Instrucciones")
    st.markdown(
        "1. Haz un gesto frente a la cámara.\n"
        "2. Toma la foto.\n"
        "3. La cerradura en Wokwi responde:\n"
        "   - ✋ **Abre** → abre la cerradura\n"
        "   - ✊ **Cierra** → cierra la cerradura\n"
        "   - **Nada** → no hace nada"
    )
    st.divider()
    st.caption(f"Broker: `{BROKER}`")
    st.caption(f"Tema MQTT: `{TOPIC}`")
    UMBRAL = st.slider("Confianza mínima", 0.3, 0.95, UMBRAL, 0.05)

st.title("🔒 Cerradura Inteligente")
st.write("Controla la cerradura con gestos reconocidos por Teachable Machine.")

estado_box = st.empty()  # se llena al final, ya con el estado actualizado

img_file_buffer = st.camera_input("Toma una foto con tu gesto")

if img_file_buffer is not None:
    prediction = model.predict(preparar_imagen(img_file_buffer), verbose=0)[0]
    idx = int(np.argmax(prediction))
    gesto, confianza = labels[idx], float(prediction[idx])

    st.subheader(f"Gesto detectado: {gesto} ({confianza:.0%})")
    for label, p in zip(labels, prediction):
        st.progress(float(p), text=f"{label}: {p:.0%}")

    if confianza < UMBRAL:
        st.warning("No estoy seguro del gesto. Intenta de nuevo.")
    elif gesto == "Abre":
        client.publish(TOPIC, json.dumps({"gesto": "Abre"}))
        st.session_state.estado = "Abierta"
        st.success("🔓 Abriendo la cerradura")
    elif gesto == "Cierra":
        client.publish(TOPIC, json.dumps({"gesto": "Cierra"}))
        st.session_state.estado = "Cerrada"
        st.success("🔒 Cerrando la cerradura")
    else:
        st.info("Sin gesto: la cerradura no cambia.")

estado = st.session_state.estado
icono = {"Abierta": "🔓", "Cerrada": "🔒"}.get(estado, "❔")
estado_box.metric("Estado de la cerradura", f"{icono} {estado}")
