import { createApp } from 'vue'
import MusicMemo from './MusicMemo.vue'
import { registerSW } from 'virtual:pwa-register'

// Register the service worker for PWA support
registerSW({ immediate: true })

createApp(MusicMemo).mount('#app')
