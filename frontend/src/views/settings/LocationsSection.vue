<script setup lang="ts">
import ChamberManager from '../../components/settings/ChamberManager.vue'
import FloorManager from '../../components/settings/FloorManager.vue'
import BlockManager from '../../components/settings/BlockManager.vue'
</script>

<template>
  <div class="locations-tab-content">
    <ChamberManager />
    <FloorManager />
    <BlockManager />
  </div>
</template>

<style scoped>
.locations-tab-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
