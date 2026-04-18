<template>
    <div>
        <p class="text-gray-700 dark:text-gray-300">{{ t('contributorsPara1') }}</p>
        <p class="text-gray-700 dark:text-gray-300 mt-2">{{ t('contributorsPara2') }}</p>
        <div class="mt-4 p-4 bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 rounded">
            <p>{{ t('contributorsWelcome') }}</p>
            <hr class="my-3 border-green-200 dark:border-green-700">
            <p class="flex flex-wrap gap-2">
                <a href="https://github.com/xunbu/docutranslate" target="_blank"
                   class="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-info text-white rounded hover:opacity-90 transition-opacity">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.107-3.162 0 0 1.008-.322 3.301 1.23.957-.266 1.976-.399 3-.404 1.024.005 2.043.138 3 .404 2.293-1.552 3.301-1.23 3.301-1.23.643 1.638.232 2.859.107 3.162.768.84 1.236 1.91 1.236 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.214.694.825.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    <span>{{ t('contributorsGithub') }}</span>
                </a>
                <a href="https://github.com/xunbu/docutranslate/pulls" target="_blank"
                   class="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-success text-white rounded hover:opacity-90 transition-opacity">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>{{ t('contributorsPR') }}</span>
                </a>
                <a href="https://github.com/xunbu/docutranslate/issues" target="_blank"
                   class="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-warning text-gray-800 rounded hover:opacity-90 transition-opacity">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>{{ t('contributorsIssue') }}</span>
                </a>
            </p>
            <hr class="my-3 border-green-200 dark:border-green-700">
            <p>{{ t('contributorsQQ') }}</p>
        </div>
        <div class="mt-4 flex justify-end">
            <button type="button" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors" @click="$emit('close')">
                {{ t('closeBtn') }}
            </button>
        </div>
    </div>
</template>

<script setup>
defineProps(['t']);
defineEmits(['close']);
</script>
