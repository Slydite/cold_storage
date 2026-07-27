import {
  invoicesList,
  invoicesRetrieve,
  invoicesCreate,
  invoicesPostCreate,
  invoicesCancelCreate,
  invoicesPaymentsCreate,
  invoicesPaymentsDestroy,
  invoicesPreviewList
} from './generated/sdk.gen'
import type {
  InvoiceOutput,
  InvoiceLineOutput,
  GenerateInvoicesInput,
  PaymentInput,
  PaymentOutput,
  StatusEnum,
  InvoicePreviewPartyOutput,
  InvoicePreviewLineOutput
} from './generated/types.gen'

export type {
  InvoiceOutput,
  InvoiceLineOutput,
  GenerateInvoicesInput,
  PaymentInput,
  PaymentOutput,
  StatusEnum,
  InvoicePreviewPartyOutput,
  InvoicePreviewLineOutput
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

export async function generateInvoices(body: GenerateInvoicesInput): Promise<InvoiceOutput[]> {
  const res = await invoicesCreate({
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to generate invoices'))
  }
  if (!res.data) {
    throw new Error('No data returned from invoice generation')
  }
  return Array.isArray(res.data) ? res.data : [res.data]
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

// The API returns the full refreshed invoice (with recalculated amount_paid /
// amount_due / payment_status), not the bare payment row.
export async function createInvoicePayment(
  invoiceId: number,
  body: PaymentInput
): Promise<InvoiceOutput> {
  const res = await invoicesPaymentsCreate({
    path: { id: invoiceId },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to record payment'))
  }
  if (!res.data) {
    throw new Error('No data returned from recording payment')
  }
  return res.data
}

export async function deleteInvoicePayment(
  invoiceId: number,
  paymentId: number
): Promise<void> {
  const res = await invoicesPaymentsDestroy({
    path: { id: invoiceId, payment_id: String(paymentId) }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to delete payment'))
  }
}

export async function fetchInvoicePreview(params: {
  facilityId: number
  partyId?: number
}): Promise<InvoicePreviewPartyOutput[]> {
  const res = await invoicesPreviewList({
    query: {
      facility_id: params.facilityId,
      party_id: params.partyId
    }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch invoice preview'))
  }
  return res.data ?? []
}

