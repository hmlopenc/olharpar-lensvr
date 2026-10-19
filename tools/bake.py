"""Gera as imagens 360° (equiretangulares) da cena sintética.

Uso: python3 tools/bake.py   (grava em media/)

A cena é uma sala vista de quem está sentado, com camadas em distâncias conhecidas:
rua a 6 m, sala ~3 m, mesa 0,7 m, notebook 0,66 m, cardápio 0,40 m.
Convenção (a mesma do three.js): centro da imagem = +x (frente), +y = cima, +z = direita.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 4096, 2048  # shortcut: 11 px/grau, abaixo da tela do S23 Ultra; subir para 6K se o aparelho aguentar
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTE_N = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def lin(img):
    """sRGB (PIL) -> linear float."""
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(a):
    a = np.clip(a / np.maximum(1, a.max(-1, keepdims=True)), 0, 1)  # satura preservando a cor (neon continua colorido)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055)


def direcoes():
    lon = ((np.arange(W, dtype=np.float32) + 0.5) / W - 0.5) * 2 * np.pi
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
        e.rectangle([700, 420, 1300, 880], fill=70)
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
    alvo = int(2 * np.degrees(2 * np.arctan(largura / 2 / np.linalg.norm(c))) * W / 360)
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


def salvar(rgb, nome):
    os.makedirs(os.path.join(RAIZ, "media"), exist_ok=True)
    Image.fromarray((srgb(rgb) * 255 + 0.5).astype(np.uint8)).save(os.path.join(RAIZ, "media", nome), quality=90)


if __name__ == "__main__":
    for cena, noite in (("manha", False), ("noite", True)):
        camadas = construir_cena(noite)
        img = compor(camadas)
        # autoverificação: frente = rua, cardápio onde foi posto, luzes à noite
        assert img.shape == (H, W, 3)
        assert camadas[0][2][H // 2 - 20, W // 2] == 1, "o centro da imagem deve mostrar a rua"
        lon, lat = int((0.5 - 12 / 360) * W), int((0.5 + 30 / 180) * H)
        assert camadas[4][2][lat, lon] == 1, "o cardápio deve estar a 12° à esquerda e 30° abaixo"
        assert (img.max(-1) > 1).sum() > (100 if noite else -1), "a cena noturna precisa de luzes intensas"
        salvar(img, f"{cena}-nitida.jpg")
        print(cena, "ok")
