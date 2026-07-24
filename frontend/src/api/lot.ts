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
  facilityId: number
  partyId?: number
  commodityId?: number
  chamber?: string
  inStockOnly?: boolean
}): Promise<LotOutput[]> {
  const res = await lotsList({
    query: {
      facility_id: params.facilityId,
      party_id: params.partyId,
      commodity_id: params.commodityId,
      chamber: params.chamber,
      in_stock_only: params.inStockOnly
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch inventory lots'))
  }
  return res.data ?? []
}
