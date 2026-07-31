#!/usr/bin/env python3
"""
test_vision_extraction.py

Herramienta manual para probar la extraccion de productos desde una imagen
de cotizacion (letra impresa o manuscrita) contra el modelo de vision local
(qwen2.5vl:7b via Ollama), usando el prompt + JSON Schema v3 documentados
en docs/AI_MODEL_ODOO_CONFIG.md §5.3 -- la unica version que dio resultados
correctos en las pruebas con texto impreso sintetico (2026-07-27).

Uso / Usage:
    python3 scripts/test_vision_extraction.py /ruta/a/la/foto.jpg

No escribe nada en Odoo ni en ninguna base de datos -- es solo para ver
como responde el modelo con una imagen real, antes de decidir si vale la
pena construir el flujo completo (local_ai_connector, §7 del documento).

Si algun renglon de la imagen menciona una cantidad fisica de inventario
existente, el prompt le pide al modelo usar unicamente el termino
'A la mano' (On Hand) -- nunca "disponible", "stock" ni "existencias".
"""
import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5vl:7b"

# Fotos reales (ej. capturas de WhatsApp) llegan en ~800x1600px o mas -- eso
# infla el conteo de tokens de la imagen (~2000 tokens vs ~500 en una prueba
# sintetica chica) y la inferencia en CPU se vuelve impracticamente lenta
# (>10 min, confirmado empiricamente 2026-07-27, hubo que cancelar la
# corrida). Se reescala el lado mayor a este valor antes de mandarla a
# Ollama -- suficiente para leer texto de cotizacion, no para fotografia
# de alta fidelidad.
MAX_DIMENSION = 1024


def resize_if_needed(image_path):
    proc = subprocess.run(
        ["identify", "-format", "%w %h", image_path],
        capture_output=True, text=True, check=True,
    )
    width, height = (int(v) for v in proc.stdout.split())
    if max(width, height) <= MAX_DIMENSION:
        return image_path

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    subprocess.run(
        ["convert", image_path, "-resize", "{0}x{0}>".format(MAX_DIMENSION),
         "-quality", "85", tmp.name],
        check=True,
    )
    print("Imagen redimensionada de {}x{} a un maximo de {}px por lado -> {}".format(
        width, height, MAX_DIMENSION, tmp.name
    ))
    return tmp.name

PROMPT = """Vas a recibir una imagen con una lista de productos escrita o impresa por un cliente
de una farmacia, para generar una cotizacion.

Transcribe CADA renglon de texto que veas en la imagen como un elemento separado de la
lista. Si un renglon incluye una cantidad (ej. "x2", "x1"), separa el texto del producto
de la cantidad numerica.

Ejemplo: si la imagen dice "PARACETAMOL 500MG C/20 TAB x2" y "LOSARTAN 50MG C/30 TABS",
la respuesta debe tener 2 elementos:
- texto_detectado: "PARACETAMOL 500MG C/20 TAB", cantidad_detectada: 2
- texto_detectado: "LOSARTAN 50MG C/30 TABS", cantidad_detectada: null

No devuelvas una lista vacia si hay texto legible en la imagen. No adivines el producto
exacto del catalogo, solo transcribe.

Si algun renglon menciona una cantidad fisica de inventario existente (poco comun en
este flujo), refierete a ella unicamente como "A la mano" (On Hand). Nunca uses
"disponible", "stock" ni "existencias"."""

SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "properties": {
            "texto_detectado": {"type": "string"},
            "cantidad_detectada": {"type": ["integer", "null"]},
        },
        "required": ["texto_detectado", "cantidad_detectada"],
    },
}


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: python3 scripts/test_vision_extraction.py /ruta/a/la/foto.jpg")

    image_path = resize_if_needed(sys.argv[1])
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "images": [img_b64],
        "format": SCHEMA,
        "stream": False,
        # Con la imagen ya redimensionada (MAX_DIMENSION) 4096 da margen de
        # sobra; sin redimensionar, 2048 se quedaba corto (done_reason=
        # "length", JSON cortado a la mitad) y 8192 sin redimensionar
        # resultaba impracticamente lento en CPU. Confirmado 2026-07-27.
        "options": {"temperature": 0, "num_ctx": 4096},
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    print("Procesando '{}' con {} (puede tardar 20-90s en CPU)...".format(image_path, MODEL))
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read())
    elapsed = time.time() - t0

    raw = body.get("response", "")
    print("\nTiempo: {:.1f}s\n".format(elapsed))

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print("ERROR: el modelo no devolvio JSON valido: {}".format(e))
        print("Respuesta cruda:\n{}".format(raw))
        return

    if not isinstance(parsed, list) or len(parsed) == 0:
        print("ADVERTENCIA: se esperaba una lista con al menos 1 elemento, se recibio: {!r}".format(parsed))
        print("(esto NO es un exito silencioso -- revisar manualmente)")
        return

    print("Renglones detectados: {}\n".format(len(parsed)))
    for i, item in enumerate(parsed, 1):
        texto = item.get("texto_detectado", "<falta>")
        cantidad = item.get("cantidad_detectada")
        print("  {}. \"{}\"  (cantidad: {})".format(i, texto, cantidad if cantidad is not None else "sin detectar"))


if __name__ == "__main__":
    main()
