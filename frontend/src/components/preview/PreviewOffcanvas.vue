<template>
    <div>
        <!-- Preview Offcanvas -->
        <div class="offcanvas offcanvas-end" tabindex="-1" id="previewOffcanvas" ref="previewOffcanvas">
            <div class="offcanvas-header border-bottom">
                <h5 class="offcanvas-title">
                    {{ previewMode === 'bilingual' ? t('preview_bilingual') : t('preview_translatedOnly') }}</h5>
                <div class="btn-group me-auto ms-4">
                    <button class="btn btn-sm" :class="previewMode === 'bilingual' ? 'btn-primary' : 'btn-outline-primary'"
                            @click="setPreviewMode('bilingual')">{{ t('previewBilingualBtn') }}
                    </button>
                    <button class="btn btn-sm"
                            :class="previewMode === 'translatedOnly' ? 'btn-primary' : 'btn-outline-primary'"
                            @click="setPreviewMode('translatedOnly')">{{ t('previewTranslatedOnlyBtn') }}
                    </button>
                </div>
                <button class="btn btn-sm btn-outline-secondary ms-2"
                        :class="{active: syncScrollEnabled, 'btn-primary': syncScrollEnabled}" @click="toggleSyncScroll"
                        data-bs-toggle="tooltip" :data-bs-title="t('syncScrollTooltip')"><i class="bi"
                                                                                   :class="syncScrollEnabled ? 'bi-link' : 'bi-link-45deg'"></i>
                </button>

                <!-- New Download Dropdown in Preview Header -->
                <div class="btn-group ms-2" v-if="previewTask && previewTask.downloads">
                    <button type="button" class="btn btn-sm btn-outline-primary dropdown-toggle" data-bs-toggle="dropdown">
                        <i class="bi bi-download me-1"></i><span>{{ t('taskCardDownloadBtn') }}</span>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li v-for="(link, key) in previewTask.downloads" :key="key">
                            <a class="dropdown-item" :href="link">
                                <i class="bi me-2" :class="getWorkflowIcon(key)"></i>
                                {{ key === 'markdown_zip' ? t('downloadMdZip') : (key === 'markdown' ? t('downloadMdEmbedded') : key.toUpperCase())
                                }}
                            </a>
                        </li>
                        <li v-if="previewTask.downloads.html">
                            <a class="dropdown-item" href="#" @click.prevent="printPdf(previewTask.downloads.html)">
                                <i class="bi bi-file-earmark-pdf me-2"></i>PDF
                            </a>
                        </li>
                    </ul>
                </div>

                <button type="button" class="btn-close ms-2" data-bs-dismiss="offcanvas"></button>
            </div>
            <div class="offcanvas-body d-flex flex-column p-2">
                <div class="preview-split-container flex-grow-1" ref="splitContainer">
                    <div id="originalPreviewContainer" class="preview-pane-wrapper" v-show="previewMode === 'bilingual'">
                        <h6 class="text-center text-muted small">{{ t('previewOriginal') }}</h6>
                        <div class="preview-pane" ref="originalPane"></div>
                    </div>
                    <div id="translatedPreviewContainer" class="preview-pane-wrapper">
                        <h6 class="text-center text-muted small">{{ t('previewTranslated') }}</h6>
                        <div class="preview-pane">
                            <iframe ref="translatedFrame" src="about:blank"></iframe>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <iframe id="printFrame" ref="printFrame" style="display: none;"></iframe>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { getFileIcon } from '../../utils/helpers';

const props = defineProps({
    t: Function,
    previewMode: String,
    syncScrollEnabled: Boolean,
    previewTask: Object,
});

const emit = defineEmits([
    'setPreviewMode',
    'toggleSyncScroll',
    'printPdf',
]);

const previewOffcanvas = ref(null);
const splitContainer = ref(null);
const originalPane = ref(null);
const translatedFrame = ref(null);
const printFrame = ref(null);

defineExpose({
    previewOffcanvas,
    splitContainer,
    originalPane,
    translatedFrame,
    printFrame,
});

const getWorkflowIcon = (key) => getFileIcon(key);
</script>
