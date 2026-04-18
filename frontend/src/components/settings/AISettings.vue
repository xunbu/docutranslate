<template>
    <!-- 2. AI Settings -->
    <Collapse>
        <template #header>
            <strong>
                <span class="step-number">{{ stepNumber }} </span>
                <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
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
