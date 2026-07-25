import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  fetchFloors,
  createFloor,
  updateFloor,
  fetchChambers,
  createChamber,
  updateChamber
} from '../api/location'
import type {
  FloorInput,
  FloorUpdateInput,
  ChamberInput,
  ChamberUpdateInput
} from '../api/location'

export function useFloorList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  isActive?: Ref<boolean | undefined>
) {
  return useQuery({
    queryKey: computed(() => ['floors', facilityId.value, isActive?.value]),
    queryFn: () => fetchFloors({ facilityId: facilityId.value!, isActive: isActive?.value }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useCreateFloor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: FloorInput) => createFloor(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['floors'] })
    }
  })
}

export function useUpdateFloor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: FloorUpdateInput }) => updateFloor(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['floors'] })
    }
  })
}

export function useChamberList(params: {
  facilityId?: Ref<number | undefined> | ComputedRef<number | undefined>
  floorId?: Ref<number | undefined> | ComputedRef<number | undefined>
  isActive?: Ref<boolean | undefined>
}) {
  return useQuery({
    queryKey: computed(() => [
      'chambers',
      params.facilityId?.value,
      params.floorId?.value,
      params.isActive?.value
    ]),
    queryFn: () =>
      fetchChambers({
        facilityId: params.facilityId?.value,
        floorId: params.floorId?.value,
        isActive: params.isActive?.value
      }),
    enabled: computed(
      () => params.facilityId?.value !== undefined || params.floorId?.value !== undefined
    )
  })
}

export function useCreateChamber() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ChamberInput) => createChamber(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chambers'] })
    }
  })
}

export function useUpdateChamber() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: ChamberUpdateInput }) =>
      updateChamber(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chambers'] })
    }
  })
}
