<template>
    <!-- Controls -->
    <div class="bottom-left-controls">
        <Dropdown>
            <template #trigger>
                <button class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                    </svg>
                </button>
            </template>
            <a class="block px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
               :class="currentLang === 'zh' ? 'text-primary font-medium' : 'text-gray-700 dark:text-gray-300'"
               href="#" @click.prevent="emit('setLang', 'zh')">中文</a>
            <a class="block px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
               :class="currentLang === 'en' ? 'text-primary font-medium' : 'text-gray-700 dark:text-gray-300'"
               href="#" @click.prevent="emit('setLang', 'en')">English</a>
            <a class="block px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
               :class="currentLang === 'vi' ? 'text-primary font-medium' : 'text-gray-700 dark:text-gray-300'"
               href="#" @click.prevent="emit('setLang', 'vi')">Tiếng Việt</a>
        </Dropdown>
        <Dropdown>
            <template #trigger>
                <button class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                </button>
            </template>
            <button class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2" @click="emit('setTheme', 'light')">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                Light
            </button>
            <button class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2" @click="emit('setTheme', 'dark')">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
                Dark
            </button>
            <button class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2" @click="emit('setTheme', 'auto')">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Auto
            </button>
        </Dropdown>
    </div>
</template>

<script setup>
import Dropdown from '../ui/Dropdown.vue';

defineProps({
    currentLang: String,
});

const emit = defineEmits(['setLang', 'setTheme']);
</script>
