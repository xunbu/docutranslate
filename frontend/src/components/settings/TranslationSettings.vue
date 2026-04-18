<template>
    <!-- 3. Translation Settings -->
    <div class="accordion-item" v-show="!form.skip_translate">
        <h2 class="accordion-header">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                    data-bs-target="#collapseThree">
                <strong><span class="step-number">{{ stepNumber }} </span><i
                        class="bi bi-translate me-2"></i><span>{{ t('translationSettingsTitleText')
                    }}</span></strong>
            </button>
        </h2>
        <div id="collapseThree" class="accordion-collapse collapse">
            <div class="accordion-body">
                <div class="mb-3">
                    <label class="form-label">{{ t('targetLanguageLabel') }}</label>
                    <select class="form-select" v-model="form.to_lang"
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
                        <input type="text" class="form-control"
                               :class="{'is-invalid': errors.custom_to_lang}"
                               v-model="form.custom_to_lang"
                               @change="saveSetting('translator_custom_to_lang', form.custom_to_lang); clearError('custom_to_lang')"
                               :placeholder="t('customLangPlaceholder')">
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">{{ t('thinkingModeLabel') }}</label>
                    <i class="bi bi-question-circle ms-2" data-bs-toggle="tooltip"
                       :data-bs-title="t('thinkingModeTooltip')"></i>
                    <div class="btn-group w-100" role="group">
                        <input type="radio" class="btn-check" value="enable" id="thinkEn"
                               v-model="form.thinking"
                               @change="saveSetting('translator_thinking_mode', 'enable')">
                        <label class="btn btn-outline-primary"
                               for="thinkEn">{{ t('thinkingModeEnable') }}</label>
                        <input type="radio" class="btn-check" value="disable" id="thinkDis"
                               v-model="form.thinking"
                               @change="saveSetting('translator_thinking_mode', 'disable')">
                        <label class="btn btn-outline-primary"
                               for="thinkDis">{{ t('thinkingModeDisable') }}</label>
                        <input type="radio" class="btn-check" value="default" id="thinkDef"
                               v-model="form.thinking"
                               @change="saveSetting('translator_thinking_mode', 'default')">
                        <label class="btn btn-outline-primary"
                               for="thinkDef">{{ t('thinkingModeDefault') }}</label>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">{{ t('customPromptLabel') }}</label>
                    <textarea class="form-control" v-model="form.custom_prompt"
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
                    <label class="form-label">RPM <small class="text-muted">({{ t('rpmLabel')
                        }})</small></label>
                    <input type="number" class="form-control" v-model="form.rpm"
                           @change="saveSetting('rpm', form.rpm)"
                           min="1" :placeholder="t('unlimitedPlaceholder')">
                </div>
                <div class="mb-3">
                    <label class="form-label">TPM <small class="text-muted">({{ t('tpmLabel')
                        }})</small></label>
                    <input type="number" class="form-control" v-model="form.tpm"
                           @change="saveSetting('tpm', form.tpm)"
                           min="1" :placeholder="t('unlimitedPlaceholder')">
                </div>

                <div class="mb-3">
                    <label class="form-label">{{ t('extraBodyLabel') }} <small class="text-muted">(JSON)</small>
                        <i class="bi bi-question-circle ms-2" data-bs-toggle="tooltip"
                           :data-bs-title="t('extraBodyTooltip')"></i>
                    </label>
                    <textarea class="form-control" v-model="form.extra_body"
                              @change="saveSetting('extra_body', form.extra_body)"
                              rows="2"
                              :placeholder="t('extraBodyPlaceholder')"></textarea>
                </div>

            </div>
        </div>
    </div>
</template>

<script setup>
import SliderControl from '../common/SliderControl.vue';

const props = defineProps({
    t: Function,
    form: Object,
    errors: Object,
    defaultParams: Object,
    stepNumber: Number,
});

const emit = defineEmits(['saveSetting', 'clearError']);

const saveSetting = (k, v) => {
    localStorage.setItem(k, v);
    emit('saveSetting', k, v);
};
const clearError = (k) => {
    emit('clearError', k);
};
</script>
