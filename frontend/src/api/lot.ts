import { lotsList } from './generated/sdk.gen'
import type { LotOutput } from './generated/types.gen'

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
  floor?: string
  partyId?: number
  commodityId?: number
  chamber?: string
  inStockOnly?: boolean
}): Promise<LotOutput[]> {
  const queryObj: Record<string, unknown> = {}
  if (params.facilityId !== undefined) queryObj.facility_id = params.facilityId
  if (params.floor !== undefined) queryObj.floor = params.floor
  if (params.partyId !== undefined) queryObj.party_id = params.partyId
  if (params.commodityId !== undefined) queryObj.commodity_id = params.commodityId
  if (params.chamber !== undefined) queryObj.chamber = params.chamber
  if (params.inStockOnly !== undefined) queryObj.in_stock_only = params.inStockOnly

  const res = await lotsList({
    query: queryObj
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch inventory lots'))
  }
  return (res.data ?? []) as LotOutput[]
}

