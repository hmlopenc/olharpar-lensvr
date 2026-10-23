"""Parâmetros clínicos das lentes: o único arquivo a editar para calibrar o que o paciente vê.

Valores aprovados pelo Dr. Henrique em 23/10/2026 como ponto de partida (tabela da spec).
Depois de editar: python3 tools/bake.py  (regera media/ e a folha de contato).

Componente = (foco em D, faixa nítida em D, fração da luz). Frações de uma lente somam 1.
Desfoque efetivo de um objeto = |vergência do objeto − foco| − faixa (nunca negativo).
Diâmetro do borrão = pupila × desfoque × GANHO.
"""

GANHO = 2.0                             # 1,0 = óptica física; 2,0 compensa a tela do óculos (~20/75)
PUPILA_MM = {"dia": 3.0, "noite": 5.0}

LENTES = {
    "catarata": {
        "componentes": [(0.0, 0.25, 1.0)],
        "desfoque_basal": 0.75,         # D somadas ao desfoque de tudo
        "veu": 0.30,                    # fração da luz espalhada num véu largo (ofuscamento)
        "contraste": 0.70,
        "amarelamento": (1.0, 0.92, 0.70),  # transmissão R, G, B
    },
    "monofocal": {"componentes": [(0.0, 0.25, 1.0)]},
    "edof": {"componentes": [(0.75, 0.75, 0.9), (2.0, 0.25, 0.1)]},
    "multifocal": {"componentes": [(0.0, 0.25, 0.5), (1.5, 0.25, 0.2), (2.5, 0.25, 0.3)]},
    # Monofocal comum num olho com astigmatismo: equivalente esférico no foco, meridianos a ±cilindro/2.
    # Eixo em graus na imagem (0 = horizontal, 90 = vertical); o meridiano do eixo fica em foco − cilindro/2.
    "astig": {"componentes": [(0.0, 0.25, 1.0)], "cilindro": 1.50, "eixo": 90},
    # Olho de perto da monovisão (OE, −1,50 D). O OD usa a monofocal.
    "perto": {"componentes": [(1.5, 0.25, 1.0)]},
}
