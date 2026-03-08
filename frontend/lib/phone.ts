/**
 * Centralized Brand Identity & Billing Phone Configuration
 * ==========================================================
 * Single source of truth for FusionEMS Quantum brand identity across all
 * patient-facing digital experiences (portal, statements, invoices).
 *
 * In production, NEXT_PUBLIC_* values are injected from the ECS task
 * definition environment via Dockerfile build args.  All patient-facing
 * pages must import from this module instead of hardcoding brand values.
 */

const RAW_PHONE = process.env.NEXT_PUBLIC_BILLING_PHONE ?? "";

/**
 * Format an E.164 US phone number for display: +18005551234 → (800) 555-1234
 */
function formatUSPhone(e164: string): string {
  const digits = e164.replace(/\D/g, "");
  const national = digits.length === 11 && digits.startsWith("1") ? digits.slice(1) : digits;
  if (national.length !== 10) return e164 || "";
  return `(${national.slice(0, 3)}) ${national.slice(3, 6)}-${national.slice(6)}`;
}

// ── Brand Identity ──────────────────────────────────────────────────────────

/** Platform display name used in headers, footers, and notifications. */
export const BRAND_NAME: string =
  process.env.NEXT_PUBLIC_BRAND_NAME ?? "FusionEMS Quantum";

/** CNAM display name shown on outbound caller ID. */
export const CNAM_DISPLAY_NAME: string =
  process.env.NEXT_PUBLIC_CNAM_DISPLAY_NAME ?? "FusionEMS Quantum";

/** Primary web domain. */
export const BRAND_DOMAIN: string =
  process.env.NEXT_PUBLIC_BRAND_DOMAIN ?? "fusionemsquantum.com";

/** Support email displayed on patient-facing pages. */
export const BRAND_SUPPORT_EMAIL: string =
  process.env.NEXT_PUBLIC_BRAND_SUPPORT_EMAIL ?? "billing@fusionemsquantum.com";

/** No-reply sender shown in email footers. */
export const BRAND_NOREPLY_EMAIL: string =
  process.env.NEXT_PUBLIC_BRAND_NOREPLY_EMAIL ?? "noreply@fusionemsquantum.com";

// ── Billing Phone ───────────────────────────────────────────────────────────

/** E.164 billing phone for `tel:` href attributes. */
export const BILLING_PHONE_E164: string = RAW_PHONE;

/** Human-readable billing phone for display. */
export const BILLING_PHONE_DISPLAY: string = formatUSPhone(RAW_PHONE);

/** tel: URI for anchor href attributes. */
export const BILLING_PHONE_TEL: string = RAW_PHONE ? `tel:${RAW_PHONE}` : "";
