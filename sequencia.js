// Monta a sequência de capítulos a partir das lentes marcadas. Lógica pura, testada com node --test.
// Cada capítulo: { cena, nome, od, oe } (imagens do olho direito e do esquerdo).

// Ordem da spec. Cada lente vira um ou mais capítulos: [nome, imagem do OD, imagem do OE (padrão: a mesma)].
export const LENTES = {
  monofocal: [['Lente monofocal', 'monofocal']],
  edof: [['Lente EDOF', 'edof']],
  multifocal: [['Lente multifocal', 'multifocal']],
  torica: [['Astigmatismo sem correção', 'astig'], ['Lente tórica', 'monofocal']],
  monovisao: [['Monovisão', 'monofocal', 'perto']],  // OD para longe, OE para perto
};

const CENAS = { dia: 'De dia', noite: 'À noite' };

export function montar(marcadas) {
  const caps = [];
  for (const [cena, quando] of Object.entries(CENAS)) {
    const lista = [['Com catarata', 'catarata']];  // a catarata abre cada cena
    for (const [id, capitulos] of Object.entries(LENTES)) if (marcadas.includes(id)) lista.push(...capitulos);
    for (const [nome, od, oe = od] of lista) {
      caps.push({ cena: quando, nome, od: `media/${cena}-${od}.jpg`, oe: `media/${cena}-${oe}.jpg` });
    }
  }
  return caps;
}
