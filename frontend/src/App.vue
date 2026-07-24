<script setup lang="ts">
import AppLayout from './components/layout/AppLayout.vue'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
</script>

<template>
  <AppLayout>
    <RouterView />
  </AppLayout>
  <Toast position="top-right" />
  <ConfirmDialog />
</template>

<style>
/* Global resets */
html, body, #app {
  height: 100%;
  margin: 0;
}
</style>
