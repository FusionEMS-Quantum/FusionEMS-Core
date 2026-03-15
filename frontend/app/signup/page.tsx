'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  getPublicPricingCatalog,
  lookupPublicOnboardingNpi,
  submitPublicOnboardingApplication,
} from '@/services/api';

interface SchedulingTier {
  code: string;
  label: string;
  monthly_cents: number;
  price_display: string;
}

interface BillingTier {
  code: string;
  label: string;
  mode: string;
  base_monthly_cents: number;
  per_claim_cents: number;
  base_display: string;
  per_claim_display: string;
  compare_display?: string;
}

interface PlanDef {
  code: string;
  label: string;
  desc: string;
  contact_sales: boolean;
  color: string;
  price_display: string;
}

interface AddonDef {
  code: string;
  label: string;
  desc: string;
  monthly_cents: number;
  gov_only: boolean;
  uses_billing_tier: boolean;
  price_display: string;
}

interface BillingModeDef {
  code: string;
  label: string;
  summary: string;
}

interface Catalog {
  plans: PlanDef[];
  scheduling_tiers: SchedulingTier[];
  billing_tiers: BillingTier[];
  addons: AddonDef[];
  billing_modes: BillingModeDef[];
}

const COLLECTIONS_MODES = [
  { code: 'none', label: 'No soft collections' },
  { code: 'soft_only', label: 'Soft collections (statements + payment portal)' },
  { code: 'soft_and_handoff', label: 'Soft + vendor handoff export' },
];

const US_STATES = ['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming'];
const AGENCY_TYPES = ['EMS', 'Fire EMS', 'Fire Dept', 'Air Medical', 'Transport'];
const OPERATIONAL_MODES = [
  { code: 'EMS_TRANSPORT', label: 'EMS Transport' },
  { code: 'MEDICAL_TRANSPORT', label: 'Medical Transport' },
  { code: 'HEMS_TRANSPORT', label: 'HEMS Transport' },
  { code: 'EXTERNAL_911_CAD', label: 'External 911 CAD' },
];
const BILLING_MODES = [
  { code: 'FUSION_RCM', label: 'FusionEMS AI Billing Center' },
  { code: 'THIRD_PARTY_EXPORT', label: 'Internal / Third-Party Billing' },
];

const inputCls = "bg-[var(--color-bg-base)] border border-[var(--color-border-default)] px-4 py-3 text-[12px] font-mono text-[var(--color-text-primary)] placeholder-zinc-700 focus:outline-none focus:border-[var(--q-orange)] focus:ring-1 focus:ring-[var(--q-orange)]/20 transition-all tracking-widest w-full uppercase";
const selectCls = "bg-[var(--color-bg-base)] border border-[var(--color-border-default)] px-4 py-3 text-[12px] font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--q-orange)] transition-all tracking-widest appearance-none w-full uppercase";
const labelCls = "block text-[10px] font-bold mb-2 tracking-[0.2em] text-[var(--color-text-muted)] uppercase";

type Step = 1 | 2 | 3 | 4 | 5;

