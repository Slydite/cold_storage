import {
  grnsList,
  grnsRetrieve,
  grnsCreate,
  grnsPostCreate,
  grnsCancelCreate,
  grnsEmailCreate,
  grnsPartialUpdate,
  grnsUpdateAndPostCreate
} from './generated/sdk.gen'
import type {
  GrnOutput,
  GrnCreateInput,
  GrnUpdateInput,
  LotItemInput,
  LotItemUpdateInput,
  LotOutput,
  LoadingChargeModeEnum,
  StatusEnum
} from './generated/types.gen'

export type {
  GrnOutput,
  GrnCreateInput,
  GrnUpdateInput,
  LotItemInput,
  LotItemUpdateInput,
  LotOutput,
  LoadingChargeModeEnum,
  StatusEnum
}

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

export async function fetchGrns(params: {
  facilityId: number
  partyId?: number
  status?: string
}): Promise<GrnOutput[]> {
  const res = await grnsList({
    query: {
      facility_id: params.facilityId,
      party_id: params.partyId,
      status: params.status
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch Goods Receipt Notes'))
  }
  return res.data ?? []
}

export async function fetchGrn(id: number): Promise<GrnOutput> {
  const res = await grnsRetrieve({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch GRN details'))
  }
  if (!res.data) {
    throw new Error('GRN record not found')
  }
  return res.data
}

export async function createGrn(body: GrnCreateInput): Promise<GrnOutput> {
  const res = await grnsCreate({
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create Goods Receipt Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from GRN creation')
  }
  return res.data
}

export async function postGrn(id: number): Promise<GrnOutput> {
  const res = await grnsPostCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to post Goods Receipt Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from posting GRN')
  }
  return res.data
}

export async function cancelGrn(id: number): Promise<GrnOutput> {
  const res = await grnsCancelCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to cancel Goods Receipt Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from cancelling GRN')
  }
  return res.data
}

export async function emailGrn(id: number): Promise<GrnOutput> {
  const res = await grnsEmailCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to email Goods Receipt Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from emailing GRN')
  }
  return res.data
}

export async function updateGrn(id: number, body: GrnUpdateInput): Promise<GrnOutput> {
  const res = await grnsPartialUpdate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to update Goods Receipt Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from GRN update')
  }
  return res.data
}

export async function updateAndPostGrn(id: number, body: GrnUpdateInput): Promise<GrnOutput> {
  const res = await grnsUpdateAndPostCreate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to post Goods Receipt Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from posting GRN')
  }
  return res.data
}


