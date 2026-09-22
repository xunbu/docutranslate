import { ref, computed } from 'vue';
import Papa from 'papaparse';
import { detect } from 'jschardet';

// 编码映射：jschardet 返回的编码名 -> TextDecoder 支持的编码名
const encodingMap = {
    'ascii': 'utf-8',
    'utf-8': 'utf-8',
    'utf-8-sig': 'utf-8',
    'utf-16': 'utf-16',
    'utf-16le': 'utf-16le',
    'utf-16be': 'utf-16be',
    'utf-16-le': 'utf-16le',
    'utf-16-be': 'utf-16be',
    'big5': 'big5',
    'gb2312': 'gbk',
    'gbk': 'gbk',
    'gb18030': 'gb18030',
    'euc-kr': 'euc-kr',
    'euc-jp': 'euc-jp',
    'iso-8859-1': 'iso-8859-1',
    'iso-8859-2': 'iso-8859-2',
    'shift_jis': 'shift_jis',
    'windows-1250': 'windows-1250',
    'windows-1251': 'windows-1251',
    'windows-1252': 'windows-1252',
};

// 将文件读取为 ArrayBuffer 并检测编码
async function detectEncoding(file) {
    const buffer = await file.arrayBuffer();
    const uint8Array = new Uint8Array(buffer);

    // 如果文件为空，直接返回 utf-8
    if (uint8Array.length === 0) {
        return { buffer, encoding: 'utf-8', confidence: 1 };
    }

    try {
        const result = detect(uint8Array);

        // 检查返回结果是否有效
        if (!result || typeof result.encoding !== 'string') {
            return { buffer, encoding: 'utf-8', confidence: 0 };
        }

        const detectedEncoding = result.encoding.toLowerCase();
        const confidence = result.confidence || 0;

        // v4 对短文本的置信度较低；仅在字节确实是 UTF-8 时回退。
        if (confidence < 0.5) {
            try {
                new TextDecoder('utf-8', { fatal: true }).decode(buffer);
                return { buffer, encoding: 'utf-8', confidence };
            } catch {
                // 非 UTF-8 数据继续使用检测结果，避免将有效的旧编码文本解码为乱码。
            }
        }

        // 映射到 TextDecoder 支持的编码名
        let normalizedEncoding = encodingMap[detectedEncoding] || detectedEncoding;
        // v4 将带 BOM 的 UTF-16 统一标记为 UTF-16，TextDecoder 需要明确字节序。
        if (detectedEncoding === 'utf-16') {
            normalizedEncoding = uint8Array[0] === 0xfe && uint8Array[1] === 0xff
                ? 'utf-16be'
                : 'utf-16le';
        }

        return { buffer, encoding: normalizedEncoding, confidence };
    } catch (e) {
        console.warn('Encoding detection failed, falling back to utf-8:', e);
        return { buffer, encoding: 'utf-8', confidence: 0 };
    }
}

// 使用指定编码解码 ArrayBuffer（TextDecoder 会自动处理 BOM）
function decodeBuffer(buffer, encoding) {
    try {
        const decoder = new TextDecoder(encoding, { fatal: true });
        return decoder.decode(buffer);
    } catch (e) {
        console.warn(`Failed to decode with ${encoding}, falling back to utf-8:`, e);
        const decoder = new TextDecoder('utf-8', { fatal: false });
        return decoder.decode(buffer);
    }
}

export function useGlossary() {
    const glossaryData = ref({});
    const glossaryModalRef = ref(null);

    const glossaryCount = computed(() => Object.keys(glossaryData.value).length);

    const handleGlossaryFiles = async (e) => {
        const files = e.target.files;
        if (!files.length) return;

        for (const file of Array.from(files)) {
            try {
                // 检测编码
                const { buffer, encoding, confidence } = await detectEncoding(file);
                console.log(`Detected encoding for ${file.name}: ${encoding} (confidence: ${confidence.toFixed(2)})`);

                // 解码文件内容（TextDecoder 自动处理 BOM）
                const text = decodeBuffer(buffer, encoding);

                if (!text || !text.trim()) {
                    console.warn(`File ${file.name} is empty or contains no text`);
                    continue;
                }

                // 解析 CSV
                const res = Papa.parse(text, {
                    header: true,
                    skipEmptyLines: true,
                });

                if (res.data) {
                    res.data.forEach(r => {
                        if (r.src && r.dst) {
                            glossaryData.value[r.src.trim()] = r.dst.trim();
                        }
                    });
                }
            } catch (err) {
                console.error(`Failed to parse glossary file ${file.name}:`, err);
            }
        }
    };

    const clearGlossary = () => {
        glossaryData.value = {};
    };

    const openGlossaryModal = () => {
        if (glossaryModalRef.value) {
            glossaryModalRef.value.show();
        }
    };

    const downloadGlossaryTemplate = () => {
        window.open('/service/glossary/template', '_blank');
    };

    return {
        glossaryData,
        glossaryCount,
        glossaryModalRef,
        handleGlossaryFiles,
        clearGlossary,
        openGlossaryModal,
        downloadGlossaryTemplate
    };
}
