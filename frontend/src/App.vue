<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppLayout from './components/layout/AppLayout.vue'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'

const route = useRoute()
</script>

<template>
  <template v-if="route.meta.public">
    <RouterView />
  </template>
  <template v-else>
    <AppLayout>
      <RouterView />
    </AppLayout>
  </template>
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
