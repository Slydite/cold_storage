import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  fetchChambers,
  createChamber,
  updateChamber,
  fetchFloors,
  createFloor,
  updateFloor,
  fetchBlocks,
  createBlock,
  updateBlock
} from '../api/location'
import type {
  ChamberInput,
  ChamberUpdateInput,
  FloorInput,
  FloorUpdateInput,
  BlockInput,
  BlockUpdateInput
} from '../api/location'

export function useChamberList(params: {
  facilityId?: Ref<number | undefined> | ComputedRef<number | undefined>
  isActive?: Ref<boolean | undefined>
}) {
  return useQuery({
    queryKey: computed(() => [
      'chambers',
      params.facilityId?.value,
      params.isActive?.value
    ]),
    queryFn: () =>
      fetchChambers({
        facilityId: params.facilityId?.value,
        isActive: params.isActive?.value
      }),
    enabled: computed(() => params.facilityId?.value !== undefined)
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

export function useFloorList(params: {
  facilityId?: Ref<number | undefined> | ComputedRef<number | undefined>
  chamberId?: Ref<number | undefined> | ComputedRef<number | undefined>
  isActive?: Ref<boolean | undefined>
}) {
  return useQuery({
    queryKey: computed(() => [
      'floors',
      params.facilityId?.value,
      params.chamberId?.value,
      params.isActive?.value
    ]),
    queryFn: () =>
      fetchFloors({
        facilityId: params.facilityId?.value,
        chamberId: params.chamberId?.value,
        isActive: params.isActive?.value
      }),
    enabled: computed(
      () => params.facilityId?.value !== undefined || params.chamberId?.value !== undefined
    )
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

export function useBlockList(params: {
  facilityId?: Ref<number | undefined> | ComputedRef<number | undefined>
  chamberId?: Ref<number | undefined> | ComputedRef<number | undefined>
  floorId?: Ref<number | undefined> | ComputedRef<number | undefined>
  isActive?: Ref<boolean | undefined>
}) {
  return useQuery({
    queryKey: computed(() => [
      'blocks',
      params.facilityId?.value,
      params.chamberId?.value,
      params.floorId?.value,
      params.isActive?.value
    ]),
    queryFn: () =>
      fetchBlocks({
        facilityId: params.facilityId?.value,
        chamberId: params.chamberId?.value,
        floorId: params.floorId?.value,
        isActive: params.isActive?.value
      }),
    enabled: computed(
      () =>
        params.facilityId?.value !== undefined ||
        params.chamberId?.value !== undefined ||
        params.floorId?.value !== undefined
    )
  })
}

export function useCreateBlock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: BlockInput) => createBlock(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocks'] })
    }
  })
}

export function useUpdateBlock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: BlockUpdateInput }) => updateBlock(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocks'] })
    }
  })
}

