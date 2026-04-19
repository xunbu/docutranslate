<template>
    <!-- 4. Glossary Settings -->
    <Collapse v-model="isOpen">
        <template #header>
            <strong>
                <Heroicon name="BookOpenIcon" class="w-5 h-5 inline-block mr-2" />
                <span>{{ t('glossaryGenTitle') }}</span>
            </strong>
        </template>
        <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('glossaryLabel') }}</label>
            <input
                class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-gray-100 file:text-gray-700 dark:file:bg-gray-600 dark:file:text-gray-200"
                type="file"
                @change="handleGlossaryFiles"
                multiple
                accept=".csv"
                ref="glossaryInput"
            >
            <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ t('glossaryHelp') }}</div>
            <div class="flex gap-2 mt-2">
                <button
                    type="button"
                    class="px-3 py-1.5 text-sm border border-info text-info rounded hover:bg-info hover:text-white transition-colors inline-flex items-center"
                    @click="openGlossaryModal"
                >
                    <Heroicon name="ClipboardDocumentListIcon" class="w-4 h-4 mr-1" />
                    <span>{{ t('viewGlossaryBtn') }} <span v-if="glossaryCount">({{ glossaryCount }})</span></span>
                </button>
                <button
                    type="button"
                    class="px-3 py-1.5 text-sm border border-danger text-danger rounded hover:bg-danger hover:text-white transition-colors inline-flex items-center"
                    @click="clearGlossary"
                >
                    <Heroicon name="TrashIcon" class="w-4 h-4 mr-1" />
                    <span>{{ t('clearGlossaryBtn') }}</span>
                </button>
            </div>
            <div class="mt-2">
                <a
                    href="javascript:void(0)"
                    @click="downloadGlossaryTemplate"
                    class="text-sm text-primary dark:text-blue-400 hover:underline inline-flex items-center"
                >
                    <Heroicon name="ArrowDownTrayIcon" class="w-4 h-4 mr-1" />
                    {{ t('downloadGlossaryTemplateBtn') }}
                </a>
            </div>
        </div>

        <div class="border-t border-gray-200 dark:border-gray-700 pt-3 mb-3">
            <Toggle
                v-model="form.glossary_generate_enable"
                :label="t('glossaryGenEnableLabel')"
                @update:model-value="saveSetting('glossary_generate_enable', form.glossary_generate_enable)"
            />
        </div>

        <div v-if="form.glossary_generate_enable">
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('glossaryCustomPromptLabel') }}</label>
                <textarea
                    class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                    v-model="form.glossary_agent_custom_prompt"
                    @change="saveSetting('glossary_agent_custom_prompt', form.glossary_agent_custom_prompt)"
                    rows="3"
                    :placeholder="t('glossaryCustomPromptPlaceholder')"
                ></textarea>
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('glossaryGenConfigLabel') }}</label>
                <div class="flex rounded overflow-hidden border border-gray-300 dark:border-gray-600">
                    <button
                        type="button"
                        class="flex-1 px-3 py-1.5 text-sm transition-colors"
                        :class="form.glossary_agent_config_choice === 'same' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'"
                        @click="form.glossary_agent_config_choice = 'same'; saveSetting('glossary_agent_config_choice', 'same')"
                    >
                        {{ t('glossaryGenConfigSame') }}
                    </button>
                    <button
                        type="button"
                        class="flex-1 px-3 py-1.5 text-sm transition-colors border-l border-gray-300 dark:border-gray-600"
                        :class="form.glossary_agent_config_choice === 'custom' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'"
                        @click="form.glossary_agent_config_choice = 'custom'; saveSetting('glossary_agent_config_choice', 'custom')"
                    >
                        {{ t('glossaryGenConfigCustom') }}
                    </button>
                </div>
            </div>

            <div
                v-if="form.glossary_agent_config_choice === 'custom'"
                class="border border-gray-300 dark:border-gray-600 p-3 rounded mb-4"
            >
                <platform-selector
                    v-model:platform="form.glossary_agent_platform"
                    v-model:base-url="form.glossary_agent_baseurl"
                    v-model:api-key="form.glossary_agent_key"
                    v-model:model-id="form.glossary_agent_model_id"
                    v-model:provider="form.glossary_agent_provider"
                    :t="t"
                    prefix="glossary_agent_platform"
                />

                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('targetLanguageLabel') }}</label>
                    <select
                        class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                        v-model="form.glossary_agent_to_lang"
                        @change="saveSetting('glossary_agent_to_lang', form.glossary_agent_to_lang)"
                    >
                        <option value="Simplified Chinese">中文(简体中文)</option>
                        <option value="English">英文(English)</option>
                        <option value="Spanish">西班牙文(Español)</option>
                        <option value="French">法文(Français)</option>
                        <option value="German">德文(Deutsch)</option>
                        <option value="Japanese">日文(日本語)</option>
                        <option value="Korean">韩文(한국어)</option>
                        <option value="Russian">俄文(Русский)</option>
                        <option value="Portuguese">葡萄牙文(Português)</option>
                        <option value="Arabic">阿拉伯文(العَرَبِيَّة)</option>
                        <option value="Vietnamese">越南文(tiếng Việt)</option>
                        <option value="custom">{{ t('targetLanguageCustom') }}</option>
                    </select>
                    <div class="mt-2" v-if="form.glossary_agent_to_lang === 'custom'">
                        <input
                            type="text"
                            class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                            v-model="form.glossary_agent_custom_to_lang"
                            @change="saveSetting('glossary_agent_custom_to_lang', form.glossary_agent_custom_to_lang)"
                            :placeholder="t('customLangPlaceholder')"
                        >
                    </div>
                </div>

                <slider-control
                    :label="t('chunkSizeLabel')"
                    v-model="form.glossary_agent_chunk_size"
                    save-key="glossary_agent_chunk_size"
                    :default-val="defaultParams.chunk_size"
                    :min="1000"
                    :max="8000"
                    :step="100"
                    :t="t"
                />
                <slider-control
                    :label="t('concurrentLabel')"
                    v-model="form.glossary_agent_concurrent"
                    save-key="glossary_agent_concurrent"
                    :default-val="defaultParams.concurrent"
                    :min="1"
                    :max="120"
                    :step="1"
                    :t="t"
                />
                <slider-control
                    label="Temperature"
                    v-model="form.glossary_agent_temperature"
                    save-key="glossary_agent_temperature"
                    :default-val="0.7"
                    :min="0"
                    :max="2"
                    :step="0.1"
                    :t="t"
                />
                <slider-control
                    label="Top-P"
                    v-model="form.glossary_agent_top_p"
                    save-key="glossary_agent_top_p"
                    :default-val="0.9"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    :t="t"
                />
                <slider-control
                    :label="t('retryLabel')"
                    v-model="form.glossary_agent_retry"
                    save-key="glossary_agent_retry"
                    :default-val="defaultParams.retry"
                    :min="1"
                    :max="6"
                    :step="1"
                    :t="t"
                />

                <!-- Glossary Agent RPM/TPM [Vertical Layout] -->
                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        RPM <small class="text-gray-500 dark:text-gray-400">({{ t('rpmLabel') }})</small>
                    </label>
                    <input
                        type="number"
                        class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                        v-model="form.glossary_agent_rpm"
                        @change="saveSetting('glossary_agent_rpm', form.glossary_agent_rpm)"
                        min="1"
                        :placeholder="t('unlimitedPlaceholder')"
                    >
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        TPM <small class="text-gray-500 dark:text-gray-400">({{ t('tpmLabel') }})</small>
                    </label>
                    <input
                        type="number"
                        class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                        v-model="form.glossary_agent_tpm"
                        @change="saveSetting('glossary_agent_tpm', form.glossary_agent_tpm)"
                        min="1"
                        :placeholder="t('unlimitedPlaceholder')"
                    >
                </div>

                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Extra Body <small class="text-gray-500 dark:text-gray-400">(JSON)</small>
                    </label>
                    <textarea
                        class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                        v-model="form.glossary_agent_extra_body"
                        @change="saveSetting('glossary_agent_extra_body', form.glossary_agent_extra_body)"
                        rows="2"
                        placeholder='{"user": "your-id", "other_param": "value"}'
                    ></textarea>
                    <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">额外的 API 请求参数，JSON 格式，会合并到请求体中</div>
                </div>

                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('thinkingModeLabel') }}</label>
                    <div class="flex rounded overflow-hidden border border-gray-300 dark:border-gray-600">
                        <button
                            type="button"
                            class="flex-1 px-3 py-1.5 text-sm transition-colors"
                            :class="form.glossary_agent_thinking === 'enable' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'"
                            @click="form.glossary_agent_thinking = 'enable'; saveSetting('glossary_agent_thinking_mode', 'enable')"
                        >
                            {{ t('thinkingModeEnable') }}
                        </button>
                        <button
                            type="button"
                            class="flex-1 px-3 py-1.5 text-sm transition-colors border-l border-gray-300 dark:border-gray-600"
                            :class="form.glossary_agent_thinking === 'disable' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'"
                            @click="form.glossary_agent_thinking = 'disable'; saveSetting('glossary_agent_thinking_mode', 'disable')"
                        >
                            {{ t('thinkingModeDisable') }}
                        </button>
                        <button
                            type="button"
                            class="flex-1 px-3 py-1.5 text-sm transition-colors border-l border-gray-300 dark:border-gray-600"
                            :class="form.glossary_agent_thinking === 'default' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'"
                            @click="form.glossary_agent_thinking = 'default'; saveSetting('glossary_agent_thinking_mode', 'default')"
                        >
                            {{ t('thinkingModeDefault') }}
                        </button>
                    </div>
                </div>
                <div class="mb-3">
                    <Toggle
                        v-model="form.glossary_agent_system_proxy_enable"
                        :label="t('systemProxyLabel')"
                        @update:model-value="saveSetting('glossary_agent_system_proxy_enable', form.glossary_agent_system_proxy_enable)"
                    />
                </div>
                <div class="mb-3">
                    <Toggle
                        v-model="form.glossary_agent_force_json"
                        :label="t('forceJson')"
                        @update:model-value="saveSetting('glossary_agent_force_json', form.glossary_agent_force_json)"
                    />
                </div>
            </div>
        </div>
    </Collapse>
</template>

<script setup>
import { inject, ref, computed } from 'vue';
import Collapse from '../ui/Collapse.vue';
import Toggle from '../ui/Toggle.vue';
import PlatformSelector from '../common/PlatformSelector.vue';
import SliderControl from '../common/SliderControl.vue';
import Heroicon from '../ui/Heroicon.vue';

const props = defineProps({
    t: Function,
});

// Inject from parent
const form = inject('form');
const defaultParams = inject('defaultParams');
const glossaryCount = inject('glossaryCount');
const saveSetting = inject('saveSetting');
const handleGlossaryFiles = inject('handleGlossaryFiles');
const clearGlossary = inject('clearGlossary');
const openGlossaryModal = inject('openGlossaryModal');
const downloadGlossaryTemplate = inject('downloadGlossaryTemplate');

const glossaryInput = ref(null);
const isOpen = ref(false);
</script>
