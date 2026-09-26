import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ref } from 'vue';
import { useTasks } from './useTasks.js';

for (const [engine, key, expected] of [
    ['mineru_deploy', 'local-service-key', 'local-service-key'],
    ['mineru_deploy', '', null],
    ['mineru', 'local-service-key', undefined],
    ['identity', 'local-service-key', undefined],
]) {
    test(`local MinerU key is scoped to its parser: ${engine}/${key || 'empty'}`, () => {
        const tasks = useTasks({
            form: { workflow_type: 'markdown_based', convert_engine: engine, mineru_deploy_api_key: key },
            workflowParams: {}, default_workflows: {}, queue_concurrent: ref(1),
        }, { glossaryData: ref({}) }, { t: key => key });
        assert.equal(tasks.buildPayload().mineru_deploy_api_key, expected);
    });
}

for (const [value, expected] of [[0, 0], ['0', 0], ['5', 5], ['', 99999], [undefined, 99999]]) {
    test(`MinerU end page preserves ${JSON.stringify(value)}`, () => {
        const form = {
            workflow_type: 'markdown_based', convert_engine: 'mineru_deploy',
            mineru_deploy_backend: 'standard', mineru_deploy_start_page: '0',
            mineru_deploy_end_page: value,
        };
        const tasks = useTasks({ form, workflowParams: {}, default_workflows: {}, queue_concurrent: ref(1) },
            { glossaryData: ref({}) }, { t: key => key });
        const payload = tasks.buildPayload();
        assert.equal(payload.mineru_deploy_end_page_id, expected);
        assert.equal(payload.mineru_deploy_start_page_id, 0);
    });
}

test('batch queue starts the next task after the previous task finishes', async () => {
    const originalFetch = globalThis.fetch;
    const originalSetInterval = globalThis.setInterval;
    const originalClearInterval = globalThis.clearInterval;
    const originalWindow = globalThis.window;
    const originalLocalStorage = globalThis.localStorage;
    const polling = [];
    const uploads = [];
    globalThis.window = { location: { pathname: '/' } };
    globalThis.localStorage = { setItem() {}, getItem() { return null; } };
    globalThis.setInterval = callback => { polling.push(callback); return polling.length; };
    globalThis.clearInterval = () => {};
    globalThis.fetch = async url => {
        if (url === '/service/translate/file') {
            uploads.push(url);
            return { ok: true, json: async () => ({ task_started: true, task_id: `task-${uploads.length}` }) };
        }
        if (url.startsWith('/service/logs/')) return { json: async () => ({ logs: [] }) };
        if (url.startsWith('/service/cancel/')) return { ok: true };
        if (url.startsWith('/service/status/')) return {
            ok: true,
            json: async () => ({ is_processing: false, download_ready: true, downloads: {} })
        };
        throw new Error(`Unexpected request: ${url}`);
    };
    try {
        const settings = {
            form: { workflow_type: 'markdown_based', convert_engine: 'identity', skip_translate: true },
            workflowParams: {}, default_workflows: {}, queue_concurrent: ref(1),
            errors: {}, webSkipValidation: ref(false)
        };
        const tasks = useTasks(settings, { glossaryData: ref({}) }, { t: key => key });
        const first = tasks.createNewTask();
        const second = tasks.createNewTask();
        first.file = new Blob(['first']);
        second.file = new Blob(['second']);
        tasks.runAllPendingTasks();
        await new Promise(setImmediate);
        assert.equal(uploads.length, 1);
        assert.equal(tasks.runningCount.value, 1);

        const queuedTask = tasks.pendingQueue[0];
        await tasks.removeTask(queuedTask);
        await polling[0]();
        await new Promise(setImmediate);
        assert.equal(uploads.length, 1, 'a removed pending task must not upload');
        assert.equal(tasks.runningCount.value, 0);

        const third = tasks.createNewTask();
        third.file = new Blob(['third']);
        const fourth = tasks.createNewTask();
        fourth.file = new Blob(['fourth']);
        tasks.runAllPendingTasks();
        await new Promise(setImmediate);
        assert.equal(uploads.length, 2);
        await polling[1]();
        await new Promise(setImmediate);
        assert.equal(uploads.length, 3, 'completion should start the next queued upload');
        const lastRunningTask = tasks.tasks.value.find(task => task.backendId === 'task-3');
        await tasks.toggleTaskState(lastRunningTask, settings.errors);
        assert.equal(tasks.runningCount.value, 0, 'cancellation should release the batch slot');
    } finally {
        globalThis.fetch = originalFetch;
        globalThis.setInterval = originalSetInterval;
        globalThis.clearInterval = originalClearInterval;
        globalThis.window = originalWindow;
        globalThis.localStorage = originalLocalStorage;
    }
});

test('task validation and payload use the task workflow without changing the selected workflow', async () => {
    const originalFetch = globalThis.fetch;
    const originalSetInterval = globalThis.setInterval;
    const originalWindow = globalThis.window;
    const originalLocalStorage = globalThis.localStorage;
    let payload;
    globalThis.window = { location: { pathname: '/' } };
    globalThis.localStorage = { setItem() {} };
    globalThis.setInterval = () => 1;
    globalThis.fetch = async (url, options) => {
        assert.equal(url, '/service/translate/file');
        payload = JSON.parse(options.body.get('payload'));
        return { ok: true, json: async () => ({ task_started: true, task_id: 'json-task' }) };
    };
    try {
        const form = { workflow_type: 'markdown_based', convert_engine: 'mineru', mineru_token: '', skip_translate: true };
        const settings = {
            form, workflowParams: { json: { json_paths: '$.title' } }, default_workflows: {},
            queue_concurrent: ref(1), errors: {}, webSkipValidation: ref(false)
        };
        const tasks = useTasks(settings, { glossaryData: ref({}) }, { t: key => key });
        const task = tasks.createNewTask();
        task.file = new Blob(['{"title":"hello"}']);
        task.detectedWorkflow = 'json';
        await tasks.toggleTaskState(task, settings.errors);
        assert.equal(payload.workflow_type, 'json');
        assert.deepEqual(payload.json_paths, ['$.title']);
        assert.equal(form.workflow_type, 'markdown_based');
        assert.equal(task.isTranslating, true);
    } finally {
        globalThis.fetch = originalFetch;
        globalThis.setInterval = originalSetInterval;
        globalThis.window = originalWindow;
        globalThis.localStorage = originalLocalStorage;
    }
});
