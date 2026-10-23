"""Gera as imagens de cada lente a partir da cena sintética: equirretangular parcial de 220° × 180°.

Uso: python3 tools/bake.py [folha_de_contato.jpg]   (grava media/{dia|noite}-{lente}.jpg)
Os parâmetros clínicos ficam em tools/lentes.py.

A cena é uma sala vista de quem está sentado, com camadas em distâncias conhecidas:
rua a 6 m, sala ~3 m, mesa 0,7 m, notebook 0,66 m, cardápio 0,40 m.
Convenção (a mesma do three.js): centro da imagem = +x (frente), +y = cima, +z = direita.
O campo horizontal sai da proporção da imagem: CAMPO = 180 × W / H.
"""
import os, sys, tempfile
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
OMBRO = (0.7, 40.0)    # noite: acima de 0,7 comprime em log até a luz mais forte (40); o halo aparece como disco
                       # mais fraco em volta da luz, em vez de tudo saturar em branco
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTE_N = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def lin(img):
    """sRGB (PIL) -> linear float."""
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(a, noite=False):
    if noite:  # comprime os realces pela luminância máxima do pixel, preservando a cor
        k, L = OMBRO
        m = np.maximum(a.max(-1, keepdims=True), 1e-6)
        a = a * np.where(m > k, k + (1 - k) * np.log1p(np.maximum(m - k, 0) / 0.5) / np.log1p((L - k) / 0.5), m) / m
    a = np.clip(a / np.maximum(1, a.max(-1, keepdims=True)), 0, 1)  # satura preservando a cor (neon continua colorido)
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

def fachada(noite):
    """Frente da sala aberta para a rua: 5 m x 2,7 m a 6 m. 400 px/m."""
    ppm = 400
    img = Image.new("RGB", (5 * ppm, int(2.7 * ppm)), (52, 58, 74) if noite else (196, 186, 168))
    em = Image.new("L", img.size, 0)  # emissão noturna: intensidade = 40 * (valor/255)^2
    d, e = ImageDraw.Draw(img), ImageDraw.Draw(em)
    # calçada e vitrines
    d.rectangle([0, 920, 2000, 1080], fill=(40, 40, 44) if noite else (150, 150, 150))
    for x0, x1 in ((80, 900), (1100, 1920)):
        d.rectangle([x0, 380, x1, 900], fill=(90, 70, 40) if noite else (120, 150, 170))
        e.rectangle([x0, 380, x1, 900], fill=60 if noite else 0)
    # letreiros (0,35 m e 0,30 m)
    d.rectangle([120, 120, 860, 320], fill=(30, 30, 30) if noite else (250, 240, 220))
    texto(d, (490, 220), "PADARIA", 160, (255, 170, 60) if noite else (120, 40, 20), True, "mm")
    if noite:
        texto(e, (490, 220), "PADARIA", 160, 160, True, "mm")
    d.rectangle([1140, 140, 1880, 300], fill=(20, 40, 25) if noite else (255, 255, 255))
    texto(d, (1510, 220), "FARMÁCIA", 120, (80, 255, 120) if noite else (20, 120, 50), True, "mm")
    if noite:
        texto(e, (1510, 220), "FARMÁCIA", 120, 160, True, "mm")
    # painel do ponto de ônibus: linhas de 15, 8, 5 e 3,5 cm
    d.rectangle([700, 420, 1300, 880], fill=(245, 245, 240))
    if noite:
        e.rectangle([700, 420, 1300, 880], fill=38)  # painel iluminado ~0,9: superfície legível, não fonte de luz
    y = 440
    for linha, cm in (("LINHA 309", 15), ("Recreio  10 min", 8), ("Barra  15 min  ·  Tijuca  25 min", 5),
                      ("Horários sujeitos a alteração", 3.5)):
        texto(d, (1000, y), linha, int(cm * 4 / 0.73), (20, 20, 20), cm >= 8, "ma")
        y += int(cm * 4 / 0.73 * 1.35)
    if noite:  # postes e faróis: fontes pequenas e muito intensas
        for x, yy, r in ((60, 60, 14), (1940, 60, 14), (420, 980, 16), (560, 980, 16)):
            d.ellipse([x - r, yy - r, x + r, yy + r], fill=(255, 240, 210))
            e.ellipse([x - r, yy - r, x + r, yy + r], fill=255)
    return img, em


