<template>
<div>
    <div class="container-fluid main-container">
        <div class="row gx-4">
            <!-- Left: Settings Panel -->
            <div class="col-lg-4">
                <div class="settings-panel">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div class="d-flex align-items-center">
                            <h4 class="mb-0 me-3 fw-bold" :title="t('pageTitle')">DocuTranslate</h4>
                            <div class="btn-group">
                                <button type="button" class="btn btn-sm btn-outline-info" data-bs-toggle="modal"
                                        data-bs-target="#tutorialModal">
                                    <i class="bi bi-question-circle-fill me-1"></i><span>{{ t('tutorialBtn') }}</span>
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-warning" data-bs-toggle="modal"
                                        data-bs-target="#contributorsModal">
                                    <i class="bi bi-people-fill me-1"></i><span>{{ t('projectContributeBtn') }}</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    <form id="translateForm" @submit.prevent>
                        <div class="accordion" id="settingsAccordion">

                            <!-- 1. Workflow Configuration (Merged) -->
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                                            data-bs-target="#collapseWorkflowConfig">
                                        <strong><span class="step-number">1</span><i
                                                class="bi bi-diagram-3 me-2"></i><span>{{ t('workflowConfigTitle')
                                            }}</span></strong>
                                    </button>
                                </h2>
                                <div id="collapseWorkflowConfig" class="accordion-collapse collapse">
                                    <div class="accordion-body">
                                        <!-- Top: Configure default workflow button -->
                                        <div class="mb-3">
                                            <button type="button" class="btn btn-outline-primary" @click="openDefaultWorkflowModal">
                                                <i class="bi bi-gear-fill me-2"></i>{{ t('openExtWorkflowBtn') }}
                                            </button>
                                        </div>
                                        <!-- Workflow type selection -->
                                        <div class="mb-3">
                                            <select class="form-select" v-model="form.workflow_type"
                                                    @change="saveSetting('translator_last_workflow', form.workflow_type)">
                                                <option value="markdown_based">{{ t('workflowOptionMarkdown') }}</option>
                                                <option value="docx">{{ t('workflowOptionDocx') }}</option>
                                                <option value="xlsx">{{ t('workflowOptionXlsx') }}</option>
                                                <option value="epub">{{ t('workflowOptionEpub') }}</option>
                                                <option value="txt">{{ t('workflowOptionTxt') }}</option>
                                                <option value="pptx">{{ t('workflowOptionPptx') }}</option>
                                                <option value="srt">{{ t('workflowOptionSrt') }}</option>
                                                <option value="ass">{{ t('workflowOptionAss') }}</option>
                                                <option value="json">{{ t('workflowOptionJson') }}</option>
                                                <option value="html">{{ t('workflowOptionHtml') }}</option>
                                            </select>
                                        </div>
                                        <hr>
                                        <!-- Workflow-specific options -->
                                        <template v-if="currentWorkflowConfig">
                                        <!-- Common Insert Mode -->
                                        <div class="mb-3" v-if="currentWorkflowConfig.hasInsertMode">
                                            <label class="form-label">{{ t('insertModeLabel') }}</label>
                                            <select class="form-select"
                                                    v-model="workflowParams[form.workflow_type].insert_mode"
                                                    @change="saveWorkflowParam('insert_mode')">
                                                <option value="replace">{{ t('insertModeReplace') }}</option>
                                                <option value="append">{{ t('insertModeAppend') }}</option>
                                                <option value="prepend">{{ t('insertModePrepend') }}</option>
                                            </select>
                                            <div class="form-text">
                                                {{ t(currentWorkflowConfig.insertHelpKey || 'insertModeHelpTxt') }}
                                            </div>
                                        </div>
                                        <!-- Common Separator -->
                                        <div class="mb-3" v-if="currentWorkflowConfig.hasInsertMode"
                                             v-show="['append', 'prepend'].includes(workflowParams[form.workflow_type].insert_mode)">
                                            <label class="form-label">{{ t('separatorLabel') }}</label>
                                            <input type="text" class="form-control"
                                                   v-model="workflowParams[form.workflow_type].separator"
                                                   @input="saveWorkflowParam('separator')"
                                                   :placeholder="t(currentWorkflowConfig.separatorPlaceholderKey || 'separatorPlaceholderSimple')">
                                            <div class="form-text"
                                                 v-html="t(currentWorkflowConfig.separatorHelpKey || 'separatorHelp')"></div>
                                        </div>

                                        <!-- TXT Specific -->
                                        <div class="mb-3" v-if="form.workflow_type === 'txt'">
                                            <label class="form-label">{{ t('segmentModeLabel') }}</label>
                                            <select class="form-select" v-model="workflowParams.txt.segment_mode"
                                                    @change="saveWorkflowParam('segment_mode')">
                                                <option value="line">{{ t('segmentModeLine') }}</option>
                                                <option value="paragraph">{{ t('segmentModeParagraph') }}</option>
                                                <option value="none">{{ t('segmentModeNone') }}</option>
                                            </select>
                                            <div class="form-text">{{ t('segmentModeHelp') }}</div>
                                        </div>
                                        <!-- XLSX Specific -->
                                        <div class="mb-3" v-if="form.workflow_type === 'xlsx'">
                                            <label class="form-label">{{ t('xlsxTranslateRegionsLabel') }}</label>
                                            <textarea class="form-control"
                                                      v-model="workflowParams.xlsx.translate_regions"
                                                      @input="saveWorkflowParam('translate_regions')" rows="3"
                                                      :placeholder="t('xlsxTranslateRegionsPlaceholder')"></textarea>
                                        </div>
                                        <!-- JSON Specific -->
                                        <div class="mb-3" v-if="form.workflow_type === 'json'">
                                            <label class="form-label">{{ t('jsonPathLabel') }}</label>
                                            <textarea class="form-control" :class="{'is-invalid': errors.json_paths}"
                                                      v-model="workflowParams.json.json_paths"
                                                      @input="saveWorkflowParam('json_paths'); clearError('json_paths')"
                                                      rows="4" required
                                                      :placeholder="t('jsonPathPlaceholder')"></textarea>
                                            <div class="form-text" v-html="t('jsonPathHelp')"></div>
                                        </div>
                                        </template>
                                        <!-- Markdown Parsing Settings (only shown for markdown_based workflow) -->
                                        <div v-if="form.workflow_type === 'markdown_based'">
                                            <div class="mb-3">
                                                <label class="form-label">{{ t('parsingEngineLabel') }}</label>
                                                <select class="form-select" v-model="form.convert_engine"
                                                        @change="saveSetting('translator_convert_engin', form.convert_engine)">
                                                    <option value="identity" v-if="showIdentityOption">
                                                        {{ t('engineOptionIdentity') || '已经是markdown' }}
                                                    </option>
                                                    <option v-for="eng in enginList" :key="eng" :value="eng">
                                                        {{ t('engineOption' + capitalize(eng)) || eng }}
                                                    </option>
                                                </select>
                                                <div class="form-text">{{ t('parsingEngineHelp') }}</div>
                                            </div>

                                            <!-- Mineru Cloud Config -->
                                            <div v-if="form.convert_engine === 'mineru'">
                                                <div class="mb-3">
                                                    <label class="form-label">Mineru Token <a
                                                            href="https://mineru.net/apiManage/token" target="_blank"
                                                            class="ms-1"><i
                                                            class="bi bi-box-arrow-up-right"></i></a></label>
                                                    <div class="input-group">
                                                        <input :type="showMineruToken ? 'text' : 'password'"
                                                               autocomplete="new-password" class="form-control"
                                                               :class="{'is-invalid': errors.mineru_token}"
                                                               v-model="form.mineru_token"
                                                               @change="saveSetting('translator_mineru_token', form.mineru_token); clearError('mineru_token')"
                                                               :placeholder="t('mineruTokenPlaceholder')">
                                                        <button class="btn btn-outline-secondary" type="button"
                                                                @click="showMineruToken = !showMineruToken"><i class="bi"
                                                                                                               :class="showMineruToken ? 'bi-eye' : 'bi-eye-slash'"></i>
                                                        </button>
                                                    </div>
                                                </div>
                                                <div class="mb-3">
                                                    <label class="form-label">{{ t('modelVersionLabel') }}</label>
                                                    <select class="form-select" v-model="form.model_version"
                                                            @change="saveSetting('translator_model_version', form.model_version)">
                                                        <option value="vlm">{{ t('modelVersionVlm') }}</option>
                                                        <option value="pipeline">{{ t('modelVersionPipline') }}</option>
                                                    </select>
                                                    <div class="form-text">{{ t('modelVersionHelp') }}</div>
                                                </div>
                                                <div class="mb-3">
                                                    <label class="form-label">{{ t('mineruLanguageLabel') }}</label>
                                                    <select class="form-select" v-model="form.mineru_language"
                                                            @change="saveSetting('translator_mineru_language', form.mineru_language)">
                                                        <option v-for="lang in mineruLangOptions" :key="lang.val" :value="lang.val">
                                                            {{ lang.label }}
                                                        </option>
                                                    </select>
                                                </div>
                                            </div>

                                            <!-- Mineru Local Deploy Config -->
                                            <div v-if="form.convert_engine === 'mineru_deploy'"
                                                 class="border p-3 rounded mb-3">
                                                <div class="mb-3">
                                                    <label class="form-label">{{ t('mineruDeployBaseUrlLabel') }}</label>
                                                    <input type="url" class="form-control"
                                                           :class="{'is-invalid': errors.mineru_deploy_base_url}"
                                                           v-model="form.mineru_deploy_base_url"
                                                           @change="saveSetting('mineru_deploy_base_url', form.mineru_deploy_base_url); clearError('mineru_deploy_base_url')"
                                                           required :placeholder="t('mineruDeployBaseUrlPlaceholder')">
                                                </div>
                                                <div class="mb-3">
                                                    <label class="form-label">{{ t('mineruDeployBackendLabel') }}</label>
                                                    <select class="form-select" v-model="form.mineru_deploy_backend"
                                                            @change="saveSetting('mineru_deploy_backend', form.mineru_deploy_backend)">
                                                        <option value="pipeline">pipeline</option>
                                                        <option value="vlm-auto-engine">vlm-auto-engine</option>
                                                        <option value="vlm-http-client">vlm-http-client</option>
                                                        <option value="hybrid-auto-engine">hybrid-auto-engine</option>
                                                        <option value="hybrid-http-client">hybrid-http-client</option>
                                                    </select>
                                                </div>

                                                <div class="mb-3">
                                                    <label class="form-label">{{ t('mineruDeployParseMethodLabel')
                                                        }}</label>
                                                    <select class="form-select" v-model="form.mineru_deploy_parse_method"
                                                            @change="saveSetting('mineru_deploy_parse_method', form.mineru_deploy_parse_method)">
                                                        <option value="auto">auto</option>
                                                        <option value="txt">txt</option>
                                                        <option value="ocr">ocr</option>
                                                    </select>
                                                </div>

                                                <!-- Condition: If Backend is Pipeline or Hybrid, show Lang List -->
                                                <div class="mb-3"
                                                     v-if="['pipeline', 'hybrid-auto-engine', 'hybrid-http-client'].includes(form.mineru_deploy_backend)">
                                                    <label class="form-label">{{ t('mineruDeployLangListLabel') }}</label>
                                                    <div class="lang-list-container">
                                                        <div class="form-check" v-for="lang in mineruLangOptions"
                                                             :key="lang.val">
                                                            <input class="form-check-input" type="checkbox"
                                                                   :value="lang.val"
                                                                   :id="'langCheck-'+lang.val"
                                                                   v-model="form.mineru_deploy_lang_list"
                                                                   @change="saveSettingArray('mineru_deploy_lang_list', form.mineru_deploy_lang_list)">
                                                            <label class="form-check-label" :for="'langCheck-'+lang.val">
                                                                {{ lang.label }}
                                                            </label>
                                                        </div>
                                                    </div>
                                                </div>

                                                <!-- Condition: If Backend is vlm-http-client or hybrid-http-client, show Server URL -->
                                                <div class="mb-3"
                                                     v-if="['vlm-http-client', 'hybrid-http-client'].includes(form.mineru_deploy_backend)">
                                                    <label class="form-label">{{ t('mineruDeployServerUrlLabel') }}</label>
                                                    <input type="url" class="form-control"
                                                           v-model="form.mineru_deploy_server_url"
                                                           @change="saveSetting('mineru_deploy_server_url', form.mineru_deploy_server_url)"
                                                           :placeholder="t('mineruDeployServerUrlPlaceholder')">
                                                </div>

                                                <div class="row">
                                                    <div class="col-md-6 mb-3">
                                                        <label class="form-label">{{ t('mineruDeployStartPageLabel')
                                                            }}</label>
                                                        <input type="number" class="form-control"
                                                               v-model="form.mineru_deploy_start_page"
                                                               @change="saveSetting('mineru_deploy_start_page', form.mineru_deploy_start_page)"
                                                               min="0">
                                                    </div>
                                                    <div class="col-md-6 mb-3">
                                                        <label class="form-label">{{ t('mineruDeployEndPageLabel')
                                                            }}</label>
                                                        <input type="number" class="form-control"
                                                               v-model="form.mineru_deploy_end_page"
                                                               @change="saveSetting('mineru_deploy_end_page', form.mineru_deploy_end_page)"
                                                               min="0">
                                                    </div>
                                                </div>
                                                <div class="form-check form-switch mb-2">
                                                    <input class="form-check-input" type="checkbox" role="switch"
                                                           v-model="form.mineru_deploy_formula_enable"
                                                           @change="saveSetting('mineru_deploy_formula_enable', form.mineru_deploy_formula_enable)">
                                                    <label class="form-check-label">{{ t('mineruDeployFormulaEnableLabel')
                                                        }}</label>
                                                </div>
                                                <div class="form-check form-switch mb-2">
                                                    <input class="form-check-input" type="checkbox" role="switch"
                                                           v-model="form.mineru_deploy_table_enable"
                                                           @change="saveSetting('mineru_deploy_table_enable', form.mineru_deploy_table_enable)">
                                                    <label class="form-check-label">{{ t('mineruDeployTableEnableLabel')
                                                        }}</label>
                                                </div>
                                            </div>


                                            <div class="mt-3">
                                                <div class="form-check form-switch mb-2" v-if="ocrOptions.showFormula">
                                                    <input class="form-check-input" type="checkbox" role="switch"
                                                           v-model="form.formula_ocr"
                                                           @change="saveSetting('translator_formula_ocr', form.formula_ocr)">
                                                    <label class="form-check-label">{{ t('formulaOcrLabel') }}</label>
                                                </div>
                                                <div class="form-check form-switch mb-2" v-if="ocrOptions.showCode">
                                                    <input class="form-check-input" type="checkbox" role="switch"
                                                           v-model="form.code_ocr"
                                                           @change="saveSetting('translator_code_ocr', form.code_ocr)">
                                                    <label class="form-check-label">{{ t('codeOcrLabel') }}</label>
                                                </div>
                                            </div>

                                            <!-- Markdown to Docx Engine Selector -->
                                            <div class="border-top mt-3  pt-3">
                                                <label class="form-label">{{ t('md2docxEngineLabel') || 'Markdown转Docx引擎'
                                                    }}</label>
                                                <select class="form-select" v-model="form.md2docx_engine"
                                                        @change="saveSetting('translator_md2docx_engine', form.md2docx_engine)">
                                                    <option :value="null">{{ t('engineOptionNone') || '不生成docx' }}
                                                    </option>
                                                    <option value="auto">{{ t('engineOptionAuto') || '自动选择' }}</option>
                                                    <option value="python">{{ t('engineOptionPython') || '纯Python' }}
                                                    </option>
                                                    <option value="pandoc">{{ t('engineOptionPandoc') || 'Pandoc' }}
                                                    </option>
                                                </select>
                                                <div class="form-text">{{ t('md2docxEngineHelp') || '选择将Markdown导出为Docx的方式'
                                                    }}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 2. AI Settings -->
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                                            data-bs-target="#collapseTwo">
                                        <strong><span class="step-number">{{ stepMap.ai }} </span><i
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

                            <!-- 3. Translation Settings -->
                            <div class="accordion-item" v-show="!form.skip_translate">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                                            data-bs-target="#collapseThree">
                                        <strong><span class="step-number">{{ stepMap.trans }} </span><i
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

                            <!-- 4. Glossary Settings -->
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                                            data-bs-target="#collapseGlossary">
                                        <strong><span class="step-number">{{ stepMap.glossary }} </span><i
                                                class="bi bi-journal-bookmark me-2"></i><span>{{ t('glossaryGenTitle')
                                            }}</span></strong>
                                    </button>
                                </h2>
                                <div id="collapseGlossary" class="accordion-collapse collapse">
                                    <div class="accordion-body">
                                        <div class="mb-3">
                                            <label class="form-label">{{ t('glossaryLabel') }}</label>
                                            <input class="form-control" type="file" @change="handleGlossaryFiles"
                                                   multiple accept=".csv" ref="glossaryInput">
                                            <div class="form-text">{{ t('glossaryHelp') }}</div>
                                            <div class="btn-group mt-2">
                                                <button type="button" class="btn btn-sm btn-outline-info"
                                                        @click="openGlossaryModal">
                                                    <i class="bi bi-card-list me-1"></i><span>{{ t('viewGlossaryBtn') }} <span
                                                        v-if="glossaryCount">({{glossaryCount}})</span></span>
                                                </button>
                                                <button type="button" class="btn btn-sm btn-outline-danger"
                                                        @click="clearGlossary">
                                                    <i class="bi bi-trash me-1"></i><span>{{ t('clearGlossaryBtn')
                                                    }}</span>
                                                </button>
                                            </div>
                                            <div class="mt-2">
                                                <a href="javascript:void(0)" @click="downloadGlossaryTemplate" class="text-decoration-none small">
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
                        </div>
                    </form>

                    <!-- Import/Export -->
                    <div class="d-flex justify-content-center gap-2 mt-4">
                        <button type="button" class="btn btn-outline-primary" @click="configFile.click()"><i
                                class="bi bi-box-arrow-in-down me-1"></i><span>{{ t('importConfigBtn') }}</span>
                        </button>
                        <button type="button" class="btn btn-outline-secondary" @click="exportConfig"><i
                                class="bi bi-box-arrow-up me-1"></i><span>{{ t('exportConfigBtn') }}</span></button>
                    </div>
                    <input type="file" ref="configFile" class="d-none" accept=".json" @change="importConfig">

                    <!-- Project Info -->
                    <div class="mt-4 text-center text-muted small project-info">
                        <p class="bi bi-github mb-2"> {{ t('githubHomepage') }}<br/><a
                                href="https://github.com/xunbu/docutranslate" target="_blank">https://github.com/xunbu/docutranslate</a>
                        </p>
                        <p class="bi bi-tencent-qq mb-2"> {{ t('qqGroup') }}</p>
                        <p class="bi mb-0">version:<span>{{ version ? 'v' + version : '' }}</span></p>
                    </div>
                </div>
            </div>

            <!-- Right: Task Area -->
            <div class="col-lg-8">
                <div class="task-area">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4 class="mb-0"><i class="bi bi-list-task me-2"></i><span>{{ t('taskListTitle') }}</span></h4>
                        <div class="d-flex gap-2">
                            <button class="btn btn-outline-danger" @click="clearAllTasks()" v-if="tasks.length > 0"><i
                                    class="bi bi-trash me-2"></i><span>{{ t('clearAllTasksBtn') }}</span></button>
                            <input type="file" id="folderInput" ref="folderInput" class="d-none" webkitdirectory directory multiple
                                   @change="handleFolderSelect($event)">
                            <button class="btn btn-outline-primary" @click="$refs.folderInput.click()">
                                <i class="bi bi-folder-fill me-2"></i><span>{{ t('importFolderBtn') }}</span>
                            </button>
                            <button class="btn btn-success" @click="runAllPendingTasks()" v-if="hasPendingTasks">
                                <i class="bi bi-play-fill me-2"></i><span>{{ t('runAllBtn') }}</span>
                            </button>
                            <button class="btn btn-primary" @click="createNewTask()"><i
                                    class="bi bi-plus-circle-fill me-2"></i><span>{{ t('newTaskBtn') }}</span></button>
                            <button type="button" class="btn btn-outline-primary icon-btn"
                                    :title="t('queueConcurrentLabel')"
                                    data-bs-toggle="modal" data-bs-target="#queueSettingsModal">
                                <i class="bi bi-gear-fill"></i>
                            </button>
                        </div>
                    </div>
                    <div id="task-container">
                        <div v-if="tasks.length === 0" class="text-center text-muted mt-5">
                            <img src="/static/favicon.ico" alt="LOGO" style="width:10%;min-width: 55px; height: auto;">
                            <p class="mt-3">{{ t('noTaskPlaceholder') }}</p>
                        </div>
                        <div v-for="task in tasks" :key="task.uiId" class="card mb-3 task-card" @click="selectTaskWorkflow(task)">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <span class="fw-bold"><span>{{ t('taskCardIdLabel')
                                    }}</span>: <code>{{ task.backendId || t('taskCardIdPlaceholder') }}</code></span>
                                <button type="button" class="btn-close" @click.stop="removeTask(task)"></button>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-5">
                                        <input type="file" class="d-none" :id="'fileInput-' + task.uiId"
                                               @change="handleTaskFileSelect($event, task)">
                                        <div class="file-drop-area"
                                             :class="{'drag-over': task.isDragOver, 'file-selected': !!task.file, 'input-error': task.validationError}"
                                             @click.stop="triggerFileInput(task.uiId)"
                                             @dragenter.prevent="task.isDragOver = true"
                                             @dragover.prevent="task.isDragOver = true"
                                             @dragleave.prevent="task.isDragOver = false"
                                             @drop.prevent="handleTaskFileDrop($event, task)">
                                            <div v-if="!task.file" class="file-drop-default">
                                                <i class="bi bi-cloud-arrow-up fs-1"></i>
                                                <p class="mb-0">{{ t('taskCardFileDrop') }}</p>
                                            </div>
                                            <div v-else class="file-drop-selected">
                                                <i class="bi bi-check-circle-fill fs-1 text-success"></i>
                                                <p class="mb-0 mt-2 fw-bold text-success">{{ t('taskCardFileSelected')
                                                    }}</p>
                                            </div>
                                        </div>
                                        <div class="mt-2" v-if="task.file || task.fileName">
                                            <span class="fw-bold">{{ t('taskCardFilenameLabel') }} </span><span
                                                class="text-success">{{ task.fileName || task.file.name }}</span>
                                        </div>
                                    </div>
                                    <div class="col-md-7">
                                        <h6><i class="bi bi-terminal me-2"></i><span>{{ t('taskCardLogLabel') }}</span>
                                        </h6>
                                        <div class="log-area-wrapper">
                                            <div class="log-area" v-html="task.logs" :id="'log-' + task.uiId"></div>
                                            <button type="button" class="btn btn-sm btn-outline-secondary copy-log-btn"
                                                    @click.stop="copyLog($event, task.logs)" data-bs-toggle="tooltip"
                                                    :data-bs-title="t('copyLogsTooltip')">
                                                <i class="bi bi-clipboard"></i>
                                            </button>
                                        </div>
                                        <div class="mt-2 d-flex align-items-center">
                                            <span class="small"
                                                  :class="task.statusClass">
                                                <template v-if="task.queuePosition && !task.isTranslating && !task.isFinished">
                                                    {{ t('taskCardQueuePosition', { n: task.queuePosition, total: task.queueTotal }) }}
                                                </template>
                                                <template v-else>
                                                    {{ task.statusMessage || t('taskCardStatusWaiting') }}
                                                </template>
                                            </span>
                                            <div v-if="task.isProcessing" class="spinner-border spinner-border-sm ms-2"
                                                 role="status"></div>
                                            <span v-if="task.isProcessing"
                                                  class="ms-2 small text-muted">{{ task.progressPercent || 0 }}%</span>
                                        </div>
                                        <!-- Progress Bar - 不影响卡片布局 -->
                                        <div v-if="task.isProcessing" class="progress"
                                             style="height: 4px; min-height: 4px; margin-top: 4px;">
                                            <div class="progress-bar bg-primary"
                                                 :class="{'progress-bar-striped progress-bar-animated': task.progressPercent < 100}"
                                                 :style="{width: (task.progressPercent || 0) + '%'}"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="card-footer d-flex justify-content-between align-items-center">
                                <div class="download-buttons" v-if="task.downloads">
                                    <button class="btn btn-sm btn-success me-1" v-if="task.downloads.html"
                                            @click.stop="openPreview(task)"><i
                                            class="bi bi-eye-fill me-1"></i><span>{{ t('taskCardPreviewBtn') }}</span>
                                    </button>
                                    <div class="btn-group me-1">
                                        <button type="button" class="btn btn-sm btn-secondary dropdown-toggle"
                                                data-bs-toggle="dropdown"><i
                                                class="bi bi-download me-1"></i><span>{{ t('taskCardDownloadBtn')
                                            }}</span></button>
                                        <ul class="dropdown-menu">
                                            <li v-for="(link, key) in task.downloads" :key="key">
                                                <a class="dropdown-item" :href="link"><i class="bi me-2"
                                                                                         :class="getWorkflowIcon(key)"></i>{{ key === 'markdown_zip' ? t('downloadMdZip') : (key === 'markdown' ? t('downloadMdEmbedded') : key.toUpperCase())
                                                    }}</a>
                                            </li>
                                            <li v-if="task.downloads.html">
                                                <a class="dropdown-item" href="#"
                                                   @click.stop.prevent="printPdf(task.downloads.html)"><i
                                                        class="bi bi-file-earmark-pdf me-2"></i>PDF</a>
                                            </li>
                                        </ul>
                                    </div>
                                    <div class="btn-group"
                                         v-if="task.attachment && Object.keys(task.attachment).length">
                                        <button type="button" class="btn btn-sm btn-info dropdown-toggle"
                                                data-bs-toggle="dropdown"><i
                                                class="bi bi-paperclip me-1"></i><span>{{ t('taskCardAttachmentBtn')
                                            }}</span></button>
                                        <ul class="dropdown-menu">
                                            <li v-for="(link, name) in task.attachment" :key="name"><a
                                                    class="dropdown-item" :href="link"><i
                                                    class="bi bi-file-earmark-arrow-down me-2"></i>{{ name }}</a></li>
                                        </ul>
                                    </div>
                                </div>
                                <button class="btn ms-auto" :class="task.isTranslating ? 'btn-danger' : 'btn-primary'"
                                        @click.stop="toggleTaskState(task)" :disabled="task.initializing">
                                    <span v-if="task.initializing"><span
                                            class="spinner-border spinner-border-sm"></span> {{ t('btn_initializing') }}</span>
                                    <span v-else-if="task.isTranslating"><i
                                            class="bi bi-stop-circle-fill me-1"></i>{{ t('btn_cancelTranslation')
                                        }}</span>
                                    <span v-else-if="task.isFinished"><i
                                            class="bi bi-arrow-clockwise me-1"></i>{{ t('btn_reTranslate') }}</span>
                                    <span v-else><i class="bi bi-play-fill me-1"></i>{{ t('taskCardStartBtn') }}</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modals -->
    <div class="modal fade" id="glossaryModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header"><h5 class="modal-title">{{ t('glossaryModalTitle') }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <table class="table table-striped table-hover">
                        <thead>
                        <tr>
                            <th>{{ t('glossaryTableSource') }}</th>
                            <th>{{ t('glossaryTableDestination') }}</th>
                        </tr>
                        </thead>
                        <tbody>
                        <tr v-for="(dst, src) in glossaryData" :key="src">
                            <td>{{ src }}</td>
                            <td>{{ dst }}</td>
                        </tr>
                        <tr v-if="Object.keys(glossaryData).length === 0">
                            <td colspan="2" class="text-center text-muted">{{ t('glossaryEmpty') }}</td>
                        </tr>
                        </tbody>
                    </table>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ t('closeBtn') }}</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Default Workflow Settings Modal -->
    <div class="modal fade" id="defaultWorkflowModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">{{ t('defaultWorkflowModalTitle') }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div v-if="addExtensionError" class="alert alert-danger py-2 mb-3 small">
                        {{ addExtensionError }}
                    </div>
                    <!-- Workflow Cards - 2 Column Layout -->
                    <div class="row g-2">
                        <div class="col-md-6" v-for="wf in workflowOptions" :key="wf.value">
                            <div class="card h-100 workflow-card"
                                 :class="{'drag-over': workflowDragOver === wf.value}"
                                 @dragover.prevent="workflowDragOver = wf.value"
                                 @dragleave.prevent="workflowDragOver = null"
                                 @drop.prevent="onDropWorkflow($event, wf.value); workflowDragOver = null">
                                <div class="card-header py-2 d-flex justify-content-between align-items-center">
                                    <span class="fw-medium">{{ getSimpleWorkflowLabel(wf.value) }}</span>
                                    <span class="badge bg-secondary">{{ getWorkflowExtensions(wf.value).length }}</span>
                                </div>
                                <div class="card-body p-2 min-h-8">
                                    <div class="d-flex flex-wrap gap-1 mb-2">
                                        <span v-for="ext in getWorkflowExtensions(wf.value)" :key="ext"
                                              class="badge bg-light text-dark border d-flex align-items-center gap-1 pe-1 ext-badge"
                                              draggable="true"
                                              @dragstart="onDragStart($event, ext)"
                                              @dragend="onDragEnd($event)">
                                            <span>.{{ ext }}</span>
                                            <button type="button" class="btn-close btn-close-xs ms-1"
                                                    @click.stop="deleteExtension(ext)"
                                                    :title="t('deleteExtTooltip')"></button>
                                        </span>
                                    </div>
                                    <!-- Inline add extension -->
                                    <div class="input-group input-group-sm" style="max-width: 140px;">
                                        <span class="input-group-text">.</span>
                                        <input type="text" class="form-control"
                                               @keyup.enter="addExtToWorkflow(wf.value, $event)"
                                               maxlength="10">
                                        <button class="btn btn-outline-primary" type="button"
                                                @click="addExtToWorkflow(wf.value, $event)">
                                            <i class="bi bi-plus-lg"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline-secondary" @click="resetDefaultWorkflows" data-bs-toggle="tooltip" :title="t('resetBtn')">
                        <i class="bi bi-arrow-counterclockwise"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <style>
        .btn-close-xs {
            transform: scale(0.6);
            opacity: 0.6;
        }
        .btn-close-xs:hover {
            opacity: 1;
        }
        .min-h-8 {
            min-height: 80px;
        }
        .ext-badge {
            cursor: grab;
        }
        .ext-badge:active {
            cursor: grabbing;
        }
        .ext-badge.dragging {
            opacity: 0.5;
        }
        .workflow-card.drag-over {
            border-color: var(--bs-primary);
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }
    </style>

    <div class="modal fade" id="tutorialModal" tabindex="-1">
        <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header"><h5 class="modal-title"><i
                        class="bi bi-book-half me-2"></i>{{ t('tutorialModalTitle') }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body" v-html="t('tutorialModalBody')"></div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" data-bs-dismiss="modal">{{ t('tutorialUnderstandBtn')
                        }}
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="contributorsModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header"><h5 class="modal-title"><i
                        class="bi bi-heart-fill me-2 text-danger"></i>{{ t('contributorsModalTitle') }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>{{ t('contributorsPara1') }}</p>
                    <p>{{ t('contributorsPara2') }}</p>
                    <div class="alert alert-success mt-4" role="alert">
                        <p>{{ t('contributorsWelcome') }}</p>
                        <hr>
                        <p class="mb-0">
                            <a href="https://github.com/xunbu/docutranslate" target="_blank"
                               class="btn btn-info btn-sm ms-2"><i
                                    class="bi bi-github me-1"></i><span>{{ t('contributorsGithub') }}</span></a>
                            <a href="https://github.com/xunbu/docutranslate/pulls" target="_blank"
                               class="btn btn-success btn-sm ms-2"><i
                                    class="bi bi-git me-1"></i><span>{{ t('contributorsPR') }}</span></a>
                            <a href="https://github.com/xunbu/docutranslate/issues" target="_blank"
                               class="btn btn-warning btn-sm ms-2"><i
                                    class="bi bi-bug-fill me-1"></i><span>{{ t('contributorsIssue') }}</span></a>
                        </p>
                        <hr>
                        <p>{{ t('contributorsQQ') }}</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ t('closeBtn') }}</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Queue Settings Modal -->
    <div class="modal fade" id="queueSettingsModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-sm">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-gear-fill me-2"></i>{{ t('queueConcurrentLabel') }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">{{ t('queueConcurrentLabel') }}</label>
                        <input type="number" class="form-control"
                               v-model.number="queue_concurrent" min="1" max="10"
                               @change="saveSetting('queue_concurrent', queue_concurrent)">
                        <div class="form-text">{{ t('queueConcurrentHelp') || '设置批量运行时同时翻译的任务数量（1-10）' }}</div>
                    </div>
                    <div class="alert alert-info py-2 small mb-0">
                        <i class="bi bi-info-circle me-1"></i>
                        {{ t('queueConcurrentNote') || '手动逐个点击开始翻译不受此限制影响' }}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ t('closeBtn') }}</button>
                </div>
            </div>
        </div>
    </div>

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

    <!-- Controls -->
    <div class="bottom-left-controls">
        <div class="dropdown">
            <button class="btn btn-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown"><i
                    class="bi bi-translate"></i></button>
            <ul class="dropdown-menu">
                <li><a class="dropdown-item" :class="{active: currentLang==='zh'}" href="#"
                       @click.prevent="setLang('zh')">中文</a></li>
                <li><a class="dropdown-item" :class="{active: currentLang==='en'}" href="#"
                       @click.prevent="setLang('en')">English</a></li>
                <li><a class="dropdown-item" :class="{active: currentLang==='vi'}" href="#"
                       @click.prevent="setLang('vi')">Tiếng Việt</a></li>
            </ul>
        </div>
        <div class="dropdown">
            <button class="btn btn-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown"><i
                    class="bi bi-circle-half"></i></button>
            <ul class="dropdown-menu">
                <li>
                    <button class="dropdown-item" @click="setTheme('light')"><i class="bi bi-sun-fill me-2"></i> Light
                    </button>
                </li>
                <li>
                    <button class="dropdown-item" @click="setTheme('dark')"><i class="bi bi-moon-stars-fill me-2"></i>
                        Dark
                    </button>
                </li>
                <li>
                    <button class="dropdown-item" @click="setTheme('auto')"><i class="bi bi-circle-half me-2"></i> Auto
                    </button>
                </li>
            </ul>
        </div>
    </div>
