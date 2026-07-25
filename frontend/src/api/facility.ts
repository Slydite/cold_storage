import { facilitiesList, facilitiesCreate, facilitiesUpdate } from './generated/sdk.gen'
import type { FacilityOutput, FacilityInput } from './generated/types.gen'

export type { FacilityOutput, FacilityInput }

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

export async function fetchFacilities(): Promise<FacilityOutput[]> {
  const res = await facilitiesList()
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch facilities'))
  }
  return res.data ?? []
}

export async function createFacility(body: FacilityInput): Promise<FacilityOutput> {
  const res = await facilitiesCreate({ body })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create facility'))
  }
  if (!res.data) {
    throw new Error('No data returned from facility creation')
  }
  return res.data
}

export async function updateFacility(id: number, body: FacilityInput): Promise<FacilityOutput> {
  const res = await facilitiesUpdate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to update facility'))
  }
  if (!res.data) {
    throw new Error('No data returned from facility update')
  }
  return res.data
}
