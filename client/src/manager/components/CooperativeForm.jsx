import { SubmitButton } from '../../shared/hooks/useFormAction'

const KENYA_COUNTIES = [
  'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo Marakwet',
  'Embu', 'Garissa', 'Homa Bay', 'Isiolo', 'Kajiado',
  'Kakamega', 'Kericho', 'Kiambu', 'Kilifi', 'Kirinyaga',
  'Kisii', 'Kisumu', 'Kitui', 'Kwale', 'Laikipia',
  'Lamu', 'Machakos', 'Makueni', 'Mandera', 'Marsabit',
  'Meru', 'Migori', 'Mombasa', "Murang'a", 'Nairobi',
  'Nakuru', 'Nandi', 'Narok', 'Nyamira', 'Nyandarua',
  'Nyeri', 'Samburu', 'Siaya', 'Taita Taveta', 'Tana River',
  'Tharaka Nithi', 'Trans Nzoia', 'Turkana', 'Uasin Gishu',
  'Vihiga', 'Wajir', 'West Pokot',
]

const produceTypeOptions = [
  { value: 'DAIRY', label: 'Dairy' },
  { value: 'COFFEE', label: 'Coffee' },
  { value: 'HONEY', label: 'Honey' },
]

const paymentModelOptions = [
  { value: 'FIXED_PRICE', label: 'Fixed Price' },
  { value: 'REVENUE_SHARE', label: 'Revenue Share' },
]

const defaultCoopForm = {
  name: '',
  registration_number: '',
  county: 'Nairobi',
  sub_county: '',
  ward: '',
  produce_type: 'DAIRY',
  payment_model: 'FIXED_PRICE',
  levy_percentage: '',
  monthly_fee: '',
  prefix: '',
  email: '',
  phone_number: '',
  physical_address: '',
}

export { KENYA_COUNTIES, produceTypeOptions, paymentModelOptions, defaultCoopForm }

export default function CooperativeForm({ formAction, submitLabel, readOnly }) {
  return (
    <form action={formAction} className="space-y-3">
      <div>
        <label htmlFor="coop-name" className="block text-label-md font-bold text-on-surface-variant mb-1">Name *</label>
        <input id="coop-name" name="name" required defaultValue={defaultCoopForm.name} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="coop-prefix" className="block text-label-md font-bold text-on-surface-variant mb-1">Prefix</label>
          <input id="coop-prefix" name="prefix" defaultValue={defaultCoopForm.prefix} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" placeholder="e.g. KCC" />
        </div>
        <div>
          <label htmlFor="coop-reg-number" className="block text-label-md font-bold text-on-surface-variant mb-1">Reg Number *</label>
          <input id="coop-reg-number" name="registration_number" required defaultValue={defaultCoopForm.registration_number} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="coop-county" className="block text-label-md font-bold text-on-surface-variant mb-1">County *</label>
          <select id="coop-county" name="county" required defaultValue={defaultCoopForm.county} disabled={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">
            {KENYA_COUNTIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="coop-sub-county" className="block text-label-md font-bold text-on-surface-variant mb-1">Sub-County</label>
          <input id="coop-sub-county" name="sub_county" defaultValue={defaultCoopForm.sub_county} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="coop-ward" className="block text-label-md font-bold text-on-surface-variant mb-1">Ward</label>
          <input id="coop-ward" name="ward" defaultValue={defaultCoopForm.ward} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
        <div>
          <label htmlFor="coop-produce-type" className="block text-label-md font-bold text-on-surface-variant mb-1">Produce Type *</label>
          <select id="coop-produce-type" name="produce_type" required defaultValue={defaultCoopForm.produce_type} disabled={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">
            {produceTypeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="coop-payment-model" className="block text-label-md font-bold text-on-surface-variant mb-1">Payment Model *</label>
          <select id="coop-payment-model" name="payment_model" required defaultValue={defaultCoopForm.payment_model} disabled={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">
            {paymentModelOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="coop-levy" className="block text-label-md font-bold text-on-surface-variant mb-1">Levy % *</label>
          <input id="coop-levy" name="levy_percentage" required type="number" step="0.01" min="0" max="100" defaultValue={defaultCoopForm.levy_percentage} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="coop-monthly-fee" className="block text-label-md font-bold text-on-surface-variant mb-1">Monthly Fee *</label>
          <input id="coop-monthly-fee" name="monthly_fee" required type="number" step="0.01" min="0" defaultValue={defaultCoopForm.monthly_fee} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
        <div>
          <label htmlFor="coop-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
          <input id="coop-email" name="email" type="email" defaultValue={defaultCoopForm.email} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
      </div>
      <div>
        <label htmlFor="coop-phone" className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
        <input id="coop-phone" name="phone_number" type="tel" defaultValue={defaultCoopForm.phone_number} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
      </div>
      <div>
        <label htmlFor="coop-address" className="block text-label-md font-bold text-on-surface-variant mb-1">Physical Address</label>
        <textarea id="coop-address" name="physical_address" rows={2} defaultValue={defaultCoopForm.physical_address} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
      </div>
      {!readOnly && (
        <div className="flex justify-end gap-3 pt-2">
          <SubmitButton className="px-6 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50">
            {submitLabel || 'Save'}
          </SubmitButton>
        </div>
      )}
    </form>
  )
}
