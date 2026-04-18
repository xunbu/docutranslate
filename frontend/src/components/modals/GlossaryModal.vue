<template>
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
</template>

<script setup>
import { inject } from 'vue';

defineProps(['t']);

// Inject from parent
const glossaryData = inject('glossaryData');
</script>
