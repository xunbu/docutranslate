<template>
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
</template>

<script setup>
defineProps(['t']);
</script>
