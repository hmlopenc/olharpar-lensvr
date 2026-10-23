# Spec — Simulador VR de lentes intraoculares (OlharPar)

## Problema

O paciente de catarata precisa escolher entre lentes (monofocal, EDOF, multifocal, tórica, monovisão) sem conseguir imaginar como vai enxergar com cada uma. Explicações verbais e folhetos não mostram a diferença entre longe, intermediário e perto, nem os halos noturnos. O app anterior (LensVR) ficou instável e simulava a óptica com filtros que borram a imagem inteira por igual, o que não diferencia as distâncias.

## Solução

Um simulador em óculos VR de encaixar celular. O paciente olha ao redor de uma cena real de ~220° e vê, capítulo por capítulo, como enxergaria com catarata e depois com cada lente, de dia e à noite. A secretária escolhe as lentes antes de encaixar o celular e a sequência roda sozinha.

- **MVP (sem gravação):** fotos 360° HDR de domínio público do Poly Haven (CC0): uma rua em Palermo de dia (`palermo_sidewalk`) e uma praça em Vignaioli à noite (`vignaioli_night`). Na frente, mesa, cardápio e notebook sintéticos em distâncias exatas, com as letras do kit. Narração do Dr. Henrique em áudio quando gravada.
- **Depois do MVP:** fotos da Insta360 X6 (café na calçada de dia, carro parado à noite), ticket 05.
- **Produto final:** vídeo da X6 no lugar das fotos, com a mesma óptica aplicada quadro a quadro.

## User stories

1. Como secretária, quero marcar quais lentes mostrar antes de encaixar o celular, para adaptar a demonstração a cada paciente.
2. Como secretária, quero um único botão para iniciar, com contagem regressiva, para ter tempo de encaixar o celular no óculos.
3. Como paciente, quero olhar ao redor movendo a cabeça, para me sentir dentro da cena.
4. Como paciente, quero ver primeiro como enxergo com catarata, para ter uma referência.
5. Como paciente, quero ver as lentes uma após a outra na mesma cena, para perceber a diferença em longe, intermediário e perto.
6. Como paciente, quero ver a comparação à noite, para entender os halos e o ofuscamento de cada lente.
7. Como paciente, quero ver uma lente comum com astigmatismo e depois a tórica corrigindo, para entender por que a tórica existe.
8. Como paciente, quero ver a monovisão com um olho para longe e outro para perto, para sentir como os dois olhos se combinam.
9. Como paciente, quero ver o nome do capítulo no início, para saber o que estou vendo.
10. Como médico, quero configurar o óculos uma vez por aparelho, para a imagem ficar confortável e sem distorção.
11. Como médico, quero ajustar o desfoque e os halos de cada lente num único arquivo, para calibrar clinicamente o que o paciente vê.
12. Como médico, quero que a tela fique cheia, na horizontal e sem apagar durante a experiência.
13. Como médico, quero que o app volte à tela inicial no fim, pronto para o próximo paciente.
14. Como médico, quero publicar atualizações sem instalar nada nos aparelhos.
15. Como paciente, quero ouvir o Dr. Henrique explicando cada capítulo.

## Decisões de implementação

**Plataforma**
- Página web estática, sem React e sem etapa de build. three.js carregado por CDN. Publicada no GitHub Pages, repositório `olharpar-lensvr`.
- WebXR (`immersive-vr`) pelo `renderer.xr` do three.js. No Chrome Android o WebXR usa o Cardboard SDK, ativado por padrão, que cuida de rastrear a cabeça, do estéreo, da tela cheia e da correção da distorção das lentes pelo perfil do óculos. O perfil é um QR code escaneado uma vez por aparelho; se o óculos não trouxer, gera-se um no gerador de perfis do Google. Sem calibração própria no app.
- Aparelho-alvo: Galaxy S23 Ultra no Chrome, com a tela em WQHD+ (de fábrica vem em FHD+). O Fold 7 fica como aparelho de teste secundário. O mesmo link roda num Meta Quest.
- Óculos do MVP: Shinecon SC-G15E (ajuste de IPD e de foco, almofada de PU). Não há óculos de celular premium à venda no Brasil (pesquisa de 23/10/2026). Antes de comprar mais, testar o encaixe do S23 Ultra sem capa (163,4 mm). Os fones do óculos pedem adaptador USB-C.
- Aviso "Simulação ilustrativa. Os resultados variam de pessoa para pessoa." na tela inicial.

**Visualização**
- Imagem monoscópica (a X6 não grava em 3D) numa esfera parcial de 220° × 180°, centrada na frente. O campo sai da proporção da própria imagem (largura ÷ altura × 180°), então o app não repete a constante. A borda lateral some num degradê gravado na imagem.
- Uma malha por olho (camadas 1 e 2 do three.js), o que viabiliza a monovisão. Nos demais capítulos as duas usam a mesma textura.
- Contagem e nome do capítulo presos à cabeça, desenhados em 3D: no `immersive-vr` não existe HTML sobreposto.
- A visão é recentralizada ao fim da contagem: a cena gira para a direção da cabeça.
- Sem WebXR (computador, teste headless), a mesma experiência roda na tela, olhando para a frente.

