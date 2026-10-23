# 05: Cenas reais (fotos da X6, depois do MVP)

**What to build:** Transformar as fotos do café (dia) e do carro (noite) nas imagens das lentes, no lugar dos fundos do Poly Haven do MVP. Junta as 3 exposições em HDR, recorta 220° × 180° com a cena no centro, estima a profundidade com um modelo monocular métrico ajustado às medidas da trena, fatia em camadas por dioptria e passa pela óptica do ticket 03.

**Blocked by:** 03 e as fotos (roteiro em `tools/kit-gravacao.html`)

**Status:** blocked

- [ ] Foto-teste a 40 cm conferida (nitidez da X6 de perto)
- [ ] HDR da noite preserva a intensidade das luzes (o halo aparece na multifocal)
- [ ] Profundidade nos objetos medidos dentro de ±10% da trena
- [ ] Folha de contato com as cenas reais revisada
- [ ] Imagens `media/{dia|noite}-*.jpg` substituídas e testadas no óculos
