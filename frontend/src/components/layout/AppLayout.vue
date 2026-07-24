<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
</script>

<template>
  <div class="app-layout">
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
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  width: 100%;
  background-color: var(--bg-page);
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
  }
}
</style>
