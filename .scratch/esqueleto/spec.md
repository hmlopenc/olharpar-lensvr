# Spec — Esqueleto do simulador VR de lentes intraoculares (OlharPar)

## Problema

O paciente de catarata precisa escolher entre lentes (monofocal, EDOF, multifocal, tórica, monovisão) sem conseguir imaginar como vai enxergar com cada uma. Explicações verbais e folhetos não mostram a diferença entre longe, intermediário e perto, nem os halos noturnos. O app anterior (LensVR) ficou instável e simulava a óptica com filtros que borram a imagem inteira por igual, o que não diferencia as distâncias.

## Solução

Um simulador em óculos VR de encaixar celular. O paciente olha ao redor de uma cena 360° e vê, capítulo por capítulo, como enxergaria com catarata e depois com cada lente, de manhã e à noite. A secretária escolhe as lentes antes de encaixar o celular e a sequência roda sozinha. Nesta fase (esqueleto) a cena é uma sala 360° sintética; na fase 2 entra o vídeo 360° gravado pelo Dr. Henrique com a Insta360 X6, com ele ao lado do paciente narrando.

## User stories

1. Como secretária, quero marcar quais lentes mostrar antes de encaixar o celular, para adaptar a demonstração a cada paciente.
2. Como secretária, quero um único botão para iniciar, com contagem regressiva, para ter tempo de encaixar o celular no óculos.
3. Como paciente, quero olhar ao redor movendo a cabeça, para me sentir dentro da cena.
4. Como paciente, quero ver primeiro como enxergo com catarata, para ter uma referência.
5. Como paciente, quero ver as lentes uma após a outra na mesma cena, para perceber a diferença em longe, intermediário e perto.
6. Como paciente, quero ver a mesma comparação à noite, para entender os halos e o ofuscamento de cada lente.
7. Como paciente, quero ver uma lente comum com astigmatismo e depois a tórica corrigindo, para entender por que a tórica existe.
8. Como paciente, quero ver a monovisão com um olho para longe e outro para perto, para sentir como os dois olhos se combinam.
9. Como paciente, quero ver o nome do capítulo no início, para saber o que estou vendo.
10. Como médico, quero calibrar a distância entre lentes e o zoom uma vez por aparelho, para a imagem ficar confortável no óculos.
11. Como médico, quero ajustar o desfoque e os halos de cada lente num único arquivo, para calibrar clinicamente o que o paciente vê.
12. Como médico, quero que a tela fique cheia, na horizontal e sem apagar durante a experiência.
13. Como médico, quero que o app volte à tela inicial no fim, pronto para o próximo paciente.
14. Como médico, quero publicar atualizações sem instalar nada nos aparelhos.

## Decisões de implementação

**Plataforma**
- Página web estática, sem React e sem etapa de build. three.js carregado por CDN. Publicada no GitHub Pages, repositório `olharpar-lensvr`.
- Aparelho-alvo: Galaxy S23 Ultra no Chrome, com a resolução da tela em WQHD+ (de fábrica vem em FHD+). O Fold 7 fica como aparelho de teste secundário.
- Aviso "Simulação ilustrativa. Os resultados variam de pessoa para pessoa." na tela inicial.

**Visualização**
- Estéreo lado a lado: uma câmera por olho no mesmo ponto (imagem 360° não tem paralaxe) e cada olho com a sua própria imagem, o que viabiliza a monovisão.
- Orientação pelos sensores de movimento do aparelho. A visão é recentralizada no início da experiência.
- Durante a experiência: tela cheia, travada na horizontal e sem apagar.
- Atalho declarado: sem correção da distorção das lentes do óculos. Entra um perfil de distorção se as bordas incomodarem.

