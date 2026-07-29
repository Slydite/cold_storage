<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, X } from 'lucide-vue-next'

interface NavigatorStandalone extends Navigator {
  standalone?: boolean;
}

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

const { t } = useI18n()

const deferredPrompt = ref<BeforeInstallPromptEvent | null>(null)
const isDismissed = ref(false)
const isStandalone = ref(false)
const showPrompt = ref(false)

const isIOS = computed(() => {
  return /iPad|iPhone|iPod/.test(navigator.userAgent)
})

const checkStandalone = () => {
  const nav = navigator as NavigatorStandalone
  const isStandaloneMatch = window.matchMedia('(display-mode: standalone)').matches
  const isIOSStandalone = !!nav.standalone
  isStandalone.value = isStandaloneMatch || isIOSStandalone
}

const handleBeforeInstallPrompt = (e: Event) => {
  e.preventDefault()
  deferredPrompt.value = e as BeforeInstallPromptEvent
  checkShowPrompt()
}

const checkShowPrompt = () => {
  checkStandalone()
  const dismissed = localStorage.getItem('pwa_install_prompt_dismissed') === 'true'
  isDismissed.value = dismissed

  // Show if not standalone AND not dismissed AND (deferredPrompt is captured OR isIOS for iOS custom prompt)
  showPrompt.value = !isStandalone.value && !isDismissed.value && (!!deferredPrompt.value || isIOS.value)
}

onMounted(() => {
  window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
  checkShowPrompt()
})

onUnmounted(() => {
  window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
})

const install = async () => {
  if (!deferredPrompt.value) return
  await deferredPrompt.value.prompt()
  const { outcome } = await deferredPrompt.value.userChoice
  if (outcome === 'accepted') {
    deferredPrompt.value = null
    showPrompt.value = false
  }
}

const dismiss = () => {
  localStorage.setItem('pwa_install_prompt_dismissed', 'true')
  isDismissed.value = true
  showPrompt.value = false
}
</script>

<template>
  <div v-if="showPrompt" class="install-prompt-banner">
    <div class="prompt-content">
      <div class="prompt-header">
        <div class="prompt-title">
          <Download :size="18" class="prompt-icon" />
          <span>{{ t('installPrompt.bannerTitle') }}</span>
        </div>
        <button class="close-btn" @click="dismiss" :title="t('installPrompt.dismissBtn')">
          <X :size="16" />
        </button>
      </div>
      
      <p class="prompt-text">
        <template v-if="isIOS">
          {{ t('installPrompt.iosPrompt') }}
        </template>
        <template v-else>
          {{ t('installPrompt.bannerText') }}
        </template>
      </p>
      
      <div v-if="!isIOS" class="prompt-actions">
        <button class="btn-cancel" @click="dismiss">{{ t('installPrompt.dismissBtn') }}</button>
        <button class="btn-install" @click="install">{{ t('installPrompt.installBtn') }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.install-prompt-banner {
  display: none;
}

@media (max-width: 768px) {
  .install-prompt-banner {
    display: block;
    position: fixed;
    bottom: calc(76px + env(safe-area-inset-bottom));
    left: 16px;
    right: 16px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 101;
    animation: slideUp 0.3s ease-out;
  }
}

.prompt-content {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.prompt-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 14px;
  color: var(--text-primary);
}

.prompt-icon {
  color: var(--accent-primary);
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-primary);
}

.prompt-text {
  font-size: 12.5px;
  line-height: 1.4;
  color: var(--text-secondary);
  margin: 0;
}

.prompt-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-primary);
}

.btn-install {
  background: var(--accent-primary);
  border: 1px solid var(--accent-primary);
  color: #ffffff;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-install:hover {
  background: var(--accent-primary-hover);
  border-color: var(--accent-primary-hover);
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
</style>
