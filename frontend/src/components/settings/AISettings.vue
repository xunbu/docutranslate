<template>
    <!-- 2. AI Settings -->
    <Collapse>
        <template #header>
            <strong>
                <span class="step-number">{{ stepNumber }} </span>
                <Heroicon name="SparklesIcon" class="w-5 h-5 inline-block mr-2" />
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
                    <Heroicon name="QuestionMarkCircleIcon" class="w-4 h-4 text-gray-400 ml-2 cursor-help" />
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
import Heroicon from '../ui/Heroicon.vue';

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
