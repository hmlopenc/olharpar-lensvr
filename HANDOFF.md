# Handoff — Simulador VR de lentes (OlharPar) · checkpoint de 23/10/2026

## Onde está
- Código: github.com/hmlopenc/olharpar-lensvr, branch `main`. O app do Claude está instalado no repositório, então dá para fazer push daqui.
- Site: https://hmlopenc.github.io/olharpar-lensvr/ (GitHub Pages a partir do `main`, raiz; cada push publica sozinho).
- Spec e tickets: `.scratch/esqueleto/` (`spec.md` e `issues/01, 03, 04, 05`). Leia a spec antes de mexer.
- No Mac do Henrique, em `~/Desktop/Apps/VR IOL`: `kit-gravacao.pdf`, `folha-de-contato.jpg`, cópia zipada do projeto e a pasta `fotos/teste`.

## Decisões de 23/10/2026
- **MVP sem gravação.** Os fundos são fotos 360° HDR do Poly Haven (CC0): `palermo_sidewalk` de dia e `vignaioli_night` à noite. Na frente, mesa, cardápio e notebook sintéticos em distâncias exatas, com as mesmas letras do kit. As fotos da X6 (café de dia, carro à noite) ficam para depois do MVP (ticket 05); o vídeo, para o produto final.
- **WebXR nativo do Chrome** (Cardboard) no lugar do giroscópio e do estéreo próprios. O antigo ticket 02 (calibração) saiu; a calibração passa a ser o QR code do óculos.
- **Campo de 220° × 180°.** O app tira o campo da proporção da imagem (4096 × 3352) e a borda some num degradê.
- **Óptica.** A tabela da spec foi aprovada como ponto de partida e fica em `tools/lentes.py`. Ordem dos capítulos da spec mantida.
- **Astigmatismo** com o equivalente esférico no foco (+0,75 −1,50 × 90°). **Curva de tom** ACES nas duas cenas.
- **Óculos do MVP:** Shinecon SC-G15E (testar o encaixe do S23 Ultra sem capa). Opção premium futura: Meta Quest 3, que abre o mesmo link.

## Estado
- Tickets 01 (código), 03 e 04 prontos e publicados. Evidência:
  - verificações embutidas do `bake.py` passando;
  - `node --test` 4/4;
  - teste de fumaça headless: vista da frente com correlação 0,999 com a projeção esperada (0,55 contra o espelho), OE da monovisão com a imagem de perto, volta à tela inicial.
- **Não verificado no aparelho:** WebXR no S23 Ultra, QR code do Cardboard no óculos, tela acesa durante a sessão, nitidez real no óculos.

## Pendências do Henrique
1. Abrir o site no Chrome do S23 Ultra, tocar em Iniciar e contar se entra no modo VR do Cardboard.
2. Comprar um SC-G15E e testar o encaixe.
3. Avaliação clínica da folha de contato e, depois, no óculos. O ganho 2,0 também dobra o tamanho do halo.
4. Gravar a narração por capítulo (opcional no MVP).

## Como rodar
- `python3 tools/bake.py [folha.jpg]` regera `media/` e a folha de contato em ~2 min. Na primeira vez, baixa os HDR (~210 MB) para `~/.cache/olharpar-lensvr`. Precisa de numpy, Pillow, scipy e opencv. Frente e exposição de cada fundo ficam em `FUNDOS`, dentro do `bake.py`.
- `node --test` testa a montagem da sequência.
- `THREE_DIR=<three/build> python3 tests/smoke.py <pasta>` roda o teste da página (Playwright + Chromium). Sem acesso ao CDN, use `npm pack three@0.186.1`.
- Para publicar: `git push origin main`.

## Próximos passos
- Ajustar o que o teste no aparelho mostrar: escala do framebuffer, legenda, ganho, campo.
- Narração: cada capítulo toca o seu áudio e dura o tempo dele (nota no ticket 04).
- Ticket 05 quando existirem as fotos da X6.

## Forma de trabalho
Skill ponytail (full): menor caminho, sem governança extra. Só dizer "pronto" com evidência. Terminar as respostas com o que não foi verificado. Português, com uma recomendação única.
