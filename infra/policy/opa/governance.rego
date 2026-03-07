package fusionems.governance

# Governance policy rules for FusionEMS trust domains

default allow_protected_action := false

# Protected actions require explicit approval
allow_protected_action {
    input.approval_status == "approved"
    input.approver_role == "founder"
}

allow_protected_action {
    input.approval_status == "approved"
    input.approver_role == "agency_admin"
}

# Support access must be time-bound and logged
deny_support_access[msg] {
    input.is_support_access == true
    not input.support_grant_active
    msg := "Support access denied: no active grant"
}

deny_support_access[msg] {
    input.is_support_access == true
    input.support_grant_expired == true
    msg := "Support access denied: grant has expired"
}

# Impersonation must always be visible
deny_impersonation[msg] {
    input.is_impersonation == true
    not input.impersonation_logged
    msg := "Impersonation blocked: event not logged"
}

# Policy changes require versioning
deny_policy_change[msg] {
    input.action == "policy_change"
    not input.version_incremented
    msg := "Policy change blocked: version must be incremented"
}

# High-risk actions list
is_high_risk_action(action) {
    high_risk := {
        "delete_tenant",
        "export_all_phi",
        "modify_rbac_roles",
        "grant_support_access",
        "disable_mfa",
        "modify_audit_retention",
        "cross_tenant_read"
    }
    high_risk[action]
}

deny_unaudited_high_risk[msg] {
    is_high_risk_action(input.action)
    not input.audit_event_created
    msg := sprintf("High-risk action %s blocked: audit event required", [input.action])
}
