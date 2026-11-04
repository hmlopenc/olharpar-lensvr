# Handoff — Simulador VR de lentes (OlharPar) · checkpoint de 04/11/2026

## Onde está
- Código: github.com/hmlopenc/olharpar-lensvr, branch `main`. O app do Claude está instalado no repositório, então dá para fazer push daqui.
- Site: https://hmlopenc.github.io/olharpar-lensvr/ (GitHub Pages a partir do `main`, raiz; cada push publica sozinho).
- Spec e tickets: `.scratch/esqueleto/` (`spec.md` e `issues/01, 03, 04, 05`). Leia a spec antes de mexer.
- No Mac do Henrique, em `~/Desktop/Apps/VR IOL`: `kit-gravacao.pdf`, `folha-de-contato.jpg`, cópia zipada do projeto e a pasta `fotos/teste`.
- Vídeo de origem: `~/Desktop/VR simulator/VR IOL Simulator/video teste/` (o `.insv` de 56 s e o `trecho_37-49s.mp4`, cópia sem recodificar).

## Decisões
- **MVP (01/11/2026):** de dia, 10 s de vídeo da X6 gravado pelo Henrique na varanda (livro a ~30 cm, criança e mulher a ~1 m, árvores ao longe), publicação autorizada por ele. À noite, a foto HDR `vignaioli_night` do Poly Haven (CC0) com mesa, cardápio e notebook sintéticos. As gravações do roteiro (café de dia, carro à noite) ficam para depois do MVP (ticket 05).
- **Vídeo:** só a lente da frente, sem costura, 190° × 180° em 3800 × 3600 (20 px/grau, a resolução da lente), em HEVC. A profundidade vem do Depth Anything V2 small, calibrada pelas distâncias que o Henrique informou; o livro conta como perto (40 cm). Detalhes na spec, seção "Vídeo".
- **Perto (01/11/2026):** a multifocal e o olho de perto da monovisão (agora −2,50 D) leem o livro 100% nítido. De dia a multifocal é seletiva: onde uma imagem está em foco, só ela conta. À noite segue a óptica física, com halos.
- **WebXR nativo do Chrome** (Cardboard) no lugar do giroscópio e do estéreo próprios. O antigo ticket 02 (calibração) saiu; a calibração passa a ser o QR code do óculos.
- **Campo:** 220° × 180° nas fotos e 190° × 180° no vídeo. O app tira o campo da proporção da mídia, e a borda some num degradê.
- **Óptica.** A tabela da spec foi aprovada como ponto de partida e fica em `tools/lentes.py`. Ordem dos capítulos da spec mantida.
- **Astigmatismo** com o equivalente esférico no foco (+0,75 −1,50 × 90°). **Curva de tom** ACES nas fotos HDR; o vídeo, que já é SDR, sai sem curva.
- **Óculos:** o do Henrique é o Shinecon SC-G04E V2, com o controle Bluetooth SC-B03. Opção premium futura: Meta Quest 3, que abre o mesmo link.
- **Controle (04/11/2026):** o SC-B03 no modo GAME (ele não tem modo mouse). Dentro do óculos, qualquer botão abre o menu na própria legenda, um item por vez; com controle, o fim da sequência volta ao menu sem sair do VR. Entrar no VR continua pedindo um toque em Iniciar.

## Estado
- Tickets 01 (código), 03 e 04 prontos e publicados; de dia, vídeo da X6 desde 01/11/2026, em resolução cheia (HEVC 3800 × 3600) e com o perto nítido desde a tarde do mesmo dia. Evidência:
  - verificações embutidas do `bake.py` passando (noite) e asserção do `video.py`: livro sem borrão na multifocal e no OE da monovisão;
  - folha de contato do vídeo (quadro do meio) revisada: monofocal nítida longe; EDOF nítida longe e no intermediário; multifocal nítida longe e no livro, macia na criança e na mulher (o foco intermediário da tabela é 67 cm); OE da monovisão nítido no livro;
  - os 6 vídeos: HEVC (`hvc1`), 3800 × 3600, 300 quadros, 10 s, 2–18 MB. No quadro do meio, o HEVC guarda 95% do detalhe fino da imagem antes da compressão; o H.264 de 16 px/grau anterior guardava 72%;
  - `node --test` 4/4;
  - teste de fumaça headless: vídeo do dia tocando, vista da frente batendo com a projeção esperada (e não com o espelho), OE da monovisão com a imagem de perto, volta à tela inicial, falha de carregamento escrita na tela, e o menu respondendo a um controle falso (abre, troca de item, marca a lente, recomeça e volta no fim).
- **Não verificado no aparelho:** o Chrome do S23 repassar os botões do SC-B03 à página durante a sessão VR, WebXR no S23 Ultra, QR code do Cardboard no óculos, tela acesa durante a sessão, nitidez real no óculos, reprodução do HEVC de 3800 × 3600 no Chrome do S23 (dois ao mesmo tempo na monovisão), vídeo atualizando dentro da sessão VR, cintilação da tela de arame ao mexer a cabeça (o vídeo tem mais pixels por grau que a tela).

## Pendências do Henrique
1. Feito em 01/11/2026: o vídeo tocou no S23 Ultra com um óculos Shinecon, mas a resolução pareceu baixa. Conferir se a tela está em WQHD+ e retestar com o vídeo em resolução cheia (HEVC).
2. Avaliação clínica das folhas de contato (noite e vídeo) e, depois, no óculos. O ganho 2,0 também dobra o tamanho do halo.
3. Gravar a narração por capítulo (opcional no MVP).
4. Testar o controle SC-B03: parear no modo GAME, abrir o site e apertar um botão (aparece "Controle conectado"), tocar em Iniciar e, no óculos, apertar um botão para abrir o menu.

## Como rodar
- `python3 tools/bake.py [folha.jpg]` regera as fotos da noite e a folha de contato em ~1 min. Na primeira vez, baixa o HDR para `~/.cache/olharpar-lensvr`. Precisa de numpy, Pillow, scipy e opencv.
- `python3 tools/video.py <trecho.mp4> 1.0 10 [folha.jpg]` regera os vídeos do dia e a folha de contato deles em ~1h30. Precisa também de onnxruntime; baixa o modelo de profundidade (~100 MB) na primeira vez. O trecho precisa ser copiado do Mac (device_stage_files).
- `node --test` testa a montagem da sequência.
- `THREE_DIR=<three/build> python3 tests/smoke.py <pasta>` roda o teste da página (Playwright + Chromium). Sem acesso ao CDN, use `npm pack three@0.186.1`.
- Para publicar: `git push origin main`.

## Próximos passos
- Ajustar o que o teste no aparelho mostrar: escala do framebuffer, legenda, ganho, campo.
- Se o Chrome do S23 não tocar o HEVC (a tela inicial mostra "não carregou"), converter os 6 vídeos para H.264 de 3040 × 2880 com ffmpeg (minutos, sem renderizar de novo).
- Narração: cada capítulo toca o seu áudio e dura o tempo dele (nota no ticket 04).
- Ticket 05 quando existirem as gravações do roteiro.

## Forma de trabalho
Skill ponytail (full): menor caminho, sem governança extra. Só dizer "pronto" com evidência. Terminar as respostas com o que não foi verificado. Português, com uma recomendação única.