</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue';
import SliderControl from './components/common/SliderControl.vue';
import PlatformSelector from './components/common/PlatformSelector.vue';
import { mineruLangOptions } from './constants/mineruLanguages';
import { KNOWN_PLATFORMS } from './constants/platforms';
import { emptyToNull, capitalize, getFileIcon } from './utils/helpers';

// ===== 存储键名常量 =====
const STORAGE = {
    keys: {
        WORKFLOW: 'translator_last_workflow',
        ENGINE: 'translator_convert_engin',
        MD2DOCX: 'translator_md2docx_engine',
        PLATFORM: 'translator_platform_last_platform',
        CHUNK_SIZE: 'chunk_size',
        CONCURRENT: 'concurrent',
        TEMPERATURE: 'temperature',
        TOP_P: 'top_p',
        RETRY: 'retry',
        RPM: 'rpm',
        TPM: 'tpm',
        EXTRA_BODY: 'extra_body',
        CUSTOM_PROMPT: 'custom_prompt',
        QUEUE_CONCURRENT: 'queue_concurrent',
        ACTIVE_TASK_IDS: 'active_task_ids',
        UI_LANGUAGE: 'ui_language',
        UI_SYNC_SCROLL: 'ui_sync_scroll_enabled',
        THEME: 'theme',
        DEFAULT_WORKFLOWS: 'default_workflows',
        CUSTOM_EXTENSIONS: 'custom_extensions',
    },
    prefix: (name, platform, suffix) => `${name}_${platform}_${suffix}`,
};

