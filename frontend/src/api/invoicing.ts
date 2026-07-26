import {
  invoicesList,
  invoicesRetrieve,
  invoicesCreate,
  invoicesPostCreate,
  invoicesCancelCreate
} from './generated/sdk.gen'
import type {
  InvoiceOutput,
  InvoiceLineOutput,
  GenerateInvoicesInput,
  StatusEnum
} from './generated/types.gen'

export type { InvoiceOutput, InvoiceLineOutput, GenerateInvoicesInput, StatusEnum }

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

export async function fetchInvoices(params: {
  facilityId: number
  partyId?: number
  status?: string
}): Promise<InvoiceOutput[]> {
  const res = await invoicesList({
    query: {
      facility_id: params.facilityId,
      party_id: params.partyId,
      status: params.status
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch invoices'))
  }
  return res.data ?? []
}

export async function fetchInvoice(id: number): Promise<InvoiceOutput> {
  const res = await invoicesRetrieve({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch invoice details'))
  }
  if (!res.data) {
    throw new Error('Invoice record not found')
  }
  return res.data
}

export async function generateInvoices(body: {
  facility_id: number
  rent_run_id: number
}): Promise<InvoiceOutput[]> {
  const res = await invoicesCreate({
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to generate invoices'))
  }
  if (!res.data) {
    throw new Error('No data returned from invoice generation')
  }
  return res.data
}

export async function postInvoice(id: number): Promise<InvoiceOutput> {
  const res = await invoicesPostCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to post invoice'))
  }
  if (!res.data) {
    throw new Error('No data returned from posting invoice')
  }
  return res.data
}

export async function cancelInvoice(id: number): Promise<InvoiceOutput> {
  const res = await invoicesCancelCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to cancel invoice'))
  }
  if (!res.data) {
    throw new Error('No data returned from cancelling invoice')
  }
  return res.data
}
