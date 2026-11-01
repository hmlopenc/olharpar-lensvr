"""Gera um vídeo por lente a partir de um trecho da Insta360 X6 (só a lente da frente, sem costura).

Uso: python3 tools/video.py <trecho.mp4> <início_s> [duração_s=10] [folha.jpg]
Grava media/dia-{lente}.mp4 (190° × 180°, 3040 × 2880, H.264) e a folha de contato do quadro do meio.

A distância de cada pixel vem do Depth Anything V2 (ONNX, CPU), quadro a quadro. O modelo dá a profundidade
relativa; as três referências medidas na gravação a convertem em vergência (dioptrias), e uma mediana no
tempo tira a tremulação. A óptica é a mesma do bake.py (tools/lentes.py), aplicada por faixas de vergência.
"""
import os, shutil, sys, subprocess, tempfile, time, urllib.request
import numpy as np
import cv2
import onnxruntime as ort
import bake
from lentes import LENTES, PUPILA_MM

# Lente da frente da X6 (projeção equidistante), calibrada em 01/11/2026 pela sobreposição com a lente de trás.
F_PX_GRAU, CENTRO, LADO = 19.75, (1919.0, 1919.9), 3840
CAMPO, W, H = 190, 3040, 2880   # 16 px/grau; a lente cobre ~194° no quadro; 3040 × 2880 cabe no H.264 nível 5.2
PX_GRAU = W / CAMPO
FPS = "30000/1001"
MODELO = os.path.join(bake.CACHE, "modelos", "da2-small.onnx")  # ponytail: o small; o base tem bordas melhores e custa 2,5x
URL_MODELO = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"

# Referências do trecho de 01/11/2026 (caixas x0, y0, x1, y1 no quadro de saída) e vergências medidas (D):
# árvores e poste ao longe, criança e mulher a ~1 m, livro a ~30 cm (informadas pelo Dr. Henrique).
REFS = [([(500, 1280, 2300, 1440)], 0.03),
        ([(1250, 1630, 1530, 1850), (1710, 1690, 2080, 1930)], 1.0),
        ([(760, 2080, 1960, 2400)], 1 / 0.30)]
FAIXAS = np.float32([0.0, 1.0, 2.2, 1 / 0.30, 4.3])  # centros das faixas de vergência (D), alinhados às referências


def mapas():
    """Quadro olho-de-peixe -> equirretangular parcial: centro = frente, +x à direita, +y para cima."""
    lon = ((np.arange(W) + 0.5) / W - 0.5) * np.radians(CAMPO)
    lat = (0.5 - (np.arange(H) + 0.5) / H) * np.pi
    lon, lat = np.meshgrid(lon, lat)
    dx, dy, dz = np.cos(lat) * np.cos(lon), np.sin(lat), np.cos(lat) * np.sin(lon)
    th = np.degrees(np.arccos(np.clip(dx, -1, 1)))
    s = np.sqrt(np.maximum(1 - dx * dx, 1e-12))
    return (CENTRO[0] + F_PX_GRAU * th * dz / s).astype(np.float32), (CENTRO[1] - F_PX_GRAU * th * dy / s).astype(np.float32)


def quadros(trecho, inicio, n):
    """Quadros RGB 8 bits da lente da frente (fluxo 0), já em equirretangular."""
    mx, my = mapas()
    cmd = ["ffmpeg", "-v", "error", "-threads", "1", "-ss", str(inicio), "-i", trecho, "-map", "0:0", "-frames:v", str(n),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=LADO * LADO * 3) as p:
        for _ in range(n):
            buf = p.stdout.read(LADO * LADO * 3)
            if len(buf) < LADO * LADO * 3:
                return
            yield cv2.remap(np.frombuffer(buf, np.uint8).reshape(LADO, LADO, 3), mx, my, cv2.INTER_CUBIC)


