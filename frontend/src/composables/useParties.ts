import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { fetchParties, createParty } from '../api/party'
import type { PartyInput } from '../api/party'

export function usePartyList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>
) {
  return useQuery({
    queryKey: computed(() => ['parties', facilityId.value]),
    queryFn: () => fetchParties({ facilityId: facilityId.value! }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useCreateParty() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: PartyInput) => createParty(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parties'] })
    }
  })
}
