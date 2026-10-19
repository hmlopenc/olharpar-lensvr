"""Teste de fumaça da página num Chromium headless.

Uso: python3 tests/smoke.py [pasta_de_saida]
Sem internet para o CDN, aponte THREE_DIR para uma cópia local de three/build.
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = sys.argv[1] if len(sys.argv) > 1 else "."
THREE_DIR = os.environ.get("THREE_DIR")

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
        olhar = lambda alpha: pag.evaluate(
            "a => dispatchEvent(new DeviceOrientationEvent('deviceorientation', {alpha: a, beta: 90, gamma: 0}))", alpha)

        pag.goto("http://localhost:8765/")
        pag.click("#iniciar")
        pag.wait_for_selector("canvas:not([hidden])")
        olhar(30)                      # cabeça virada para um lado qualquer durante a contagem
        pag.wait_for_timeout(6000)     # contagem de 5 s e recentralização
        olhar(30)
        pag.wait_for_timeout(300)
        pag.screenshot(path=os.path.join(SAIDA, "smoke-frente.png"))
        olhar(120)                     # vira 90° para a esquerda
        pag.wait_for_timeout(300)
        pag.screenshot(path=os.path.join(SAIDA, "smoke-esquerda.png"))
        nav.close()
finally:
    servidor.terminate()

assert not erros, erros
print("smoke ok")
