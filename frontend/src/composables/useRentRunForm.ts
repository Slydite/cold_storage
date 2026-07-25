import { ref, type Ref, type ComputedRef } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useToast } from 'primevue/usetoast'
import { useCreateRentRun, usePreviewRentRun } from './useRentRuns'
import type { RentRunCreateInput, RentRunOutput, RentRunPreviewInput, RentRunPreviewOutput } from '../api/billing'

const rentRunFormSchema = z
  .object({
    period_start: z
      .date()
      .nullable()
      .refine((v): v is Date => v != null, { message: 'Period start date is required' }),
    period_end: z
      .date()
      .nullable()
      .refine((v): v is Date => v != null, { message: 'Period end date is required' }),
    party_id: z.number().nullable().optional(),
    commodity_id: z.number().nullable().optional(),
    chamber: z.string().optional(),
    min_billing_days: z.number().min(0, { message: 'Minimum days cannot be negative' }),
    notes: z.string().optional()
  })
  .refine(
    (data) => {
      if (data.period_start && data.period_end) {
        return data.period_end >= data.period_start
      }
      return true
    },
    {
      message: 'Period end date must be on or after period start date',
      path: ['period_end']
    }
  )

function formatDateToYMD(d: Date): string {
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

export function useRentRunForm(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  onSuccessCallback?: (createdRun: RentRunOutput) => void
) {
  const toast = useToast()
  const createRentRunMutation = useCreateRentRun()
  const previewRentRunMutation = usePreviewRentRun()

  const step = ref<1 | 2>(1)
  const previewData = ref<RentRunPreviewOutput | null>(null)
  const previewError = ref<string | null>(null)

  const now = new Date()
  const defaultStart = new Date(now.getFullYear(), now.getMonth(), 1)
  const defaultEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0)

  const { handleSubmit, errors, defineField, resetForm } = useForm({
    validationSchema: toTypedSchema(rentRunFormSchema),
    initialValues: {
      period_start: defaultStart,
      period_end: defaultEnd,
      party_id: null as number | null,
      commodity_id: null as number | null,
      chamber: '',
      min_billing_days: 0,
      notes: ''
    }
  })

  const [period_start, periodStartProps] = defineField('period_start')
  const [period_end, periodEndProps] = defineField('period_end')
  const [party_id, partyIdProps] = defineField('party_id')
  const [commodity_id, commodityIdProps] = defineField('commodity_id')
  const [chamber, chamberProps] = defineField('chamber')
  const [min_billing_days, minBillingDaysProps] = defineField('min_billing_days')
  const [notes, notesProps] = defineField('notes')

  const handleResetForm = () => {
    resetForm()
    step.value = 1
    previewData.value = null
    previewError.value = null
  }

  const handlePreview = handleSubmit(async (formValues) => {
    if (!facilityId.value) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Facility ID is not available.',
        life: 4000
      })
      return
    }

    const payload: RentRunPreviewInput = {
      facility_id: facilityId.value,
      period_start: formatDateToYMD(formValues.period_start),
      period_end: formatDateToYMD(formValues.period_end),
      party_id: formValues.party_id ?? undefined,
      commodity_id: formValues.commodity_id ?? undefined,
      chamber: formValues.chamber && formValues.chamber.trim() ? formValues.chamber.trim() : undefined,
      min_billing_days: formValues.min_billing_days ?? 0
    }

    previewError.value = null
    try {
      const res = await previewRentRunMutation.mutateAsync(payload)
      previewData.value = res
      step.value = 2
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to preview rent run'
      previewError.value = msg
      toast.add({
        severity: 'error',
        summary: 'Preview Failed',
        detail: msg,
        life: 5000
      })
    }
  })

  const backToParameters = () => {
    step.value = 1
  }

  const submitForm = async () => {
    if (!facilityId.value) return
    if (!previewData.value) return
    if (previewData.value.missing_rate_cards && previewData.value.missing_rate_cards.length > 0) {
      toast.add({
        severity: 'error',
        summary: 'Cannot Create Rent Run',
        detail: 'There are missing rate cards that must be added first.',
        life: 5000
      })
      return
    }

    const submitFn = handleSubmit(async (formValues) => {
      const payload: RentRunCreateInput = {
        facility_id: facilityId.value!,
        period_start: formatDateToYMD(formValues.period_start),
        period_end: formatDateToYMD(formValues.period_end),
        party_id: formValues.party_id ?? undefined,
        commodity_id: formValues.commodity_id ?? undefined,
        chamber: formValues.chamber && formValues.chamber.trim() ? formValues.chamber.trim() : undefined,
        min_billing_days: formValues.min_billing_days ?? 0,
        notes: formValues.notes && formValues.notes.trim() ? formValues.notes.trim() : undefined
      }

      try {
        const result = await createRentRunMutation.mutateAsync(payload)
        const lineCount = result.lines ? result.lines.length : 0
        if (lineCount === 0) {
          toast.add({
            severity: 'info',
            summary: 'Rent Run Created',
            detail: `Rent Run #${result.id} created, but no lots were found to bill for this period.`,
            life: 5000
          })
        } else {
          toast.add({
            severity: 'success',
            summary: 'Rent Run Executed',
            detail: `Rent Run #${result.id} created with ${lineCount} lot line item(s).`,
            life: 4000
          })
        }
        handleResetForm()
        if (onSuccessCallback) {
          onSuccessCallback(result)
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to execute rent run'
        toast.add({
          severity: 'error',
          summary: 'Rent Run Failed',
          detail: msg,
          life: 7000
        })
      }
    })

    await submitFn()
  }

  return {
    period_start,
    periodStartProps,
    period_end,
    periodEndProps,
    party_id,
    partyIdProps,
    commodity_id,
    commodityIdProps,
    chamber,
    chamberProps,
    min_billing_days,
    minBillingDaysProps,
    notes,
    notesProps,
    step,
    previewData,
    previewError,
    isPreviewing: previewRentRunMutation.isPending,
    isSubmitting: createRentRunMutation.isPending,
    handlePreview,
    backToParameters,
    errors,
    submitForm,
    resetForm: handleResetForm
  }
}