**Óptica (fora do app)**
- O app não calcula desfoque. Um script gera as imagens de cada lente e o app só troca as imagens.
- A entrada do script são camadas (distância, cor linear, alfa), da mais distante para a mais próxima. No MVP, a foto HDR inteira conta como longe (10 m) e os objetos da frente têm distância exata; nas fotos da X6, as camadas virão do mapa de profundidade fatiado em dioptrias.
- Saída pela curva de tom ACES: os realces rolam suavemente para o branco, e as luzes fortes continuam acima do branco antes do borrão, o que gera o halo.
- Modelo: cada lente é um conjunto de componentes (foco em dioptrias, faixa nítida em torno do foco, fração da luz). O desfoque efetivo de um objeto é a distância dióptrica até o foco, menos a faixa. O tamanho do borrão é pupila × desfoque × ganho. À noite as luzes têm alta intensidade, de modo que os halos surgem do próprio desfoque (a parte da luz que a lente desvia para perto aparece como halo em volta das luzes de longe).
- A catarata soma um véu de espalhamento, perda de contraste e amarelamento. O astigmatismo usa um borrão elíptico: o equivalente esférico fica no foco e os dois meridianos principais a ±C/2 dele.
- Ganho inicial 2,0 (1,0 = óptica física). Motivo: a tela do óculos não mostra nada mais fino que ~20/75, então o desfoque precisa crescer na mesma proporção para manter as diferenças entre as lentes. Por isso os textos de perto e intermediários das fotos são impressos 2× maiores que o normal: com ganho 2,0, a proporção entre borrão e letra fica igual à da vida real. Calibrado pelo médico olhando no óculos.

Valores iniciais, aprovados pelo Dr. Henrique em 23/10/2026 como ponto de partida (vergência no plano dos óculos; longe ≈ 0 D, intermediário 1,5 D, perto 2,5 D; pupila 3 mm de dia e 5 mm à noite):

| Lente | Componentes (foco D · faixa D · fração) | Extra |
|---|---|---|
| Catarata (antes) | 0 · 0,25 · 1,0 | desfoque basal 0,75 D, véu 30%, contraste 70%, amarelamento |
| Monofocal | 0 · 0,25 · 1,0 | — |
| EDOF | 0,75 · 0,75 · 0,9 + 2,0 · 0,25 · 0,1 | — |
| Multifocal (trifocal) | 0 · 0,25 · 0,5 + 1,5 · 0,25 · 0,2 + 2,5 · 0,25 · 0,3 | — |
| Tórica: sem correção | 0 · 0,25 · 1,0 | astigmatismo residual 1,50 D a 90° |
| Tórica: corrigida | igual à monofocal | — |
| Monovisão | OD: 0 · 0,25 · 1,0 / OE: 1,5 · 0,25 · 1,0 (−1,50 D) | imagem diferente por olho |

- Imagens em 4096 × 3352 (220° × 180°, ≈18,6 px/grau, acima dos ~16 px/grau da tela no óculos). Nomes: `media/{dia|noite}-{catarata|monofocal|edof|multifocal|astig|perto}.jpg`. A tórica corrigida e o OD da monovisão reusam a monofocal.

**Cenas da gravação (depois do MVP)**
- Dia: café na calçada. Longe a 6 m ou mais (placas, fachadas), intermediário a ~66 cm (notebook), perto a 40 cm (cardápio).
- Noite: banco do motorista de um carro parado. Longe (faróis, postes, semáforo), intermediário a ~70 cm (painel, GPS), perto a 40 cm (celular).
- Roteiro de gravação, medidas e adereços com letras graduadas: `tools/kit-gravacao.html` (o PDF é gerado dele).
- Profundidade das fotos: modelo monocular métrico, ajustado às distâncias medidas com trena. À noite, 3 exposições juntadas em HDR, para as luzes guardarem a intensidade real (é isso que gera o halo).

**Sequência**
- Cena por cena: primeiro o dia com todas as lentes selecionadas, depois a noite com as mesmas lentes. A catarata abre cada cena.
- Ordem fixa (mantida em 23/10/2026): catarata, monofocal, EDOF, multifocal, tórica (dois tempos: sem correção e corrigida), monovisão.
- 15 s por capítulo (parâmetro `?s=` na URL para testar mais rápido). Quando houver narração, o capítulo dura o áudio. Nome do capítulo nos primeiros segundos.
- Tela inicial: catarata sempre incluída, lentes todas marcadas por padrão, sem escolha de cena. No fim, volta à tela inicial.
- Sem tablet e sem controle remoto.

**Vídeo (produto final, registrado aqui para não se perder)**
- X6 em 8K 360°, recortado para 3840 × 3840 na frente. Mesma óptica quadro a quadro; com tripé fixo, um mapa de profundidade por cena.
- ~1 GB de vídeo não cabe bem no GitHub Pages: hospedar à parte e baixar no celular antes da consulta.

## Decisões de teste

- Um bom teste verifica comportamento externo, não detalhes internos.
- Costura 1: montagem da sequência a partir da seleção de lentes (lógica pura), testada com o test runner nativo do Node.
- Costura 2: processamento óptico, com verificações embutidas no script (sem borrão onde a lente foca, borrão crescente com o desfoque, frações somando 1, dimensões das imagens) e uma folha de contato com todas as variantes para revisão visual.
- Costura 3: a página num navegador headless, sem WebXR (carrega sem erros, avança os capítulos, a vista da frente bate com a projeção esperada da imagem e não está espelhada). A aceitação final é o teste do médico com o óculos.

## Fora do escopo

Vídeo e seu processamento; transferência NAS → celular; personalização por paciente; controle por tablet ou remoto; iPhone (o Safari não tem WebXR).
