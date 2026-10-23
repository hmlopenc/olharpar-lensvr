"""Gera as imagens de cada lente: equirretangular parcial de 220° × 180°.

Uso: python3 tools/bake.py [folha_de_contato.jpg]   (grava media/{dia|noite}-{lente}.jpg)
Os parâmetros clínicos ficam em tools/lentes.py. Precisa de numpy, Pillow, scipy e opencv.

MVP sem gravação: o fundo é uma foto 360° HDR real do Poly Haven (CC0, domínio público), baixada uma vez
para ~/.cache/olharpar-lensvr. Na frente, objetos em distâncias exatas: mesa 0,7 m, notebook 0,66 m e
cardápio 0,40 m, com as mesmas letras do kit de gravação (tools/kit-gravacao.html).
Convenção (a mesma do three.js): centro da imagem = +x (frente), +y = cima, +z = direita.
O campo horizontal sai da proporção da imagem: CAMPO = 180 × W / H.
"""
import os, sys, tempfile, urllib.request
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, maximum_filter, zoom
from scipy.signal import oaconvolve
from lentes import GANHO, LENTES, PUPILA_MM

CAMPO = 220            # graus na horizontal; 180 na vertical
W, H = 4096, 3352      # ≈18,6 px/grau, acima dos ~16 px/grau da tela no óculos
FADE = 8               # graus de degradê para o preto em cada borda lateral
PX_GRAU = W / CAMPO
VEU_GRAUS = 3.0        # largura (sigma) do véu da catarata
PT = 0.0352778         # cm por ponto tipográfico
CACHE = os.path.expanduser("~/.cache/olharpar-lensvr")
# Fotos 360° HDR do Poly Haven (CC0): (nome, longitude que fica na frente em graus, exposição)
FUNDOS = {"dia": ("palermo_sidewalk", -10, 1.0), "noite": ("vignaioli_night", -35, 0.5)}
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"   # a fonte do kit de gravação
FONTE_N = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def lin(img):
    """sRGB (PIL) -> linear float."""
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(a):
    """Linear HDR -> sRGB pela curva ACES (aproximação de Narkowicz): os realces rolam suavemente para o branco."""
    a = np.clip(a * (2.51 * a + 0.03) / (a * (2.43 * a + 0.59) + 0.14), 0, 1)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055)


def direcoes():
    lon = ((np.arange(W, dtype=np.float32) + 0.5) / W - 0.5) * np.radians(CAMPO)
    lat = (0.5 - (np.arange(H, dtype=np.float32) + 0.5) / H) * np.pi
    lon, lat = np.meshgrid(lon, lat)
    return np.stack([np.cos(lat) * np.cos(lon), np.sin(lat), np.cos(lat) * np.sin(lon)], -1)


