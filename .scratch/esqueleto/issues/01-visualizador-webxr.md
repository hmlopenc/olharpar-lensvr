# 01: Visualizador WebXR com a cena de 220°

**What to build:** No S23 Ultra, a página abre e o toque em "Iniciar" entra no modo VR do Chrome (WebXR com o Cardboard). Uma contagem de 5 s presa à cabeça dá tempo de encaixar o celular, e a cena de 220° × 180° aparece nítida, acompanhando a cabeça e recentralizada ao fim da contagem. Inclui o gerador da cena sintética (dia e noite) no formato de 220° e a publicação no GitHub Pages.

**Histórico:** a primeira versão (commit 9d2804f) usava giroscópio e estéreo próprios, sem correção de distorção. Em 23/10/2026 passou para o WebXR nativo, que também substitui o antigo ticket 02 (calibração).

**Blocked by:** None. A publicação depende do GitHub conectado e do repositório `olharpar-lensvr` criado.

**Status:** código pronto em 23/10/2026; falta o teste no S23 Ultra e a publicação (GitHub desconectado)

- [x] Gerador produz a cena sintética de dia e de noite em 220° × 180°, com letreiros/rua a 6 m, tela a 66 cm e cardápio a 40 cm
- [x] Esfera parcial com o campo tirado da proporção da imagem, sem espelhamento, uma malha por olho (camadas 1 e 2)
- [x] Contagem em 3D presa à cabeça; recentraliza ao fim
- [x] Sem WebXR, roda na tela olhando para a frente; carrega sem erros no navegador headless
- [ ] No S23 Ultra: entra no VR do Chrome, perfil do óculos escaneado, sem distorção nas bordas
- [ ] Publicado no GitHub Pages
