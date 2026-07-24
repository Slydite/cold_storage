import { computed } from 'vue'
import { useFacility } from './useFacility'
import { useLotList } from './useLots'
import { useGrnList } from './useGrns'
import { useDeliveryNoteList } from './useDeliveryNotes'

export interface ActivityItem {
  id: string
  title: string
  partyName: string
  time: string
  createdAt: string
  type: 'grn' | 'dn'
  badgeClass: string
}

export interface StockGroup {
  label: string
  qty: number // in MT
  count: number // number of lots
}

export function formatRelativeTime(dateString: string): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  const timestamp = date.getTime()
  if (isNaN(timestamp)) return ''

  const now = Date.now()
  const diffMs = now - timestamp
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)

  if (diffSec < 60) return 'Just now'
  if (diffMin < 60) return `${diffMin} ${diffMin === 1 ? 'min' : 'mins'} ago`
  if (diffHr < 24) return `${diffHr} ${diffHr === 1 ? 'hr' : 'hrs'} ago`
  if (diffDay < 30) return `${diffDay} ${diffDay === 1 ? 'day' : 'days'} ago`

  return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
}

export function useDashboardStats() {
  const {
    facilityId,
    isLoading: loadingFacility,
    isError: facilityError,
    refetch: refetchFacility
  } = useFacility()

  const inStockFilter = computed(() => ({ inStockOnly: true }))
  const lotQuery = useLotList(facilityId, inStockFilter)
  const grnQuery = useGrnList(facilityId)
  const deliveryNoteQuery = useDeliveryNoteList(facilityId)

  // Unit assumption: unit_weight is stored in kg per unit.
  // Multiplying remaining_qty by Number(unit_weight || 0) gives weight in kg.
  // Dividing by 1000 converts kg to Metric Tons (MT).
  // If unit_weight is missing or invalid, weight defaults to 0.
  const totalStock = computed(() => {
    const lots = lotQuery.data.value ?? []
    return lots.reduce((acc, lot) => {
      if (lot.remaining_qty <= 0) return acc
      const weightKg = Number(lot.unit_weight || 0)
      const mt = (lot.remaining_qty * weightKg) / 1000
      return acc + mt
    }, 0)
  })

  const activeLots = computed(() => {
    const lots = lotQuery.data.value ?? []
    return lots.filter((lot) => lot.remaining_qty > 0).length
  })

  const totalGrns = computed(() => grnQuery.data.value?.length ?? 0)

  const totalDeliveryNotes = computed(() => deliveryNoteQuery.data.value?.length ?? 0)

  const recentActivities = computed<ActivityItem[]>(() => {
    const grns = grnQuery.data.value ?? []
    const dns = deliveryNoteQuery.data.value ?? []

    const grnItems: ActivityItem[] = grns.map((grn) => ({
      id: `grn-${grn.id}`,
      title: `GRN ${grn.grn_number} created`,
      partyName: grn.party_name || '',
      time: formatRelativeTime(grn.created_at),
      createdAt: grn.created_at,
      type: 'grn',
      badgeClass: 'badge-purple'
    }))

    const dnItems: ActivityItem[] = dns.map((dn) => ({
      id: `dn-${dn.id}`,
      title: `DN ${dn.dn_number} created`,
      partyName: dn.party_name || '',
      time: formatRelativeTime(dn.created_at),
      createdAt: dn.created_at,
      type: 'dn',
      badgeClass: 'badge-blue'
    }))

    const combined = [...grnItems, ...dnItems]
    combined.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    return combined.slice(0, 5)
  })

  const stockByCommodity = computed<StockGroup[]>(() => {
    const lots = lotQuery.data.value ?? []
    const map = new Map<string, { qty: number; count: number }>()

    for (const lot of lots) {
      if (lot.remaining_qty <= 0) continue
      const key = lot.commodity_name || 'Unspecified'
      const weightKg = Number(lot.unit_weight || 0)
      const mt = (lot.remaining_qty * weightKg) / 1000
      const existing = map.get(key) ?? { qty: 0, count: 0 }
      map.set(key, {
        qty: existing.qty + mt,
        count: existing.count + 1
      })
    }

    return Array.from(map.entries()).map(([label, val]) => ({
      label,
      qty: Number(val.qty.toFixed(2)),
      count: val.count
    }))
  })

  const stockByChamber = computed<StockGroup[]>(() => {
    const lots = lotQuery.data.value ?? []
    const map = new Map<string, { qty: number; count: number }>()

    for (const lot of lots) {
      if (lot.remaining_qty <= 0) continue
      const key = lot.chamber || 'Unassigned'
      const weightKg = Number(lot.unit_weight || 0)
      const mt = (lot.remaining_qty * weightKg) / 1000
      const existing = map.get(key) ?? { qty: 0, count: 0 }
      map.set(key, {
        qty: existing.qty + mt,
        count: existing.count + 1
      })
    }

    return Array.from(map.entries()).map(([label, val]) => ({
      label,
      qty: Number(val.qty.toFixed(2)),
      count: val.count
    }))
  })

  const isLoading = computed(
    () =>
      loadingFacility.value ||
      lotQuery.isLoading.value ||
      grnQuery.isLoading.value ||
      deliveryNoteQuery.isLoading.value
  )

  const isError = computed(
    () =>
      facilityError.value ||
      lotQuery.isError.value ||
      grnQuery.isError.value ||
      deliveryNoteQuery.isError.value
  )

  const errorMessage = computed(() => {
    if (facilityError.value) return 'Failed to load facility information'
    if (lotQuery.error.value instanceof Error) return lotQuery.error.value.message
    if (grnQuery.error.value instanceof Error) return grnQuery.error.value.message
    if (deliveryNoteQuery.error.value instanceof Error) return deliveryNoteQuery.error.value.message
    return 'Failed to load dashboard metrics'
  })

  const refetch = () => {
    refetchFacility()
    lotQuery.refetch()
    grnQuery.refetch()
    deliveryNoteQuery.refetch()
  }

  return {
    totalStock,
    activeLots,
    totalGrns,
    totalDeliveryNotes,
    recentActivities,
    stockByCommodity,
    stockByChamber,
    isLoading,
    isError,
    errorMessage,
    refetch
  }
}
