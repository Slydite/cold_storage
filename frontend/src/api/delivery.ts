import {
  deliveryNotesList,
  deliveryNotesCreate,
  deliveryNotesPostCreate,
  deliveryNotesCancelCreate,
  deliveryNotesGeneratePdfCreate
} from './generated/sdk.gen'
import type {
  DeliveryNoteOutput,
  DeliveryNoteCreateInput,
  DeliveryLineInput,
  DeliveryLineOutput,
  StatusEnum
} from './generated/types.gen'

export type {
  DeliveryNoteOutput,
  DeliveryNoteCreateInput,
  DeliveryLineInput,
  DeliveryLineOutput,
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

export async function fetchDeliveryNotes(params: {
  facilityId: number
  partyId?: number
  status?: string
}): Promise<DeliveryNoteOutput[]> {
  const res = await deliveryNotesList({
    query: {
      facility_id: params.facilityId,
      party_id: params.partyId,
      status: params.status
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch Delivery Notes'))
  }
  return res.data ?? []
}

export async function createDeliveryNote(
  body: DeliveryNoteCreateInput
): Promise<DeliveryNoteOutput> {
  const res = await deliveryNotesCreate({
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create Delivery Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from Delivery Note creation')
  }
  return res.data
}

export async function postDeliveryNote(id: number): Promise<DeliveryNoteOutput> {
  const res = await deliveryNotesPostCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to post Delivery Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from posting Delivery Note')
  }
  return res.data
}

export async function cancelDeliveryNote(id: number): Promise<DeliveryNoteOutput> {
  const res = await deliveryNotesCancelCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to cancel Delivery Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from cancelling Delivery Note')
  }
  return res.data
}

export async function generateDeliveryNotePdf(id: number): Promise<DeliveryNoteOutput> {
  const res = await deliveryNotesGeneratePdfCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to generate PDF for Delivery Note'))
  }
  if (!res.data) {
    throw new Error('No data returned from Delivery Note PDF generation')
  }
  return res.data
}
