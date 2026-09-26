import assert from 'node:assert/strict';
import { test } from 'node:test';
import { useSettings } from './useSettings.js';

test('local MinerU key is optional and persists through settings reload and clearing', () => {
    const previous = globalThis.localStorage;
    const data = new Map();
    globalThis.localStorage = {
        getItem: key => data.get(key) ?? null,
        setItem: (key, value) => data.set(key, String(value)),
    };
    try {
        const settings = useSettings();
        settings.loadConfig({});
        assert.equal(settings.form.mineru_deploy_api_key, '');
        settings.form.mineru_deploy_api_key = 'saved-service-key';
        settings.saveAllSettings();
        const restored = useSettings();
        restored.loadConfig({});
        assert.equal(restored.form.mineru_deploy_api_key, 'saved-service-key');
        restored.form.mineru_deploy_api_key = '';
        restored.saveAllSettings();
        settings.loadConfig({});
        assert.equal(settings.form.mineru_deploy_api_key, '');
    } finally {
        globalThis.localStorage = previous;
    }
});
