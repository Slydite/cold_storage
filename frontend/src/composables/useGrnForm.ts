import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useI18n } from 'vue-i18n'
import { useCreateGrn } from './useGrns'
import { useToast } from 'primevue/usetoast'
import type { GrnCreateInput, LotItemInput, LoadingChargeModeEnum } from '../api/grn'

export interface FormLineItem {
  commodity_id: number | null
  chamber_id?: number | null
  floor_id?: number | null
  block_id?: number | null
  initial_qty: number
  unit?: string
  unit_weight?: number | null
  rent_rate_per_unit?: number | null
}

const createDefaultLineItem = (): FormLineItem => ({
  commodity_id: null,
  chamber_id: null,
  floor_id: null,
  block_id: null,
  initial_qty: 100,
  unit: 'Bags',
  unit_weight: null,
  rent_rate_per_unit: null
})

export function useGrnForm(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  onSuccessCallback?: (grnNumber: string, status: string) => void
) {
  const toast = useToast()
  const { t } = useI18n()
  const createGrnMutation = useCreateGrn()

  const lineItemSchema = computed(() =>
    z.object({
      commodity_id: z
        .number()
        .nullable()
        .refine((v): v is number => v != null && v > 0, { message: t('validation.commodityRequired') }),
      chamber_id: z.number().nullable().optional(),
      floor_id: z.number().nullable().optional(),
      block_id: z.number().nullable().optional(),
      initial_qty: z.number().min(1, t('validation.qtyMin1')),
      unit: z.string().optional(),
      unit_weight: z.number().nullable().optional(),
      rent_rate_per_unit: z.number().nullable().optional()
    })
  )

  const grnFormSchema = computed(() =>
    z.object({
      party_id: z
        .number()
        .nullable()
        .refine((v): v is number => v != null && v > 0, { message: t('validation.partyRequired') }),
      receipt_date: z
        .date()
        .nullable()
        .refine((v): v is Date => v != null, { message: t('validation.receiptDateRequired') }),
      vehicle_number: z.string().optional(),
      driver_name: z.string().optional(),
      remarks: z.string().optional(),
      loading_charge_mode: z.enum(['FLAT', 'PER_UNIT']),
      loading_charge: z.string().optional(),
      loading_unloading_rate_per_bag: z.string().optional()
    })
  )

  const { handleSubmit, errors, defineField, resetForm } = useForm({
    validationSchema: computed(() => toTypedSchema(grnFormSchema.value)),
    initialValues: {
      party_id: null as number | null,
      receipt_date: new Date(),
      vehicle_number: '',
      driver_name: '',
      remarks: '',
      loading_charge_mode: 'FLAT' as LoadingChargeModeEnum,
      loading_charge: '',
      loading_unloading_rate_per_bag: ''
    }
  })

  const [party_id, partyIdProps] = defineField('party_id')
  const [receipt_date, receiptDateProps] = defineField('receipt_date')
  const [vehicle_number, vehicleNoProps] = defineField('vehicle_number')
  const [driver_name, driverNameProps] = defineField('driver_name')
  const [remarks, remarksProps] = defineField('remarks')
  const [loading_charge_mode] = defineField('loading_charge_mode')
  const [loading_charge, loadingChargeProps] = defineField('loading_charge')
  const [loading_unloading_rate_per_bag, loadingRateProps] = defineField('loading_unloading_rate_per_bag')

  const items = ref<FormLineItem[]>([createDefaultLineItem()])

  const addItemRow = () => {
    items.value.push({
      commodity_id: null,
      chamber_id: null,
      floor_id: null,
      block_id: null,
      initial_qty: 1,
      unit: 'Bags',
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

  const totalQty = computed(() => {
    return items.value.reduce((sum, item) => sum + (item.initial_qty || 0), 0)
  })

  const computedReceivingChargeEstimate = computed(() => {
    if (loading_charge_mode.value === 'FLAT') {
      return Number(loading_charge.value || 0)
    } else {
      const rate = Number(loading_unloading_rate_per_bag.value || 0)
      return totalQty.value * rate
    }
  })

  const handleResetForm = () => {
    resetForm()
    items.value = [createDefaultLineItem()]
  }

  const submitForm = async (targetStatus: 'DRAFT' | 'POSTED') => {
    if (!facilityId.value) {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: t('errors.facilityIdUnavailable'),
        life: 4000
      })
      return
    }

    const submitFn = handleSubmit(async (formValues) => {
      const parsed = z
        .array(lineItemSchema.value)
        .min(1, t('errors.atLeastOneLineItem'))
        .safeParse(items.value)

      if (!parsed.success) {
        const firstIssue = parsed.error.issues[0]
        const msg = firstIssue ? firstIssue.message : t('errors.invalidLineItems')
        toast.add({
          severity: 'error',
          summary: t('common.error'),
          detail: msg,
          life: 4000
        })
        return
      }

      const yyyy = formValues.receipt_date.getFullYear()
      const mm = String(formValues.receipt_date.getMonth() + 1).padStart(2, '0')
      const dd = String(formValues.receipt_date.getDate()).padStart(2, '0')
      const formattedDate = `${yyyy}-${mm}-${dd}`

      const formattedItems: LotItemInput[] = parsed.data.map((item) => ({
        commodity_id: item.commodity_id!,
        chamber_id: item.chamber_id || undefined,
        floor_id: item.floor_id || undefined,
        block_id: item.block_id || undefined,
        initial_qty: item.initial_qty,
        unit: item.unit || undefined,
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
        loading_charge_mode: formValues.loading_charge_mode,
        loading_charge: formValues.loading_charge_mode === 'FLAT' ? formValues.loading_charge || '0' : undefined,
        loading_unloading_rate_per_bag: formValues.loading_charge_mode === 'PER_UNIT' ? formValues.loading_unloading_rate_per_bag || '0' : undefined,
        status: targetStatus,
        items: formattedItems
      }

      try {
        const result = await createGrnMutation.mutateAsync(payload)
        const isDraft = targetStatus === 'DRAFT'
        toast.add({
          severity: isDraft ? 'info' : 'success',
          summary: isDraft ? t('grn.draftSavedToastSummary') : t('grn.createdToastSummary'),
          detail: isDraft
            ? t('grn.draftSavedToastDetail', { number: result.grn_number })
            : t('grn.createdToastDetail', { number: result.grn_number }),
          life: 4000
        })
        if (onSuccessCallback) {
          onSuccessCallback(result.grn_number, targetStatus)
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : t('grn.createFailed')
        toast.add({
          severity: 'error',
          summary: t('common.error'),
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
    loading_charge_mode,
    loading_charge,
    loadingChargeProps,
    loading_unloading_rate_per_bag,
    loadingRateProps,
    items,
    errors,
    addItemRow,
    removeItemRow,
    totalNetWeight,
    totalQty,
    computedReceivingChargeEstimate,
    submitForm,
    isSubmitting: createGrnMutation.isPending,
    resetForm: handleResetForm
  }
}
