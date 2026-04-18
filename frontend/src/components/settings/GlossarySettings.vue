<template>
    <!-- 4. Glossary Settings -->
    <div class="accordion-item">
        <h2 class="accordion-header">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                    data-bs-target="#collapseGlossary">
                <strong><span class="step-number">{{ stepNumber }} </span><i
                        class="bi bi-journal-bookmark me-2"></i><span>{{ t('glossaryGenTitle')
                    }}</span></strong>
            </button>
        </h2>
        <div id="collapseGlossary" class="accordion-collapse collapse">
            <div class="accordion-body">
                <div class="mb-3">
                    <label class="form-label">{{ t('glossaryLabel') }}</label>
                    <input class="form-control" type="file" @change="e => emit('handleGlossaryFiles', e)"
                           multiple accept=".csv" ref="glossaryInput">
                    <div class="form-text">{{ t('glossaryHelp') }}</div>
                    <div class="btn-group mt-2">
                        <button type="button" class="btn btn-sm btn-outline-info"
                                @click="emit('openGlossaryModal')">
                            <i class="bi bi-card-list me-1"></i><span>{{ t('viewGlossaryBtn') }} <span
                                v-if="glossaryCount">({{glossaryCount}})</span></span>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger"
                                @click="emit('clearGlossary')">
                            <i class="bi bi-trash me-1"></i><span>{{ t('clearGlossaryBtn')
                            }}</span>
                        </button>
                    </div>
                    <div class="mt-2">
                        <a href="javascript:void(0)" @click="emit('downloadGlossaryTemplate')" class="text-decoration-none small">
                            <i class="bi bi-download me-1"></i>{{ t('downloadGlossaryTemplateBtn') }}
                        </a>
                    </div>
                </div>

                <div class="form-check form-switch mb-3 border-top pt-3">
                    <input class="form-check-input" type="checkbox" role="switch"
                           v-model="form.glossary_generate_enable"
                           @change="saveSetting('glossary_generate_enable', form.glossary_generate_enable)">
                    <label class="form-check-label">{{ t('glossaryGenEnableLabel') }}</label>
                </div>

                <div v-if="form.glossary_generate_enable">
                    <div class="mb-3">
                        <label class="form-label">{{ t('glossaryCustomPromptLabel') }}</label>
                        <textarea class="form-control"
                                  v-model="form.glossary_agent_custom_prompt"
                                  @change="saveSetting('glossary_agent_custom_prompt', form.glossary_agent_custom_prompt)"
                                  rows="3"
                                  :placeholder="t('glossaryCustomPromptPlaceholder')"></textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">{{ t('glossaryGenConfigLabel') }}</label>
                        <div class="btn-group w-100">
                            <input type="radio" class="btn-check" value="same" id="gSame"
                                   v-model="form.glossary_agent_config_choice"
                                   @change="saveSetting('glossary_agent_config_choice', 'same')">
                            <label class="btn btn-outline-primary"
                                   for="gSame">{{ t('glossaryGenConfigSame') }}</label>
                            <input type="radio" class="btn-check" value="custom" id="gCustom"
                                   v-model="form.glossary_agent_config_choice"
                                   @change="saveSetting('glossary_agent_config_choice', 'custom')">
                            <label class="btn btn-outline-primary"
                                   for="gCustom">{{ t('glossaryGenConfigCustom') }}</label>
                        </div>
                    </div>

                    <div v-if="form.glossary_agent_config_choice === 'custom'"
                         class="border p-3 rounded">
                        <platform-selector
                                v-model:platform="form.glossary_agent_platform"
                                v-model:base-url="form.glossary_agent_baseurl"
                                v-model:api-key="form.glossary_agent_key"
                                v-model:model-id="form.glossary_agent_model_id"
                                v-model:provider="form.glossary_agent_provider"
                                :t="t" prefix="glossary_agent_platform"></platform-selector>

                        <div class="mb-3">
                            <label class="form-label">{{ t('targetLanguageLabel') }}</label>
                            <select class="form-select" v-model="form.glossary_agent_to_lang"
                                    @change="saveSetting('glossary_agent_to_lang', form.glossary_agent_to_lang)">
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
                                <input type="text" class="form-control"
                                       v-model="form.glossary_agent_custom_to_lang"
                                       @change="saveSetting('glossary_agent_custom_to_lang', form.glossary_agent_custom_to_lang)"
                                       :placeholder="t('customLangPlaceholder')">
                            </div>
                        </div>

                        <slider-control :label="t('chunkSizeLabel')"
                                        v-model="form.glossary_agent_chunk_size"
                                        save-key="glossary_agent_chunk_size"
                                        :default-val="defaultParams.chunk_size" :min="1000"
                                        :max="8000" :step="100" :t="t"></slider-control>
                        <slider-control :label="t('concurrentLabel')"
                                        v-model="form.glossary_agent_concurrent"
                                        save-key="glossary_agent_concurrent"
                                        :default-val="defaultParams.concurrent" :min="1"
                                        :max="120" :step="1" :t="t"></slider-control>
                        <slider-control label="Temperature"
                                        v-model="form.glossary_agent_temperature"
                                        save-key="glossary_agent_temperature" :default-val="0.7"
                                        :min="0" :max="2" :step="0.1" :t="t"></slider-control>
                        <slider-control label="Top-P"
                                        v-model="form.glossary_agent_top_p"
                                        save-key="glossary_agent_top_p" :default-val="0.9"
                                        :min="0" :max="1" :step="0.05" :t="t"></slider-control>
                        <slider-control :label="t('retryLabel')"
                                        v-model="form.glossary_agent_retry"
                                        save-key="glossary_agent_retry"
                                        :default-val="defaultParams.retry" :min="1" :max="6"
                                        :step="1" :t="t"></slider-control>

                        <!-- Glossary Agent RPM/TPM [Vertical Layout] -->
                        <div class="mb-3">
                            <label class="form-label">RPM <small
                                    class="text-muted">({{ t('rpmLabel')
                                }})</small></label>
                            <input type="number" class="form-control"
                                   v-model="form.glossary_agent_rpm"
                                   @change="saveSetting('glossary_agent_rpm', form.glossary_agent_rpm)"
                                   min="1" :placeholder="t('unlimitedPlaceholder')">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">TPM <small
                                    class="text-muted">({{ t('tpmLabel')
                                }})</small></label>
                            <input type="number" class="form-control"
                                   v-model="form.glossary_agent_tpm"
                                   @change="saveSetting('glossary_agent_tpm', form.glossary_agent_tpm)"
                                   min="1" :placeholder="t('unlimitedPlaceholder')">
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Extra Body <small class="text-muted">(JSON)</small></label>
                            <textarea class="form-control"
                                      v-model="form.glossary_agent_extra_body"
                                      @change="saveSetting('glossary_agent_extra_body', form.glossary_agent_extra_body)"
                                      rows="2"
                                      placeholder='{"user": "your-id", "other_param": "value"}'></textarea>
                            <div class="form-text">额外的 API 请求参数，JSON 格式，会合并到请求体中</div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">{{ t('thinkingModeLabel') }}</label>
                            <div class="btn-group w-100">
                                <input type="radio" class="btn-check" value="enable"
                                       id="gtEnable" v-model="form.glossary_agent_thinking"
                                       @change="saveSetting('glossary_agent_thinking_mode', 'enable')">
                                <label class="btn btn-outline-primary"
                                       for="gtEnable">{{ t('thinkingModeEnable') }}</label>
                                <input type="radio" class="btn-check" value="disable"
                                       id="gtDisable" v-model="form.glossary_agent_thinking"
                                       @change="saveSetting('glossary_agent_thinking_mode', 'disable')">
                                <label class="btn btn-outline-primary"
                                       for="gtDisable">{{ t('thinkingModeDisable') }}</label>
                                <input type="radio" class="btn-check" value="default"
                                       id="gtDefault" v-model="form.glossary_agent_thinking"
                                       @change="saveSetting('glossary_agent_thinking_mode', 'default')">
                                <label class="btn btn-outline-primary"
                                       for="gtDefault">{{ t('thinkingModeDefault') }}</label>
                            </div>
                        </div>
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" role="switch"
                                   v-model="form.glossary_agent_system_proxy_enable"
                                   @change="saveSetting('glossary_agent_system_proxy_enable', form.glossary_agent_system_proxy_enable)">
                            <label class="form-check-label">{{ t('systemProxyLabel') }}</label>
                        </div>
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" role="switch"
                                   v-model="form.glossary_agent_force_json"
                                   @change="saveSetting('glossary_agent_force_json', form.glossary_agent_force_json)">
                            <label class="form-check-label">{{ t('forceJson') }}</label>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue';
import PlatformSelector from '../common/PlatformSelector.vue';
import SliderControl from '../common/SliderControl.vue';

const props = defineProps({
    t: Function,
    form: Object,
    defaultParams: Object,
    glossaryCount: Number,
    stepNumber: Number,
});

const emit = defineEmits([
    'saveSetting',
    'handleGlossaryFiles',
    'openGlossaryModal',
    'clearGlossary',
    'downloadGlossaryTemplate',
]);

const saveSetting = (k, v) => {
    localStorage.setItem(k, v);
    emit('saveSetting', k, v);
};
</script>
