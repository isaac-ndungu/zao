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

export default function CooperativeForm({ form, onChange, onSubmit, loading, submitLabel, readOnly }) {
  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div>
        <label className="block text-label-md font-bold text-on-surface-variant mb-1">Name *</label>
        <input required value={form.name} onChange={(e) => onChange({ ...form, name: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Prefix</label>
          <input value={form.prefix} onChange={(e) => onChange({ ...form, prefix: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" placeholder="e.g. KCC" />
        </div>
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Reg Number *</label>
          <input required value={form.registration_number} onChange={(e) => onChange({ ...form, registration_number: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">County *</label>
          <select required value={form.county} onChange={(e) => onChange({ ...form, county: e.target.value })} disabled={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">
            {KENYA_COUNTIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Sub-County</label>
          <input value={form.sub_county} onChange={(e) => onChange({ ...form, sub_county: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Ward</label>
          <input value={form.ward} onChange={(e) => onChange({ ...form, ward: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Produce Type *</label>
          <select required value={form.produce_type} onChange={(e) => onChange({ ...form, produce_type: e.target.value })} disabled={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">
            {produceTypeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Payment Model *</label>
          <select required value={form.payment_model} onChange={(e) => onChange({ ...form, payment_model: e.target.value })} disabled={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface">
            {paymentModelOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Levy % *</label>
          <input required type="number" step="0.01" min="0" max="100" value={form.levy_percentage} onChange={(e) => onChange({ ...form, levy_percentage: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Monthly Fee *</label>
          <input required type="number" step="0.01" min="0" value={form.monthly_fee} onChange={(e) => onChange({ ...form, monthly_fee: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
        <div>
          <label className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
          <input type="email" value={form.email} onChange={(e) => onChange({ ...form, email: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
        </div>
      </div>
      <div>
        <label className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
        <input type="tel" value={form.phone_number} onChange={(e) => onChange({ ...form, phone_number: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
      </div>
      <div>
        <label className="block text-label-md font-bold text-on-surface-variant mb-1">Physical Address</label>
        <textarea rows={2} value={form.physical_address} onChange={(e) => onChange({ ...form, physical_address: e.target.value })} readOnly={readOnly} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
      </div>
      {!readOnly && (
        <div className="flex justify-end gap-3 pt-2">
          <button type="submit" disabled={loading} className="px-6 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50">
            {loading ? 'Saving...' : submitLabel || 'Save'}
          </button>
        </div>
      )}
    </form>
  )
}
