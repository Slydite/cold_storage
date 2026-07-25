import {
  rateCardsList,
  rateCardsCreate,
  rentRunsList,
  rentRunsRetrieve,
  rentRunsCreate,
  rentRunsPostCreate,
  rentRunsCancelCreate,
  rentRunsPreviewCreate,
  rentRunsGeneratePdfCreate
} from './generated/sdk.gen'
import type {
  RateCardOutput,
  RateCardInput,
  RentRunOutput,
  RentRunCreateInput,
  RentRunLineOutput,
  RentRunPreviewInput,
  RentRunPreviewOutput,
  RentRunPreviewLine,
  MissingRateCard,
  StatusEnum,
  WeightCategoryEnum
} from './generated/types.gen'

export type {
  RateCardOutput,
  RateCardInput,
  RentRunOutput,
  RentRunCreateInput,
  RentRunLineOutput,
  RentRunPreviewInput,
  RentRunPreviewOutput,
  RentRunPreviewLine,
  MissingRateCard,
  StatusEnum,
  WeightCategoryEnum
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

export async function fetchRateCards(params: {
  facilityId: number
  commodityId?: number
  isActive?: boolean
  partyId?: number | null
}): Promise<RateCardOutput[]> {
  const res = await rateCardsList({
    query: {
      facility_id: params.facilityId,
      commodity_id: params.commodityId,
      is_active: params.isActive,
      party_id: params.partyId !== undefined && params.partyId !== null ? String(params.partyId) : undefined
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch rate cards'))
  }
  return res.data ?? []
}

export async function createRateCard(body: RateCardInput): Promise<RateCardOutput> {
  const res = await rateCardsCreate({
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create rate card'))
  }
  if (!res.data) {
    throw new Error('No data returned from rate card creation')
  }
  return res.data
}

export async function fetchRentRuns(params: {
  facilityId: number
  status?: string
}): Promise<RentRunOutput[]> {
  const res = await rentRunsList({
    query: {
      facility_id: params.facilityId,
      status: params.status as StatusEnum | undefined
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch rent runs'))
  }
  return res.data ?? []
}

export async function fetchRentRun(id: number): Promise<RentRunOutput> {
  const res = await rentRunsRetrieve({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch rent run details'))
  }
  if (!res.data) {
    throw new Error('Rent run record not found')
  }
  return res.data
}

export async function previewRentRun(body: RentRunPreviewInput): Promise<RentRunPreviewOutput> {
  const res = await rentRunsPreviewCreate({
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to preview rent run'))
  }
  if (!res.data) {
    throw new Error('No data returned from rent run preview')
  }
  return res.data
}

export async function createRentRun(body: RentRunCreateInput): Promise<RentRunOutput> {
  const res = await rentRunsCreate({
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create rent run'))
  }
  if (!res.data) {
    throw new Error('No data returned from rent run creation')
  }
  return res.data
}

export async function postRentRun(id: number): Promise<RentRunOutput> {
  const res = await rentRunsPostCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to post rent run'))
  }
  if (!res.data) {
    throw new Error('No data returned from posting rent run')
  }
  return res.data
}

export async function cancelRentRun(id: number): Promise<RentRunOutput> {
  const res = await rentRunsCancelCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to cancel rent run'))
  }
  if (!res.data) {
    throw new Error('No data returned from cancelling rent run')
  }
  return res.data
}

export async function generateRentRunPdf(id: number): Promise<RentRunOutput> {
  const res = await rentRunsGeneratePdfCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to generate PDF for rent run'))
  }
  if (!res.data) {
    throw new Error('No data returned from PDF generation')
  }
  return res.data
}
