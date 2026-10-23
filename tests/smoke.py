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
FOTO = {c: os.path.join(SAIDA, f"smoke-{c}.png") for c in ("monofocal", "monovisao")}

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
        pag.goto("http://localhost:8765/?s=10")
        for lente in ("edof", "multifocal", "torica"):  # sobram catarata, monofocal e monovisão em cada cena
            pag.uncheck(f"#lentes input[value={lente}]")
        pag.click("#iniciar")
        for cap, foto in (("De dia · Lente monofocal", "monofocal"), ("De dia · Monovisão", "monovisao")):
            pag.wait_for_selector(f'body[data-capitulo="{cap}"]', timeout=60000)
            pag.wait_for_timeout(3300)  # a legenda some depois de 3 s
            pag.screenshot(path=FOTO[foto])  # no SwiftShader cada quadro demora: confere se ainda é o mesmo capítulo
            assert pag.get_attribute("body", "data-capitulo") == cap, f"a foto de {cap} saiu atrasada"
        pag.wait_for_selector("#inicio:not([hidden])", timeout=60000)  # no fim volta à tela inicial
        nav.close()
finally:
    servidor.terminate()

assert not erros, erros
img = {k: np.asarray(Image.open(v).convert("RGB"), np.int16) for k, v in FOTO.items()}


def vista_esperada(jpg, h, w, fov_v=75):
    """Projeta a imagem equirretangular parcial numa câmera olhando para +x, como o app mostra fora do VR."""
    src = np.asarray(Image.open(jpg).convert("L"), np.float32)
    campo = np.pi * src.shape[1] / src.shape[0]
    t = np.tan(np.radians(fov_v / 2))
    v, u = np.mgrid[0:h, 0:w] + 0.5
    y, z = (1 - 2 * v / h) * t, (2 * u / w - 1) * t * w / h
    lon, lat = np.arctan2(z, 1), np.arctan2(y, np.hypot(1, z))
    col = ((lon / campo + 0.5) * src.shape[1]).astype(int).clip(0, src.shape[1] - 1)
    lin = ((0.5 - lat / np.pi) * src.shape[0]).astype(int).clip(0, src.shape[0] - 1)
    return src[lin, col]


# Frente no centro e sem espelhamento: a tela bate com a projeção esperada da imagem, e não com o espelho dela.
reduz = lambda a: np.asarray(Image.fromarray(a.astype(np.uint8)).resize((193, 90), Image.BOX), np.float32).ravel()
tela = reduz(img["monofocal"].mean(-1))
esperada = vista_esperada(os.path.join(RAIZ, "media", "dia-monofocal.jpg"), *img["monofocal"].shape[:2])
corr, corr_espelho = (np.corrcoef(tela, reduz(e))[0, 1] for e in (esperada, esperada[:, ::-1]))
assert corr > 0.9 and corr > corr_espelho + 0.2, f"vista da frente: correlação {corr:.2f}, espelhada {corr_espelho:.2f}"
# Fora do VR aparece o olho esquerdo; na monovisão ele é o de perto, então o fundo ao longe fica borrado.
nitidez = lambda a: np.square(np.diff(a[150:330, 500:1050].mean(-1), axis=1)).mean()  # energia do gradiente cai com o borrão
assert nitidez(img["monovisao"]) < 0.8 * nitidez(img["monofocal"]), "monovisão: OE devia mostrar a imagem de perto"
print("smoke ok")
