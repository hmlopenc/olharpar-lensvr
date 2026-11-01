# Handoff — Simulador VR de lentes (OlharPar) · checkpoint de 01/11/2026

## Onde está
- Código: github.com/hmlopenc/olharpar-lensvr, branch `main`. O app do Claude está instalado no repositório, então dá para fazer push daqui.
- Site: https://hmlopenc.github.io/olharpar-lensvr/ (GitHub Pages a partir do `main`, raiz; cada push publica sozinho).
- Spec e tickets: `.scratch/esqueleto/` (`spec.md` e `issues/01, 03, 04, 05`). Leia a spec antes de mexer.
- No Mac do Henrique, em `~/Desktop/Apps/VR IOL`: `kit-gravacao.pdf`, `folha-de-contato.jpg`, cópia zipada do projeto e a pasta `fotos/teste`.
- Vídeo de origem: `~/Desktop/VR simulator/VR IOL Simulator/video teste/` (o `.insv` de 56 s e o `trecho_37-49s.mp4`, cópia sem recodificar).

## Decisões
- **MVP (01/11/2026):** de dia, 10 s de vídeo da X6 gravado pelo Henrique na varanda (livro a ~30 cm, criança e mulher a ~1 m, árvores ao longe), publicação autorizada por ele. À noite, a foto HDR `vignaioli_night` do Poly Haven (CC0) com mesa, cardápio e notebook sintéticos. As gravações do roteiro (café de dia, carro à noite) ficam para depois do MVP (ticket 05).
- **Vídeo:** só a lente da frente, sem costura, 190° × 180° em 3040 × 2880 (H.264 nível 5.2). A profundidade vem do Depth Anything V2 small, calibrada pelas três distâncias que o Henrique informou. Detalhes na spec, seção "Vídeo".
- **WebXR nativo do Chrome** (Cardboard) no lugar do giroscópio e do estéreo próprios. O antigo ticket 02 (calibração) saiu; a calibração passa a ser o QR code do óculos.
- **Campo:** 220° × 180° nas fotos e 190° × 180° no vídeo. O app tira o campo da proporção da mídia, e a borda some num degradê.
- **Óptica.** A tabela da spec foi aprovada como ponto de partida e fica em `tools/lentes.py`. Ordem dos capítulos da spec mantida.
- **Astigmatismo** com o equivalente esférico no foco (+0,75 −1,50 × 90°). **Curva de tom** ACES nas fotos HDR; o vídeo, que já é SDR, sai sem curva.
- **Óculos do MVP:** Shinecon SC-G15E (testar o encaixe do S23 Ultra sem capa). Opção premium futura: Meta Quest 3, que abre o mesmo link.

## Estado
- Tickets 01 (código), 03 e 04 prontos e publicados; de dia, vídeo da X6 desde 01/11/2026. Evidência:
  - verificações embutidas do `bake.py` passando (noite);
  - folha de contato do vídeo (quadro do meio) revisada: monofocal nítida longe, EDOF nítida longe e no intermediário, multifocal nítida com véu;
  - `node --test` 4/4;
  - teste de fumaça headless: vídeo do dia tocando, vista da frente batendo com a projeção esperada (e não com o espelho), OE da monovisão com a imagem de perto, volta à tela inicial, falha de carregamento escrita na tela.
- **Não verificado no aparelho:** WebXR no S23 Ultra, QR code do Cardboard no óculos, tela acesa durante a sessão, nitidez real no óculos, reprodução do vídeo de 3040 × 2880 (dois ao mesmo tempo na monovisão), vídeo atualizando dentro da sessão VR.

## Pendências do Henrique
1. Abrir o site no Chrome do S23 Ultra, tocar em Iniciar e contar se entra no modo VR do Cardboard.
2. Comprar um SC-G15E e testar o encaixe.
3. Avaliação clínica das folhas de contato (noite e vídeo) e, depois, no óculos. O ganho 2,0 também dobra o tamanho do halo.
4. Gravar a narração por capítulo (opcional no MVP).

## Como rodar
- `python3 tools/bake.py [folha.jpg]` regera as fotos da noite e a folha de contato em ~1 min. Na primeira vez, baixa o HDR para `~/.cache/olharpar-lensvr`. Precisa de numpy, Pillow, scipy e opencv.
- `python3 tools/video.py <trecho.mp4> 1.0 10 [folha.jpg]` regera os vídeos do dia e a folha de contato deles em ~55 min. Precisa também de onnxruntime; baixa o modelo de profundidade (~100 MB) na primeira vez. O trecho precisa ser copiado do Mac (device_stage_files).
- `node --test` testa a montagem da sequência.
- `THREE_DIR=<three/build> python3 tests/smoke.py <pasta>` roda o teste da página (Playwright + Chromium). Sem acesso ao CDN, use `npm pack three@0.186.1`.
- Para publicar: `git push origin main`.

## Próximos passos
- Ajustar o que o teste no aparelho mostrar: escala do framebuffer, legenda, ganho, campo.
- Narração: cada capítulo toca o seu áudio e dura o tempo dele (nota no ticket 04).
- Ticket 05 quando existirem as gravações do roteiro.

## Forma de trabalho
Skill ponytail (full): menor caminho, sem governança extra. Só dizer "pronto" com evidência. Terminar as respostas com o que não foi verificado. Português, com uma recomendação única.
