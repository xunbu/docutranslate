<template>
    <div class="prose dark:prose-invert max-w-none" v-html="t('tutorialModalBody')"></div>
    <div class="mt-4 flex justify-end">
        <button type="button" class="px-4 py-2 bg-primary text-white rounded hover:bg-primary-hover transition-colors" @click="$emit('close')">
            {{ t('tutorialUnderstandBtn') }}
        </button>
    </div>
</template>

<script setup>
defineProps(['t']);
defineEmits(['close']);
</script>
