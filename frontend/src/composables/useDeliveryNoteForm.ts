import { ref, computed, watch, type Ref, type ComputedRef } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useI18n } from 'vue-i18n'
import { useCreateDeliveryNote, useUpdateDeliveryNote, useUpdateAndPostDeliveryNote } from './useDeliveryNotes'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import type { DeliveryNoteCreateInput, DeliveryNoteUpdateInput, DeliveryLineInput, LoadingChargeModeEnum, DeliveryNoteOutput } from '../api/delivery'
import type { LotOutput } from '../api/lot'

export interface FormDeliveryLine {
  lot_id: number | null
  qty: number
}

const createDefaultLine = (): FormDeliveryLine => ({
  lot_id: null,
  qty: 1
})

export function useDeliveryNoteForm(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  availableLots: Ref<LotOutput[]> | ComputedRef<LotOutput[]>,
  deliveryNote?: Ref<DeliveryNoteOutput | undefined> | ComputedRef<DeliveryNoteOutput | undefined>,
  onSuccessCallback?: (dnNumber: string, status: string) => void
) {
  const toast = useToast()
  const confirm = useConfirm()
  const { t } = useI18n()
  const createMutation = useCreateDeliveryNote()
  const updateMutation = useUpdateDeliveryNote()
  const updateAndPostMutation = useUpdateAndPostDeliveryNote()

  const lineItemSchema = computed(() =>
    z.object({
      lot_id: z
        .number()
        .nullable()
        .refine((v): v is number => v != null && v > 0, { message: t('validation.lotRequired') }),
      qty: z.number().min(1, t('validation.qtyMin1'))
    })
  )

  const deliveryNoteFormSchema = computed(() =>
    z.object({
      party_id: z
        .number()
        .nullable()
        .refine((v): v is number => v != null && v > 0, { message: t('validation.partyRequired') }),
      dispatch_date: z
        .date()
        .nullable()
        .refine((v): v is Date => v != null, { message: t('validation.dispatchDateRequired') }),
      vehicle_number: z.string().optional(),
      driver_name: z.string().optional(),
      remarks: z.string().optional(),
      loading_charge_mode: z.enum(['FLAT', 'PER_UNIT']),
      loading_charge: z.string().optional(),
      loading_unloading_rate_per_unit: z.string().optional()
    })
  )

  const { handleSubmit, errors, defineField, resetForm } = useForm({
    validationSchema: computed(() => toTypedSchema(deliveryNoteFormSchema.value)),
    initialValues: {
      party_id: null as number | null,
      dispatch_date: new Date(),
      vehicle_number: '',
      driver_name: '',
      remarks: '',
      loading_charge_mode: 'FLAT' as LoadingChargeModeEnum,
      loading_charge: '',
      loading_unloading_rate_per_unit: ''
    }
  })

  const [party_id, partyIdProps] = defineField('party_id')
  const [dispatch_date, dispatchDateProps] = defineField('dispatch_date')
  const [vehicle_number, vehicleNoProps] = defineField('vehicle_number')
  const [driver_name, driverNameProps] = defineField('driver_name')
  const [remarks, remarksProps] = defineField('remarks')
  const [loading_charge_mode] = defineField('loading_charge_mode')
  const [loading_charge, loadingChargeProps] = defineField('loading_charge')
  const [loading_unloading_rate_per_unit, loadingRateProps] = defineField('loading_unloading_rate_per_unit')

  const lines = ref<FormDeliveryLine[]>([createDefaultLine()])

  if (deliveryNote) {
    watch(
      () => deliveryNote.value,
      (newNote) => {
        if (newNote) {
          resetForm({
            values: {
              party_id: newNote.party_id,
              dispatch_date: newNote.dispatch_date ? new Date(newNote.dispatch_date) : new Date(),
              vehicle_number: newNote.vehicle_number || '',
              driver_name: newNote.driver_name || '',
              remarks: newNote.remarks || '',
              loading_charge_mode: newNote.loading_charge_mode || 'FLAT',
              loading_charge: newNote.loading_charge || '',
              loading_unloading_rate_per_unit: newNote.loading_unloading_rate_per_unit || ''
            }
          })
          if (newNote.lines) {
            lines.value = newNote.lines.map((line) => ({
              lot_id: line.lot_id,
              qty: line.qty
            }))
          }
        }
      },
      { immediate: true }
    )
  }

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

  const computedDeliveryChargeEstimate = computed(() => {
    if (loading_charge_mode.value === 'FLAT') {
      return Number(loading_charge.value || 0)
    } else {
      const rate = Number(loading_unloading_rate_per_unit.value || 0)
      return totalQty.value * rate
    }
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
      return t('delivery.qtyExceedsAvailable', { avail })
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
        summary: t('common.error'),
        detail: t('errors.facilityIdUnavailable'),
        life: 4000
      })
      return
    }

    if (hasQtyExceeded.value) {
      toast.add({
        severity: 'error',
        summary: t('common.actionFailed'),
        detail: t('errors.invalidLineItems'),
        life: 4000
      })
      return
    }

    const isEdit = deliveryNote?.value !== undefined

    const submitFn = handleSubmit(async (formValues) => {
      const parsed = z
        .array(lineItemSchema.value)
        .min(1, t('errors.atLeastOneLineItem'))
        .safeParse(lines.value)

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

      if (isEdit && deliveryNote.value) {
        const originalLines = deliveryNote.value.lines || []
        const currentLotIds = lines.value.map((l) => l.lot_id).filter((id) => id != null)
        const removedLinesCount = originalLines.filter((line) => !currentLotIds.includes(line.lot_id)).length

        if (removedLinesCount > 0) {
          const confirmed = await new Promise<boolean>((resolve) => {
            confirm.require({
              message: t('delivery.confirmDeleteLinesMessage', { count: removedLinesCount }),
              header: t('delivery.confirmDeleteLinesTitle'),
              icon: 'pi pi-exclamation-triangle',
              rejectProps: {
                label: t('common.cancel'),
                severity: 'secondary',
                outlined: true
              },
              acceptProps: {
                label: t('common.confirm'),
                severity: 'danger'
              },
              accept: () => resolve(true),
              reject: () => resolve(false)
            })
          })
          if (!confirmed) return
        }
      }

      for (let i = 0; i < parsed.data.length; i++) {
        const line = parsed.data[i]
        if (!line || line.lot_id == null) continue
        const avail = getLotAvailable(line.lot_id)
        if (avail !== null && line.qty > avail) {
          toast.add({
            severity: 'error',
            summary: t('common.error'),
            detail: t('delivery.lineQtyExceedsAvailable', { qty: line.qty, avail }),
            life: 4000
          })
          return
        }
      }

      const yyyy = formValues.dispatch_date.getFullYear()
      const mm = String(formValues.dispatch_date.getMonth() + 1).padStart(2, '0')
      const dd = String(formValues.dispatch_date.getDate()).padStart(2, '0')
      const formattedDate = `${yyyy}-${mm}-${dd}`

      const formattedLines: DeliveryLineInput[] = parsed.data.map((line) => ({
        lot_id: line.lot_id!,
        qty: line.qty
      }))

      try {
        let result: DeliveryNoteOutput
        if (isEdit && deliveryNote.value) {
          const payload: DeliveryNoteUpdateInput = {
            party_id: formValues.party_id,
            dispatch_date: formattedDate,
            vehicle_number: formValues.vehicle_number || undefined,
            driver_name: formValues.driver_name || undefined,
            remarks: formValues.remarks || undefined,
            loading_charge_mode: formValues.loading_charge_mode,
            loading_charge: formValues.loading_charge_mode === 'FLAT' ? formValues.loading_charge || '0' : undefined,
            loading_unloading_rate_per_unit: formValues.loading_charge_mode === 'PER_UNIT' ? formValues.loading_unloading_rate_per_unit || '0' : undefined,
            lines: formattedLines
          }

          if (targetStatus === 'DRAFT') {
            result = await updateMutation.mutateAsync({ id: deliveryNote.value.id, body: payload })
          } else {
            result = await updateAndPostMutation.mutateAsync({ id: deliveryNote.value.id, body: payload })
          }
        } else {
          const payload: DeliveryNoteCreateInput = {
            facility_id: facilityId.value!,
            party_id: formValues.party_id,
            dispatch_date: formattedDate,
            vehicle_number: formValues.vehicle_number || undefined,
            driver_name: formValues.driver_name || undefined,
            remarks: formValues.remarks || undefined,
            loading_charge_mode: formValues.loading_charge_mode,
            loading_charge: formValues.loading_charge_mode === 'FLAT' ? formValues.loading_charge || '0' : undefined,
            loading_unloading_rate_per_unit: formValues.loading_charge_mode === 'PER_UNIT' ? formValues.loading_unloading_rate_per_unit || '0' : undefined,
            status: targetStatus,
            lines: formattedLines
          }

          result = await createMutation.mutateAsync(payload)
        }

        const isDraft = targetStatus === 'DRAFT'
        toast.add({
          severity: isDraft ? 'info' : 'success',
          summary: isDraft
            ? t('delivery.draftSavedToastSummary')
            : (isEdit ? t('delivery.updatedToastSummary') : t('delivery.createdToastSummary')),
          detail: isDraft
            ? t('delivery.draftSavedToastDetail', { number: result.dn_number })
            : (isEdit ? t('delivery.updatedToastDetail', { number: result.dn_number }) : t('delivery.createdToastDetail', { number: result.dn_number })),
          life: 4000
        })

        if (onSuccessCallback) {
          onSuccessCallback(result.dn_number, targetStatus)
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : t(isEdit ? 'delivery.updateFailed' : 'delivery.createFailed')
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
    dispatch_date,
    dispatchDateProps,
    vehicle_number,
    vehicleNoProps,
    driver_name,
    driverNameProps,
    remarks,
    remarksProps,
    loading_charge_mode,
    loading_charge,
    loadingChargeProps,
    loading_unloading_rate_per_unit,
    loadingRateProps,
    lines,
    errors,
    addLineRow,
    removeLineRow,
    totalQty,
    computedDeliveryChargeEstimate,
    getLotAvailable,
    getLineQtyError,
    hasQtyExceeded,
    submitForm,
    isSubmitting: computed(() => createMutation.isPending.value || updateMutation.isPending.value || updateAndPostMutation.isPending.value),
    resetForm: handleResetForm
  }
}
