import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { MAX_QUEUE_CONCURRENT, useSettings } from './useSettings.js';

const here = dirname(fileURLToPath(import.meta.url));

function withLocalStorage(run) {
    const previous = globalThis.localStorage;
    const data = new Map();
    globalThis.localStorage = {
        getItem: key => (data.has(key) ? data.get(key) : null),
        setItem: (key, value) => data.set(key, String(value)),
        removeItem: key => data.delete(key),
    };
    try {
        return run(data);
    } finally {
        globalThis.localStorage = previous;
    }
}

test('corrupt mineru_deploy_lang_list does not break loadConfig', () => {
    withLocalStorage(data => {
        data.set('mineru_deploy_lang_list', 'not-json');
        const settings = useSettings();
        settings.loadConfig({});
        assert.deepEqual(settings.form.mineru_deploy_lang_list, []);
        assert.equal(data.has('mineru_deploy_lang_list'), false);
    });
});

test('non-array mineru_deploy_lang_list is normalised to an array', () => {
    withLocalStorage(data => {
        data.set('mineru_deploy_lang_list', '{"a":1}');
        const settings = useSettings();
        settings.loadConfig({});
        assert.deepEqual(settings.form.mineru_deploy_lang_list, []);
    });
});

test('queue concurrency is clamped on write and on reload', () => {
    withLocalStorage(() => {
        const settings = useSettings();

        settings.saveSetting('queue_concurrent', 0);
        assert.equal(settings.queue_concurrent.value, 1);

        settings.saveSetting('queue_concurrent', 9999);
        assert.equal(settings.queue_concurrent.value, MAX_QUEUE_CONCURRENT);

        settings.saveSetting('queue_concurrent', 'abc');
        assert.equal(settings.queue_concurrent.value, 1);

        // 重新加载旧数据（0 / 空 / 负数）时也要得到合法值
        globalThis.localStorage.setItem('queue_concurrent', '0');
        const reloaded = useSettings();
        reloaded.loadConfig({});
        assert.equal(reloaded.queue_concurrent.value, 3);
    });
});

test('platform provider round-trips through the per-platform key', () => {
    withLocalStorage(() => {
        const settings = useSettings();
        settings.form.platform = 'deepseek';
        settings.form.provider = 'gateway-v1';
        settings.saveAllSettings();

        const reloaded = useSettings();
        reloaded.loadConfig({});
        assert.equal(reloaded.form.platform, 'deepseek');
        assert.equal(reloaded.form.provider, 'gateway-v1');
    });
});

test('every confirmRemoveTranslatingTask key exists in all language files', () => {
    for (const lang of ['en', 'zh', 'vi']) {
        const path = join(here, '..', '..', 'public', 'i18n', `${lang}.json`);
        const dict = JSON.parse(readFileSync(path, 'utf8'));
        assert.ok(
            typeof dict.confirmRemoveTranslatingTask === 'string' && dict.confirmRemoveTranslatingTask.length > 0,
            `${lang}.json is missing confirmRemoveTranslatingTask`
        );
    }
});
