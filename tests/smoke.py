"""Teste de fumaça da página num Chromium headless (sem WebXR: roda na tela, olhando para a frente).

Uso: python3 tests/smoke.py [pasta_de_saida]
Sem internet para o CDN, aponte THREE_DIR para uma cópia local de three/build.
"""
import os, subprocess, sys, time
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = sys.argv[1] if len(sys.argv) > 1 else "."
THREE_DIR = os.environ.get("THREE_DIR")
FRENTE = os.path.join(SAIDA, "smoke-frente.png")

servidor = subprocess.Popen([sys.executable, "-m", "http.server", "8765"], cwd=RAIZ,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
erros = []
try:
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pag = nav.new_page(viewport={"width": 1544, "height": 720})
        pag.on("console", lambda m: m.type == "error" and erros.append(m.text))
        pag.on("pageerror", lambda e: erros.append(str(e)))
        if THREE_DIR:
            pag.route("https://cdn.jsdelivr.net/npm/three@*/build/*", lambda r: r.fulfill(
                path=os.path.join(THREE_DIR, r.request.url.rsplit("/", 1)[1]), content_type="text/javascript"))
        pag.goto("http://localhost:8765/")
        pag.click("#iniciar")
        pag.wait_for_selector("canvas:not([hidden])")
        pag.wait_for_timeout(6500)     # contagem de 5 s, imagem carregada e recentralizada
        pag.screenshot(path=FRENTE)
        nav.close()
finally:
    servidor.terminate()

assert not erros, erros
# Sem espelhamento e com a frente no centro: na cena sintética a PADARIA (vermelho-escuro) fica à esquerda
# da FARMÁCIA (verde) na fachada em frente.
img = np.asarray(Image.open(FRENTE).convert("RGB"), np.int16)
r, g, b = img[..., 0], img[..., 1], img[..., 2]
verde = (g > r + 50) & (g > b + 30)
vermelho = (r > g + 50) & (r > b + 50) & (r < 170)
assert verde.sum() > 50 and vermelho.sum() > 50, "fachada não aparece na frente"
xv, xr = np.nonzero(verde)[1].mean(), np.nonzero(vermelho)[1].mean()
assert xr < xv, f"imagem espelhada: PADARIA em x={xr:.0f}, FARMÁCIA em x={xv:.0f}"
assert abs((xr + xv) / 2 - img.shape[1] / 2) < img.shape[1] * 0.1, "a frente da cena não está no centro"
print("smoke ok")
