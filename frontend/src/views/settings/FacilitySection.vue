<script setup lang="ts">
import FacilityForm from '../../components/settings/FacilityForm.vue'
import FacilityListTable from '../../components/settings/FacilityListTable.vue'
</script>

<template>
  <div class="facility-tab-content">
    <FacilityForm />
    <FacilityListTable />
  </div>
</template>

<style scoped>
.facility-tab-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
