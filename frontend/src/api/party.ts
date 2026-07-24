import { partiesList, partiesCreate } from './generated/sdk.gen'
import type { PartyOutput, PartyInput, TypeEnum } from './generated/types.gen'

export type { PartyOutput, PartyInput, TypeEnum }

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

export async function fetchParties(params: { facilityId: number }): Promise<PartyOutput[]> {
  const res = await partiesList({
    query: {
      facility_id: params.facilityId
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch parties'))
  }
  return res.data ?? []
}

export async function createParty(body: PartyInput): Promise<PartyOutput> {
  const res = await partiesCreate({
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create party'))
  }
  if (!res.data) {
    throw new Error('No data returned from party creation')
  }
  return res.data
}

