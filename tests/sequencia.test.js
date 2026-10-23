import { test } from 'node:test';
import assert from 'node:assert/strict';
import { montar, LENTES } from '../sequencia.js';

const nomes = caps => caps.map(c => `${c.cena} · ${c.nome}`);

test('a catarata abre cada cena, mesmo sem lente marcada', () => {
  assert.deepEqual(nomes(montar([])), ['De dia · Com catarata', 'À noite · Com catarata']);
});

test('dia antes da noite, na ordem da spec, só com as lentes marcadas', () => {
  const caps = nomes(montar(['multifocal', 'monofocal']));  // a ordem da marcação não importa
  assert.deepEqual(caps, [
    'De dia · Com catarata', 'De dia · Lente monofocal', 'De dia · Lente multifocal',
    'À noite · Com catarata', 'À noite · Lente monofocal', 'À noite · Lente multifocal',
  ]);
});

test('tórica em dois tempos e monovisão com OD longe e OE perto', () => {
  const caps = montar(['torica', 'monovisao']).filter(c => c.cena === 'À noite');
  assert.deepEqual(caps.map(c => [c.nome, c.od, c.oe]), [
    ['Com catarata', 'media/noite-catarata.jpg', 'media/noite-catarata.jpg'],
    ['Astigmatismo sem correção', 'media/noite-astig.jpg', 'media/noite-astig.jpg'],
    ['Lente tórica', 'media/noite-monofocal.jpg', 'media/noite-monofocal.jpg'],
    ['Monovisão', 'media/noite-monofocal.jpg', 'media/noite-perto.jpg'],
  ]);
});

test('todas as lentes marcadas: 14 capítulos, todos com imagem que o bake gera', async () => {
  const { readdirSync } = await import('node:fs');
  const geradas = new Set(readdirSync(new URL('../media/', import.meta.url)).map(f => `media/${f}`));
  const caps = montar(Object.keys(LENTES));
  assert.equal(caps.length, 14);
  for (const c of caps) assert.ok(geradas.has(c.od) && geradas.has(c.oe), `${c.od} / ${c.oe}`);
});