def notebook(noite):
    """Tela de 30 x 19 cm a 66 cm. 60 px/cm. A tela emite luz própria."""
    ppc = 60
    img = Image.new("RGB", (30 * ppc, 19 * ppc), (25, 25, 28))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 30 * ppc - 40, 19 * ppc - 40], fill=(250, 250, 248))
    y = 70
    for linha, cm, neg in (("Notícias", 2, True), ("Rio de Janeiro: sol com nuvens, 28 °C", 1, False),
                           ("Trânsito livre na Avenida das Américas", 0.6, False),
                           ("Feira de artesanato no domingo, das 9 h às 17 h", 0.4, False)):
        texto(d, (100, y), linha, int(cm * ppc / 0.73), (20, 20, 30), neg)
        y += int(cm * ppc / 0.73 * 1.5)
    return img


def cardapio(noite):
    """Cardápio de 15 x 21 cm a 40 cm, na mão. 60 px/cm."""
    ppc = 60
    img = Image.new("RGB", (15 * ppc, 21 * ppc), (252, 248, 236))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 15 * ppc - 20, 21 * ppc - 20], outline=(120, 80, 40), width=8)
    y = 70
    for linha, cm, neg in (("CARDÁPIO", 1.5, True), ("Café expresso   R$ 6", 0.6, False),
                           ("Pão de queijo   R$ 8", 0.6, False), ("Suco de laranja   R$ 10", 0.6, False),
                           ("Pergunte pelas opções sem glúten", 0.35, False),
                           ("Aceitamos cartões e Pix", 0.25, False)):
        texto(d, (15 * ppc // 2, y), linha, int(cm * ppc / 0.73), (40, 25, 15), neg, "ma")
        y += int(cm * ppc / 0.73 * 1.7)
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


def sala(D, noite):
    """Caixa x[-3,6] y[-1.2,1.5] z[-2.5,2.5]. Devolve as camadas (rua, sala)."""
    lim = ((-3.0, 6.0), (-1.2, 1.5), (-2.5, 2.5))
    t = np.full(D.shape[:2], np.inf, np.float32)
    face = np.zeros(D.shape[:2], np.int8)
    with np.errstate(divide="ignore", invalid="ignore"):
        for i, (lo, hi) in enumerate(lim):
            for k, b in ((0, lo), (1, hi)):
                ti = b / D[..., i]
                m = (ti > 0) & (ti < t)
                t[m], face[m] = ti[m], 2 * i + k
    p = D * t[..., None]
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    luz = 0.05 if noite else 1.0
    rgb = np.zeros(D.shape, np.float32)
    cor = {0: (0.42, 0.36, 0.30), 2: (0.20, 0.16, 0.13), 3: (0.70, 0.70, 0.68), 4: (0.50, 0.44, 0.36), 5: (0.48, 0.42, 0.35)}
    for f, c in cor.items():
        rgb[face == f] = np.array(c, np.float32) * luz
    chao = face == 2  # piso em ladrilhos de 50 cm com rejunte
    rejunte = (np.abs((x / 0.5) % 1 - 0.5) > 0.47) | (np.abs((z / 0.5) % 1 - 0.5) > 0.47)
    xadrez = ((np.floor(x / 0.5) + np.floor(z / 0.5)) % 2 == 0)
    rgb[chao & xadrez] *= 1.35
    rgb[chao & rejunte] = np.array((0.08, 0.08, 0.08), np.float32) * luz
    rodape = np.isin(face, (0, 4, 5)) & (y < -1.08)
    rgb[rodape] = np.array((0.12, 0.10, 0.09), np.float32) * luz
    if noite:  # luminária pendente no teto, à esquerda
        lamp = (face == 3) & ((x - 1.0) ** 2 + (z + 1.2) ** 2 < 0.06 ** 2)
        rgb[lamp] = 30.0
    frente = face == 1
    img, em = fachada(noite)
    tex = lin(img) * ((0.10 if noite else 1.0) + 40 * ((np.asarray(em, np.float32) / 255) ** 2)[..., None])
    th, tw = tex.shape[:2]
    rua = np.zeros(D.shape, np.float32)
    rua[frente] = amostrar(tex, (z[frente] + 2.5) / 5 * tw, (1.5 - y[frente]) / 2.7 * th)
    return (rua, frente.astype(np.float32)), (rgb, (~frente).astype(np.float32))


def mesa(D, noite):
    """Tampo a 45 cm abaixo dos olhos, x[0.25,1.0] z[-0.7,0.7]."""
    with np.errstate(divide="ignore", invalid="ignore"):
        t = -0.45 / D[..., 1]
    p = D * t[..., None]
    dentro = (t > 0) & (p[..., 0] > 0.25) & (p[..., 0] < 1.0) & (np.abs(p[..., 2]) < 0.7)
    rgb = np.zeros(D.shape, np.float32)
    rgb[dentro] = np.array((0.30, 0.17, 0.08), np.float32) * (0.06 if noite else 1.0)
    return rgb, dentro.astype(np.float32)


def posicao(dist, azim, elev):
    a, e = np.radians(azim), np.radians(elev)
    return (dist * np.cos(e) * np.cos(a), dist * np.sin(e), dist * np.cos(e) * np.sin(a))


def construir_cena(noite):
    """Camadas da mais distante para a mais próxima: (distância em m, rgb linear, alfa)."""
    D = direcoes()
    rua, sala_ = sala(D, noite)
    nb_img, cd_img = notebook(noite), cardapio(noite)
    return [
        (6.0, *rua),
        (3.0, *sala_),
        (0.7, *mesa(D, noite)),
        (0.66, *cartao(D, posicao(0.66, 25, -32), 0.30, 0.19, nb_img, 0.9)),
        (0.40, *cartao(D, posicao(0.40, -12, -30), 0.15, 0.21, cd_img, 0.30 if noite else 0.9)),
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
        luz = nitida.max(-1) > 5
        anel = maximum_filter(luz, 25) & ~maximum_filter(luz, 7)
        brilho = lambda n: imgs[n].max(-1)[anel].mean()
        assert brilho("multifocal") > 1.5 * brilho("monofocal"), "a multifocal precisa de halo à noite"


def degrade(rgb):
    """Escurece as bordas laterais nos últimos FADE graus: a imagem some no preto, sem quina."""
    lon = np.abs((np.arange(W) + 0.5) / W - 0.5) * CAMPO
    f = np.clip((CAMPO / 2 - lon) / FADE, 0, 1)
    return rgb * (f * f * (3 - 2 * f))[None, :, None]


def oito_bits(rgb, noite=False):
    return (srgb(rgb, noite) * 255 + 0.5).astype(np.uint8)


def salvar(rgb, nome, noite=False):
    os.makedirs(os.path.join(RAIZ, "media"), exist_ok=True)
    Image.fromarray(oito_bits(degrade(rgb), noite)).save(os.path.join(RAIZ, "media", nome), quality=90)


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
    regioes = {"longe": (2048, 1620), "intermediário": (2513, 2272), "perto": (1825, 2086)}  # centros em px
    recortes = {}
    for cena, noite in (("dia", False), ("noite", True)):
        camadas = construir_cena(noite)
        nitida = compor(camadas)
        # autoverificação da cena: frente = rua, cardápio onde foi posto, luzes à noite
        assert camadas[0][2][H // 2 - 20, W // 2] == 1, "o centro da imagem deve mostrar a rua"
        lon, lat = int((0.5 - 12 / CAMPO) * W), int((0.5 + 30 / 180) * H)
        assert camadas[4][2][lat, lon] == 1, "o cardápio deve estar a 12° à esquerda e 30° abaixo"
        assert (nitida.max(-1) > 1).sum() > (100 if noite else -1), "a cena noturna precisa de luzes intensas"
        imgs = {nome: catarata(desfocar(camadas, l, PUPILA_MM[cena]), l) for nome, l in LENTES.items()}
        verificar(cena, imgs, nitida, camadas[0][2] == 1)
        for nome, img in imgs.items():
            salvar(img, f"{cena}-{nome}.jpg", noite)
        recortes[cena] = {n: {r: oito_bits(i[y - 150:y + 150, x - 200:x + 200], noite) for r, (x, y) in regioes.items()}
                          for n, i in {"nítida": nitida, **imgs}.items()}
        print(cena, "ok")
    folha_de_contato(recortes, folha)
    print("folha de contato:", folha)
