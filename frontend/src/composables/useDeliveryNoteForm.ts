import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useCreateDeliveryNote } from './useDeliveryNotes'
import { useToast } from 'primevue/usetoast'
import type { DeliveryNoteCreateInput, DeliveryLineInput } from '../api/delivery'
import type { LotOutput } from '../api/lot'

const lineItemSchema = z.object({
  lot_id: z
    .number()
    .nullable()
    .refine((v): v is number => v != null && v > 0, { message: 'Lot is required' }),
  qty: z.number().min(1, 'Qty must be at least 1')
})

export type FormDeliveryLine = z.input<typeof lineItemSchema>
type ValidatedDeliveryLine = z.output<typeof lineItemSchema>

const deliveryNoteFormSchema = z.object({
  party_id: z
    .number()
    .nullable()
    .refine((v): v is number => v != null && v > 0, { message: 'Party is required' }),
  dispatch_date: z
    .date()
    .nullable()
    .refine((v): v is Date => v != null, { message: 'Dispatch date is required' }),
  vehicle_number: z.string().optional(),
  driver_name: z.string().optional(),
  remarks: z.string().optional()
})

const createDefaultLine = (): FormDeliveryLine => ({
  lot_id: null,
  qty: 1
})

export function useDeliveryNoteForm(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  availableLots: Ref<LotOutput[]> | ComputedRef<LotOutput[]>,
  onSuccessCallback?: (dnNumber: string, status: string) => void
) {
  const toast = useToast()
  const createMutation = useCreateDeliveryNote()

  const { handleSubmit, errors, defineField, resetForm } = useForm({
    validationSchema: toTypedSchema(deliveryNoteFormSchema),
    initialValues: {
      party_id: null,
      dispatch_date: new Date(),
      vehicle_number: '',
      driver_name: '',
      remarks: ''
    }
  })

  const [party_id, partyIdProps] = defineField('party_id')
  const [dispatch_date, dispatchDateProps] = defineField('dispatch_date')
  const [vehicle_number, vehicleNoProps] = defineField('vehicle_number')
  const [driver_name, driverNameProps] = defineField('driver_name')
  const [remarks, remarksProps] = defineField('remarks')

  const lines = ref<FormDeliveryLine[]>([createDefaultLine()])

  const addLineRow = () => {
    lines.value.push({
      lot_id: null,
      qty: 1
    })
  }

  const removeLineRow = (index: number) => {
    if (lines.value.length <= 1) return
    lines.value.splice(index, 1)
  }

  const totalQty = computed(() => {
    return lines.value.reduce((sum, line) => sum + (line?.qty || 0), 0)
  })

  const getLotAvailable = (lotId: number | null): number | null => {
    if (lotId == null) return null
    const lot = availableLots.value.find((l) => l.id === lotId)
    return lot ? lot.remaining_qty : null
  }

  const getLineQtyError = (index: number): string | null => {
    const line = lines.value[index]
    if (!line || line.lot_id == null) return null
    const avail = getLotAvailable(line.lot_id)
    if (avail !== null && line.qty > avail) {
      return `Qty cannot exceed available stock (${avail})`
    }
    return null
  }

  const hasQtyExceeded = computed(() => {
    return lines.value.some((_, idx) => getLineQtyError(idx) !== null)
  })

  const handleResetForm = () => {
    resetForm()
    lines.value = [createDefaultLine()]
  }

  const submitForm = async (targetStatus: 'DRAFT' | 'POSTED') => {
    if (!facilityId.value) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Facility ID is not available.',
        life: 4000
      })
      return
    }

    if (hasQtyExceeded.value) {
      toast.add({
        severity: 'error',
        summary: 'Validation Error',
        detail: 'One or more lines exceed the available lot quantity.',
        life: 4000
      })
      return
    }

    const submitFn = handleSubmit(async (formValues) => {
      const parsed = z.array(lineItemSchema).min(1, 'At least one line item is required').safeParse(lines.value)
      if (!parsed.success) {
        const firstIssue = parsed.error.issues[0]
        const msg = firstIssue ? firstIssue.message : 'Invalid line items'
        toast.add({
          severity: 'error',
          summary: 'Validation Error',
          detail: msg,
          life: 4000
        })
        return
      }

      for (let i = 0; i < parsed.data.length; i++) {
        const line: ValidatedDeliveryLine | undefined = parsed.data[i]
        if (!line) continue
        const avail = getLotAvailable(line.lot_id)
        if (avail !== null && line.qty > avail) {
          toast.add({
            severity: 'error',
            summary: 'Validation Error',
            detail: `Line item quantity (${line.qty}) exceeds available lot quantity (${avail}).`,
            life: 4000
          })
          return
        }
      }

      const yyyy = formValues.dispatch_date.getFullYear()
      const mm = String(formValues.dispatch_date.getMonth() + 1).padStart(2, '0')
      const dd = String(formValues.dispatch_date.getDate()).padStart(2, '0')
      const formattedDate = `${yyyy}-${mm}-${dd}`

      const formattedLines: DeliveryLineInput[] = parsed.data.map((line: ValidatedDeliveryLine) => ({
        lot_id: line.lot_id,
        qty: line.qty
      }))

      const payload: DeliveryNoteCreateInput = {
        facility_id: facilityId.value!,
        party_id: formValues.party_id,
        dispatch_date: formattedDate,
        vehicle_number: formValues.vehicle_number || undefined,
        driver_name: formValues.driver_name || undefined,
        remarks: formValues.remarks || undefined,
        status: targetStatus,
        lines: formattedLines
      }

      try {
        const result = await createMutation.mutateAsync(payload)
        if (onSuccessCallback) {
          onSuccessCallback(result.dn_number, targetStatus)
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to create Delivery Note'
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: msg,
          life: 5000
        })
      }
    })

    await submitFn()
  }

  return {
    party_id,
    partyIdProps,
    dispatch_date,
    dispatchDateProps,
    vehicle_number,
    vehicleNoProps,
    driver_name,
    driverNameProps,
    remarks,
    remarksProps,
    lines,
    errors,
    addLineRow,
    removeLineRow,
    totalQty,
    getLotAvailable,
    getLineQtyError,
    hasQtyExceeded,
    submitForm,
    isSubmitting: createMutation.isPending,
    resetForm: handleResetForm
  }
}
