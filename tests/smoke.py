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
FOTO = {c: os.path.join(SAIDA, f"smoke-{c}.png") for c in ("video1", "video2", "monofocal", "monovisao")}
# No SwiftShader cada quadro do vídeo em resolução cheia leva segundos: o teste usa cópias de 760 × 720 (mesmo campo).
for lente in ("catarata", "monofocal", "perto"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", "3", "-i", os.path.join(RAIZ, "media", f"dia-{lente}.mp4"),
                    "-vf", "scale=760:720", "-c:v", "libx264", "-preset", "veryfast", os.path.join(SAIDA, f"dia-{lente}.mp4")],
                   check=True)

servidor = subprocess.Popen([sys.executable, "-m", "http.server", "8765"], cwd=RAIZ,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
erros = []


def pagina(nav, w, h, vigiar=True):
    p = nav.new_page(viewport={"width": w, "height": h})
    if vigiar:
        p.on("console", lambda m: m.type == "error" and erros.append(m.text))
        p.on("pageerror", lambda e: erros.append(str(e)))
    if THREE_DIR:
        p.route("https://cdn.jsdelivr.net/npm/three@*/build/*", lambda r: r.fulfill(
            path=os.path.join(THREE_DIR, r.request.url.rsplit("/", 1)[1]), content_type="text/javascript"))
    p.route("**/media/dia-*.mp4", lambda r: r.fulfill(path=os.path.join(SAIDA, r.request.url.rsplit("/", 1)[1])))
    return p


try:
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pag = pagina(nav, 1544, 720)
        pag.goto("http://localhost:8765/?s=20")  # no SwiftShader as fotos de tela com vídeo levam segundos
        for lente in ("edof", "multifocal", "torica"):  # sobram catarata, monofocal e monovisão em cada cena
            pag.uncheck(f"#lentes input[value={lente}]")
        pag.click("#iniciar")
        # De dia é vídeo: duas fotos do mesmo capítulo têm de diferir (o vídeo está tocando).
        cap = "De dia · Lente monofocal"
        pag.wait_for_selector(f'body[data-capitulo="{cap}"]', timeout=90000)
        pag.wait_for_timeout(3300)
        pag.screenshot(path=FOTO["video1"])
        pag.wait_for_timeout(1500)
        pag.screenshot(path=FOTO["video2"])
        assert pag.get_attribute("body", "data-capitulo") == cap, "as fotos do vídeo saíram atrasadas"
        for cap, foto in (("À noite · Lente monofocal", "monofocal"), ("À noite · Monovisão", "monovisao")):
            pag.wait_for_selector(f'body[data-capitulo="{cap}"]', timeout=90000)
            pag.wait_for_timeout(3300)  # a legenda some depois de 3 s
            pag.screenshot(path=FOTO[foto])  # no SwiftShader cada quadro demora: confere se ainda é o mesmo capítulo
            assert pag.get_attribute("body", "data-capitulo") == cap, f"a foto de {cap} saiu atrasada"
        pag.wait_for_selector("#inicio:not([hidden])", timeout=60000)  # sem controle, no fim volta à tela inicial
        # Controle no modo GAME (falso, no lugar do Bluetooth): qualquer botão abre o menu, o joystick troca de item,
        # o botão marca a lente ou recomeça, e no fim o menu volta em vez de sair.
        ctrl = pagina(nav, 800, 600)
        ctrl.add_init_script("""const b = Array.from({ length: 17 }, () => ({ pressed: false, value: 0 })), e = [0, 0];
            navigator.getGamepads = () => [{ id: 'teste', mapping: 'standard', connected: true, buttons: b, axes: e }];
            window.aperta = i => { b[i].pressed = true; setTimeout(() => { b[i].pressed = false; }, 500); };
            window.empurra = v => { e[1] = v; setTimeout(() => { e[1] = 0; }, 500); };""")
        ctrl.goto("http://localhost:8765/?s=2")
        for lente in ("edof", "multifocal", "torica", "monovisao"):
            ctrl.uncheck(f"#lentes input[value={lente}]")
        ctrl.click("#iniciar")
        ctrl.wait_for_selector("body[data-capitulo]", timeout=90000)
        for acao, item in (("aperta(0)", "Iniciar"), ("empurra(-1)", "Monovisão: não"),
                           ("aperta(1)", "Monovisão: sim"), ("empurra(1)", "Iniciar")):
            ctrl.evaluate(acao)
            ctrl.wait_for_selector(f'body[data-menu="{item}"]:not([data-capitulo])', timeout=30000)
            ctrl.wait_for_timeout(1000)  # o botão solta antes da próxima ação
        assert ctrl.is_checked("#lentes input[value=monovisao]"), "o menu não marcou a lente"
        ctrl.evaluate("aperta(2)")
        ctrl.wait_for_selector('body[data-capitulo="À noite · Monovisão"]', timeout=90000)  # recomeçou com a lente nova
        ctrl.wait_for_selector('body[data-menu="Iniciar"]', timeout=90000)
        assert ctrl.is_hidden("#inicio"), "com controle, o fim devia voltar ao menu, não à tela inicial"
        # Falha visível: sem as imagens, volta à tela inicial com o motivo escrito (no celular não há console).
        ruim = pagina(nav, 800, 600, vigiar=False)
        ruim.route("**/media/*", lambda r: r.fulfill(status=404, body="sem imagem"))
        ruim.goto("http://localhost:8765/?s=1")
        ruim.click("#iniciar")
        ruim.wait_for_selector("#erro:not([hidden])", timeout=30000)
        assert "não carregou" in ruim.inner_text("#erro") and ruim.is_visible("#inicio"), ruim.inner_text("#erro")
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
esperada = vista_esperada(os.path.join(RAIZ, "media", "noite-monofocal.jpg"), *img["monofocal"].shape[:2])
corr, corr_espelho = (np.corrcoef(tela, reduz(e))[0, 1] for e in (esperada, esperada[:, ::-1]))
assert corr > 0.9 and corr > corr_espelho + 0.2, f"vista da frente: correlação {corr:.2f}, espelhada {corr_espelho:.2f}"
# Fora do VR aparece o olho esquerdo; na monovisão ele é o de perto, então o fundo ao longe fica borrado.
nitidez = lambda a: np.square(np.diff(a[150:330, 500:1050].mean(-1), axis=1)).mean()  # energia do gradiente cai com o borrão
assert nitidez(img["monovisao"]) < 0.8 * nitidez(img["monofocal"]), "monovisão: OE devia mostrar a imagem de perto"
assert np.abs(img["video1"] - img["video2"]).mean() > 0.3, "o vídeo do dia não está tocando"
print("smoke ok")
