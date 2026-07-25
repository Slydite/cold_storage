import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'

export const useFacilityStore = defineStore('facility', () => {
  const getInitialFacilityId = (): number | undefined => {
    const saved = localStorage.getItem('cs_facility_id')
    if (saved) {
      const parsed = parseInt(saved, 10)
      if (!isNaN(parsed)) return parsed
    }
    return undefined
  }

  const selectedFacilityId = ref<number | undefined>(getInitialFacilityId())

  const setSelectedFacilityId = (id: number | undefined) => {
    selectedFacilityId.value = id
  }

  watchEffect(() => {
    if (selectedFacilityId.value !== undefined) {
      localStorage.setItem('cs_facility_id', String(selectedFacilityId.value))
    } else {
      localStorage.removeItem('cs_facility_id')
    }
  })

  return {
    selectedFacilityId,
    setSelectedFacilityId
  }
})
