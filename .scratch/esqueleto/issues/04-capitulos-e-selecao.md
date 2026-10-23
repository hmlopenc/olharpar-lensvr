# 04: Capítulos e seleção

**What to build:** Tela inicial com seleção de lentes e aviso de simulação ilustrativa. Ao iniciar, a sequência roda cena por cena (dia, depois noite), com a catarata abrindo cada cena, a tórica em dois tempos e a monovisão com imagem diferente por olho, mostrando o nome do capítulo em 3D no início. No fim, volta à tela inicial.

**Blocked by:** 01, 03

**Status:** done em 23/10/2026 (o nome nos dois olhos só se confirma no óculos)

- [x] Catarata sempre incluída; lentes todas marcadas por padrão
- [x] Sequência na ordem da spec, só com as lentes marcadas
- [x] Tórica em dois capítulos (sem correção, corrigida); monovisão com OD longe e OE perto
- [x] Nome do capítulo visível nos dois olhos nos primeiros segundos
- [x] Carrega a imagem do capítulo atual e a do próximo e descarta as anteriores
- [x] `?s=` encurta os capítulos para teste
- [x] Teste da montagem da sequência passa (`node --test`)
- [x] No fim, volta à tela inicial

Narração: quando os áudios existirem, cada capítulo toca o seu e dura o tempo do áudio. Fica para depois da gravação.
