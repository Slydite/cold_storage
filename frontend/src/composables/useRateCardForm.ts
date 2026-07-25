import { type Ref, type ComputedRef } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useToast } from 'primevue/usetoast'
import { useCreateRateCard } from './useRateCards'
import type { RateCardInput, WeightCategoryEnum } from '../api/billing'

const rateCardFormSchema = z.object({
  commodity_id: z
    .number()
    .nullable()
    .refine((v): v is number => v != null && v > 0, { message: 'Commodity is required' }),
  weight_category: z
    .enum(['KG_20', 'KG_50', 'OTHER'] as const, {
      message: 'Weight category is required'
    }),
  rate_per_bag_per_month: z
    .number()
    .nullable()
    .refine((v): v is number => v != null && v > 0, { message: 'Rate must be greater than 0' }),
  effective_from: z
    .date()
    .nullable()
    .refine((v): v is Date => v != null, { message: 'Effective date is required' }),
  is_active: z.boolean()
})

function formatDateToYMD(d: Date): string {
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

export function useRateCardForm(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  onSuccessCallback?: () => void
) {
  const toast = useToast()
  const createRateCardMutation = useCreateRateCard()

  const { handleSubmit, errors, defineField, resetForm } = useForm({
    validationSchema: toTypedSchema(rateCardFormSchema),
    initialValues: {
      commodity_id: null as number | null,
      weight_category: 'KG_50' as WeightCategoryEnum,
      rate_per_bag_per_month: null as number | null,
      effective_from: new Date(),
      is_active: true
    }
  })

  const [commodity_id, commodityIdProps] = defineField('commodity_id')
  const [weight_category, weightCategoryProps] = defineField('weight_category')
  const [rate_per_bag_per_month, ratePerBagProps] = defineField('rate_per_bag_per_month')
  const [effective_from, effectiveFromProps] = defineField('effective_from')
  const [is_active, isActiveProps] = defineField('is_active')

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
      const formattedDate = formatDateToYMD(formValues.effective_from)

      const payload: RateCardInput = {
        facility_id: facilityId.value!,
        commodity_id: formValues.commodity_id,
        weight_category: formValues.weight_category,
        rate_per_bag_per_month: String(formValues.rate_per_bag_per_month),
        effective_from: formattedDate,
        is_active: formValues.is_active
      }

      try {
        await createRateCardMutation.mutateAsync(payload)
        toast.add({
          severity: 'success',
          summary: 'Rate Card Created',
          detail: 'Rate card has been created successfully.',
          life: 4000
        })
        handleResetForm()
        if (onSuccessCallback) {
          onSuccessCallback()
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to create rate card'
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
    commodity_id,
    commodityIdProps,
    weight_category,
    weightCategoryProps,
    rate_per_bag_per_month,
    ratePerBagProps,
    effective_from,
    effectiveFromProps,
    is_active,
    isActiveProps,
    errors,
    submitForm,
    isSubmitting: createRateCardMutation.isPending,
    resetForm: handleResetForm
  }
}
