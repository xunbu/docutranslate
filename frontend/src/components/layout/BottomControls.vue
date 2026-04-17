<template>
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
</template>

<script setup>
defineProps({
    currentLang: String,
});

defineEmits(['setLang', 'setTheme']);
</script>
