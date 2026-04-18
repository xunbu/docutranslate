<template>
    <div class="modal fade" id="defaultWorkflowModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">{{ t('defaultWorkflowModalTitle') }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div v-if="addExtensionError" class="alert alert-danger py-2 mb-3 small">
                        {{ addExtensionError }}
                    </div>
                    <!-- Workflow Cards - 2 Column Layout -->
                    <div class="row g-2">
                        <div class="col-md-6" v-for="wf in workflowOptions" :key="wf.value">
                            <div class="card h-100 workflow-card"
                                 :class="{'drag-over': workflowDragOver === wf.value}"
                                 @dragover.prevent="workflowDragOver = wf.value"
                                 @dragleave.prevent="workflowDragOver = null"
                                 @drop.prevent="onDropWorkflow($event, wf.value); workflowDragOver = null">
                                <div class="card-header py-2 d-flex justify-content-between align-items-center">
                                    <span class="fw-medium">{{ getSimpleWorkflowLabel(wf.value) }}</span>
                                    <span class="badge bg-secondary">{{ getWorkflowExtensions(wf.value).length }}</span>
                                </div>
                                <div class="card-body p-2 min-h-8">
                                    <div class="d-flex flex-wrap gap-1 mb-2">
                                        <span v-for="ext in getWorkflowExtensions(wf.value)" :key="ext"
                                              class="badge bg-light text-dark border d-flex align-items-center gap-1 pe-1 ext-badge"
                                              draggable="true"
                                              @dragstart="onDragStart($event, ext)"
                                              @dragend="onDragEnd($event)">
                                            <span>.{{ ext }}</span>
                                            <button type="button" class="btn-close btn-close-xs ms-1"
                                                    @click.stop="deleteExtension(ext)"
                                                    :title="t('deleteExtTooltip')"></button>
                                        </span>
                                    </div>
                                    <!-- Inline add extension -->
                                    <div class="input-group input-group-sm" style="max-width: 140px;">
                                        <span class="input-group-text">.</span>
                                        <input type="text" class="form-control"
                                               @keyup.enter="addExtToWorkflow(wf.value, $event)"
                                               maxlength="10">
                                        <button class="btn btn-outline-primary" type="button"
                                                @click="addExtToWorkflow(wf.value, $event)">
                                            <i class="bi bi-plus-lg"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline-secondary" @click="resetDefaultWorkflows" data-bs-toggle="tooltip" :title="t('resetBtn')">
                        <i class="bi bi-arrow-counterclockwise"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <style>
        .btn-close-xs {
            transform: scale(0.6);
            opacity: 0.6;
        }
        .btn-close-xs:hover {
            opacity: 1;
        }
        .min-h-8 {
            min-height: 80px;
        }
        .ext-badge {
            cursor: grab;
        }
        .ext-badge:active {
            cursor: grabbing;
        }
        .ext-badge.dragging {
            opacity: 0.5;
        }
        .workflow-card.drag-over {
            border-color: var(--bs-primary);
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }
    </style>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
    t: Function,
    defaultWorkflows: Object,
});

const emit = defineEmits(['update:defaultWorkflows', 'save']);

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

const customExtensions = computed(() => {
    return ALL_EXTENSIONS.value.filter(ext => !DEFAULT_EXTENSIONS.includes(ext));
});

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
    return ALL_EXTENSIONS.value.filter(ext => props.defaultWorkflows[ext] === workflow);
};

const onDragStart = (e, ext) => {
    e.dataTransfer.setData('text/plain', ext);
    e.target.classList.add('dragging');
};

const onDragEnd = (e) => {
    e.target.classList.remove('dragging');
};

const onDropWorkflow = (e, workflow) => {
    const ext = e.dataTransfer.getData('text/plain');
    if (ext && ALL_EXTENSIONS.value.includes(ext)) {
        const newWorkflows = { ...props.defaultWorkflows, [ext]: workflow };
        emit('update:defaultWorkflows', newWorkflows);
        emit('save');
    }
};

const deleteExtension = (ext) => {
    const newWorkflows = { ...props.defaultWorkflows };
    delete newWorkflows[ext];
    emit('update:defaultWorkflows', newWorkflows);
    emit('save');
    const idx = ALL_EXTENSIONS.value.indexOf(ext);
    if (idx !== -1) {
        ALL_EXTENSIONS.value.splice(idx, 1);
    }
};

const addExtToWorkflow = (workflow, event) => {
    const input = event.target.closest('.input-group').querySelector('input');
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
    const newWorkflows = { ...props.defaultWorkflows, [raw]: workflow };
    emit('update:defaultWorkflows', newWorkflows);
    emit('save');
    input.value = '';
};

const resetDefaultWorkflows = () => {
    ALL_EXTENSIONS.value = [...DEFAULT_EXTENSIONS];
    emit('update:defaultWorkflows', { ...DEFAULT_WORKFLOW_MAPPING });
    emit('save');
};

// Initialize ALL_EXTENSIONS from saved data
const initFromSaved = () => {
    const allExts = new Set([...DEFAULT_EXTENSIONS]);
    Object.keys(props.defaultWorkflows).forEach(ext => allExts.add(ext));
    ALL_EXTENSIONS.value = [...allExts];
};

initFromSaved();
</script>
