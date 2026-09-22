import assert from 'node:assert/strict';
import { test } from 'node:test';
import { useGlossary } from './useGlossary.js';

const csv = 'src,dst\r\nhello,你好\r\nworld,世界\r\n';
const expected = { hello: '你好', world: '世界' };
const utf16 = Buffer.from(csv, 'utf16le');
const legacyCsv = (hello, world) => Buffer.concat([
    Buffer.from('src,dst\r\nhello,'), Buffer.from(hello),
    Buffer.from('\r\nworld,'), Buffer.from(world),
]);
const cases = [
    ['UTF-8', Buffer.from(csv), expected],
    ['UTF-8 BOM', Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(csv)]), expected],
    ['UTF-16 LE', Buffer.concat([Buffer.from([0xff, 0xfe]), utf16]), expected],
    ['UTF-16 BE', Buffer.concat([Buffer.from([0xfe, 0xff]), Buffer.from(utf16).swap16()]), expected],
    ['GBK', legacyCsv([0xc4, 0xe3, 0xba, 0xc3], [0xca, 0xc0, 0xbd, 0xe7]), expected],
    ['Big5', legacyCsv([0xa7, 0x41, 0xa6, 0x6e], [0xa5, 0x40, 0xac, 0xc9]), expected],
    ['ASCII', Buffer.from('src,dst\r\nhello,world'), { hello: 'world' }],
    ['empty file', Buffer.alloc(0), {}],
];

for (const [name, bytes, entries] of cases) {
    test(`imports glossary CSV: ${name}`, async () => {
        const glossary = useGlossary();
        const file = { name, arrayBuffer: async () => Uint8Array.from(bytes).buffer };
        await glossary.handleGlossaryFiles({ target: { files: [file] } });
        assert.deepEqual(glossary.glossaryData.value, entries);
        assert.equal(glossary.glossaryCount.value, Object.keys(entries).length);
    });
}
