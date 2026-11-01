# Spec — Simulador VR de lentes intraoculares (OlharPar)

## Problema

O paciente de catarata precisa escolher entre lentes (monofocal, EDOF, multifocal, tórica, monovisão) sem conseguir imaginar como vai enxergar com cada uma. Explicações verbais e folhetos não mostram a diferença entre longe, intermediário e perto, nem os halos noturnos. O app anterior (LensVR) ficou instável e simulava a óptica com filtros que borram a imagem inteira por igual, o que não diferencia as distâncias.

## Solução

Um simulador em óculos VR de encaixar celular. O paciente olha ao redor de uma cena real de ~220° e vê, capítulo por capítulo, como enxergaria com catarata e depois com cada lente, de dia e à noite. A secretária escolhe as lentes antes de encaixar o celular e a sequência roda sozinha.

- **MVP:** de dia, 10 s de vídeo da Insta360 X6 gravado pelo Dr. Henrique em 01/11/2026 (varanda: livro na mão a ~30 cm, criança na cadeira e mulher a ~1 m, árvores e poste ao longe), com publicação autorizada por ele. À noite, a foto 360° HDR do Poly Haven `vignaioli_night` (CC0), com mesa, cardápio e notebook sintéticos em distâncias exatas. Narração em áudio quando gravada.
- **Depois do MVP:** gravações da X6 nas cenas do roteiro (café na calçada de dia, carro parado à noite), ticket 05.
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
- Imagem monoscópica (a X6 não grava em 3D) numa esfera parcial centrada na frente: 220° × 180° nas fotos, 190° × 180° no vídeo. O campo sai da proporção da própria imagem (largura ÷ altura × 180°), então o app não repete a constante. A borda lateral some num degradê gravado na imagem.
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
| Multifocal (trifocal) | 0 · 0,25 · 0,5 + 1,5 · 0,25 · 0,2 + 2,5 · 0,25 · 0,3 | de dia, a imagem em foco prevalece: longe e perto 100% nítidos (01/11/2026); à noite, halos |
| Tórica: sem correção | 0 · 0,25 · 1,0 | astigmatismo residual 1,50 D a 90° |
| Tórica: corrigida | igual à monofocal | — |
| Monovisão | OD: 0 · 0,25 · 1,0 / OE: 2,5 · 0,25 · 1,0 (−2,50 D; era −1,50 D até 01/11/2026) | imagem diferente por olho; o OE lê o perto nítido |

- Fotos em 4096 × 3352 (220° × 180°, ≈18,6 px/grau, acima dos ~16 px/grau da tela no óculos): `media/noite-{lente}.jpg`. Vídeo do dia: `media/dia-{lente}.mp4`. Lentes: catarata, monofocal, edof, multifocal, astig, perto. A tórica corrigida e o OD da monovisão reusam a monofocal.

**Cenas da gravação (depois do MVP)**
- Dia: café na calçada. Longe a 6 m ou mais (placas, fachadas), intermediário a ~66 cm (notebook), perto a 40 cm (cardápio).
- Noite: banco do motorista de um carro parado. Longe (faróis, postes, semáforo), intermediário a ~70 cm (painel, GPS), perto a 40 cm (celular).
- Roteiro de gravação, medidas e adereços com letras graduadas: `tools/kit-gravacao.html` (o PDF é gerado dele).
- Profundidade das fotos: modelo monocular métrico, ajustado às distâncias medidas com trena. À noite, 3 exposições juntadas em HDR, para as luzes guardarem a intensidade real (é isso que gera o halo).

**Sequência**
- Cena por cena: primeiro o dia com todas as lentes selecionadas, depois a noite com as mesmas lentes. A catarata abre cada cena.
- Ordem fixa (mantida em 23/10/2026): catarata, monofocal, EDOF, multifocal, tórica (dois tempos: sem correção e corrigida), monovisão.
- 15 s por capítulo de foto; o de vídeo dura o vídeo (10 s). O parâmetro `?s=` na URL encurta todos para testar. Quando houver narração, o capítulo dura o áudio. Nome do capítulo nos primeiros segundos.
- Tela inicial: catarata sempre incluída, lentes todas marcadas por padrão, sem escolha de cena. No fim, volta à tela inicial.
- Sem tablet e sem controle remoto.

**Vídeo (`tools/video.py`)**
- Origem: o `.insv` da X6 traz as duas lentes em fluxos separados (3840 × 3840, HEVC 10 bits, 29,97 fps). Usa-se só a lente da frente (fluxo 0), sem costura: ela cobre ~194° no quadro. Projeção equidistante calibrada pela sobreposição com a lente de trás: 19,75 px/grau, centro (1919; 1920).
- Saída 190° × 180° em 3800 × 3600 (20 px/grau, a resolução da própria lente), em HEVC: passa do teto do H.264 (~9 MP por quadro), e o S23 Ultra decodifica HEVC no hardware. A versão anterior, em H.264 a 3040 × 2880, tocou nele.
- Profundidade: Depth Anything V2 small (ONNX, CPU) quadro a quadro. A profundidade relativa vira vergência pelas três referências medidas na gravação: árvores 0,03 D, criança e mulher 1,0 D. O livro, a ~30 cm, conta como o perto do app (2,5 D), e nada fica mais perto que ele (01/11/2026: não importa 30 ou 40 cm). Depois, mediana de 5 quadros no tempo.
- Óptica: a mesma do `bake.py`, em 4 faixas de vergência (0; 1,0; 1,75; 2,5 D), somadas com normalização (o que o objeto da frente escondia é preenchido). Cada componente da lente é borrado na sua escala: borrões grandes em 1/2 ou 1/4 da resolução, a parte nítida da EDOF e da multifocal na resolução cheia. A memória do container (~6 GB) manda: duas passadas de 3 lentes, cada lente gravada primeiro num rascunho quase sem perda e comprimida em HEVC depois, uma por vez. Leva ~1h30 por 10 s.
- O trecho de origem fica no Mac (`VR simulator/VR IOL Simulator/video teste/trecho_37-49s.mp4`, cópia sem recodificar de 37 a 49 s). Para regerar: `python3 tools/video.py <trecho> 1.0 10`.
- Produto final: vídeos mais longos passam do limite do GitHub Pages (~1 GB): hospedar à parte e baixar no celular antes da consulta.

## Decisões de teste

- Um bom teste verifica comportamento externo, não detalhes internos.
- Costura 1: montagem da sequência a partir da seleção de lentes (lógica pura), testada com o test runner nativo do Node.
- Costura 2: processamento óptico, com verificações embutidas no script (sem borrão onde a lente foca, borrão crescente com o desfoque, frações somando 1, dimensões das imagens) e uma folha de contato com todas as variantes para revisão visual.
- Costura 3: a página num navegador headless, sem WebXR (carrega sem erros, avança os capítulos, o vídeo do dia toca, a vista da frente bate com a projeção esperada da imagem e não está espelhada). A aceitação final é o teste do médico com o óculos.

## Fora do escopo

Vídeos longos e sua hospedagem fora do GitHub Pages; transferência NAS → celular; personalização por paciente; controle por tablet ou remoto; iPhone (o Safari não tem WebXR).
