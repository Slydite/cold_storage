<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import AppBottomNav from './AppBottomNav.vue'
import MoreSheet from './MoreSheet.vue'
import { useSidebar } from '../../composables/useSidebar'

const route = useRoute()
const { isOpen, close } = useSidebar()

const isMoreOpen = ref(false)
const toggleMore = () => {
  isMoreOpen.value = !isMoreOpen.value
}
const closeMore = () => {
  isMoreOpen.value = false
}

watch(
  () => route.fullPath,
  () => {
    close()
    closeMore()
  }
)
</script>

<template>
  <div class="app-layout">
    <!-- Semi-transparent backdrop for mobile off-canvas sidebar -->
    <div v-if="isOpen" class="sidebar-backdrop" @click="close" />

    <!-- Sidebar -->
    <AppSidebar />

    <!-- Main Body Container -->
    <div class="main-wrapper">
      <!-- Header -->
      <AppHeader />

      <!-- Page Content Area -->
      <main class="content-area">
        <slot />
      </main>
    </div>

    <!-- Bottom Navigation for Mobile -->
    <AppBottomNav @toggle-more="toggleMore" />

    <!-- More Sheet for Mobile -->
    <MoreSheet :is-open="isMoreOpen" @close="closeMore" />
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  width: 100%;
  background-color: var(--bg-page);
}

.sidebar-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 95;
}

.main-wrapper {
  margin-left: 240px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background-color: var(--bg-page);
  transition: background-color 0.25s ease;
}

.content-area {
  padding: 24px;
  flex: 1;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  box-sizing: border-box;
}

@media (max-width: 768px) {
  .main-wrapper {
    margin-left: 0;
  }
  .content-area {
    padding: 16px;
    padding-bottom: calc(60px + 16px + env(safe-area-inset-bottom));
  }
}
</style>
