<template>
    <!-- 3. Translation Settings -->
    <Collapse v-show="!form.skip_translate" v-model="isOpen">
        <template #header>
            <strong>
                <span class="step-number">{{ stepNumber }} </span>
                <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
                <span>{{ t('translationSettingsTitleText') }}</span>
            </strong>
        </template>

        <div class="mb-3">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('targetLanguageLabel') }}</label>
            <select class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary" v-model="form.to_lang"
                    @change="saveSetting('translator_to_lang', form.to_lang)">
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
            <div class="mt-2" v-if="form.to_lang === 'custom'">
                <input type="text" class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
                       :class="{'border-red-500 dark:border-red-400': errors.custom_to_lang}"
                       v-model="form.custom_to_lang"
                       @change="saveSetting('translator_custom_to_lang', form.custom_to_lang); clearError('custom_to_lang')"
                       :placeholder="t('customLangPlaceholder')">
            </div>
        </div>

        <div class="mb-3">
            <div class="flex items-center mb-1">
                <label class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('thinkingModeLabel') }}</label>
                <Tooltip :content="t('thinkingModeTooltip')">
                    <svg class="w-4 h-4 ml-2 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </Tooltip>
            </div>
            <div class="flex rounded overflow-hidden border border-gray-300 dark:border-gray-600" role="group">
                <button type="button"
                        class="flex-1 px-3 py-1.5 text-sm transition-colors"
                        :class="form.thinking === 'enable'
                            ? 'bg-primary text-white'
                            : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'"
                        @click="form.thinking = 'enable'; saveSetting('translator_thinking_mode', 'enable')">
                    {{ t('thinkingModeEnable') }}
                </button>
                <button type="button"
                        class="flex-1 px-3 py-1.5 text-sm border-x border-gray-300 dark:border-gray-600 transition-colors"
                        :class="form.thinking === 'disable'
                            ? 'bg-primary text-white'
                            : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'"
                        @click="form.thinking = 'disable'; saveSetting('translator_thinking_mode', 'disable')">
                    {{ t('thinkingModeDisable') }}
                </button>
                <button type="button"
                        class="flex-1 px-3 py-1.5 text-sm transition-colors"
                        :class="form.thinking === 'default'
                            ? 'bg-primary text-white'
                            : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'"
                        @click="form.thinking = 'default'; saveSetting('translator_thinking_mode', 'default')">
                    {{ t('thinkingModeDefault') }}
                </button>
            </div>
        </div>

        <div class="mb-3">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('customPromptLabel') }}</label>
            <textarea class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary resize-none" v-model="form.custom_prompt"
                      @change="saveSetting('custom_prompt', form.custom_prompt)" rows="3"
                      :placeholder="t('customPromptPlaceholder')"></textarea>
        </div>

        <slider-control :label="t('chunkSizeLabel')" v-model="form.chunk_size"
                        save-key="chunk_size" :default-val="defaultParams.chunk_size"
                        :min="1000" :max="12000" :step="100" :t="t"></slider-control>
        <slider-control :label="t('concurrentLabel')" v-model="form.concurrent"
                        save-key="concurrent" :default-val="defaultParams.concurrent"
                        :min="1" :max="120" :step="1" :t="t"></slider-control>
        <slider-control label="Temperature" v-model="form.temperature"
                        save-key="temperature" :default-val="defaultParams.temperature"
                        :min="0" :max="2" :step="0.1" :t="t"></slider-control>
        <slider-control label="Top-P" v-model="form.top_p"
                        save-key="top_p" :default-val="defaultParams.top_p"
                        :min="0" :max="1" :step="0.05" :t="t"></slider-control>
        <slider-control :label="t('retryLabel')" v-model="form.retry" save-key="retry"
                        :default-val="defaultParams.retry" :min="1" :max="6" :step="1"
                        :t="t"></slider-control>

        <!-- New RPM/TPM Settings [Vertical Layout] -->
        <div class="mb-3">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">RPM <small class="text-sm text-gray-500 dark:text-gray-400">({{ t('rpmLabel') }})</small></label>
            <input type="number" class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary" v-model="form.rpm"
                   @change="saveSetting('rpm', form.rpm)"
                   min="1" :placeholder="t('unlimitedPlaceholder')">
        </div>
        <div class="mb-3">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">TPM <small class="text-sm text-gray-500 dark:text-gray-400">({{ t('tpmLabel') }})</small></label>
            <input type="number" class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary" v-model="form.tpm"
                   @change="saveSetting('tpm', form.tpm)"
                   min="1" :placeholder="t('unlimitedPlaceholder')">
        </div>

        <div class="mb-3">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {{ t('extraBodyLabel') }} <small class="text-sm text-gray-500 dark:text-gray-400">(JSON)</small>
                <Tooltip :content="t('extraBodyTooltip')">
                    <svg class="w-4 h-4 inline-block ml-2 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </Tooltip>
            </label>
            <textarea class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary resize-none" v-model="form.extra_body"
                      @change="saveSetting('extra_body', form.extra_body)"
                      rows="2"
                      :placeholder="t('extraBodyPlaceholder')"></textarea>
        </div>
    </Collapse>
</template>

<script setup>
import { ref, inject } from 'vue';
import Collapse from '../ui/Collapse.vue';
import Tooltip from '../ui/Tooltip.vue';
import SliderControl from '../common/SliderControl.vue';

const props = defineProps({
    t: Function,
    stepNumber: Number,
});

// Collapse state
const isOpen = ref(false);

// Inject from parent
const form = inject('form');
const errors = inject('errors');
const defaultParams = inject('defaultParams');
const saveSetting = inject('saveSetting');
const clearError = inject('clearError');
</script>
