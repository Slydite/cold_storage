import {
  commoditiesList,
  commoditiesCreate,
  commoditiesUpdate,
  commoditiesAliasesCreate,
  commoditiesAliasesDestroy,
  commoditiesMergeCreate
} from './generated/sdk.gen'
import type {
  CommodityOutput,
  CommodityInput,
  CommodityAlias,
  CommodityAliasInput,
  CommodityMergeInput
} from './generated/types.gen'

export type { CommodityOutput, CommodityInput, CommodityAlias }

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

export async function createCommodity(body: CommodityInput): Promise<CommodityOutput> {
  const res = await commoditiesCreate({ body })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create commodity'))
  }
  if (!res.data) {
    throw new Error('No data returned from commodity creation')
  }
  return res.data
}

export async function updateCommodity(
  id: number,
  body: CommodityInput
): Promise<CommodityOutput> {
  const res = await commoditiesUpdate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to update commodity'))
  }
  if (!res.data) {
    throw new Error('No data returned from commodity update')
  }
  return res.data
}

export async function addCommodityAlias(id: number, body: CommodityAliasInput): Promise<CommodityAlias> {
  const res = await commoditiesAliasesCreate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to add alias'))
  }
  if (!res.data) {
    throw new Error('No data returned from alias creation')
  }
  return res.data
}

export async function deleteCommodityAlias(id: number, aliasId: number): Promise<void> {
  const res = await commoditiesAliasesDestroy({
    path: {
      id,
      alias_id: String(aliasId)
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to delete alias'))
  }
}

export async function mergeCommodities(id: number, body: CommodityMergeInput): Promise<unknown> {
  const res = await commoditiesMergeCreate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to merge commodities'))
  }
  return res.data
}
