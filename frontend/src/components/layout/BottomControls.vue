<template>
    <!-- Controls -->
    <div class="bottom-left-controls">
        <Dropdown>
            <template #trigger>
                <button class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center gap-1">
                    <Heroicon name="LanguageIcon" class="w-4 h-4" />
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
                    <Heroicon name="SunIcon" class="w-4 h-4" />
                </button>
            </template>
            <button class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2" @click="emit('setTheme', 'light')">
                <Heroicon name="SunIcon" class="w-4 h-4" />
                Light
            </button>
            <button class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2" @click="emit('setTheme', 'dark')">
                <Heroicon name="MoonIcon" class="w-4 h-4" />
                Dark
            </button>
            <button class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2" @click="emit('setTheme', 'auto')">
                <Heroicon name="ComputerDesktopIcon" class="w-4 h-4" />
                Auto
            </button>
        </Dropdown>
    </div>
</template>

<script setup>
import Dropdown from '../ui/Dropdown.vue';
import Heroicon from '../ui/Heroicon.vue';

defineProps({
    currentLang: String,
});

const emit = defineEmits(['setLang', 'setTheme']);
</script>