export default function SignupPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefillApplied = useRef(false);
  const [step, setStep] = useState<Step>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogError, setCatalogError] = useState('');
  const [catalogLoading, setCatalogLoading] = useState(true);

  const [plan, setPlan] = useState('');
  const [tier, setTier] = useState('');
  const [billingTier, setBillingTier] = useState('');
  const [addons, setAddons] = useState<string[]>([]);
  const [isGovEntity, setIsGovEntity] = useState(false);
  const [collectionsMode, setCollectionsMode] = useState('none');
  const [statementChannels, setStatementChannels] = useState<string[]>(['mail']);
  const [collectorVendor, setCollectorVendor] = useState('');
  const [placementMethod, setPlacementMethod] = useState('portal_upload');
  const [statementVendor, setStatementVendor] = useState('LOB');
  const [clearinghouseVendor, setClearinghouseVendor] = useState('OFFICE_ALLY');
  const [activationTarget, setActivationTarget] = useState('IMMEDIATE_IMPORT');
  const [offboardingMode, setOffboardingMode] = useState('SELF_SERVICE_EXPORT');

  const [agencyName, setAgencyName] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [agencyType, setAgencyType] = useState('');
  const [state, setState] = useState('Wisconsin');
  const [npiNumber, setNpiNumber] = useState('');
  const [operationalMode, setOperationalMode] = useState('EMS_TRANSPORT');
  const [billingMode, setBillingMode] = useState('FUSION_RCM');
  const [primaryTailNumber, setPrimaryTailNumber] = useState('');
  const [baseIcao, setBaseIcao] = useState('');
  const [billingContactName, setBillingContactName] = useState('');
  const [billingContactEmail, setBillingContactEmail] = useState('');
  const [implementationOwnerName, setImplementationOwnerName] = useState('');
  const [implementationOwnerEmail, setImplementationOwnerEmail] = useState('');
  const [identitySsoPreference, setIdentitySsoPreference] = useState('OIDC');
  const [npiLookupLoading, setNpiLookupLoading] = useState(false);
  const [npiLookupError, setNpiLookupError] = useState('');

  const fetchCatalog = useCallback(async () => {
    setCatalogLoading(true);
    setCatalogError('');
    try {
      const data = await getPublicPricingCatalog<Catalog>();
      setCatalog(data);
    } catch (e: unknown) {
      setCatalogError(e instanceof Error ? e.message : 'Failed to load pricing');
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  useEffect(() => { fetchCatalog(); }, [fetchCatalog]);

  useEffect(() => {
    if (!catalog || prefillApplied.current) {
      return;
    }

    const planParam = searchParams.get('plan');
    const tierParam = searchParams.get('tier');
    const billingTierParam = searchParams.get('billing_tier') ?? searchParams.get('billingTier');
    const billingModeParam = searchParams.get('billing_mode') ?? searchParams.get('billingMode');
    const stepParam = searchParams.get('step');
    const collectionsModeParam = searchParams.get('collections_mode');
    const addonsParam = [
      ...searchParams.getAll('addon'),
      ...(searchParams.get('addons')?.split(',') ?? []),
    ]
      .map(value => value.trim())
      .filter(Boolean);

    if (planParam && catalog.plans.some(item => item.code === planParam)) {
      setPlan(planParam);
    }
    if (tierParam && catalog.scheduling_tiers.some(item => item.code === tierParam)) {
      setTier(tierParam);
    }
    if (billingModeParam && BILLING_MODES.some(item => item.code === billingModeParam)) {
      setBillingMode(billingModeParam);
    }
    if (billingTierParam && catalog.billing_tiers.some(item => item.code === billingTierParam)) {
      setBillingTier(billingTierParam);
    }
    if (collectionsModeParam && COLLECTIONS_MODES.some(item => item.code === collectionsModeParam)) {
      setCollectionsMode(collectionsModeParam);
    }
    if (addonsParam.length > 0) {
      const validAddonCodes = new Set(catalog.addons.map(item => item.code));
      setAddons(Array.from(new Set(addonsParam.filter(code => validAddonCodes.has(code)))));
    }
    if (stepParam) {
      const parsedStep = Number(stepParam);
      if (parsedStep >= 1 && parsedStep <= 5) {
        setStep(parsedStep as Step);
      }
    }

    prefillApplied.current = true;
  }, [catalog, searchParams]);

  const billingModeCatalog = catalog?.billing_modes ?? [];
  const availableBillingTiers = useMemo(
    () => (catalog?.billing_tiers ?? []).filter(item => item.mode === billingMode),
    [catalog?.billing_tiers, billingMode],
  );

  useEffect(() => {
    if (!billingTier) {
      return;
    }
    if (!availableBillingTiers.some(item => item.code === billingTier)) {
      setBillingTier('');
    }
  }, [availableBillingTiers, billingTier]);

  const toggleAddon = (code: string) => {
    setAddons(prev => prev.includes(code) ? prev.filter(a => a !== code) : [...prev, code]);
  };

  const toggleChannel = (ch: string) => {
    setStatementChannels(prev => prev.includes(ch) ? prev.filter(c => c !== ch) : [...prev, ch]);
  };

  const selectedPlan = catalog?.plans.find(p => p.code === plan);
  const canProceed1 = !!plan && (plan !== 'SCHEDULING_ONLY' || !!tier);
  const canProceed2 = !addons.includes('BILLING_AUTOMATION') || !!billingTier;
  const hemsMode = operationalMode === 'HEMS_TRANSPORT';
  const canProceed4 =
    agencyName && firstName && lastName && email && agencyType && state &&
    billingMode && operationalMode &&
    (!hemsMode || (primaryTailNumber && baseIcao));

  async function lookupNPI() {
    if (!npiNumber.trim()) return;
    setNpiLookupLoading(true);
    setNpiLookupError('');
    try {
      const data = await lookupPublicOnboardingNpi<{ legal_organization_name?: string; state?: string }>(npiNumber.trim());
      if (!agencyName && data?.legal_organization_name) setAgencyName(data.legal_organization_name);
      if (!state && data?.state) setState(data.state);
    } catch (e: unknown) {
      setNpiLookupError(e instanceof Error ? e.message : 'NPI lookup failed');
    } finally {
      setNpiLookupLoading(false);
    }
  }

  async function submit() {
    setLoading(true); setError('');
    try {
      const payload = {
        agency_name: agencyName, first_name: firstName, last_name: lastName,
        email, phone, agency_type: agencyType, state,
        npi_number: npiNumber || null,
        operational_mode: operationalMode,
        billing_mode: billingMode,
        primary_tail_number: primaryTailNumber || null,
        base_icao: baseIcao || null,
        billing_contact_name: billingContactName || null,
        billing_contact_email: billingContactEmail || null,
        implementation_owner_name: implementationOwnerName || null,
        implementation_owner_email: implementationOwnerEmail || null,
        identity_sso_preference: identitySsoPreference || null,
        policy_flags: {
          collections_mode: collectionsMode,
          statement_channels: statementChannels,
          statement_vendor: statementVendor,
          clearinghouse_vendor: clearinghouseVendor,
          office_ally_enrollment_requested: clearinghouseVendor === 'OFFICE_ALLY',
          activation_target: activationTarget,
          data_portability_mode: offboardingMode,
          agency_choice_enabled: true,
        },
        plan_code: plan,
        tier_code: tier || null,
        billing_tier_code: billingTier || null,
        addon_codes: addons,
        is_government_entity: isGovEntity,
        collections_mode: collectionsMode,
        statement_channels: statementChannels,
        collector_vendor_name: collectorVendor,
        placement_method: placementMethod,
      };
      const data = await submitPublicOnboardingApplication<{ application_id?: string; id?: string }>(payload);
      localStorage.setItem('qs_app_id', data.application_id || data.id || '');
      localStorage.setItem('qs_agency_name', agencyName);
      localStorage.setItem('qs_signer_name', `${firstName} ${lastName}`.trim());
      localStorage.setItem('qs_signer_email', email);
      router.push('/signup/legal');
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed to submit onboarding application'); }
    finally { setLoading(false); }
  }

  if (catalogLoading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] flex items-center justify-center">
        <div className="text-sm text-[var(--color-text-muted)]">Loading...</div>
      </div>
    );
  }

  if (catalogError || !catalog) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="text-sm text-[var(--color-brand-red)]">{catalogError || 'Unable to load pricing'}</div>
          <button onClick={fetchCatalog} className="px-4 py-2 bg-[var(--q-orange)] text-black text-sm font-bold chamfer-4">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] flex flex-col items-center py-12 px-4">
      <div className="w-full max-w-3xl">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 bg-[var(--q-orange)] flex items-center justify-center text-sm font-black text-black" style={{ clipPath: 'polygon(0 0, calc(100% - 7px) 0, 100% 7px, 100% 100%, 0 100%)' }}>FQ</div>
          <div>
            <div className="text-lg font-bold tracking-wide">QuantumEMS</div>
            <div className="text-xs text-[var(--color-text-muted)]">Agency Signup</div>
          </div>
        </div>

        <div className="flex gap-2 mb-10">
          {(['Plan','Addons','Collections','Agency Info','Review'] as const).map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div className={`w-6 h-6  flex items-center justify-center text-xs font-bold ${step === i+1 ? 'bg-[var(--q-orange)] text-black' : step > i+1 ? 'bg-status-active text-black' : 'bg-[rgba(255,255,255,0.1)] text-[var(--color-text-muted)]'}`}>{i+1}</div>
              <span className={`text-xs hidden sm:block ${step === i+1 ? 'text-[var(--color-text-primary)] font-semibold' : 'text-[var(--color-text-muted)]'}`}>{label}</span>
              {i < 4 && <span className="text-[rgba(255,255,255,0.15)] text-xs">›</span>}
            </div>
          ))}
        </div>

        {step === 1 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Choose your plan</h2>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">Start with your billing lane, then layer in the modules your agency wants to run.</p>
            <div className="mb-6">
              <div className={labelCls}>Billing operating model</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(billingModeCatalog.length ? billingModeCatalog : BILLING_MODES).map(mode => (
                  <button
                    key={mode.code}
                    onClick={() => setBillingMode(mode.code)}
                    className={`text-left p-4 chamfer-4 border transition-all ${billingMode === mode.code ? 'border-[var(--q-orange)] bg-[rgba(255,106,0,0.12)]' : 'border-border-DEFAULT hover:border-[rgba(255,255,255,0.2)]'}`}
                  >
                    <div className="text-[11px] font-bold tracking-[0.18em] uppercase text-[var(--q-orange)] mb-2">{mode.label}</div>
                    <div className="text-sm text-[var(--color-text-muted)] leading-relaxed">{'summary' in mode ? mode.summary : ''}</div>
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              {catalog.plans.map(p => (
                <button key={p.code} onClick={() => { setPlan(p.code); setTier(''); }}
                  className={`text-left p-4 chamfer-4 border transition-all ${plan === p.code ? 'border-[var(--q-orange)] bg-[rgba(255,106,0,0.12)]' : 'border-border-DEFAULT hover:border-[rgba(255,255,255,0.2)]'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2 h-2 " style={{ background: p.color }} />
                    <span className="font-semibold text-sm">{p.label}</span>
                  </div>
                  <div className="text-xs text-[var(--color-text-muted)] mb-2">{p.desc}</div>
                  <div className="text-xs font-bold" style={{ color: p.color }}>{p.price_display}</div>
                </button>
              ))}
            </div>
            {plan === 'SCHEDULING_ONLY' && (
              <div className="mb-6">
                <div className={labelCls}>Select size tier</div>
                <div className="grid grid-cols-3 gap-2">
                  {catalog.scheduling_tiers.map(t => (
                    <button key={t.code} onClick={() => setTier(t.code)}
                      className={`p-3 chamfer-4 border text-left transition-all ${tier === t.code ? 'border-[var(--q-orange)] bg-[rgba(255,106,0,0.12)]' : 'border-border-DEFAULT hover:border-[rgba(255,255,255,0.2)]'}`}>
                      <div className="text-xs font-semibold">{t.label}</div>
                      <div className="text-xs text-[var(--q-orange)] font-bold mt-1">{t.price_display}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="mb-4 flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={isGovEntity} onChange={e => setIsGovEntity(e.target.checked)} className="w-4 h-4 accent-orange" />
                <span className="text-sm">We are a government agency (municipal/county/tribal)</span>
              </label>
            </div>
            <div className="mb-6 p-4 border border-border-DEFAULT chamfer-4 bg-[rgba(255,255,255,0.02)]">
              <div className="text-[11px] font-bold tracking-[0.18em] uppercase text-[var(--q-orange)] mb-2">Agency choice stays intact</div>
              <div className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                Choose FusionEMS AI billing or keep your current billing team/vendor. We support Office Ally onboarding, Lob-driven patient statements, real-time analytics, and self-service data export if you ever leave.
              </div>
            </div>
            <button disabled={!canProceed1} onClick={() => setStep(2)}
              className="w-full py-3 bg-[var(--q-orange)] text-black text-sm font-bold chamfer-4 disabled:opacity-40 hover:bg-[#FF6A1A] transition-colors">
              Continue to Add-ons
            </button>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Add-ons</h2>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">Add capabilities to your plan.</p>
            <div className="space-y-2 mb-6">
              {catalog.addons.filter(a => !a.gov_only || isGovEntity).map(a => (
                <label key={a.code} className={`flex items-center justify-between p-4 chamfer-4 border cursor-pointer transition-all ${addons.includes(a.code) ? 'border-[var(--q-orange)] bg-[rgba(255,106,0,0.12)]' : 'border-border-DEFAULT hover:border-border-strong'}`}>
                  <div className="flex items-center gap-3">
                    <input type="checkbox" checked={addons.includes(a.code)} onChange={() => toggleAddon(a.code)} className="w-4 h-4 accent-orange" />
                    <div>
                      <div className="text-sm font-semibold">{a.label}</div>
                      {a.gov_only && <div className="text-xs text-status-warning">Government agencies only</div>}
                    </div>
                  </div>
                  <div className="text-xs text-[var(--q-orange)] font-bold">{a.price_display}</div>
                </label>
              ))}
            </div>
            {addons.includes('BILLING_AUTOMATION') && (
              <div className="mb-6 p-4 border border-border-DEFAULT chamfer-4">
                <div className={labelCls}>Billing Automation tier</div>
                <div className="text-xs text-[var(--color-text-muted)] mb-3">
                  {billingMode === 'FUSION_RCM'
                    ? 'Fixed-fee AI billing with statements, payment orchestration, and revenue analytics.'
                    : 'Lower-cost export mode for agencies keeping their internal or third-party biller.'}
                </div>
                <div className="space-y-2">
                  {availableBillingTiers.map(t => (
                    <label key={t.code} className={`flex items-center justify-between p-3 chamfer-4 border cursor-pointer ${billingTier === t.code ? 'border-[var(--q-orange)]' : 'border-border-subtle'}`}>
                      <div className="flex items-center gap-2">
                        <input type="radio" checked={billingTier === t.code} onChange={() => setBillingTier(t.code)} className="accent-orange" />
                        <div>
                          <div className="text-xs">{t.label}</div>
                          {t.compare_display && <div className="text-[10px] text-[var(--color-text-muted)] mt-1">{t.compare_display}</div>}
                        </div>
                      </div>
                      <span className="text-xs text-[var(--q-orange)] font-bold">{t.base_display} {t.per_claim_display}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="flex-1 py-3 border border-border-strong text-sm font-bold chamfer-4 hover:bg-[rgba(255,255,255,0.05)]">Back</button>
              <button disabled={!canProceed2} onClick={() => setStep(3)} className="flex-1 py-3 bg-[var(--q-orange)] text-black text-sm font-bold chamfer-4 hover:bg-[#FF6A1A] disabled:opacity-40">Continue</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Collections setup</h2>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">How do you want to handle patient responsibility balances?</p>
            <div className="space-y-2 mb-6">
              {COLLECTIONS_MODES.map(m => (
                <label key={m.code} className={`flex items-center gap-3 p-4 chamfer-4 border cursor-pointer transition-all ${collectionsMode === m.code ? 'border-[var(--q-orange)] bg-[rgba(255,106,0,0.12)]' : 'border-border-DEFAULT'}`}>
                  <input type="radio" checked={collectionsMode === m.code} onChange={() => setCollectionsMode(m.code)} className="accent-orange" />
                  <span className="text-sm">{m.label}</span>
                </label>
              ))}
            </div>
            {collectionsMode !== 'none' && (
              <div className="mb-6 p-4 border border-border-DEFAULT chamfer-4 space-y-4">
                <div>
                  <div className={labelCls}>Statement delivery channels</div>
                  <div className="flex gap-4">
                    {['mail','email','sms_link'].map(ch => (
                      <label key={ch} className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" checked={statementChannels.includes(ch)} onChange={() => toggleChannel(ch)} className="accent-orange" />
                        <span className="text-sm capitalize">{ch.replace('_', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>
                {collectionsMode === 'soft_and_handoff' && (
                  <div className="space-y-3">
                    <div>
                      <label className={labelCls}>Collections vendor name (optional)</label>
                      <input value={collectorVendor} onChange={e => setCollectorVendor(e.target.value)} placeholder="e.g. ABC Collections Inc." className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>Placement method</label>
                      <select value={placementMethod} onChange={e => setPlacementMethod(e.target.value)} className={selectCls}>
                        <option value="portal_upload">Portal upload (download ZIP)</option>
                        <option value="sftp">SFTP (configure after signup)</option>
                        <option value="email">Email</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div className="mb-6 p-4 border border-border-DEFAULT chamfer-4 space-y-4 bg-[rgba(255,255,255,0.02)]">
              <div>
                <div className={labelCls}>Revenue activation</div>
                <div className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                  Configure patient statements, clearinghouse access, billing start timing, and portable exit controls up front.
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Statement program</label>
                  <select value={statementVendor} onChange={e => setStatementVendor(e.target.value)} className={selectCls}>
                    <option value="LOB">FusionEMS + Lob print/mail</option>
                    <option value="INTERNAL_VENDOR">Keep existing print/mail vendor</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Clearinghouse / enrollment</label>
                  <select value={clearinghouseVendor} onChange={e => setClearinghouseVendor(e.target.value)} className={selectCls}>
                    <option value="OFFICE_ALLY">Office Ally + NPI verification</option>
                    <option value="AGENCY_VENDOR">Keep existing clearinghouse</option>
                    <option value="NOT_NEEDED">Not needed yet</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Activation target</label>
                  <select value={activationTarget} onChange={e => setActivationTarget(e.target.value)} className={selectCls}>
                    <option value="IMMEDIATE_IMPORT">Start billing on imported claims immediately</option>
                    <option value="POST_VALIDATION">Wait for validation signoff</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Offboarding / portability</label>
                  <select value={offboardingMode} onChange={e => setOffboardingMode(e.target.value)} className={selectCls}>
                    <option value="SELF_SERVICE_EXPORT">Self-service export + handoff package</option>
                    <option value="ASSISTED_EXPORT">Assisted export review</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="flex-1 py-3 border border-border-strong text-sm font-bold chamfer-4 hover:bg-[rgba(255,255,255,0.05)]">Back</button>
              <button onClick={() => setStep(4)} className="flex-1 py-3 bg-[var(--q-orange)] text-black text-sm font-bold chamfer-4 hover:bg-[#FF6A1A]">Continue</button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Agency information</h2>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">Tell us about your organization.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div className="sm:col-span-2">
                <label className={labelCls}>Agency Name *</label>
                <input value={agencyName} onChange={e => setAgencyName(e.target.value)} placeholder="City of Example EMS" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>First Name *</label>
                <input value={firstName} onChange={e => setFirstName(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Last Name *</label>
                <input value={lastName} onChange={e => setLastName(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Email *</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Phone</label>
                <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Agency Type *</label>
                <select value={agencyType} onChange={e => setAgencyType(e.target.value)} className={selectCls}>
                  <option value="">Select...</option>
                  {AGENCY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>NPI Number</label>
                <div className="flex gap-2">
                  <input value={npiNumber} onChange={e => setNpiNumber(e.target.value)} className={inputCls} placeholder="10-digit NPI" />
                  <button type="button" onClick={lookupNPI} disabled={npiLookupLoading || !npiNumber.trim()} className="px-3 py-2 border border-border-strong text-xs font-semibold chamfer-4 disabled:opacity-40">
                    {npiLookupLoading ? 'Looking…' : 'Lookup'}
                  </button>
                </div>
                {npiLookupError && <div className="text-[11px] text-[var(--color-brand-red)] mt-1">{npiLookupError}</div>}
              </div>
              <div>
                <label className={labelCls}>Operational Mode *</label>
                <select value={operationalMode} onChange={e => setOperationalMode(e.target.value)} className={selectCls}>
                  {OPERATIONAL_MODES.map(m => <option key={m.code} value={m.code}>{m.label}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Who handles billing? *</label>
                <select value={billingMode} onChange={e => setBillingMode(e.target.value)} className={selectCls}>
                  {BILLING_MODES.map(m => <option key={m.code} value={m.code}>{m.label}</option>)}
                </select>
              </div>
              {hemsMode && (
                <>
                  <div>
                    <label className={labelCls}>Primary Tail Number *</label>
                    <input value={primaryTailNumber} onChange={e => setPrimaryTailNumber(e.target.value)} className={inputCls} placeholder="N123AB" />
                  </div>
                  <div>
                    <label className={labelCls}>Base ICAO *</label>
                    <input value={baseIcao} onChange={e => setBaseIcao(e.target.value.toUpperCase())} className={inputCls} placeholder="KMSP" />
                  </div>
                </>
              )}
              <div>
                <label className={labelCls}>Billing Contact Name</label>
                <input value={billingContactName} onChange={e => setBillingContactName(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Billing Contact Email</label>
                <input type="email" value={billingContactEmail} onChange={e => setBillingContactEmail(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Implementation Owner Name</label>
                <input value={implementationOwnerName} onChange={e => setImplementationOwnerName(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Implementation Owner Email</label>
                <input type="email" value={implementationOwnerEmail} onChange={e => setImplementationOwnerEmail(e.target.value)} className={inputCls} />
              </div>
              <div className="sm:col-span-2">
                <label className={labelCls}>Identity / SSO Preference</label>
                <select value={identitySsoPreference} onChange={e => setIdentitySsoPreference(e.target.value)} className={selectCls}>
                  <option value="OIDC">OIDC / SSO (recommended)</option>
                  <option value="SAML">SAML</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>State *</label>
                <select value={state} onChange={e => setState(e.target.value)} className={selectCls}>
                  {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setStep(3)} className="flex-1 py-3 border border-border-strong text-sm font-bold chamfer-4 hover:bg-[rgba(255,255,255,0.05)]">Back</button>
              <button disabled={!canProceed4} onClick={() => setStep(5)} className="flex-1 py-3 bg-[var(--q-orange)] text-black text-sm font-bold chamfer-4 disabled:opacity-40 hover:bg-[#FF6A1A]">Review & Continue</button>
            </div>
          </div>
        )}

        {step === 5 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Review your order</h2>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">Confirm your selections before proceeding to legal signing and payment.</p>
            <div className="space-y-3 mb-6">
              {[
                { label: 'Plan', value: selectedPlan?.label || plan },
                { label: 'Tier', value: catalog.scheduling_tiers.find(t => t.code === tier)?.label || tier || '—' },
                { label: 'Add-ons', value: addons.length ? addons.map(ac => catalog.addons.find(a => a.code === ac)?.label || ac).join(', ') : 'None' },
                  { label: 'Billing Model', value: BILLING_MODES.find(m => m.code === billingMode)?.label || billingMode },
                  { label: 'Operational Mode', value: OPERATIONAL_MODES.find(m => m.code === operationalMode)?.label || operationalMode },
                { label: 'Government entity', value: isGovEntity ? 'Yes' : 'No' },
                { label: 'Collections', value: COLLECTIONS_MODES.find(m => m.code === collectionsMode)?.label || collectionsMode },
                { label: 'Agency', value: `${agencyName} (${agencyType}, ${state})` },
                { label: 'Contact', value: `${firstName} ${lastName} · ${email}` },
              ].map(row => (
                <div key={row.label} className="flex justify-between py-2 border-b border-border-subtle text-sm">
                  <span className="text-[var(--color-text-secondary)]">{row.label}</span>
                  <span className="font-semibold">{row.value}</span>
                </div>
              ))}
              <div className="flex justify-between py-2 border-b border-border-subtle text-sm">
                <span className="text-[var(--color-text-secondary)]">Statement Program</span>
                <span className="font-semibold">{statementVendor === 'LOB' ? 'FusionEMS + Lob' : 'Existing vendor'}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-border-subtle text-sm">
                <span className="text-[var(--color-text-secondary)]">Clearinghouse</span>
                <span className="font-semibold">{clearinghouseVendor === 'OFFICE_ALLY' ? 'Office Ally + NPI verification' : clearinghouseVendor === 'AGENCY_VENDOR' ? 'Existing vendor' : 'Not needed yet'}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-border-subtle text-sm">
                <span className="text-[var(--color-text-secondary)]">Portability</span>
                <span className="font-semibold">{offboardingMode === 'SELF_SERVICE_EXPORT' ? 'Self-service export' : 'Assisted export review'}</span>
              </div>
            </div>
            {error && <div className="mb-4 p-3 bg-[rgba(229,57,53,0.12)] border border-red/25 text-red text-sm chamfer-4">{error}</div>}
            <div className="flex gap-3">
              <button onClick={() => setStep(4)} className="flex-1 py-3 border border-border-strong text-sm font-bold chamfer-4 hover:bg-[rgba(255,255,255,0.05)]">Back</button>
              <button disabled={loading} onClick={submit} className="flex-1 py-3 bg-[var(--q-orange)] text-black text-sm font-bold chamfer-4 disabled:opacity-50 hover:bg-[#FF6A1A]">
                {loading ? 'Submitting...' : 'Continue to Legal Signing'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
