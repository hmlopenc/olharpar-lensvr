# 03: Óptica das lentes

**What to build:** Um arquivo único de parâmetros por lente e o processamento que gera, de dia e de noite, as imagens de catarata, monofocal, EDOF, multifocal, astigmatismo sem correção e o olho de perto da monovisão, seguindo o modelo e os valores aprovados da spec. Halos e ofuscamento noturnos surgem do próprio modelo. A entrada são camadas (distância, cor, alfa), para servir tanto à cena sintética quanto às fotos (ticket 05).

**Blocked by:** 01 (formato de 220°)

**Status:** ready-for-agent

- [ ] Parâmetros de todas as lentes num único arquivo
- [ ] Verificações embutidas passam: sem borrão onde a lente foca, borrão crescente com o desfoque, frações somando 1, dimensões das imagens
- [ ] Folha de contato com todas as variantes, revisada visualmente
- [ ] Multifocal mostra halos à noite e a monofocal quase nenhum; catarata mostra véu e amarelamento; astigmatismo borra em elipse
