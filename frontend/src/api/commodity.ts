import { commoditiesList } from './generated/sdk.gen'
import type { CommodityOutput } from './generated/types.gen'

export type { CommodityOutput }

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

export async function fetchCommodities(params: { facilityId: number }): Promise<CommodityOutput[]> {
  const res = await commoditiesList({
    query: {
      facility_id: params.facilityId
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch commodities'))
  }
  return res.data ?? []
}
