<script setup lang="ts">
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useI18n } from 'vue-i18n'
import { useHistoryDismiss } from '../../composables/useHistoryDismiss'
import { toRef } from 'vue'
import type { PartyOutput } from '../../api/party'

const props = defineProps<{
  visible: boolean
  party: PartyOutput | null
}>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
}>()

const { t } = useI18n()

// Hardware/browser Back closes the dialog instead of leaving the page.
useHistoryDismiss(toRef(props, 'visible'), () => emit('update:visible', false))

const getTypeSeverity = (type?: string) => {
  switch (type) {
    case 'DEPOSITOR':
      return 'success'
    case 'VENDOR':
      return 'info'
    case 'TRANSPORTER':
      return 'warn'
    default:
      return 'secondary'
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="party ? party.name : t('common.details')"
    :style="{ width: '560px', maxWidth: '95vw' }"
  >
    <div v-if="party" class="party-detail-body">
      <div class="top-row">
        <span class="code-chip">{{ party.code }}</span>
        <Tag :value="t(`partyType.${party.type}`, party.type)" :severity="getTypeSeverity(party.type)" />
        <Tag
          :value="party.is_active ? t('status.active') : t('status.inactive')"
          :severity="party.is_active ? 'success' : 'secondary'"
        />
      </div>

      <div class="meta-grid">
        <div class="meta-item">
          <span class="label">{{ t('parties.partyName') }}</span>
          <strong class="val">{{ party.name }}</strong>
        </div>

        <div class="meta-item">
          <span class="label">{{ t('parties.partyType') }}</span>
          <span class="val">{{ party.type_display || party.type }}</span>
        </div>

        <div class="meta-item">
          <span class="label">{{ t('parties.phone') }}</span>
          <span class="val">{{ party.phone || '—' }}</span>
        </div>

        <div class="meta-item">
          <span class="label">{{ t('parties.email') }}</span>
          <span class="val">{{ party.email || '—' }}</span>
        </div>

        <div class="meta-item">
          <span class="label">{{ t('parties.gstin') }}</span>
          <span class="val">{{ party.gstin || '—' }}</span>
        </div>

        <div class="meta-item">
          <span class="label">{{ t('common.workingFacility') }}</span>
          <span class="val">{{ party.facility_name || '—' }}</span>
        </div>

        <div class="meta-item span-2">
          <span class="label">{{ t('parties.address') }}</span>
          <span class="val">{{ party.address || '—' }}</span>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.party-detail-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-top: 6px;
}

.top-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.code-chip {
  font-weight: 700;
  color: var(--accent-primary);
  font-size: 13.5px;
}

.meta-grid {
  display: grid;
  /* minmax(0, 1fr) so a long email or address cannot force the column wider
     than the dialog and introduce horizontal scrolling. */
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.meta-item.span-2 {
  grid-column: span 2;
}

.meta-item .label {
  font-size: 11.5px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.meta-item .val {
  font-size: 13.5px;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}

@media (max-width: 640px) {
  .meta-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .meta-item.span-2 {
    grid-column: span 1;
  }
}
</style>
