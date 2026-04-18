<template>
    <!-- 2. AI Settings -->
    <Collapse>
        <template #header>
            <strong>
                <span class="step-number">{{ stepNumber }} </span>
                <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M17.664 17.664l-.707-.707M12 21v-1M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l.707.707M3 12h1m5.663-5h4.673" />
                    <circle cx="12" cy="12" r="4" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                </svg>
                <span>{{ t('aiSettingsTitleText') }}</span>
            </strong>
        </template>

        <div class="mb-3">
            <Toggle
                v-model="form.skip_translate"
                :label="t('skipTranslationLabel')"
                @update:modelValue="saveSetting('translator_skip_translate', form.skip_translate)"
            />
        </div>

        <div v-show="!form.skip_translate">
            <platform-selector
                v-model:platform="form.platform"
                v-model:base-url="form.base_url"
                v-model:api-key="form.api_key"
                v-model:model-id="form.model_id"
                v-model:provider="form.provider"
                :invalid-api-key="errors.api_key"
                :invalid-base-url="errors.base_url"
                :invalid-model-id="errors.model_id"
                @clear-error="clearError"
                :t="t" prefix="translator_platform"></platform-selector>

            <div class="mb-3">
                <Toggle
                    v-model="form.system_proxy_enable"
                    :label="t('systemProxyLabel')"
                    @update:modelValue="saveSetting('translator_system_proxy_enable', form.system_proxy_enable)"
                />
            </div>

            <div class="flex items-center mb-3">
                <Toggle
                    v-model="form.force_json"
                    :label="t('forceJson')"
                    @update:modelValue="saveSetting('translator_force_json', form.force_json)"
                />
                <Tooltip :content="t('forceJsonTooltip')">
                    <svg class="w-4 h-4 text-gray-400 ml-2 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </Tooltip>
            </div>
        </div>
    </Collapse>
</template>

<script setup>
import { inject } from 'vue';
import PlatformSelector from '../common/PlatformSelector.vue';
import Collapse from '../ui/Collapse.vue';
import Toggle from '../ui/Toggle.vue';
import Tooltip from '../ui/Tooltip.vue';

const props = defineProps({
    t: Function,
    stepNumber: Number,
});

// Inject from parent
const form = inject('form');
const errors = inject('errors');
const saveSetting = inject('saveSetting');
const clearError = inject('clearError');
</script>
