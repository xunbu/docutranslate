<template>
  <div>
    <div class="mb-2">
      <label class="form-label">{{ t('platformLabel') }}</label>
      <select class="form-select" :value="platform" @change="handlePlatformChange($event.target.value)">
        <option v-for="p in platforms" :value="p.val">{{ p.val === 'custom' ? t(p.label) : p.label }}</option>
      </select>
    </div>

    <div class="mb-3" v-if="platform === 'custom'">
      <label class="form-label">{{ t('providerLabel') }}</label>
      <select class="form-select" :value="provider" @change="handleProviderChange($event.target.value)">
        <option v-for="prov in providers" :value="prov">{{ prov }}</option>
      </select>
    </div>

    <div class="form-text mb-3">Base URL: <code ref="baseUrlDisplay">{{ baseUrl }}</code></div>
    <div class="mb-3" v-if="platform === 'custom'">
      <label class="form-label">{{ t('baseUrlLabel') }}</label>
      <input type="url" class="form-control" :class="{'is-invalid': invalidBaseUrl}"
             :value="baseUrl" @input="handleBaseUrlChange($event.target.value)" required
             placeholder="OpenAi Compatible URL">
    </div>
    <div class="mb-3">
      <label class="form-label">API Key <a v-if="apiHref" :href="apiHref[0]" target="_blank" class="ms-1"><i
          class="bi bi-box-arrow-up-right"></i></a> <span
          class="ms-2 text-muted small">{{ apiHref && apiHref[1] ? t(apiHref[1]) : '' }}</span></label>
      <div class="input-group">
        <input :type="showPass?'text':'password'" class="form-control" :class="{'is-invalid': invalidApiKey}"
               :value="apiKey" @input="handleApiKeyChange($event.target.value)"
               :placeholder="t('apiKeyPlaceholder')">
        <button class="btn btn-outline-secondary" type="button" @click="showPass=!showPass"><i class="bi"
                                                                                                       :class="showPass?'bi-eye':'bi-eye-slash'"></i>
        </button>
      </div>
    </div>
    <div class="mb-3">
      <label class="form-label">{{ t('modelIdLabel') }}</label>
      <input type="text" class="form-control" :class="{'is-invalid': invalidModelId}"
             :value="modelId" @input="handleModelChange($event.target.value)" required
             :placeholder="t('modelIdPlaceholder')">
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { KNOWN_PLATFORMS, PROVIDERS, API_HREF_MAP } from '../../constants/platforms';

const props = defineProps(['platform', 'baseUrl', 'apiKey', 'modelId', 'provider', 't', 'prefix', 'invalidApiKey', 'invalidBaseUrl', 'invalidModelId']);
const emit = defineEmits(['update:platform', 'update:baseUrl', 'update:apiKey', 'update:modelId', 'update:provider', 'clearError']);

const showPass = ref(false);
const platforms = KNOWN_PLATFORMS;
const providers = PROVIDERS;
const apiHrefMap = API_HREF_MAP;

const apiHref = computed(() => apiHrefMap[props.platform]);

const save = (key, val) => localStorage.setItem(key, val);

const handlePlatformChange = (val) => {
    emit('update:platform', val);
    save(`${props.prefix}_last_platform`, val);

    // Determine provider based on platform
    const selected = platforms.find(p => p.val === val);
    if (val === 'custom') {
        emit('update:provider', 'default');
    } else if (selected) {
        emit('update:provider', selected.provider);
    }
};

const handleProviderChange = (val) => {
    emit('update:provider', val);
};

const handleBaseUrlChange = (val) => {
    emit('update:baseUrl', val);
    emit('clearError', 'base_url');
};

const handleApiKeyChange = (val) => {
    emit('update:apiKey', val);
    emit('clearError', 'api_key');
};

const handleModelChange = (val) => {
    emit('update:modelId', val);
    emit('clearError', 'model_id');
};
</script>
