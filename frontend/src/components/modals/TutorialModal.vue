<template>
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
</template>

<script setup>
defineProps(['t']);
</script>
