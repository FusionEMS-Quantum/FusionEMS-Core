# Subprocessor Register

| Vendor | Service | Data Scope | PHI Access Potential | BAA Required | BAA Status | Last Security Review |
|---|---|---|---|---|---|---|
| AWS | Core hosting/infrastructure | Application + storage + logs | Yes | Yes | Required/Track Execution | 2026-03-09 |
| Stripe | Payments and billing events | Billing metadata, financial ops data | Possible | Yes if PHI in workflows | Pending verification | 2026-03-09 |
| Telnyx | Telephony and messaging | Communication metadata, contact data | Possible | Yes if PHI transmitted | Pending verification | 2026-03-09 |
| Lob | Mail/document operations | Address/statement data | Possible | Case-by-case | Pending verification | 2026-03-09 |
| OpenAI | AI-assisted workflows | Prompt/response data (must be controlled) | Potentially | Yes if PHI may transit | Pending verification | 2026-03-09 |
| Microsoft | Identity/productivity channels | Workforce identity and comms metadata | Possible | Case-by-case | Pending verification | 2026-03-09 |

## Governance Notes

- No subprocessor is enabled for PHI workflows without contractual and security approval.
- All subprocessors must be represented in vendor and BAA registers before production use.
- Material subprocessor changes require customer notice where contractually required.
