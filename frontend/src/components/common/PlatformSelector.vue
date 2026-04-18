<template>
  <div>
    <div class="mb-2">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('platformLabel') }}</label>
      <select
        class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
        :value="platform"
        @change="handlePlatformChange($event.target.value)">
        <option v-for="p in platforms" :key="p.val" :value="p.val">{{ p.val === 'custom' ? t(p.label) : p.label }}</option>
      </select>
    </div>

    <div class="mb-4" v-if="platform === 'custom'">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('providerLabel') }}</label>
      <select
        class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
        :value="provider"
        @change="handleProviderChange($event.target.value)">
        <option v-for="prov in providers" :key="prov" :value="prov">{{ prov }}</option>
      </select>
    </div>

    <div class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      Base URL: <code class="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs" ref="baseUrlDisplay">{{ baseUrl }}</code>
    </div>

    <div class="mb-4" v-if="platform === 'custom'">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('baseUrlLabel') }}</label>
      <input
        type="url"
        class="w-full px-3 py-1.5 text-sm border rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
        :class="invalidBaseUrl ? 'border-red-500 dark:border-red-400' : 'border-gray-300 dark:border-gray-600'"
        :value="baseUrl"
        @input="handleBaseUrlChange($event.target.value)"
        required
        placeholder="OpenAi Compatible URL">
    </div>

    <div class="mb-4">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        API Key
        <a v-if="apiHref" :href="apiHref[0]" target="_blank" class="ml-1 text-primary hover:underline">
          <svg class="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
        <span class="ml-2 text-xs text-gray-500">{{ apiHref && apiHref[1] ? t(apiHref[1]) : '' }}</span>
      </label>
      <div class="flex">
        <input
          :type="showPass ? 'text' : 'password'"
          class="flex-1 px-3 py-1.5 text-sm border rounded-l bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
          :class="invalidApiKey ? 'border-red-500 dark:border-red-400' : 'border-gray-300 dark:border-gray-600'"
          :value="apiKey"
          @input="handleApiKeyChange($event.target.value)"
          :placeholder="t('apiKeyPlaceholder')">
        <button
          type="button"
          class="px-3 py-1.5 text-sm border border-l-0 border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-r hover:bg-gray-200 dark:hover:bg-gray-500 transition-colors"
          @click="showPass = !showPass">
          <svg v-if="showPass" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          </svg>
        </button>
      </div>
    </div>

    <div class="mb-4">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('modelIdLabel') }}</label>
      <input
        type="text"
        class="w-full px-3 py-1.5 text-sm border rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
        :class="invalidModelId ? 'border-red-500 dark:border-red-400' : 'border-gray-300 dark:border-gray-600'"
        :value="modelId"
        @input="handleModelChange($event.target.value)"
        required
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

const apiHref = computed(() => apiHrefMap[props.baseUrl]);

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
    save(`${props.prefix}_${props.platform}_provider`, val);
};

const handleBaseUrlChange = (val) => {
    emit('update:baseUrl', val);
    emit('clearError', 'base_url');
    if (props.platform === 'custom') save(`${props.prefix}_custom_base_url`, val);
};

const handleApiKeyChange = (val) => {
    emit('update:apiKey', val);
    emit('clearError', 'api_key');
    save(`${props.prefix}_${props.platform}_apikey`, val);
};

const handleModelChange = (val) => {
    emit('update:modelId', val);
    emit('clearError', 'model_id');
    save(`${props.prefix}_${props.platform}_model_id`, val);
};
</script>