def vergencia(sessao, rgb):
    """Profundidade relativa do Depth Anything V2 convertida em vergência pelas referências (interpolação linear)."""
    h, w = 518, int(round(518 * W / H / 14)) * 14
    x = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    x = ((x - (0.485, 0.456, 0.406)) / (0.229, 0.224, 0.225)).transpose(2, 0, 1)[None].astype(np.float32)
    disp = sessao.run(None, {sessao.get_inputs()[0].name: x})[0].reshape(h, w)
    ref = [float(np.median(np.concatenate([disp[int(y0 * h / H):int(y1 * h / H), int(x0 * w / W):int(x1 * w / W)].ravel()
                                           for x0, y0, x1, y1 in caixas]))) for caixas, _ in REFS]
    alvo = [v for _, v in REFS]
    assert ref[0] < ref[1] < ref[2], f"referências fora de ordem na profundidade estimada: {ref}"
    v = np.interp(disp, ref, alvo)
    v = np.where(disp > ref[2], alvo[2] + (disp - ref[2]) * (alvo[2] - alvo[1]) / (ref[2] - ref[1]), v)  # mais perto que o livro
    return np.clip(v, 0, FAIXAS[-1]).astype(np.float32)


def nucleos():
    """Borrão de cada lente em cada faixa, por escala (1, 2 ou 4): componente de borrão grande dispensa resolução, e o
    componente nítido de uma multifocal fica na escala 1. Cada núcleo já vem pesado pela fração da luz."""
    out = {}
    for nome, lente in LENTES.items():
        for i, v in enumerate(FAIXAS):
            grupos = {}
            for c in lente["componentes"]:
                k = bake.psf({**lente, "componentes": [(*c[:2], 1.0)]}, v, PUPILA_MM["dia"], PX_GRAU)
                grupos.setdefault(1 if k is None or k.shape[0] < 7 else 2 if k.shape[0] < 11 else 4, []).append(c)
            out[nome, i] = []
            for esc, g in grupos.items():
                k = bake.psf({**lente, "componentes": g}, v, PUPILA_MM["dia"], PX_GRAU / esc)
                out[nome, i].append((esc, np.float32([[sum(c[2] for c in g)]]) if k is None else k))
    return out