**Óptica (fora do app)**
- O app não calcula desfoque. Um script gera as imagens de cada lente e o app só troca as imagens.
- Cena sintética: sala 360° vista de uma pessoa sentada, com letreiros e rua pela janela a 6 m, tela de computador a 66 cm e cardápio na mão a 40 cm. A versão noturna tem postes, faróis e letreiro aceso.
- Modelo: cada lente é um conjunto de componentes (foco em dioptrias, faixa nítida em torno do foco, fração da luz). O desfoque efetivo de um objeto é a distância dióptrica até o foco, menos a faixa. O tamanho do borrão é pupila × desfoque × ganho. À noite as luzes têm alta intensidade, de modo que os halos surgem do próprio desfoque (a parte da luz que a lente desvia para perto aparece como halo em volta das luzes de longe).
- A catarata soma um véu de espalhamento, perda de contraste e amarelamento. O astigmatismo usa um borrão elíptico.
- Ganho inicial 2,0 (1,0 = óptica física). Motivo: a tela do óculos não mostra nada mais fino que ~20/75, então o desfoque precisa crescer na mesma proporção para manter as diferenças entre as lentes. Calibrado pelo médico olhando no óculos.

Valores iniciais (vergência no plano dos óculos; longe ≈ 0 D, intermediário 1,5 D, perto 2,5 D; pupila 3 mm de dia e 5 mm à noite):

| Lente | Componentes (foco D · faixa D · fração) | Extra |
|---|---|---|
| Catarata (antes) | 0 · 0,25 · 1,0 | desfoque basal 0,75 D, véu 30%, contraste 70%, amarelamento |
| Monofocal | 0 · 0,25 · 1,0 | — |
| EDOF | 0,75 · 0,75 · 0,9 + 2,0 · 0,25 · 0,1 | — |
| Multifocal (trifocal) | 0 · 0,25 · 0,5 + 1,5 · 0,25 · 0,2 + 2,5 · 0,25 · 0,3 | — |
| Tórica: sem correção | 0 · 0,25 · 1,0 | astigmatismo residual 1,50 D a 90° |
| Tórica: corrigida | igual à monofocal | — |
| Monovisão | OD: 0 · 0,25 · 1,0 / OE: 1,5 · 0,25 · 1,0 (−1,50 D) | imagem diferente por olho |

- Imagens em 4096 × 2048 (atalho declarado: abaixo da resolução do S23 Ultra no óculos; subir para 6K se o aparelho aguentar a memória).

**Sequência**
- Cena por cena: primeiro manhã com todas as lentes selecionadas, depois noite com as mesmas lentes. A catarata abre cada cena.
- Ordem fixa: catarata, monofocal, EDOF, multifocal, tórica (dois tempos: sem correção e corrigida), monovisão.
- Duração fixa por capítulo no esqueleto (15 s), substituída pela duração do vídeo na fase 2. Rótulo do capítulo nos primeiros segundos.
- Tela inicial: catarata sempre incluída, lentes todas marcadas por padrão, sem escolha de cena. No fim, volta à tela inicial.
- Sem tablet e sem controle remoto.

**Calibração**
- Ajuste de distância entre lentes e de zoom, com padrão de teste em estéreo, salvo no próprio aparelho.

**Vídeo (fase 2, registrado aqui para não se perder)**
- Origem no NAS. O celular copia os vídeos uma vez e toca localmente, sem streaming na consulta. Mecanismo (Syncthing ou download) decidido na fase 2.
- Resolução de partida: 5,7K.

## Decisões de teste

- Um bom teste verifica comportamento externo, não detalhes internos.
- Costura 1: montagem da sequência a partir da seleção de lentes (lógica pura), testada com o test runner nativo do Node.
- Costura 2: processamento óptico, com verificações embutidas no script (sem borrão onde a lente foca, borrão crescente com o desfoque, frações somando 1, dimensões das imagens) e uma folha de contato com todas as variantes para revisão visual.
- Costura 3: a página num navegador headless (carrega sem erros, avança os capítulos). A aceitação final é o teste do médico com o óculos.

## Fora do escopo

Vídeo 360° e seu processamento; transferência NAS → celular; estimativa de profundidade de filmagem real; personalização por paciente; controle por tablet ou remoto; perfis de distorção por modelo de óculos; áudio; ajustes específicos para iPhone.

## Notas

- Óculos: precisa aceitar celular de 6,8" (163 × 78 mm), com ajuste de distância entre lentes e de foco.
- Gravação da fase 2: câmera fixa em tripé na altura dos olhos de uma pessoa sentada, um take por lente em cada cena, 5,7K.
