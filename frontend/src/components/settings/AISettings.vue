<template>
    <!-- 2. AI Settings -->
    <div class="accordion-item">
        <h2 class="accordion-header">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                    data-bs-target="#collapseTwo">
                <strong><span class="step-number">{{ stepNumber }} </span><i
                        class="bi bi-robot me-2"></i><span>{{ t('aiSettingsTitleText') }}</span></strong>
            </button>
        </h2>
        <div id="collapseTwo" class="accordion-collapse collapse">
            <div class="accordion-body">
                <div class="form-check form-switch mb-3">
                    <input class="form-check-input" type="checkbox" role="switch"
                           v-model="form.skip_translate"
                           @change="saveSetting('translator_skip_translate', form.skip_translate)">
                    <label class="form-check-label">{{ t('skipTranslationLabel') }}</label>
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

                                <div class="form-check form-switch mb-3">
                                    <input class="form-check-input" type="checkbox" role="switch"
                                           v-model="form.system_proxy_enable"
                                           @change="saveSetting('translator_system_proxy_enable', form.system_proxy_enable)">
                                    <label class="form-check-label">{{ t('systemProxyLabel') }}</label>
                                </div>
                                <div class="d-flex align-items-center mb-3">
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" role="switch"
                                               v-model="form.force_json"
                                               @change="saveSetting('translator_force_json', form.force_json)">
                                        <label class="form-check-label">{{ t('forceJson') }}</label>
                                    </div>
                                    <i class="bi bi-question-circle ms-2" data-bs-toggle="tooltip"
                                       :data-bs-title="t('forceJsonTooltip')"></i>
                                </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { inject } from 'vue';
import PlatformSelector from '../common/PlatformSelector.vue';

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