// ===== 存储工具 =====
const storage = {
    get: (k, def) => { const v = localStorage.getItem(k); return v === null ? def : v; },
    set: (k, v) => { localStorage.setItem(k, v); },
    getBool: (k, def) => { const v = localStorage.getItem(k); return v === null ? def : v === 'true'; },
    getNum: (k, def) => { const v = localStorage.getItem(k); return v ? Number(v) : def; },
    getNumOrNull: (k) => { const v = localStorage.getItem(k); return (v === null || v === '' || v === 'null') ? null : Number(v); },
};

const version = ref("");
            const currentLang = ref(localStorage.getItem('ui_language') || 'zh');
            const i18nData = ref({});
            const glossaryData = ref({});
            const tasks = ref([]);
            const enginList = ref([]);
            const defaultParams = reactive({});

            // Refs for DOM elements
            const glossaryInput = ref(null);
            const configFile = ref(null);
            const previewOffcanvas = ref(null);

            // UI State
            const showMineruToken = ref(false);
            const previewMode = ref('bilingual');
            const syncScrollEnabled = ref(localStorage.getItem('ui_sync_scroll_enabled') === 'true');
            const showIdentityOption = ref(true);

            // Validation State
            const errors = reactive({
                model_id: false,
                api_key: false,
                base_url: false,
                mineru_token: false,
                mineru_deploy_base_url: false,
                custom_to_lang: false,
                json_paths: false
            });

            const clearError = (field) => {
                if (errors[field]) errors[field] = false;
            };

            // Form Data
            const form = reactive({
                workflow_type: 'markdown_based',
                convert_engine: 'mineru',
                md2docx_engine: 'auto',
                mineru_token: '',
                model_version: 'vlm',
                mineru_language: 'ch',
                mineru_deploy_base_url: 'http://127.0.0.1:8000',
                mineru_deploy_backend: 'hybrid-auto-engine', // Updated default
                mineru_deploy_parse_method: 'auto', // Added
                mineru_deploy_start_page: 0,
                mineru_deploy_end_page: 99999,
                mineru_deploy_formula_enable: true,
                mineru_deploy_table_enable: true, // Added
                mineru_deploy_lang_list: [],
                mineru_deploy_server_url: '',
                formula_ocr: true,
                code_ocr: true,
                skip_translate: false,
                platform: 'https://api.302.ai/v1',
                base_url: '',
                api_key: '',
                model_id: '',
                provider: 'api.openai.com', // Default provider
                system_proxy_enable: false,
                force_json: false,
                to_lang: 'Simplified Chinese',
                custom_to_lang: '',
                thinking: 'disable',
                custom_prompt: '',
                chunk_size: 4000,
                concurrent: 30,
                temperature: 0.7,
                top_p: 0.9,
                retry: 2,
                rpm: null, // New RPM
                tpm: null, // New TPM
                extra_body: '',
                glossary_generate_enable: false,
                glossary_agent_custom_prompt: '',
                glossary_agent_config_choice: 'same',
                glossary_agent_platform: 'https://api.302.ai/v1',
                glossary_agent_baseurl: '',
                glossary_agent_key: '',
                glossary_agent_model_id: '',
                glossary_agent_provider: 'api.openai.com', // Default glossary provider
                glossary_agent_to_lang: 'Simplified Chinese',
                glossary_agent_custom_to_lang: '',
                glossary_agent_chunk_size: 4000,
                glossary_agent_concurrent: 30,
                glossary_agent_temperature: 0.7,
                glossary_agent_top_p: 0.9,
                glossary_agent_retry: 2,
                glossary_agent_thinking: 'default',
                glossary_agent_system_proxy_enable: false,
                glossary_agent_force_json: false,
                glossary_agent_rpm: null, // New Glossary Agent RPM
                glossary_agent_tpm: null,  // New Glossary Agent TPM
                glossary_agent_extra_body: ''  // New Glossary Agent extra_body
            });

            // Default workflows per file extension
            const default_workflows = reactive({
                pdf: 'markdown_based', png: 'markdown_based', jpg: 'markdown_based', jpeg: 'markdown_based',
                gif: 'markdown_based', bmp: 'markdown_based', webp: 'markdown_based',
                txt: 'txt', md: 'markdown_based',
                docx: 'docx', doc: 'docx',
                xlsx: 'xlsx', csv: 'xlsx', xls: 'xlsx',
                epub: 'epub',
                pptx: 'pptx', ppt: 'pptx',
                srt: 'srt', ass: 'ass',
                json: 'json', html: 'html', htm: 'html'
            });

            const workflowLabels = {
                markdown_based: 'Markdown', txt: 'TXT', docx: 'DOCX', xlsx: 'XLSX',
                epub: 'EPUB', pptx: 'PPTX', srt: 'SRT', ass: 'ASS', json: 'JSON', html: 'HTML'
            };
            const getWorkflowLabel = (wf) => workflowLabels[wf] || wf;

            const queue_concurrent = ref(3);
            const runningCount = ref(0);

            // Nested Params for specific workflows
            const workflowParams = reactive({
                txt: {insert_mode: 'replace', separator: '\\n', segment_mode: 'line'},
                xlsx: {insert_mode: 'replace', separator: '\\n', translate_regions: ''},
                docx: {insert_mode: 'replace', separator: ''},
                srt: {insert_mode: 'replace', separator: '\\n'},
                epub: {insert_mode: 'replace', separator: ''},
                html: {insert_mode: 'replace', separator: ''},
                ass: {insert_mode: 'replace', separator: '\\n'},
                json: {json_paths: ''},
                pptx: {insert_mode: 'replace', separator: '\\n'}
            });

            // ===== 加载配置 - 拆分为子函数 =====
            const loadMainConfig = (defaults) => {
                form.workflow_type = storage.get(STORAGE.keys.WORKFLOW, 'markdown_based');
                form.convert_engine = storage.get(STORAGE.keys.ENGINE, 'mineru');
                const md2docxVal = storage.get(STORAGE.keys.MD2DOCX, 'auto');
                form.md2docx_engine = md2docxVal === 'null' ? null : md2docxVal;
                form.mineru_token = storage.get('translator_mineru_token', '');
                form.model_version = storage.get('translator_model_version', 'vlm');
                form.mineru_language = storage.get('translator_mineru_language', 'ch');
                form.mineru_deploy_base_url = storage.get('mineru_deploy_base_url', 'http://127.0.0.1:8000');
                form.mineru_deploy_backend = storage.get('mineru_deploy_backend', 'hybrid-auto-engine');
                form.mineru_deploy_parse_method = storage.get('mineru_deploy_parse_method', 'auto');
                form.mineru_deploy_start_page = storage.getNum('mineru_deploy_start_page', 0);
                form.mineru_deploy_end_page = storage.getNum('mineru_deploy_end_page', 99999);
                form.mineru_deploy_formula_enable = storage.getBool('mineru_deploy_formula_enable', true);
                form.mineru_deploy_table_enable = storage.getBool('mineru_deploy_table_enable', true);
                form.mineru_deploy_server_url = storage.get('mineru_deploy_server_url', '');
                const savedLangList = localStorage.getItem('mineru_deploy_lang_list');
                form.mineru_deploy_lang_list = savedLangList ? JSON.parse(savedLangList) : [];
                form.formula_ocr = storage.getBool('translator_formula_ocr', true);
                form.code_ocr = storage.getBool('translator_code_ocr', true);
                form.skip_translate = storage.getBool('translator_skip_translate', false);
                form.platform = storage.get(STORAGE.keys.PLATFORM, 'https://api.302.ai/v1');
                form.system_proxy_enable = storage.getBool('translator_system_proxy_enable', defaults.system_proxy_enable ?? false);
                form.force_json = storage.getBool('translator_force_json', false);
                form.to_lang = storage.get('translator_to_lang', 'Simplified Chinese');
                form.custom_to_lang = storage.get('translator_custom_to_lang', '');
                form.thinking = storage.get('translator_thinking_mode', defaults.thinking ?? 'disable');
                form.custom_prompt = storage.get(STORAGE.keys.CUSTOM_PROMPT, '');
                form.chunk_size = storage.getNum(STORAGE.keys.CHUNK_SIZE, defaults.chunk_size ?? 4000);
                form.concurrent = storage.getNum(STORAGE.keys.CONCURRENT, defaults.concurrent ?? 30);
                form.temperature = storage.getNum(STORAGE.keys.TEMPERATURE, defaults.temperature ?? 0.7);
                form.top_p = storage.getNum(STORAGE.keys.TOP_P, defaults.top_p ?? 0.9);
                form.retry = storage.getNum(STORAGE.keys.RETRY, defaults.retry ?? 2);
                form.rpm = storage.getNumOrNull(STORAGE.keys.RPM);
                form.tpm = storage.getNumOrNull(STORAGE.keys.TPM);
                form.extra_body = storage.get(STORAGE.keys.EXTRA_BODY, defaults.extra_body ?? '');
            };

            const loadPlatformConfig = () => {
                const platObj = KNOWN_PLATFORMS.find(p => p.val === form.platform);
                if (form.platform === 'custom') {
                    form.provider = storage.get('translator_platform_custom_provider', 'default');
                } else {
                    form.provider = platObj ? platObj.provider : '';
                }
            };

            const loadGlossaryConfig = (defaults) => {
                form.glossary_generate_enable = storage.getBool('glossary_generate_enable', false);
                form.glossary_agent_custom_prompt = storage.get('glossary_agent_custom_prompt', '');
                form.glossary_agent_config_choice = storage.get('glossary_agent_config_choice', 'same');
                form.glossary_agent_platform = storage.get('glossary_agent_platform_last_platform', 'https://api.302.ai/v1');
                form.glossary_agent_to_lang = storage.get('glossary_agent_to_lang', 'Simplified Chinese');
                form.glossary_agent_custom_to_lang = storage.get('glossary_agent_custom_to_lang', '');
                form.glossary_agent_chunk_size = storage.getNum('glossary_agent_chunk_size', defaults.chunk_size ?? 1000);
                form.glossary_agent_concurrent = storage.getNum('glossary_agent_concurrent', defaults.concurrent ?? 5);
                form.glossary_agent_temperature = storage.getNum('glossary_agent_temperature', defaults.temperature ?? 0.7);
                form.glossary_agent_top_p = storage.getNum('glossary_agent_top_p', 0.9);
                form.glossary_agent_retry = storage.getNum('glossary_agent_retry', defaults.retry ?? 3);
                form.glossary_agent_thinking = storage.get('glossary_agent_thinking_mode', defaults.thinking ?? 'default');
                form.glossary_agent_system_proxy_enable = storage.getBool('glossary_agent_system_proxy_enable', defaults.system_proxy_enable ?? false);
                form.glossary_agent_force_json = storage.getBool('glossary_agent_force_json', false);
                form.glossary_agent_rpm = storage.getNumOrNull('glossary_agent_rpm');
                form.glossary_agent_tpm = storage.getNumOrNull('glossary_agent_tpm');
                form.glossary_agent_extra_body = storage.get('glossary_agent_extra_body', defaults.extra_body ?? '');

                const gPlatObj = KNOWN_PLATFORMS.find(p => p.val === form.glossary_agent_platform);
                if (form.glossary_agent_platform === 'custom') {
                    form.glossary_agent_provider = storage.get('glossary_agent_platform_custom_provider', 'default');
                } else {
                    form.glossary_agent_provider = gPlatObj ? gPlatObj.provider : '';
                }
            };

            const loadWorkflowParams = () => {
                ['txt', 'xlsx', 'docx', 'srt', 'epub', 'html', 'ass', 'pptx'].forEach(t => {
                    workflowParams[t].insert_mode = storage.get(`translator_${t}_insert_mode`, 'replace');
                    if (workflowParams[t].separator !== undefined)
                        workflowParams[t].separator = storage.get(`translator_${t}_separator`, workflowParams[t].separator);
                });
                workflowParams.txt.segment_mode = storage.get('translator_txt_segment_mode', 'line');
                workflowParams.xlsx.translate_regions = storage.get('translator_xlsx_translate_regions', '');
                workflowParams.json.json_paths = storage.get('translator_json_paths', '');
            };

            const loadDefaultWorkflows = () => {
                const saved = localStorage.getItem(STORAGE.keys.DEFAULT_WORKFLOWS);
                if (saved) {
                    try { Object.assign(default_workflows, JSON.parse(saved)); } catch(e) {}
                }
                const savedCustom = localStorage.getItem(STORAGE.keys.CUSTOM_EXTENSIONS);
                if (savedCustom) {
                    try {
                        const parsed = JSON.parse(savedCustom);
                        if (Array.isArray(parsed)) {
                            parsed.forEach(ext => {
                                if (!ALL_EXTENSIONS.value.includes(ext)) {
                                    ALL_EXTENSIONS.value.push(ext);
                                    if (!default_workflows[ext]) default_workflows[ext] = 'markdown_based';
                                }
                            });
                        }
                    } catch(e) {}
                }
            };

            const loadConfig = (defaults = {}) => {
                loadMainConfig(defaults);
                loadPlatformConfig();
                loadGlossaryConfig(defaults);
                loadWorkflowParams();
                loadDefaultWorkflows();

                // Load queue concurrent
                const savedQueueConcurrent = localStorage.getItem(STORAGE.keys.QUEUE_CONCURRENT);
                if (savedQueueConcurrent) queue_concurrent.value = Number(savedQueueConcurrent) || 3;

                // Trigger platform updates to load API keys/models
                updatePlatformParams(form.platform, 'translator_platform', form);
                updatePlatformParams(form.glossary_agent_platform, 'glossary_agent_platform', form, true);
            };

            // ===== 保存配置 - 拆分为子函数 =====
            const saveMainConfig = () => {
                const f = form;
                storage.set(STORAGE.keys.WORKFLOW, f.workflow_type);
                storage.set(STORAGE.keys.ENGINE, f.convert_engine);
                storage.set(STORAGE.keys.MD2DOCX, f.md2docx_engine);
                storage.set('translator_mineru_token', f.mineru_token);
                storage.set('translator_model_version', f.model_version);
                storage.set('translator_mineru_language', f.mineru_language);
                storage.set('mineru_deploy_base_url', f.mineru_deploy_base_url);
                storage.set('mineru_deploy_backend', f.mineru_deploy_backend);
                storage.set('mineru_deploy_parse_method', f.mineru_deploy_parse_method);
                storage.set('mineru_deploy_start_page', f.mineru_deploy_start_page);
                storage.set('mineru_deploy_end_page', f.mineru_deploy_end_page);
                storage.set('mineru_deploy_formula_enable', f.mineru_deploy_formula_enable);
                storage.set('mineru_deploy_table_enable', f.mineru_deploy_table_enable);
                storage.set('mineru_deploy_server_url', f.mineru_deploy_server_url);
                storage.set('mineru_deploy_lang_list', JSON.stringify(f.mineru_deploy_lang_list));
                storage.set('translator_formula_ocr', f.formula_ocr);
                storage.set('translator_code_ocr', f.code_ocr);
                storage.set('translator_skip_translate', f.skip_translate);
                storage.set(STORAGE.keys.PLATFORM, f.platform);
                storage.set('translator_system_proxy_enable', f.system_proxy_enable);
                storage.set('translator_force_json', f.force_json);
                storage.set('translator_to_lang', f.to_lang);
                storage.set('translator_custom_to_lang', f.custom_to_lang);
                storage.set('translator_thinking_mode', f.thinking);
                storage.set(STORAGE.keys.CUSTOM_PROMPT, f.custom_prompt);
                storage.set(STORAGE.keys.CHUNK_SIZE, f.chunk_size);
                storage.set(STORAGE.keys.CONCURRENT, f.concurrent);
                storage.set(STORAGE.keys.TEMPERATURE, f.temperature);
                storage.set(STORAGE.keys.TOP_P, f.top_p);
                storage.set(STORAGE.keys.RETRY, f.retry);
                storage.set(STORAGE.keys.RPM, f.rpm || '');
                storage.set(STORAGE.keys.TPM, f.tpm || '');
                storage.set(STORAGE.keys.EXTRA_BODY, f.extra_body || '');
                // 平台相关
                storage.set(`translator_platform_${f.platform}_apikey`, f.api_key);
                storage.set(`translator_platform_${f.platform}_model_id`, f.model_id);
                storage.set('translator_provider', f.provider);
                if (f.platform === 'custom') storage.set('translator_platform_custom_base_url', f.base_url);
            };

            const saveGlossaryConfig = () => {
                const f = form;
                storage.set('glossary_generate_enable', f.glossary_generate_enable);
                storage.set('glossary_agent_custom_prompt', f.glossary_agent_custom_prompt);
                storage.set('glossary_agent_config_choice', f.glossary_agent_config_choice);
                storage.set('glossary_agent_platform_last_platform', f.glossary_agent_platform);
                storage.set('glossary_agent_to_lang', f.glossary_agent_to_lang);
                storage.set('glossary_agent_custom_to_lang', f.glossary_agent_custom_to_lang);
                storage.set('glossary_agent_chunk_size', f.glossary_agent_chunk_size);
                storage.set('glossary_agent_concurrent', f.glossary_agent_concurrent);
                storage.set('glossary_agent_temperature', f.glossary_agent_temperature);
                storage.set('glossary_agent_top_p', f.glossary_agent_top_p);
                storage.set('glossary_agent_retry', f.glossary_agent_retry);
                storage.set('glossary_agent_thinking_mode', f.glossary_agent_thinking);
                storage.set('glossary_agent_system_proxy_enable', f.glossary_agent_system_proxy_enable);
                storage.set('glossary_agent_force_json', f.glossary_agent_force_json);
                storage.set('glossary_agent_rpm', f.glossary_agent_rpm || '');
                storage.set('glossary_agent_tpm', f.glossary_agent_tpm || '');
                storage.set('glossary_agent_extra_body', f.glossary_agent_extra_body || '');
                // 术语表平台 Key
                storage.set(`glossary_agent_platform_${f.glossary_agent_platform}_apikey`, f.glossary_agent_key);
                storage.set(`glossary_agent_platform_${f.glossary_agent_platform}_model_id`, f.glossary_agent_model_id);
                storage.set('glossary_agent_provider', f.glossary_agent_provider);
                if (f.glossary_agent_platform === 'custom') storage.set('glossary_agent_platform_custom_base_url', f.glossary_agent_baseurl);
            };

            const saveWorkflowParamsConfig = () => {
                for (const [wfType, params] of Object.entries(workflowParams)) {
                    for (const [key, val] of Object.entries(params)) {
                        storage.set(`translator_${wfType}_${key}`, val);
                    }
                }
            };

            const saveAllSettings = () => {
                saveMainConfig();
                saveGlossaryConfig();
                saveWorkflowParamsConfig();
            };

            const updatePlatformParams = (plat, prefix, target, isGlossary = false) => {
                const get = (k) => localStorage.getItem(k) || '';
                if (isGlossary) {
                    target.glossary_agent_key = get(`${prefix}_${plat}_apikey`);
                    target.glossary_agent_model_id = get(`${prefix}_${plat}_model_id`);
                    target.glossary_agent_baseurl = plat === 'custom' ? get(`${prefix}_custom_base_url`) : plat;
                } else {
                    target.api_key = get(`${prefix}_${plat}_apikey`);
                    target.model_id = get(`${prefix}_${plat}_model_id`);
                    target.base_url = plat === 'custom' ? get(`${prefix}_custom_base_url`) : plat;
                }
            };

            let _importingConfig = false;
            watch(() => form.platform, (n) => {
                if (_importingConfig) return;
                updatePlatformParams(n, 'translator_platform', form);
            });

            watch(() => form.glossary_agent_platform, (n) => {
                if (_importingConfig) return;
                updatePlatformParams(n, 'glossary_agent_platform', form, true);
            });

            watch(() => currentLang.value, async (newLang) => {
                try {
                    const res = await fetch(`/static/i18n/${newLang}.json`);
                    i18nData.value = await res.json();
                } catch (e) {
                    console.error('Failed to load i18n:', e);
                }
            });

            const t = (k, params) => {
                let str = i18nData.value[k] || k;
                if (params) {
                    Object.keys(params).forEach(key => {
                        str = str.replace(`{${key}}`, params[key]);
                    });
                }
                return str;
            };
            const saveSetting = (k, v) => localStorage.setItem(k, v);
            const saveSettingArray = (k, v) => localStorage.setItem(k, JSON.stringify(v));

            const saveWorkflowParam = (keySuffix) => {
                const wf = form.workflow_type;
                localStorage.setItem(`translator_${wf}_${keySuffix}`, workflowParams[wf][keySuffix]);
            };

            const currentWorkflowConfig = computed(() => {
                const map = {
                    'txt': {
                        titleKey: 'txtSettingsTitleText',
                        icon: 'bi-filetype-txt',
                        hasInsertMode: true,
                        insertHelpKey: 'insertModeHelpTxt'
                    },
                    'docx': {
                        titleKey: 'docxSettingsTitleText',
                        icon: 'bi-file-earmark-word',
                        hasInsertMode: true,
                        insertHelpKey: 'insertModeHelpDocx'
                    },
                    'xlsx': {
                        titleKey: 'xlsxSettingsTitleText',
                        icon: 'bi-file-earmark-spreadsheet',
                        hasInsertMode: true,
                        insertHelpKey: 'insertModeHelpXlsx'
                    },
                    'srt': {
                        titleKey: 'srtSettingsTitleText',
                        icon: 'bi-file-text',
                        hasInsertMode: true,
                        insertHelpKey: 'insertModeHelpSrt'
                    },
                    'epub': {
                        titleKey: 'epubSettingsTitleText',
                        icon: 'bi-book',
                        hasInsertMode: true,
                        insertHelpKey: 'insertModeHelpEpub'
                    },
                    'html': {
                        titleKey: 'htmlSettingsTitleText',
                        icon: 'bi-filetype-html',
                        hasInsertMode: true,
                        insertHelpKey: 'insertModeHelpHtml'
                    },
                    'ass': {
                        titleKey: 'assSettingsTitleText',
                        icon: 'bi-file-easel',
                        hasInsertMode: true,
                        insertHelpKey: 'insertModeHelpAss',
                        separatorHelpKey: 'separatorHelpAss',
                        separatorPlaceholderKey: 'separatorPlaceholderAss'
                    },
                    'pptx': {
                        titleKey: 'pptxSettingsTitleText',
                        icon: 'bi-file-slides',
                        hasInsertMode: true,
                        insertHelpKey: 'insertModeHelpPptx'
                    },
                    'json': {titleKey: 'jsonSettingsTitleText', icon: 'bi-signpost-split', hasInsertMode: false},
                };
                return map[form.workflow_type];
            });

            // Dynamic Step Numbering
            const stepMap = computed(() => {
                let step = 2; // 1=Workflow Configuration (merged, includes parsing), from 2 onwards are dynamic
                const map = {ai: 0, trans: 0, glossary: 0};
                map.ai = step++;
                if (!form.skip_translate) map.trans = step++;
                map.glossary = step++;
                return map;
            });

            const ocrOptions = computed(() => ({
                showFormula: ['mineru', 'docling'].includes(form.convert_engine),
                showCode: form.convert_engine === 'docling'
            }));
            const glossaryCount = computed(() => Object.keys(glossaryData.value).length);

            const handleGlossaryFiles = (e) => {
                const files = e.target.files;
                if (!files.length) return;
                Array.from(files).forEach(f => {
                    Papa.parse(f, {
                        header: true, skipEmptyLines: true,
                        complete: (res) => {
                            if (res.data) res.data.forEach(r => {
                                if (r.src && r.dst) glossaryData.value[r.src.trim()] = r.dst.trim();
                            });
                        }
                    });
                });
            };
            const clearGlossary = () => {
                glossaryData.value = {};
                if (glossaryInput.value) glossaryInput.value.value = '';
            };
            const openGlossaryModal = () => new bootstrap.Modal(document.getElementById('glossaryModal')).show();
            const downloadGlossaryTemplate = () => {
                // Download template from backend
                window.open('/service/glossary/template', '_blank');
            };

            // Task Management
            const createNewTask = (backendId = null) => {
                const uiId = 'card_' + Math.random().toString(36).substring(2, 9);
                const task = reactive({
                    uiId, backendId, file: null, fileName: '', logs: '', statusMessage: '',
                    statusClass: 'text-muted', isTranslating: false, isFinished: false, isProcessing: false,
                    validationError: false, downloads: null, attachment: null, initializing: false, isDragOver: false,
                    progressPercent: 0, detectedWorkflow: null
                });
                tasks.value.unshift(task);
                if (backendId) {
                    task.isTranslating = true;
                    pollStatus(task);
                }
            };

            const removeTask = async (task) => {
                if (task.backendId) try {
                    await fetch(`/service/release/${task.backendId}`, {method: 'POST'});
                } catch (e) {
                }
                tasks.value = tasks.value.filter(t => t.uiId !== task.uiId);
                saveActiveTasks();
            };

            const clearAllTasks = async () => {
                if (!confirm(t('confirmClearAllTasks') || '确定要清空所有任务吗？')) return;
                for (const task of tasks.value) {
                    if (task.backendId) try {
                        await fetch(`/service/release/${task.backendId}`, {method: 'POST'});
                    } catch (e) {
                    }
                }
                tasks.value = [];
                saveActiveTasks();
            };

            const saveActiveTasks = () => {
                if (window.location.pathname.includes('/admin')) return;
                const ids = tasks.value.map(t => t.backendId).filter(id => id);
                localStorage.setItem('active_task_ids', JSON.stringify(ids));
            };

            const handleTaskFileSelect = (e, task) => {
                const f = e.target.files ? e.target.files[0] : e.dataTransfer.files[0];
                if (f) {
                    task.file = f;
                    task.fileName = f.name;
                    task.validationError = false;
                    task.isDragOver = false;
                    const ext = f.name.split('.').pop().toLowerCase();
                    const newWorkflow = default_workflows[ext] || 'markdown_based';
                    form.workflow_type = newWorkflow;
                    task.detectedWorkflow = newWorkflow;
                    saveSetting('translator_last_workflow', newWorkflow);
                }
            };
            const handleTaskFileDrop = (e, task) => handleTaskFileSelect(e, task);

            const triggerFileInput = (uiId) => {
                const el = document.getElementById('fileInput-' + uiId);
                if (el) el.click();
            };

            const selectTaskWorkflow = (task) => {
                if (task.file && task.detectedWorkflow) {
                    form.workflow_type = task.detectedWorkflow;
                }
            };

            // ===== 构建请求载荷 - 提取辅助函数 =====
            const buildAgentConfig = (basePayload) => {
                const isCustom = form.glossary_agent_config_choice === 'custom';
                return {
                    base_url: isCustom ? emptyToNull(form.glossary_agent_baseurl) : basePayload.base_url,
                    api_key: isCustom ? (form.glossary_agent_key || "") : basePayload.api_key,
                    model_id: isCustom ? emptyToNull(form.glossary_agent_model_id) : basePayload.model_id,
                    provider: isCustom ? emptyToNull(form.glossary_agent_provider) : basePayload.provider,
                    to_lang: isCustom ? (form.glossary_agent_to_lang === 'custom' ? form.glossary_agent_custom_to_lang : form.glossary_agent_to_lang) : basePayload.to_lang,
                    custom_prompt: emptyToNull(form.glossary_agent_custom_prompt),
                    temperature: isCustom ? Number(form.glossary_agent_temperature) : basePayload.temperature,
                    top_p: isCustom ? Number(form.glossary_agent_top_p) : basePayload.top_p,
                    concurrent: isCustom ? Number(form.glossary_agent_concurrent) : basePayload.concurrent,
                    retry: isCustom ? Number(form.glossary_agent_retry) : basePayload.retry,
                    thinking: isCustom ? form.glossary_agent_thinking : basePayload.thinking,
                    system_proxy_enable: isCustom ? form.glossary_agent_system_proxy_enable : basePayload.system_proxy_enable,
                    chunk_size: isCustom ? Number(form.glossary_agent_chunk_size) : basePayload.chunk_size,
                    force_json: isCustom ? form.glossary_agent_force_json : basePayload.force_json,
                    rpm: isCustom ? emptyToNull(form.glossary_agent_rpm) : basePayload.rpm,
                    tpm: isCustom ? emptyToNull(form.glossary_agent_tpm) : basePayload.tpm,
                    extra_body: isCustom ? emptyToNull(form.glossary_agent_extra_body) : basePayload.extra_body
                };
            };

            const buildWorkflowPayload = (basePayload) => {
                if (form.workflow_type === 'markdown_based') {
                    basePayload.convert_engine = form.convert_engine;
                    basePayload.md2docx_engine = form.md2docx_engine === 'null' ? null : form.md2docx_engine;
                    if (form.convert_engine === 'mineru') {
                        basePayload.mineru_token = emptyToNull(form.mineru_token);
                        basePayload.model_version = form.model_version;
                        basePayload.formula_ocr = form.formula_ocr;
                        basePayload.mineru_language = form.mineru_language;
                    } else if (form.convert_engine === 'mineru_deploy') {
                        basePayload.mineru_deploy_base_url = emptyToNull(form.mineru_deploy_base_url);
                        basePayload.mineru_deploy_backend = form.mineru_deploy_backend;
                        basePayload.mineru_deploy_parse_method = form.mineru_deploy_parse_method;
                        basePayload.mineru_deploy_formula_enable = form.mineru_deploy_formula_enable;
                        basePayload.mineru_deploy_table_enable = form.mineru_deploy_table_enable;
                        basePayload.mineru_deploy_start_page_id = parseInt(form.mineru_deploy_start_page) || 0;
                        basePayload.mineru_deploy_end_page_id = parseInt(form.mineru_deploy_end_page) || 99999;
                        if (['pipeline', 'hybrid-auto-engine', 'hybrid-http-client'].includes(basePayload.mineru_deploy_backend)) {
                            basePayload.mineru_deploy_lang_list = form.mineru_deploy_lang_list.length > 0 ? form.mineru_deploy_lang_list : null;
                        }
                        if (['vlm-http-client', 'hybrid-http-client'].includes(basePayload.mineru_deploy_backend)) {
                            basePayload.mineru_deploy_server_url = emptyToNull(form.mineru_deploy_server_url);
                        }
                    } else if (form.convert_engine === 'docling') {
                        basePayload.code_ocr = form.code_ocr;
                        basePayload.formula_ocr = form.formula_ocr;
                    }
                } else {
                    const params = {...workflowParams[form.workflow_type]};
                    if (params.separator) {
                        params.separator = params.separator.replace(/\\n/g, '\n');
                    }
                    if (form.workflow_type === 'json') {
                        params.json_paths = params.json_paths.split('\n').map(p => p.trim()).filter(p => p);
                    } else if (form.workflow_type === 'xlsx') {
                        if (params.translate_regions && typeof params.translate_regions === 'string' && params.translate_regions.trim()) {
                            params.translate_regions = params.translate_regions.split('\n').map(p => p.trim()).filter(p => p);
                            if (params.translate_regions.length === 0) delete params.translate_regions;
                        } else {
                            delete params.translate_regions;
                        }
                    }
                    Object.assign(basePayload, params);
                }
            };

            const buildPayload = () => {
                const basePayload = {
                    skip_translate: form.skip_translate,
                    base_url: emptyToNull(form.base_url),
                    api_key: form.api_key || "",
                    model_id: emptyToNull(form.model_id),
                    provider: emptyToNull(form.provider),
                    to_lang: form.to_lang === 'custom' ? form.custom_to_lang : form.to_lang,
                    thinking: form.thinking,
                    chunk_size: Number(form.chunk_size),
                    concurrent: Number(form.concurrent),
                    temperature: Number(form.temperature),
                    top_p: Number(form.top_p),
                    retry: Number(form.retry),
                    custom_prompt: emptyToNull(form.custom_prompt),
                    glossary_dict: Object.keys(glossaryData.value).length ? glossaryData.value : null,
                    system_proxy_enable: form.system_proxy_enable,
                    force_json: form.force_json,
                    glossary_generate_enable: form.glossary_generate_enable,
                    workflow_type: form.workflow_type,
                    rpm: emptyToNull(form.rpm),
                    tpm: emptyToNull(form.tpm),
                    extra_body: emptyToNull(form.extra_body)
                };

                if (basePayload.glossary_generate_enable) {
                    basePayload.glossary_agent_config = buildAgentConfig(basePayload);
                }

                buildWorkflowPayload(basePayload);
                return basePayload;
            };

            const validateForm = () => {
                let isValid = true;
                Object.keys(errors).forEach(k => errors[k] = false);

                if (!form.skip_translate) {
                    if (!form.model_id) {
                        errors.model_id = true;
                        isValid = false;
                    }
                    if (form.platform === 'custom' && !form.base_url) {
                        errors.base_url = true;
                        isValid = false;
                    }
                    if (form.to_lang === 'custom' && !form.custom_to_lang) {
                        errors.custom_to_lang = true;
                        isValid = false;
                    }
                }

                if (form.workflow_type === 'markdown_based') {
                    if (form.convert_engine === 'mineru' && !form.mineru_token) {
                        errors.mineru_token = true;
                        isValid = false;
                    }
                    if (form.convert_engine === 'mineru_deploy' && !form.mineru_deploy_base_url) {
                        errors.mineru_deploy_base_url = true;
                        isValid = false;
                    }
                } else if (form.workflow_type === 'json') {
                    if (!workflowParams.json.json_paths || !workflowParams.json.json_paths.trim()) {
                        errors.json_paths = true;
                        isValid = false;
                    }
                }

                if (!isValid) {
                    nextTick(() => {
                        const errorEl = document.querySelector('.is-invalid');
                        if (errorEl) {
                            errorEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                            errorEl.focus();
                        }
                    });
                }
                return isValid;
            };

            const toggleTaskState = async (task) => {
                if (task.isTranslating) {
                    task.statusMessage = t('status_cancelling');
                    if (task.backendId) await fetch(`/service/cancel/${task.backendId}`, {method: 'POST'});
                    runningCount.value = Math.max(0, runningCount.value - 1);
                } else if (task.isFinished) {
                    task.isFinished = false;
                    task.logs = '';
                    task.downloads = null;
                    toggleTaskState(task);
                } else {
                    if (!task.file) {
                        task.validationError = true;
                        return;
                    }

                    if (!validateForm()) {
                        task.statusMessage = t('status_fillRequired') || "请检查左侧配置项 (Please check settings)";
                        task.statusClass = 'text-danger';
                        return;
                    }

                    task.initializing = true;
                    try {
                        const savedWorkflow = form.workflow_type;
                        if (task.detectedWorkflow) {
                            form.workflow_type = task.detectedWorkflow;
                        }
                        const formData = new FormData();
                        formData.append('file', task.file);
                        formData.append('payload', JSON.stringify(buildPayload()));
                        form.workflow_type = savedWorkflow;
                        const res = await fetch('/service/translate/file', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await res.json();
                        if (res.ok && data.task_started) {
                            task.backendId = data.task_id;
                            task.isTranslating = true;
                            saveActiveTasks();
                            pollStatus(task);
                            task.statusMessage = data.message;
                        } else {
                            throw new Error(data.message || data.detail || 'Error');
                        }
                    } catch (e) {
                        task.statusMessage = e.message;
                        task.statusClass = 'text-danger';
                        task.isTranslating = false;
                        runningCount.value = Math.max(0, runningCount.value - 1);
                    } finally {
                        task.initializing = false;
                    }
                }
            };

            const pollStatus = (task) => {
                const interval = setInterval(async () => {
                    if (!task.isTranslating) {
                        clearInterval(interval);
                        return;
                    }
                    try {
                        // Fetch Logs
                        const logRes = await fetch(`/service/logs/${task.backendId}`);
                        const logData = await logRes.json();
                        if (logData.logs && logData.logs.length) {
                            task.logs += logData.logs.map(l => l.replace(/</g, "&lt;").replace(/>/g, "&gt;")).join('<br>') + '<br>';
                            nextTick(() => {
                                const logEl = document.getElementById('log-' + task.uiId);
                                if (logEl) logEl.scrollTop = logEl.scrollHeight;
                            });
                        }

                        // Fetch Status
                        const statRes = await fetch(`/service/status/${task.backendId}`);

                        // Handle 404 (Task not found / Expired)
                        if (!statRes.ok) {
                            if (statRes.status === 404) {
                                clearInterval(interval);
                                task.isTranslating = false;
                                task.isProcessing = false;
                                task.statusClass = 'text-danger';
                                task.statusMessage = '任务不存在或已过期 (Task not found)';
                                const savedIds = JSON.parse(localStorage.getItem('active_task_ids') || '[]');
                                const newIds = savedIds.filter(id => id !== task.backendId);
                                localStorage.setItem('active_task_ids', JSON.stringify(newIds));
                            }
                            return;
                        }

                        const statData = await statRes.json();
                        task.statusMessage = statData.status_message;
                        task.isProcessing = statData.is_processing;
                        task.progressPercent = statData.progress_percent || 0;

                        // Recover filename if task was restored and file object is missing
                        if (statData.original_filename && !task.fileName) {
                            task.fileName = statData.original_filename;
                        }

                        if (!statData.is_processing) {
                            clearInterval(interval);
                            task.isTranslating = false;
                            task.isFinished = true;
                            runningCount.value = Math.max(0, runningCount.value - 1);
                            startNextPendingTask();
                            if (statData.download_ready && !statData.error_flag) {
                                task.downloads = statData.downloads;
                                task.attachment = statData.attachment;
                                task.statusClass = 'text-success';
                            } else {
                                task.statusClass = 'text-danger';
                                task.statusMessage = statData.error_flag ? (statData.status_message || 'Failed') : statData.status_message;
                            }
                        }
                    } catch (e) {
                    }
                }, 1500);
            };

            // Preview Logic
            const splitInstance = ref(null);
            const splitContainer = ref(null);
            const originalPane = ref(null);
            const translatedFrame = ref(null);
            const previewTask = ref(null);

            const initSplit = () => {
                if (splitInstance.value) {
                    splitInstance.value.destroy();
                    splitInstance.value = null;
                }
                const isMobile = window.innerWidth < 992;
                if (splitContainer.value) {
                    splitContainer.value.style.flexDirection = isMobile ? 'column' : 'row';
                }
                if (previewMode.value === 'bilingual') {
                    nextTick(() => {
                        const el1 = document.getElementById('originalPreviewContainer');
                        const el2 = document.getElementById('translatedPreviewContainer');
                        if (el1 && el2) {
                            splitInstance.value = Split(['#originalPreviewContainer', '#translatedPreviewContainer'], {
                                sizes: [50, 50], minSize: 150, gutterSize: 10,
                                direction: isMobile ? 'vertical' : 'horizontal',
                                cursor: isMobile ? 'row-resize' : 'col-resize'
                            });
                        }
                    });
                }
                setupSyncScroll();
            };

            const openPreview = (task) => {
                previewTask.value = task;
                const offcanvas = new bootstrap.Offcanvas(document.getElementById('previewOffcanvas'));
                offcanvas.show();

                // Load Original Content
                originalPane.value.innerHTML = '';
                if (task.file) {
                    const ext = task.file.name.split('.').pop().toLowerCase();
                    if (['txt', 'md', 'json', 'html', 'js', 'py', 'css', 'java', 'c', 'cpp'].includes(ext) || task.file.type.startsWith('text/')) {
                        task.file.text().then(txt => originalPane.value.innerHTML = `<pre>${txt}</pre>`);
                    } else if (['pdf'].includes(ext) || task.file.type === 'application/pdf') {
                        const iframe = document.createElement('iframe');
                        iframe.src = URL.createObjectURL(task.file);
                        originalPane.value.appendChild(iframe);
                    } else {
                        originalPane.value.innerHTML = `<p class="p-3 text-muted">${t('preview_cantPreviewType')} (${ext})</p>`;
                    }
                } else {
                    originalPane.value.innerHTML = `<p class="p-3 text-muted">${t('preview_noOriginalCache')}</p>`;
                }

                // Load Translated Content
                if (translatedFrame.value) translatedFrame.value.src = 'about:blank';
                fetch(task.downloads.html).then(r => r.text()).then(h => {
                    if (translatedFrame.value) translatedFrame.value.srcdoc = h;
                });

                // Re-init Split.js and Sync Scroll listeners
                setTimeout(initSplit, 300);
            };

            const setupSyncScroll = () => {
                let isScrolling = false;
                const onScroll = (src, tgt) => {
                    if (!syncScrollEnabled.value || isScrolling) return;
                    const pct = src.scrollTop / (src.scrollHeight - src.clientHeight);
                    tgt.scrollTop = pct * (tgt.scrollHeight - tgt.clientHeight);
                    isScrolling = true;
                    requestAnimationFrame(() => isScrolling = false);
                };

                if (originalPane.value) originalPane.value.onscroll = () => {
                    if (translatedFrame.value && translatedFrame.value.contentWindow)
                        onScroll(originalPane.value, translatedFrame.value.contentWindow.document.documentElement);
                };

                if (translatedFrame.value) translatedFrame.value.onload = () => {
                    const win = translatedFrame.value.contentWindow;
                    if (win) win.onscroll = () => onScroll(win.document.documentElement, originalPane.value);
                };
            };

            const setPreviewMode = (m) => {
                previewMode.value = m;
                setTimeout(initSplit, 100);
            };

            const toggleSyncScroll = () => {
                syncScrollEnabled.value = !syncScrollEnabled.value;
                localStorage.setItem('ui_sync_scroll_enabled', syncScrollEnabled.value);
            };

            const printPdf = (url) => {
                const msg = t('pdf_preparing') || "正在准备打印，请稍候...";
                const toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed top-0 start-50 translate-middle-x p-3';
                toastContainer.style.zIndex = '1090';
                toastContainer.innerHTML = `
                <div class="toast align-items-center text-bg-primary border-0 fade show" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="d-flex">
                        <div class="toast-body">
                            <i class="bi bi-printer-fill me-2"></i>${msg}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                </div>
            `;
                document.body.appendChild(toastContainer);
                setTimeout(() => {
                    const t = toastContainer.querySelector('.toast');
                    if (t) {
                        t.classList.remove('show');
                        setTimeout(() => {
                            if (toastContainer.parentNode) toastContainer.remove();
                        }, 500);
                    }
                }, 3000);

                const ifr = document.getElementById('printFrame');
                fetch(url).then(r => r.text()).then(h => {
                    ifr.srcdoc = h;
                    ifr.onload = () => {
                        setTimeout(() => {
                            ifr.contentWindow.focus();
                            ifr.contentWindow.print();
                        }, 500);
                    };
                });
            };

            const copyLog = (e, l) => {
                navigator.clipboard.writeText(l.replace(/<br>/g, '\n')).then(() => {
                    const btn = e.currentTarget;
                    const icon = btn.querySelector('i');
                    btn.classList.replace('btn-outline-secondary', 'btn-success');
                    icon.classList.replace('bi-clipboard', 'bi-check-lg');
                    setTimeout(() => {
                        btn.classList.replace('btn-success', 'btn-outline-secondary');
                        icon.classList.replace('bi-check-lg', 'bi-clipboard');
                    }, 2000);
                });
            };

            const getWorkflowIcon = (t) => ({
                markdown: 'bi-markdown',
                markdown_zip: 'bi-file-zip',
                docx: 'bi-filetype-docx',
                json: 'bi-filetype-json',
                txt: 'bi-filetype-txt',
                xlsx: 'bi-filetype-xlsx',
                csv: 'bi-filetype-csv',
                srt: 'bi-file-text',
                epub: 'bi-book',
                ass: 'bi-file-easel',
                html: 'bi-filetype-html',
                pptx: 'bi-file-slides'
            }[t] || 'bi-file-earmark');

            const exportConfig = () => {
                const config = {form: form, workflowParams: workflowParams};
                const blob = new Blob([JSON.stringify(config, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'config.json';
                a.click();
                setTimeout(() => {
                    URL.revokeObjectURL(url);
                }, 100);
            };
            const importConfig = (e) => {
                const f = e.target.files[0];
                if (f) {
                    const r = new FileReader();
                    r.onload = (ev) => {
                        try {
                            const data = JSON.parse(ev.target.result);
                            _importingConfig = true;
                            if (data.form) Object.assign(form, data.form);
                            if (data.workflowParams) Object.assign(workflowParams, data.workflowParams);
                            _importingConfig = false;
                            saveAllSettings();
                            alert(t('configImportSuccess'));
                        } catch (err) {
                            _importingConfig = false;
                            alert(t('configImportError'));
                        }
                    };
                    r.readAsText(f);
                }
                e.target.value = '';
            };

            const setLang = (l) => {
                currentLang.value = l;
                localStorage.setItem('ui_language', l);
                document.documentElement.lang = l === 'zh' ? 'zh-CN' : 'en';
            };
            const setTheme = (t) => {
                localStorage.setItem('theme', t);
                if (t === 'auto') document.documentElement.setAttribute('data-bs-theme', window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
                else document.documentElement.setAttribute('data-bs-theme', t);
            };

            // ===== Default workflow drag & drop =====
            const DEFAULT_EXTENSIONS = ['pdf','png','jpg','jpeg','gif','bmp','webp','txt','md','docx','doc','xlsx','csv','xls','epub','pptx','ppt','srt','ass','json','html','htm'];
            const DEFAULT_WORKFLOW_MAPPING = {
                pdf: 'markdown_based', png: 'markdown_based', jpg: 'markdown_based', jpeg: 'markdown_based',
                gif: 'markdown_based', bmp: 'markdown_based', webp: 'markdown_based',
                txt: 'txt', md: 'markdown_based',
                docx: 'docx', doc: 'docx',
                xlsx: 'xlsx', csv: 'xlsx', xls: 'xlsx',
                epub: 'epub',
                pptx: 'pptx', ppt: 'pptx',
                srt: 'srt', ass: 'ass',
                json: 'json', html: 'html', htm: 'html'
            };
            const ALL_EXTENSIONS = ref([...DEFAULT_EXTENSIONS]);

            const customExtensions = computed(() => {
                return ALL_EXTENSIONS.value.filter(ext => !DEFAULT_EXTENSIONS.includes(ext));
            });

            const workflowOptions = [
                { value: 'markdown_based', label: 'Markdown' },
                { value: 'txt', label: 'TXT' },
                { value: 'docx', label: 'DOCX' },
                { value: 'xlsx', label: 'XLSX' },
                { value: 'epub', label: 'EPUB' },
                { value: 'pptx', label: 'PPTX' },
                { value: 'srt', label: 'SRT' },
                { value: 'ass', label: 'ASS' },
                { value: 'json', label: 'JSON' },
                { value: 'html', label: 'HTML' },
            ];

            // Map workflow value to i18n key for full label
            const workflowFullLabelKeys = {
                markdown_based: 'workflowOptionMarkdown',
                txt: 'workflowOptionTxt',
                docx: 'workflowOptionDocx',
                xlsx: 'workflowOptionXlsx',
                epub: 'workflowOptionEpub',
                pptx: 'workflowOptionPptx',
                srt: 'workflowOptionSrt',
                ass: 'workflowOptionAss',
                json: 'workflowOptionJson',
                html: 'workflowOptionHtml',
            };

            const getWorkflowFullLabel = (wf) => {
                const key = workflowFullLabelKeys[wf];
                return key ? t(key) : wf;
            };

            // Get simplified workflow label without parentheses
            const getSimpleWorkflowLabel = (wf) => {
                const fullLabel = getWorkflowFullLabel(wf);
                // Remove everything from first parenthesis
                return fullLabel.replace(/\s*\(.*$/, '');
            };

            const getWorkflowExtensions = (workflow) => {
                return ALL_EXTENSIONS.value.filter(ext => default_workflows[ext] === workflow);
            };

            // Drag handlers
            const workflowDragOver = ref(null);

            const onDragStart = (e, ext) => {
                e.dataTransfer.setData('text/plain', ext);
                e.target.classList.add('dragging');
            };

            const onDragEnd = (e) => {
                e.target.classList.remove('dragging');
            };

            const onDropWorkflow = (e, workflow) => {
                const ext = e.dataTransfer.getData('text/plain');
                if (ext && ALL_EXTENSIONS.value.includes(ext)) {
                    default_workflows[ext] = workflow;
                }
            };

            // Delete an extension entirely
            const deleteExtension = (ext) => {
                delete default_workflows[ext];
                const idx = ALL_EXTENSIONS.value.indexOf(ext);
                if (idx !== -1) {
                    ALL_EXTENSIONS.value.splice(idx, 1);
                }
            };

            // Remove a single extension's custom mapping (falls back to default) - kept for backward compatibility
            const removeExtensionMapping = (ext) => {
                deleteExtension(ext);
            };

            // Add extension directly to a specific workflow
            const addExtToWorkflow = (workflow, event) => {
                const input = event.target.closest('.input-group').querySelector('input');
                const raw = (input.value || '').trim().toLowerCase().replace(/^\.+/, '');

                if (!raw) return;
                if (!/^[a-z0-9]+$/.test(raw)) {
                    addExtensionError.value = t('addExtensionPlaceholder');
                    return;
                }
                if (ALL_EXTENSIONS.value.includes(raw)) {
                    addExtensionError.value = t('extensionExistsError');
                    return;
                }

                addExtensionError.value = '';
                ALL_EXTENSIONS.value.push(raw);
                default_workflows[raw] = workflow;
                input.value = '';
            };

            const resetDefaultWorkflows = () => {
                // Remove custom extensions
                ALL_EXTENSIONS.value.forEach(ext => {
                    if (!DEFAULT_WORKFLOW_MAPPING.hasOwnProperty(ext)) {
                        delete default_workflows[ext];
                    }
                });
                // Restore to default extensions only
                ALL_EXTENSIONS.value = [...DEFAULT_EXTENSIONS];
                // Restore default mappings
                DEFAULT_EXTENSIONS.forEach(ext => {
                    default_workflows[ext] = DEFAULT_WORKFLOW_MAPPING[ext];
                });
                localStorage.setItem('default_workflows', JSON.stringify(default_workflows));
            };

            const openDefaultWorkflowModal = () => new bootstrap.Modal(document.getElementById('defaultWorkflowModal')).show();
            const saveDefaultWorkflows = () => {
                localStorage.setItem('default_workflows', JSON.stringify(default_workflows));
                const custom = ALL_EXTENSIONS.value.filter(ext => !DEFAULT_EXTENSIONS.includes(ext));
                localStorage.setItem('custom_extensions', JSON.stringify(custom));
            };

            const addExtensionError = ref('');

            // Keep for backward compatibility
            const newExtInput = ref(null);
            const addExtension = () => {};

            // Folder upload
            const handleFolderSelect = (e) => {
                const files = Array.from(e.target.files);
                if (files.length === 0) return;
                files.forEach(f => {
                    const task = reactive({
                        uiId: 'card_' + Math.random().toString(36).substring(2, 9),
                        backendId: null, file: f, fileName: f.name, logs: '', statusMessage: '',
                        statusClass: 'text-muted', isTranslating: false, isFinished: false, isProcessing: false,
                        validationError: false, downloads: null, attachment: null, initializing: false, isDragOver: false,
                        progressPercent: 0, detectedWorkflow: null
                    });
                    tasks.value.unshift(task);
                    const ext = f.name.split('.').pop().toLowerCase();
                    const newWorkflow = default_workflows[ext] || 'markdown_based';
                    form.workflow_type = newWorkflow;
                    task.detectedWorkflow = newWorkflow;
                    saveSetting('translator_last_workflow', newWorkflow);
                });
                e.target.value = '';
            };

            // Batch run pending tasks - queue management
            const pendingQueue = [];
            const hasPendingTasks = computed(() => tasks.value.some(t => t.file && !t.isTranslating && !t.isFinished));

            const startNextPendingTask = () => {
                const maxConcurrent = Math.max(1, queue_concurrent.value);
                while (pendingQueue.length > 0 && runningCount.value < maxConcurrent) {
                    const task = pendingQueue.shift();
                    if (task.file && !task.isTranslating && !task.isFinished) {
                        runningCount.value++;
                        toggleTaskState(task).finally(() => { startNextPendingTask(); });
                    }
                }
            };

            const runAllPendingTasks = () => {
                const pending = tasks.value.filter(t => t.file && !t.isTranslating && !t.isFinished);
                pendingQueue.length = 0;
                pending.forEach((task, i) => {
                    task.queuePosition = i + 1;
                    task.queueTotal = pending.length;
                    pendingQueue.push(task);
                });
                startNextPendingTask();
            };

            onMounted(async () => {
                // I18n
                try {
                    const lang = currentLang.value || 'zh';
                    const res = await fetch(`/static/i18n/${lang}.json`);
                    i18nData.value = await res.json();

                } catch (e) {
                    i18nData.value = {
                        pageTitle: "DocuTranslate",
                        tutorialBtn: "教程",
                        projectContributeBtn: "项目协作",
                        workflowTitle: "选择工作流",
                        autoWorkflowLabel: "自动选择工作流",
                        workflowOptionPptx: "PPTX 演示文稿",
                        pptxSettingsTitleText: "PPTX 设置",
                        mineruDeployServerUrlLabel: "Server URL",
                        mineruDeployLangListLabel: "语言列表 (Pipeline模式)",
                        mineruDeployServerUrlPlaceholder: "http://127.0.0.1:30000",
                        mineruDeployParseMethodLabel: "解析方法 (Parse Method)",
                        mineruDeployTableEnableLabel: "表格识别 (Table Recognition)"
                    };
                }

                // Backend Metadata
                try {
                    const [metaRes, enginRes, paramsRes] = await Promise.all([
                        fetch("/service/meta"), fetch('/service/engin-list'), fetch("/service/default-params")
                    ]);
                    const meta = await metaRes.json();
                    version.value = meta.version;
                    enginList.value = await enginRes.json();
                    Object.assign(defaultParams, await paramsRes.json());
                } catch (e) {
                    console.error("Backend init failed", e);
                }

                loadConfig(defaultParams);
                setTheme(localStorage.getItem('theme') || 'auto');

                // Restore tasks
                if (window.location.pathname.includes('/admin')) {
                    document.title = "DocuTranslate - Admin Panel";
                    try {
                        const r = await fetch('/service/task-list');
                        const ids = await r.json();
                        if (ids) ids.reverse().forEach(id => createNewTask(id));
                    } catch (e) {
                    }
                } else {
                    const savedIds = JSON.parse(localStorage.getItem('active_task_ids') || '[]');
                    if (savedIds.length) savedIds.forEach(id => createNewTask(id));
                    else createNewTask();
                }

                new bootstrap.Tooltip(document.body, {selector: '[data-bs-toggle="tooltip"]'});

                // Global resize handler for preview
                window.addEventListener('resize', () => {
                    if (document.getElementById('previewOffcanvas').classList.contains('show')) {
                        initSplit();
                    }
                });
            });
</script>
