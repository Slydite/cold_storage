import { type Ref, type ComputedRef } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useToast } from 'primevue/usetoast'
import { useCreateRentRun } from './useRentRuns'
import type { RentRunCreateInput, RentRunOutput } from '../api/billing'

const rentRunFormSchema = z
  .object({
    period_start: z
      .date()
      .nullable()
      .refine((v): v is Date => v != null, { message: 'Period start date is required' }),
    period_end: z
      .date()
      .nullable()
      .refine((v): v is Date => v != null, { message: 'Period end date is required' })
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

  const now = new Date()
  const defaultStart = new Date(now.getFullYear(), now.getMonth(), 1)
  const defaultEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0)

  const { handleSubmit, errors, defineField, resetForm } = useForm({
    validationSchema: toTypedSchema(rentRunFormSchema),
    initialValues: {
      period_start: defaultStart,
      period_end: defaultEnd
    }
  })

  const [period_start, periodStartProps] = defineField('period_start')
  const [period_end, periodEndProps] = defineField('period_end')

  const handleResetForm = () => {
    resetForm()
  }

  const submitForm = async () => {
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
      const payload: RentRunCreateInput = {
        facility_id: facilityId.value!,
        period_start: formatDateToYMD(formValues.period_start),
        period_end: formatDateToYMD(formValues.period_end)
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
        // Surface the backend's detail message verbatim
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
    errors,
    submitForm,
    isSubmitting: createRentRunMutation.isPending,
    resetForm: handleResetForm
  }
}