def lentes_do_quadro(rgb8, v, nuc, lut):
    """Soma normalizada das faixas borradas (preenche o que o objeto da frente escondia). Gera (lente, rgb linear), uma por vez.
    Cada escala acumula à parte e só amplia no fim: ampliar é linear, então uma ampliação por lente basta."""
    rgb = lut[rgb8]
    k = np.clip(np.searchsorted(FAIXAS, v) - 1, 0, len(FAIXAS) - 2)
    f = np.clip((v - FAIXAS[k]) / (FAIXAS[k + 1] - FAIXAS[k]), 0, 1)
    soma = {}
    for i in range(len(FAIXAS)):
        peso = np.where(k == i, 1 - f, 0) + np.where(k + 1 == i, f, 0)
        if peso.max() == 0:
            continue
        c1 = np.empty((H, W, 4), np.float32)
        np.multiply(rgb, peso[..., None], out=c1[..., :3])
        c1[..., 3] = peso
        camada = {1: c1}
        for n in LENTES:
            for esc, nk in nuc[n, i]:
                if esc not in camada:
                    camada[esc] = cv2.resize(camada[1], (W // esc, H // esc), interpolation=cv2.INTER_AREA)
                b = cv2.filter2D(camada[esc], -1, nk, borderType=cv2.BORDER_REFLECT)
                if (n, esc) in soma:
                    soma[n, esc] += b
                else:
                    soma[n, esc] = b
    for n in LENTES:
        s = sum(soma.pop((n, e)) if e == 1 else cv2.resize(soma.pop((n, e)), (W, H), interpolation=cv2.INTER_LINEAR)
                for e in (1, 2, 4) if (n, e) in soma)
        yield n, bake.catarata(s[..., :3] / np.maximum(s[..., 3:], 1e-4), LENTES[n], PX_GRAU)


# Saída: linear -> sRGB 8 bits por tabela (o vídeo de origem já é SDR, sem curva ACES), com o degradê das bordas.
SAIDA = np.round(255 * np.where(np.linspace(0, 1, 4096) <= 0.0031308, 12.92 * np.linspace(0, 1, 4096),
                                1.055 * np.linspace(0, 1, 4096) ** (1 / 2.4) - 0.055)).astype(np.uint8)
FADE4095 = (bake.degrade(np.ones((1, W, 1), np.float32), CAMPO) * 4095).astype(np.float32)


def oito_bits(img):
    x = img * FADE4095
    np.clip(x, 0, 4095, out=x)
    return SAIDA[x.astype(np.uint16)]


def rascunho(arq):
    """Gravação quase sem perda e com pouca memória (são 6 ao mesmo tempo); a compressão final vem depois, uma lente por vez."""
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", FPS, "-i", "-",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "8", "-x264-params", "threads=1", "-pix_fmt", "yuv420p", arq]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


LUT = (np.where(np.arange(256) / 255 <= 0.04045, np.arange(256) / 255 / 12.92,
                ((np.arange(256) / 255 + 0.055) / 1.055) ** 2.4)).astype(np.float32)


if __name__ == "__main__":
    trecho, inicio = sys.argv[1], float(sys.argv[2])
    n = int(round(float(sys.argv[3] if len(sys.argv) > 3 else 10) * 30000 / 1001))
    folha = sys.argv[4] if len(sys.argv) > 4 else os.path.join(tempfile.gettempdir(), "folha-video.jpg")
    if not os.path.exists(MODELO):
        os.makedirs(os.path.dirname(MODELO), exist_ok=True)
        urllib.request.urlretrieve(URL_MODELO, MODELO)
    sessao = ort.InferenceSession(MODELO, providers=["CPUExecutionProvider"])
    t0 = time.time()
    vs = np.stack([vergencia(sessao, q) for q in quadros(trecho, inicio, n)])   # 1ª passada: profundidade
    n = len(vs)
    vs = np.stack([np.median(vs[max(0, i - 2):i + 3], 0) for i in range(n)])     # mediana de 5 quadros no tempo
    print(f"profundidade de {n} quadros em {time.time() - t0:.0f} s", flush=True)
    del sessao                                                                    # a memória vai para os 6 codificadores
    nuc = nucleos()
    pasta = tempfile.mkdtemp(prefix="lensvr-")
    enc = {nm: rascunho(os.path.join(pasta, f"{nm}.mkv")) for nm in LENTES}
    for i, q in enumerate(quadros(trecho, inicio, n)):                            # 2ª passada: óptica
        if i == n // 2:
            meio = {"original": oito_bits(LUT[q])}                                # quadro do meio, para a folha de contato
        for nm, img in lentes_do_quadro(q, cv2.resize(vs[i], (W, H), interpolation=cv2.INTER_LINEAR), nuc, LUT):
            b = oito_bits(img)
            enc[nm].stdin.write(b.tobytes())
            if i == n // 2:
                meio[nm] = b
        if i % 20 == 0:
            print(f"quadro {i} em {time.time() - t0:.0f} s", flush=True)
    for p in enc.values():
        p.stdin.close()
        assert p.wait() == 0, "ffmpeg falhou"
    for nm in LENTES:                                                             # compressão final, uma lente por vez
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(pasta, f"{nm}.mkv"), "-c:v", "libx264",
                        "-preset", "fast", "-crf", "21", "-profile:v", "high", "-level:v", "5.2", "-movflags", "+faststart",
                        os.path.join(bake.RAIZ, "media", f"dia-{nm}.mp4")], check=True)
    shutil.rmtree(pasta)
    regioes = {"longe": (2150, 1300), "intermediário": (1900, 1820), "perto": (1520, 2160)}
    bake.folha_de_contato({"vídeo": {nm: {r: im[y - 150:y + 150, x - 200:x + 200] for r, (x, y) in regioes.items()}
                                     for nm, im in meio.items()}}, folha)
    print(f"pronto em {time.time() - t0:.0f} s; folha de contato: {folha}")
