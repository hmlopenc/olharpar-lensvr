"""Gera um vídeo por lente a partir de um trecho da Insta360 X6 (só a lente da frente, sem costura).

Uso: python3 tools/video.py <trecho.mp4> <início_s> [duração_s=10] [folha.jpg]
Grava media/dia-{lente}.mp4 (190° × 180°, 3800 × 3600, HEVC) e a folha de contato do quadro do meio.

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
CAMPO, W, H = 190, 3800, 3600   # 20 px/grau, a resolução da própria lente; passa do teto do H.264, por isso HEVC
PX_GRAU = W / CAMPO
FPS = "30000/1001"
MODELO = os.path.join(bake.CACHE, "modelos", "da2-small.onnx")  # ponytail: o small; o base tem bordas melhores e custa 2,5x
URL_MODELO = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"

# Referências do trecho de 01/11/2026 (caixas x0, y0, x1, y1 num quadro de 3040 × 2880) e vergências (D):
# árvores e poste ao longe, criança e mulher a ~1 m (informadas pelo Dr. Henrique). O livro, a ~30 cm, conta
# como o perto do app (40 cm, 2,5 D), e nada fica mais perto que ele: assim as lentes de perto o mostram nítido.
REF_W, REF_H = 3040, 2880
REFS = [([(500, 1280, 2300, 1440)], 0.03),
        ([(1250, 1630, 1530, 1850), (1710, 1690, 2080, 1930)], 1.0),
        ([(760, 2080, 1960, 2400)], 2.5)]
FAIXAS = np.float32([0.0, 1.0, 1.75, 2.5])  # centros das faixas de vergência (D); a última é o livro
REGIOES = {r: (x * W // REF_W, y * H // REF_H)  # centros dos recortes da folha de contato
           for r, (x, y) in {"longe": (2150, 1300), "intermediário": (1900, 1820), "perto": (1520, 2160)}.items()}


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
    ref = [float(np.median(np.concatenate([disp[y0 * h // REF_H:y1 * h // REF_H, x0 * w // REF_W:x1 * w // REF_W].ravel()
                                           for x0, y0, x1, y1 in caixas]))) for caixas, _ in REFS]
    assert ref[0] < ref[1] < ref[2], f"referências fora de ordem na profundidade estimada: {ref}"
    return np.interp(disp, ref, [v for _, v in REFS]).astype(np.float32)  # além das pontas, fica no valor da ponta


def nucleos():
    """Borrão de cada lente em cada faixa, por escala (1, 2 ou 4): componente de borrão grande dispensa resolução, e o
    componente nítido de uma multifocal fica na escala 1. Cada núcleo já vem pesado pela fração da luz.
    Lente seletiva (lentes.py): onde uma das imagens está em foco, só ela conta."""
    out = {}
    for nome, lente in LENTES.items():
        for i, v in enumerate(FAIXAS):
            borrao = lambda c: bake.psf({**lente, "componentes": [(*c[:2], 1.0)]}, v, PUPILA_MM["dia"], PX_GRAU)
            comps = lente["componentes"]
            if lente.get("seletiva"):
                foco = [c for c in comps if borrao(c) is None]
                comps = [(*c[:2], 1 / len(foco)) for c in foco] or comps
            grupos = {}
            for c in comps:
                k = borrao(c)
                grupos.setdefault(1 if k is None or k.shape[0] < 7 else 2 if k.shape[0] < 11 else 4, []).append(c)
            out[nome, i] = []
            for esc, g in grupos.items():
                k = bake.psf({**lente, "componentes": g}, v, PUPILA_MM["dia"], PX_GRAU / esc)
                out[nome, i].append((esc, np.float32([[sum(c[2] for c in g)]]) if k is None else k))
    for nome in ("multifocal", "perto"):  # decisão de 01/11/2026: a multifocal e o olho de perto leem o livro nítido
        assert [(e, k.tolist()) for e, k in out[nome, len(FAIXAS) - 1]] == [(1, [[1.0]])], f"{nome}: livro borrado"
    return out


def lentes_do_quadro(rgb8, v, nuc, lut, grupo):
    """Soma normalizada das faixas borradas (preenche o que o objeto da frente escondia). Gera (lente, rgb linear), uma por vez.
    Cada escala acumula à parte e só amplia no fim: ampliar é linear, então uma ampliação por lente basta."""
    rgb = lut[rgb8]
    k = np.clip(np.searchsorted(FAIXAS, v) - 1, 0, len(FAIXAS) - 2).astype(np.int8)
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
        for n in grupo:
            for esc, nk in nuc[n, i]:
                if esc not in camada:
                    camada[esc] = cv2.resize(camada[1], (W // esc, H // esc), interpolation=cv2.INTER_AREA)
                b = cv2.filter2D(camada[esc], -1, nk, borderType=cv2.BORDER_REFLECT)
                if (n, esc) in soma:
                    soma[n, esc] += b
                else:
                    soma[n, esc] = b
    for n in grupo:
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


def recortes(img):
    return {r: img[y - 150:y + 150, x - 200:x + 200].copy() for r, (x, y) in REGIOES.items()}


def rascunho(arq):
    """Gravação quase sem perda e com pouca memória (várias ao mesmo tempo); a compressão final vem depois, uma lente por vez."""
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
    nuc = nucleos()
    sessao = ort.InferenceSession(MODELO, providers=["CPUExecutionProvider"])
    t0 = time.time()
    vs = np.stack([vergencia(sessao, q) for q in quadros(trecho, inicio, n)])   # 1ª passada: profundidade
    n = len(vs)
    vs = np.stack([np.median(vs[max(0, i - 2):i + 3], 0) for i in range(n)])     # mediana de 5 quadros no tempo
    print(f"profundidade de {n} quadros em {time.time() - t0:.0f} s", flush=True)
    del sessao
    pasta = tempfile.mkdtemp(prefix="lensvr-")
    np.save(os.path.join(pasta, "vs.npy"), vs)
    vs = np.load(os.path.join(pasta, "vs.npy"), mmap_mode="r")                    # a profundidade fica em disco
    nomes, meio = list(LENTES), {}
    for grupo in (nomes[:3], nomes[3:]):                                          # 2ª passada: óptica, 3 lentes por vez
        enc = {nm: rascunho(os.path.join(pasta, f"{nm}.mkv")) for nm in grupo}    # (as 6 juntas não cabem na memória)
        for i, q in enumerate(quadros(trecho, inicio, n)):
            if i == n // 2 and not meio:
                meio["original"] = recortes(oito_bits(LUT[q]))                    # quadro do meio, para a folha de contato
            for nm, img in lentes_do_quadro(q, cv2.resize(vs[i], (W, H), interpolation=cv2.INTER_LINEAR), nuc, LUT, grupo):
                b = oito_bits(img)
                enc[nm].stdin.write(b.tobytes())
                if i == n // 2:
                    meio[nm] = recortes(b)
            if i % 20 == 0:
                print(f"{grupo[0]} e cia.: quadro {i} em {time.time() - t0:.0f} s", flush=True)
        for p in enc.values():
            p.stdin.close()
            assert p.wait() == 0, "ffmpeg falhou"
    for nm in nomes:                                                              # compressão final, uma lente por vez
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(pasta, f"{nm}.mkv"), "-c:v", "libx265",
                        "-preset", "fast", "-crf", "24", "-tag:v", "hvc1", "-x265-params", "log-level=error",
                        "-movflags", "+faststart", os.path.join(bake.RAIZ, "media", f"dia-{nm}.mp4")], check=True)
    shutil.rmtree(pasta)
    bake.folha_de_contato({"vídeo": meio}, folha)
    print(f"pronto em {time.time() - t0:.0f} s; folha de contato: {folha}")
