<template>
    <div>
        <!-- Preview Offcanvas using Tailwind -->
        <Offcanvas v-model="isOpen" position="end" width="xl" :title="previewMode === 'bilingual' ? t('preview_bilingual') : t('preview_translatedOnly')">
            <template #header>
                <div class="flex items-center gap-2">
                    <h5 class="text-lg font-medium">
                        {{ previewMode === 'bilingual' ? t('preview_bilingual') : t('preview_translatedOnly') }}
                    </h5>
                    <div class="flex rounded overflow-hidden border border-gray-300 dark:border-gray-600">
                        <button
                            class="px-3 py-1 text-sm transition-colors"
                            :class="previewMode === 'bilingual' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'"
                            @click="setPreviewMode('bilingual')">
                            {{ t('previewBilingualBtn') }}
                        </button>
                        <button
                            class="px-3 py-1 text-sm transition-colors"
                            :class="previewMode === 'translatedOnly' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'"
                            @click="setPreviewMode('translatedOnly')">
                            {{ t('previewTranslatedOnlyBtn') }}
                        </button>
                    </div>
                    <Tooltip :content="t('syncScrollTooltip')" placement="top">
                        <button
                            class="p-1.5 rounded transition-colors"
                            :class="syncScrollEnabled ? 'bg-primary text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'"
                            @click="toggleSyncScroll">
                            <Heroicon name="LinkIcon" class="w-4 h-4" />
                        </button>
                    </Tooltip>

                    <!-- Download Dropdown -->
                    <Dropdown v-if="previewTask && previewTask.downloads" label="Download">
                        <template #trigger>
                            <button class="px-3 py-1.5 text-sm border border-primary text-primary rounded hover:bg-primary hover:text-white transition-colors flex items-center gap-1">
                                <Heroicon name="ArrowDownTrayIcon" class="w-4 h-4" />
                                <span>{{ t('taskCardDownloadBtn') }}</span>
                            </button>
                        </template>
                        <a v-for="(link, key) in previewTask.downloads" :key="key"
                           :href="link"
                           class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
                            <Heroicon :name="getDownloadIcon(key).name" class="w-4 h-4" />
                            {{ key === 'markdown_zip' ? t('downloadMdZip') : (key === 'markdown' ? t('downloadMdEmbedded') : key.toUpperCase()) }}
                        </a>
                        <a v-if="previewTask.downloads.html"
                           href="#"
                           @click.prevent="handlePrintPdf(previewTask.downloads.html)"
                           class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
                            <Heroicon name="DocumentTextIcon" class="w-4 h-4" />
                            PDF
                        </a>
                    </Dropdown>
                </div>
            </template>

            <div class="h-full flex flex-col">
                <div class="preview-split-container flex-1" ref="splitContainer">
                    <div id="originalPreviewContainer" class="preview-pane-wrapper" v-show="previewMode === 'bilingual'">
                        <h6 class="text-center text-gray-500 dark:text-gray-400 text-sm mb-2">{{ t('previewOriginal') }}</h6>
                        <div class="preview-pane" ref="originalPane"></div>
                    </div>
                    <div id="translatedPreviewContainer" class="preview-pane-wrapper">
                        <h6 class="text-center text-gray-500 dark:text-gray-400 text-sm mb-2">{{ t('previewTranslated') }}</h6>
                        <div class="preview-pane">
                            <iframe ref="translatedFrame" src="about:blank" class="w-full h-full border-0"></iframe>
                        </div>
                    </div>
                </div>
            </div>
        </Offcanvas>
        <iframe id="printFrame" ref="printFrame" style="display: none;"></iframe>
    </div>
</template>

<script setup>
import { ref, inject } from 'vue';
import { getDownloadIcon } from '../../utils/helpers';
import Offcanvas from '../ui/Offcanvas.vue';
import Tooltip from '../ui/Tooltip.vue';
import Dropdown from '../ui/Dropdown.vue';
import Heroicon from '../ui/Heroicon.vue';

const props = defineProps({
    t: Function,
});

const emit = defineEmits([
    'printPdf',
]);

// Inject from parent
const previewMode = inject('previewMode');
const syncScrollEnabled = inject('syncScrollEnabled');
const previewTask = inject('previewTask');
const isOpen = inject('previewIsOpen');
const setPreviewMode = inject('setPreviewMode');
const toggleSyncScroll = inject('toggleSyncScroll');
const printPdf = inject('printPdf');
const closePreview = inject('closePreview');

const splitContainer = ref(null);
const originalPane = ref(null);
const translatedFrame = ref(null);
const printFrame = ref(null);

defineExpose({
    splitContainer,
    originalPane,
    translatedFrame,
    printFrame,
});

const handlePrintPdf = (url) => {
    printPdf(url);
    emit('printPdf', url);
};
</script>

<style scoped>
.preview-pane-wrapper {
    min-height: 200px;
}
</style>
