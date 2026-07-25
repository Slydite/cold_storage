import {
  floorsList,
  floorsCreate,
  floorsUpdate,
  chambersList,
  chambersCreate,
  chambersUpdate
} from './generated/sdk.gen'
import type {
  FloorOutput,
  FloorInput,
  FloorUpdateInput,
  ChamberOutput,
  ChamberInput,
  ChamberUpdateInput
} from './generated/types.gen'

export type {
  FloorOutput,
  FloorInput,
  FloorUpdateInput,
  ChamberOutput,
  ChamberInput,
  ChamberUpdateInput
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

export async function fetchFloors(params: {
  facilityId: number
  isActive?: boolean
}): Promise<FloorOutput[]> {
  const res = await floorsList({
    query: {
      facility_id: params.facilityId,
      is_active: params.isActive
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch floors'))
  }
  return res.data ?? []
}

export async function createFloor(body: FloorInput): Promise<FloorOutput> {
  const res = await floorsCreate({ body })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create floor'))
  }
  if (!res.data) {
    throw new Error('No data returned from floor creation')
  }
  return res.data
}

export async function updateFloor(id: number, body: FloorUpdateInput): Promise<FloorOutput> {
  const res = await floorsUpdate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to update floor'))
  }
  if (!res.data) {
    throw new Error('No data returned from floor update')
  }
  return res.data
}

export async function fetchChambers(params: {
  facilityId?: number
  floorId?: number
  isActive?: boolean
}): Promise<ChamberOutput[]> {
  const res = await chambersList({
    query: {
      facility_id: params.facilityId,
      floor_id: params.floorId,
      is_active: params.isActive
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch chambers'))
  }
  return res.data ?? []
}

export async function createChamber(body: ChamberInput): Promise<ChamberOutput> {
  const res = await chambersCreate({ body })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create chamber'))
  }
  if (!res.data) {
    throw new Error('No data returned from chamber creation')
  }
  return res.data
}

export async function updateChamber(id: number, body: ChamberUpdateInput): Promise<ChamberOutput> {
  const res = await chambersUpdate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to update chamber'))
  }
  if (!res.data) {
    throw new Error('No data returned from chamber update')
  }
  return res.data
}
