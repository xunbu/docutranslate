import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ref } from 'vue';
import { useTasks } from './useTasks.js';

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
