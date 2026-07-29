import { lotsList } from './generated/sdk.gen'
import type { LotOutput } from './generated/types.gen'
import { apiFetch } from './client'

export type { LotOutput }

function extractErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null) {
    const errObj = error as Record<string, unknown>
    if (typeof errObj.detail === 'string') return errObj.detail
    if (typeof errObj.message === 'string') return errObj.message
    const firstKey = Object.keys(errObj)[0]
    if (firstKey !== undefined) {
      const firstVal = errObj[firstKey]
      if (Array.isArray(firstVal) && firstVal.length > 0 && typeof firstVal[0] === 'string') {
        return `${firstKey}: ${firstVal[0]}`
      }
    }
  }
  return fallback
}

export async function fetchLots(params: {
  facilityId?: number
  chamberId?: number
  floorId?: number
  blockId?: number
  partyId?: number
  commodityId?: number
  inStockOnly?: boolean
}): Promise<LotOutput[]> {
  const queryObj: Record<string, unknown> = {}
  if (params.facilityId !== undefined) queryObj.facility_id = params.facilityId
  if (params.chamberId !== undefined) queryObj.chamber_id = params.chamberId
  if (params.floorId !== undefined) queryObj.floor_id = params.floorId
  if (params.blockId !== undefined) queryObj.block_id = params.blockId
  if (params.partyId !== undefined) queryObj.party_id = params.partyId
  if (params.commodityId !== undefined) queryObj.commodity_id = params.commodityId
  if (params.inStockOnly !== undefined) queryObj.in_stock_only = params.inStockOnly

  const res = await lotsList({
    query: queryObj
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch inventory lots'))
  }
  return (res.data ?? []) as LotOutput[]
}

export async function reserveLotNumber(facilityId: number): Promise<string> {
  const res = await apiFetch('/api/lots/reserve-number/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ facility_id: facilityId })
  })

  if (!res.ok) {
    let errorDetail = 'Failed to reserve lot number'
    try {
      const errorJson = await res.json()
      errorDetail = extractErrorMessage(errorJson, errorDetail)
    } catch {
      // ignore
    }
    throw new Error(errorDetail)
  }

  const data = await res.json()
  return data.lot_number as string
}


