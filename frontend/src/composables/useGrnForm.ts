import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useCreateGrn } from './useGrns'
import { useToast } from 'primevue/usetoast'
import type { GrnCreateInput, LotItemInput } from '../api/grn'

const lineItemSchema = z.object({
  commodity_id: z
    .number()
    .nullable()
    .refine((v): v is number => v != null && v > 0, { message: 'Commodity is required' }),
  chamber: z.string(),
  initial_qty: z.number().min(1, 'Qty must be at least 1'),
  unit_weight: z.number().nullable(),
  rent_rate_per_unit: z.number().nullable()
})

// Working state used while the form is being edited (nullable fields for the "not yet chosen" state).
export type FormLineItem = z.input<typeof lineItemSchema>
// Strictly-validated shape produced once the line item passes validation.
type ValidatedLineItem = z.output<typeof lineItemSchema>

const grnFormSchema = z.object({
  party_id: z
    .number()
    .nullable()
    .refine((v): v is number => v != null && v > 0, { message: 'Party is required' }),
  receipt_date: z
    .date()
    .nullable()
    .refine((v): v is Date => v != null, { message: 'Receipt date is required' }),
  vehicle_number: z.string().optional(),
  driver_name: z.string().optional(),
  remarks: z.string().optional()
})

const createDefaultLineItem = (): FormLineItem => ({
  commodity_id: null,
  chamber: 'Chamber A',
  initial_qty: 100,
  unit_weight: null,
  rent_rate_per_unit: null
})

export function useGrnForm(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  onSuccessCallback?: (grnNumber: string, status: string) => void
) {
  const toast = useToast()
  const createGrnMutation = useCreateGrn()

  const { handleSubmit, errors, defineField, resetForm } = useForm({
    validationSchema: toTypedSchema(grnFormSchema),
    initialValues: {
      party_id: null,
      receipt_date: new Date(),
      vehicle_number: '',
      driver_name: '',
      remarks: ''
    }
  })

  const [party_id, partyIdProps] = defineField('party_id')
  const [receipt_date, receiptDateProps] = defineField('receipt_date')
  const [vehicle_number, vehicleNoProps] = defineField('vehicle_number')
  const [driver_name, driverNameProps] = defineField('driver_name')
  const [remarks, remarksProps] = defineField('remarks')

  const items = ref<FormLineItem[]>([createDefaultLineItem()])

  const addItemRow = () => {
    items.value.push({
      commodity_id: null,
      chamber: 'Chamber A',
      initial_qty: 1,
      unit_weight: null,
      rent_rate_per_unit: null
    })
  }

  const removeItemRow = (index: number) => {
    if (items.value.length <= 1) return
    items.value.splice(index, 1)
  }

  const totalNetWeight = computed(() => {
    return items.value.reduce((sum, item) => {
      const qty = item.initial_qty || 0
      const weight = item.unit_weight != null ? Number(item.unit_weight) : 0
      return sum + qty * weight
    }, 0)
  })

  const totalAmount = computed(() => {
    return items.value.reduce((sum, item) => {
      const qty = item.initial_qty || 0
      const rate = item.rent_rate_per_unit != null ? Number(item.rent_rate_per_unit) : 0
      return sum + qty * rate
    }, 0)
  })

  const handleResetForm = () => {
    resetForm()
    items.value = [createDefaultLineItem()]
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

    const submitFn = handleSubmit(async (formValues) => {
      const parsed = z.array(lineItemSchema).min(1, 'At least one line item is required').safeParse(items.value)
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

      const yyyy = formValues.receipt_date.getFullYear()
      const mm = String(formValues.receipt_date.getMonth() + 1).padStart(2, '0')
      const dd = String(formValues.receipt_date.getDate()).padStart(2, '0')
      const formattedDate = `${yyyy}-${mm}-${dd}`

      const formattedItems: LotItemInput[] = parsed.data.map((item: ValidatedLineItem) => ({
        commodity_id: item.commodity_id,
        chamber: item.chamber || undefined,
        initial_qty: item.initial_qty,
        unit_weight: item.unit_weight != null ? String(item.unit_weight) : undefined,
        rent_rate_per_unit: item.rent_rate_per_unit != null ? String(item.rent_rate_per_unit) : undefined
      }))

      const payload: GrnCreateInput = {
        facility_id: facilityId.value!,
        party_id: formValues.party_id,
        receipt_date: formattedDate,
        vehicle_number: formValues.vehicle_number || undefined,
        driver_name: formValues.driver_name || undefined,
        remarks: formValues.remarks || undefined,
        status: targetStatus,
        items: formattedItems
      }

      try {
        const result = await createGrnMutation.mutateAsync(payload)
        const isDraft = targetStatus === 'DRAFT'
        toast.add({
          severity: isDraft ? 'info' : 'success',
          summary: isDraft ? 'Draft Saved' : 'GRN Created',
          detail: `GRN ${result.grn_number} has been successfully ${isDraft ? 'saved as draft' : 'posted'}.`,
          life: 4000
        })
        if (onSuccessCallback) {
          onSuccessCallback(result.grn_number, targetStatus)
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to create GRN'
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
    receipt_date,
    receiptDateProps,
    vehicle_number,
    vehicleNoProps,
    driver_name,
    driverNameProps,
    remarks,
    remarksProps,
    items,
    errors,
    addItemRow,
    removeItemRow,
    totalNetWeight,
    totalAmount,
    submitForm,
    isSubmitting: createGrnMutation.isPending,
    resetForm: handleResetForm
  }
}