def amostrar(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0, y0 = x.astype(np.int32), y.astype(np.int32)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    top = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    bot = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return top * (1 - fy) + bot * fy


def texto(d, xy, s, tam, cor, negrito=False, anchor="la"):
    d.text(xy, s, font=ImageFont.truetype(FONTE_N if negrito else FONTE, tam), fill=cor, anchor=anchor)


# ---------- texturas (sRGB, desenhadas em alta resolução) ----------

def fundo(cena):
    """Foto 360° HDR recortada em CAMPO graus em torno da frente, em rgb linear."""
    nome, frente, exposicao = FUNDOS[cena]
    arq = os.path.join(CACHE, f"{nome}_8k.hdr")
    if not os.path.exists(arq):
        os.makedirs(CACHE, exist_ok=True)
        urllib.request.urlretrieve(f"https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/8k/{nome}_8k.hdr", arq)
    hdr = cv2.imread(arq, cv2.IMREAD_UNCHANGED)[..., ::-1]           # BGR -> RGB, float32
    w0 = hdr.shape[1]
    hdr = np.roll(hdr, int(round(-frente / 360 * w0)), axis=1)      # a longitude "frente" vai para o centro
    n = int(round(CAMPO / 360 * w0))
    hdr = np.ascontiguousarray(hdr[:, (w0 - n) // 2:(w0 + n) // 2])
    return cv2.resize(hdr, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) * exposicao  # INTER_AREA conserva a energia das luzes


def escrever(d, ppc, x, y, itens, cor, direita=None):
    """Escreve linhas com tamanhos em pontos reais (o mesmo tamanho físico do kit)."""
    for esq, dir_, pt, neg in itens:
        tam = int(pt * PT * ppc)
        texto(d, (x, y), esq, tam, cor, neg)
        if dir_:
            texto(d, (direita, y), dir_, tam, cor, neg, "ra")
        y += int(tam * 1.25)


def notebook(noite):
    """Tela de 30 x 19 cm a 66 cm, com a página 3 do kit. 60 px/cm. A tela emite luz própria."""
    ppc = 60
    img = Image.new("RGB", (30 * ppc, 19 * ppc), (25, 25, 28))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 30 * ppc - 40, 19 * ppc - 40], fill=(250, 250, 248))
    escrever(d, ppc, int(1.2 * ppc), int(1.4 * ppc), [
        ("NOTÍCIAS", "", 79, True), ("Rio: sol, 28 °C", "", 59, False), ("Trânsito livre na Barra", "", 46, False),
        ("Feira orgânica no sábado, 8h", "", 36, False), ("Cinema: sessão especial às 19h30", "", 30, False),
        ("Previsão: chuva fraca no fim da tarde de domingo", "", 23, False)], (20, 20, 30))
    return img


def cardapio(noite):
    """Cardápio de 15 x 21 cm a 40 cm, na mão, com as linhas da página 2 do kit. 60 px/cm."""
    ppc = 60
    img = Image.new("RGB", (15 * ppc, 21 * ppc), (246, 239, 225))
    d = ImageDraw.Draw(img)
    texto(d, (15 * ppc // 2, int(2.4 * ppc)), "CARDÁPIO", int(72 * PT * ppc), (27, 27, 27), True, "ma")
    escrever(d, ppc, int(0.6 * ppc), int(6 * ppc), [
        ("Expresso", "R$ 6", 48, False), ("Pão de queijo", "R$ 8", 36, False), ("Suco de laranja", "R$ 10", 28, False),
        ("Misto quente na chapa", "R$ 14", 22, False), ("Tapioca com queijo coalho", "R$ 16", 18, False),
        ("Pergunte pelas opções sem glúten e sem lactose.", "", 14, False)], (27, 27, 27), int(14.4 * ppc))
    return img


# ---------- geometria ----------

def cartao(D, centro, largura, altura, tex_rgb, ganho):
    """Retângulo virado para a câmera. Devolve (rgb linear, alfa)."""
    c = np.asarray(centro, np.float32)
    f = c / np.linalg.norm(c)
    r = np.cross(f, [0, 1, 0]).astype(np.float32)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    dn = D @ -f
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (c @ -f) / dn
    p = D * t[..., None] - c
    a, b = p @ r, p @ u
    dentro = (t > 0) & (np.abs(a) < largura / 2) & (np.abs(b) < altura / 2)
    # pré-filtra a textura para ~2x a resolução que ela terá na imagem (anti-serrilhado)
    alvo = int(2 * np.degrees(2 * np.arctan(largura / 2 / np.linalg.norm(c))) * W / CAMPO)
    esc = alvo / tex_rgb.width
    tam = (alvo, max(2, int(tex_rgb.height * esc)))
    tex = lin(tex_rgb.resize(tam, Image.LANCZOS)) * ganho
    rgb = np.zeros(D.shape, np.float32)
    th, tw = tex.shape[:2]
    rgb[dentro] = amostrar(tex, (a[dentro] / largura + 0.5) * tw, (0.5 - b[dentro] / altura) * th)
    return rgb, dentro.astype(np.float32)


def mesa(D, noite):
    """Tampo a 45 cm abaixo dos olhos, x[0.25,1.0] z[-0.7,0.7]."""
    with np.errstate(divide="ignore", invalid="ignore"):
        t = -0.45 / D[..., 1]
    p = D * t[..., None]
    dentro = (t > 0) & (p[..., 0] > 0.25) & (p[..., 0] < 1.0) & (np.abs(p[..., 2]) < 0.7)
    x, z = p[..., 0], p[..., 2]
    veio = 0.85 + 0.15 * np.sin(z * 90 + 3 * np.sin(x * 7 + z * 11))       # veios da madeira
    veio = np.where(np.abs((z / 0.14) % 1 - 0.5) > 0.485, 0.45, veio)        # frestas entre tábuas de 14 cm
    rgb = np.zeros(D.shape, np.float32)
    rgb[dentro] = np.array((0.20, 0.12, 0.065), np.float32) * veio[dentro, None] * (0.06 if noite else 0.9)
    return rgb, dentro.astype(np.float32)


def posicao(dist, azim, elev):
    a, e = np.radians(azim), np.radians(elev)
    return (dist * np.cos(e) * np.cos(a), dist * np.sin(e), dist * np.cos(e) * np.sin(a))


def construir_cena(noite):
    """Camadas da mais distante para a mais próxima: (distância em m, rgb linear, alfa)."""
    D = direcoes()
    return [
        (10.0, fundo("noite" if noite else "dia"), np.ones((H, W), np.float32)),  # ponytail: o fundo inteiro conta
        (0.7, *mesa(D, noite)),                                                    # como longe (10 m); a mesa cobre o chão
        (0.66, *cartao(D, posicao(0.66, 25, -32), 0.30, 0.19, notebook(noite), 0.9)),  # perto da câmera
        (0.40, *cartao(D, posicao(0.40, -12, -30), 0.15, 0.21, cardapio(noite), 0.15 if noite else 0.9)),
    ]


def compor(camadas):
    out = np.zeros((H, W, 3), np.float32)
    for _, rgb, a in camadas:
        out = out * (1 - a[..., None]) + rgb * a[..., None]
    return out


# ---------- óptica ----------

def disco(d_eixo, d_perp, eixo=0.0):
    """Borrão em disco normalizado; elipse quando os diâmetros (px) diferem. eixo: graus, anti-horário na imagem.
    Menor que 1 px nos dois sentidos = nítido (None)."""
    if max(d_eixo, d_perp) < 1:
        return None
    r = int(np.ceil(max(d_eixo, d_perp) / 2))
    o = (np.arange(4) + 0.5) / 4 - 0.5                        # 4 x 4 subamostras por pixel: borda suave
    y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    X, Y = x[..., None, None] + o, y[..., None, None] + o[:, None]
    c, s = np.cos(np.radians(eixo)), np.sin(np.radians(eixo))
    a, b = X * c - Y * s, X * s + Y * c                         # ao longo do eixo e perpendicular (y da imagem desce)
    k = ((a / max(d_eixo / 2, .5)) ** 2 + (b / max(d_perp / 2, .5)) ** 2 <= 1).mean((-2, -1))
    return (k / k.sum()).astype(np.float32)


def psf(lente, V, pupila_mm):
    """Borrão de um objeto com vergência V (D): soma dos componentes pesados pela fração da luz. None = nítido."""
    px_por_D = pupila_mm / 1000 * GANHO * np.degrees(1) * PX_GRAU
    basal, cil, eixo = lente.get("desfoque_basal", 0.0), lente.get("cilindro", 0.0), lente.get("eixo", 0)
    d = lambda foco, faixa: (max(0.0, abs(V - foco) - faixa) + basal) * px_por_D
    partes = [(fr, disco(d(f - cil / 2, fx), d(f + cil / 2, fx), eixo)) for f, fx, fr in lente["componentes"]]
    if all(k is None for _, k in partes):
        return None
    r = max(k.shape[0] // 2 for _, k in partes if k is not None)
    total = np.zeros((2 * r + 1,) * 2, np.float32)
    for fr, k in partes:
        m = 0 if k is None else k.shape[0] // 2
        total[r - m:r + m + 1, r - m:r + m + 1] += fr * (1 if k is None else k)
    return total


def borrar(pre, k):
    """Convolução só onde a camada existe, mais a margem do borrão."""
    r = k.shape[0] // 2
    ys, xs = np.nonzero(pre[..., 3])
    if ys.size == 0:
        return pre
    y0, y1, x0, x1 = max(ys.min() - r, 0), min(ys.max() + r + 1, H), max(xs.min() - r, 0), min(xs.max() + r + 1, W)
    out = np.zeros_like(pre)
    out[y0:y1, x0:x1] = oaconvolve(pre[y0:y1, x0:x1], k[..., None], mode="same", axes=(0, 1))
    return out


def desfocar(camadas, lente, pupila_mm):
    """Borra cada camada pelo seu desfoque (rgb pré-multiplicado e alfa) e empilha da mais distante para a mais próxima."""
    out = np.zeros((H, W, 3), np.float32)
    for dist, rgb, a in camadas:
        pre = np.concatenate([rgb * a[..., None], a[..., None]], -1)
        k = psf(lente, 1 / dist, pupila_mm)
        if k is not None:
            pre = borrar(pre, k)
        out = out * (1 - pre[..., 3:]) + pre[..., :3]
    return out


def catarata(img, lente):
    """Véu, contraste e amarelamento. Lentes sem esses campos passam intactas."""
    v = lente.get("veu", 0.0)
    if v:  # espalhamento largo, calculado em 1/8 da resolução (o véu é liso)
        p = 8
        peq = img.reshape(H // p, p, W // p, p, 3).mean((1, 3))
        peq = gaussian_filter(peq, (VEU_GRAUS * PX_GRAU / p,) * 2 + (0,), mode="nearest")
        img = (1 - v) * img + v * zoom(peq, (p, p, 1), order=1)
    c = lente.get("contraste", 1.0)
    img = c * img + (1 - c) * img.mean((0, 1))
    return img * np.asarray(lente.get("amarelamento", (1, 1, 1)), np.float32)


def verificar(cena, imgs, nitida, rua):
    for nome, l in LENTES.items():
        assert abs(sum(c[2] for c in l["componentes"]) - 1) < 1e-6, f"{nome}: frações devem somar 1"
    assert all(i.shape == (H, W, 3) for i in imgs.values()), "dimensões"
    assert np.allclose(imgs["monofocal"][rua], nitida[rua], atol=1e-5), "a monofocal não pode borrar o longe"
    tam = [0 if (k := disco(d, d)) is None else k.shape[0] for d in (0.5, 3, 8, 20)]
    assert tam == sorted(tam) and tam[-1] > tam[1], "o borrão precisa crescer com o desfoque"
    k = psf(LENTES["astig"], 2.5, PUPILA_MM[cena])
    assert (k.sum(1) > 0).sum() > (k.sum(0) > 0).sum(), "astigmatismo a 90° borra mais na vertical de perto"
    cat, mono = imgs["catarata"], imgs["monofocal"]
    assert cat[..., 2].mean() / cat[..., 0].mean() < mono[..., 2].mean() / mono[..., 0].mean(), "catarata amarela"
    assert cat.std() < mono.std(), "catarata com menos contraste"
    if cena == "noite":  # halo: brilho num anel em volta das luzes intensas
        luz = nitida.max(-1) > 50  # núcleos das lâmpadas; fachadas iluminadas ficam abaixo disso
        anel = maximum_filter(luz, 25) & ~maximum_filter(luz, 7)
        brilho = lambda n: imgs[n].max(-1)[anel].mean()
        assert brilho("multifocal") > 1.5 * brilho("monofocal"), "a multifocal precisa de halo à noite"


def degrade(rgb):
    """Escurece as bordas laterais nos últimos FADE graus: a imagem some no preto, sem quina."""
    lon = np.abs((np.arange(W) + 0.5) / W - 0.5) * CAMPO
    f = np.clip((CAMPO / 2 - lon) / FADE, 0, 1)
    return rgb * (f * f * (3 - 2 * f))[None, :, None]


def oito_bits(rgb):
    return (srgb(rgb) * 255 + 0.5).astype(np.uint8)


def salvar(rgb, nome):
    os.makedirs(os.path.join(RAIZ, "media"), exist_ok=True)
    Image.fromarray(oito_bits(degrade(rgb))).save(os.path.join(RAIZ, "media", nome), quality=90)


def folha_de_contato(recortes, caminho, w=400, h=300):
    """Uma linha por lente; colunas = cena × região, em 1:1, para comparar nitidez e halos."""
    colunas = [(cena, regiao) for cena in recortes for regiao in recortes[cena]["nítida"]]
    linhas = list(recortes["dia"])
    folha = Image.new("RGB", (150 + w * len(colunas), 34 + h * len(linhas)), (255, 255, 255))
    d = ImageDraw.Draw(folha)
    fonte = ImageFont.truetype(FONTE, 20)
    for j, (cena, regiao) in enumerate(colunas):
        d.text((150 + j * w + 8, 6), f"{cena} · {regiao}", fill=(0, 0, 0), font=fonte)
        for i, lente in enumerate(linhas):
            folha.paste(Image.fromarray(recortes[cena][lente][regiao]), (150 + j * w, 34 + i * h))
    for i, lente in enumerate(linhas):
        d.text((8, 34 + i * h + h // 2), lente, fill=(0, 0, 0), font=fonte)
    folha.save(caminho, quality=90)


if __name__ == "__main__":
    folha = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "folha-de-contato.jpg")
    perto = {"intermediário": (2486, 2235), "perto": (1825, 2160)}  # centros dos recortes em px
    regioes = {"dia": {"longe": (2700, 1620), **perto}, "noite": {"longe": (2700, 1500), **perto}}
    recortes = {}
    for cena, noite in (("dia", False), ("noite", True)):
        camadas = construir_cena(noite)
        nitida = compor(camadas)
        # autoverificação da cena: fundo cobrindo tudo, cardápio onde foi posto, luzes intensas à noite
        assert camadas[0][2].min() == 1, "o fundo deve cobrir a imagem inteira"
        lon, lat = int((0.5 - 12 / CAMPO) * W), int((0.5 + 30 / 180) * H)
        assert camadas[-1][2][lat, lon] == 1, "o cardápio deve estar a 12° à esquerda e 30° abaixo"
        assert (nitida.max(-1) > 5).sum() > (100 if noite else -1), "a cena noturna precisa de luzes intensas"
        imgs = {nome: catarata(desfocar(camadas, l, PUPILA_MM[cena]), l) for nome, l in LENTES.items()}
        longe = ~maximum_filter(sum(a for _, _, a in camadas[1:]) > 0, 61)  # só fundo, longe das bordas dos objetos
        verificar(cena, imgs, nitida, longe)
        for nome, img in imgs.items():
            salvar(img, f"{cena}-{nome}.jpg")
        recortes[cena] = {n: {r: oito_bits(i[y - 150:y + 150, x - 200:x + 200]) for r, (x, y) in regioes[cena].items()}
                          for n, i in {"nítida": nitida, **imgs}.items()}
        print(cena, "ok")
    folha_de_contato(recortes, folha)
    print("folha de contato:", folha)
