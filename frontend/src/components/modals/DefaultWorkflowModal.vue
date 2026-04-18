<template>
    <Modal v-model="visible" :title="t('defaultWorkflowModalTitle')" size="xl">
        <div v-if="addExtensionError" class="mb-3 p-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded text-sm">
            {{ addExtensionError }}
        </div>
        <!-- Workflow Cards - 2 Column Layout -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            <div
                v-for="wf in workflowOptions"
                :key="wf.value"
                class="border rounded transition-colors"
                :class="workflowDragOver === wf.value ? 'border-primary ring-2 ring-primary/25' : 'border-gray-200 dark:border-gray-700'"
                @dragover.prevent="workflowDragOver = wf.value"
                @dragleave.prevent="workflowDragOver = null"
                @drop.prevent="onDropWorkflow($event, wf.value); workflowDragOver = null">
                <div class="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-800">
                    <span class="font-medium text-gray-700 dark:text-gray-300">{{ getSimpleWorkflowLabel(wf.value) }}</span>
                    <span class="px-2 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                        {{ getWorkflowExtensions(wf.value).length }}
                    </span>
                </div>
                <div class="p-2 min-h-[80px]">
                    <div class="flex flex-wrap gap-1 mb-2">
                        <span
                            v-for="ext in getWorkflowExtensions(wf.value)"
                            :key="ext"
                            class="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 rounded cursor-grab"
                            :class="{ 'opacity-50': draggingExt === ext }"
                            draggable="true"
                            @dragstart="onDragStart($event, ext)"
                            @dragend="onDragEnd($event)">
                            <span>.{{ ext }}</span>
                            <button
                                type="button"
                                class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                                @click.stop="deleteExtension(ext)"
                                :title="t('deleteExtTooltip')">
                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </span>
                    </div>
                    <!-- Inline add extension -->
                    <div class="flex items-center gap-1 max-w-[140px]">
                        <span class="text-gray-500 dark:text-gray-400">.</span>
                        <input
                            type="text"
                            class="flex-1 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-primary"
                            maxlength="10"
                            @keyup.enter="addExtToWorkflow(wf.value, $event)">
                        <button
                            type="button"
                            class="px-2 py-1 text-sm border border-primary text-primary rounded hover:bg-primary hover:text-white transition-colors"
                            @click="addExtToWorkflow(wf.value, $event)">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        <template #footer>
            <button
                type="button"
                class="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                @click="resetDefaultWorkflows"
                :title="t('resetBtn')">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
            </button>
        </template>
    </Modal>
</template>

<script setup>
import { ref, computed, inject } from 'vue';
import Modal from '../ui/Modal.vue';

const props = defineProps({
    t: Function,
});

const emit = defineEmits(['save']);

// Inject from parent
const default_workflows = inject('default_workflows');
const saveDefaultWorkflows = inject('saveDefaultWorkflows');

const DEFAULT_EXTENSIONS = ['pdf','png','jpg','jpeg','gif','bmp','webp','txt','md','docx','doc','xlsx','csv','xls','epub','pptx','ppt','srt','ass','json','html','htm'];
const DEFAULT_WORKFLOW_MAPPING = {
    pdf: 'markdown_based', png: 'markdown_based', jpg: 'markdown_based', jpeg: 'markdown_based',
    gif: 'markdown_based', bmp: 'markdown_based', webp: 'markdown_based',
    txt: 'txt', md: 'markdown_based',
    docx: 'docx', doc: 'docx',
    xlsx: 'xlsx', csv: 'xlsx', xls: 'xlsx',
    epub: 'epub',
    pptx: 'pptx', ppt: 'pptx',
    srt: 'srt', ass: 'ass',
    json: 'json', html: 'html', htm: 'html'
};

const ALL_EXTENSIONS = ref([...DEFAULT_EXTENSIONS]);
const workflowDragOver = ref(null);
const addExtensionError = ref('');
const draggingExt = ref(null);
const visible = ref(false);

const workflowOptions = [
    { value: 'markdown_based', label: 'Markdown' },
    { value: 'txt', label: 'TXT' },
    { value: 'docx', label: 'DOCX' },
    { value: 'xlsx', label: 'XLSX' },
    { value: 'epub', label: 'EPUB' },
    { value: 'pptx', label: 'PPTX' },
    { value: 'srt', label: 'SRT' },
    { value: 'ass', label: 'ASS' },
    { value: 'json', label: 'JSON' },
    { value: 'html', label: 'HTML' },
];

const workflowFullLabelKeys = {
    markdown_based: 'workflowOptionMarkdown',
    txt: 'workflowOptionTxt',
    docx: 'workflowOptionDocx',
    xlsx: 'workflowOptionXlsx',
    epub: 'workflowOptionEpub',
    pptx: 'workflowOptionPptx',
    srt: 'workflowOptionSrt',
    ass: 'workflowOptionAss',
    json: 'workflowOptionJson',
    html: 'workflowOptionHtml',
};

const getWorkflowFullLabel = (wf) => {
    const key = workflowFullLabelKeys[wf];
    return key ? props.t(key) : wf;
};

const getSimpleWorkflowLabel = (wf) => {
    const fullLabel = getWorkflowFullLabel(wf);
    return fullLabel.replace(/\s*\(.*$/, '');
};

const getWorkflowExtensions = (workflow) => {
    return ALL_EXTENSIONS.value.filter(ext => default_workflows[ext] === workflow);
};

const onDragStart = (e, ext) => {
    e.dataTransfer.setData('text/plain', ext);
    draggingExt.value = ext;
};

const onDragEnd = (e) => {
    draggingExt.value = null;
};

const onDropWorkflow = (e, workflow) => {
    const ext = e.dataTransfer.getData('text/plain');
    if (ext && ALL_EXTENSIONS.value.includes(ext)) {
        default_workflows[ext] = workflow;
        saveDefaultWorkflows();
        emit('save');
    }
};

const deleteExtension = (ext) => {
    delete default_workflows[ext];
    saveDefaultWorkflows();
    emit('save');
    const idx = ALL_EXTENSIONS.value.indexOf(ext);
    if (idx !== -1) {
        ALL_EXTENSIONS.value.splice(idx, 1);
    }
};

const addExtToWorkflow = (workflow, event) => {
    const input = event.target.closest('.flex').querySelector('input');
    const raw = (input.value || '').trim().toLowerCase().replace(/^\.+/, '');

    if (!raw) return;
    if (!/^[a-z0-9]+$/.test(raw)) {
        addExtensionError.value = props.t('addExtensionPlaceholder');
        return;
    }
    if (ALL_EXTENSIONS.value.includes(raw)) {
        addExtensionError.value = props.t('extensionExistsError');
        return;
    }

    addExtensionError.value = '';
    ALL_EXTENSIONS.value.push(raw);
    default_workflows[raw] = workflow;
    saveDefaultWorkflows();
    emit('save');
    input.value = '';
};

const resetDefaultWorkflows = () => {
    ALL_EXTENSIONS.value = [...DEFAULT_EXTENSIONS];
    Object.assign(default_workflows, DEFAULT_WORKFLOW_MAPPING);
    saveDefaultWorkflows();
    emit('save');
};

// Initialize ALL_EXTENSIONS from saved data
const initFromSaved = () => {
    const allExts = new Set([...DEFAULT_EXTENSIONS]);
    Object.keys(default_workflows).forEach(ext => allExts.add(ext));
    ALL_EXTENSIONS.value = [...allExts];
};

initFromSaved();

defineExpose({
    show: () => { visible.value = true; },
    hide: () => { visible.value = false; }
});
</script>
