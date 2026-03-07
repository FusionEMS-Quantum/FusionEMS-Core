package fusionems.tenant_isolation

# Deny any API request where the authenticated tenant_id does not match
# the resource tenant_id being accessed.

default allow := false

allow {
    input.authenticated_tenant_id == input.resource_tenant_id
}

# Support access is allowed only when an active, non-expired support grant exists
allow {
    input.is_support_access == true
    input.support_grant_active == true
    input.support_grant_expired == false
}

deny[msg] {
    not allow
    msg := sprintf(
        "Tenant isolation violation: user tenant %s attempted to access resource in tenant %s",
        [input.authenticated_tenant_id, input.resource_tenant_id]
    )
}

# Deny cross-tenant writes unconditionally unless architecture explicitly supports it
deny[msg] {
    input.action == "write"
    input.authenticated_tenant_id != input.resource_tenant_id
    msg := sprintf(
        "Cross-tenant write blocked: %s -> %s (action: %s)",
        [input.authenticated_tenant_id, input.resource_tenant_id, input.action]
    )
}

# Deny PHI access from roles that are not clinical or admin
deny[msg] {
    input.resource_type == "phi"
    not role_allowed_phi(input.role)
    msg := sprintf(
        "PHI access denied for role %s on resource %s",
        [input.role, input.resource_id]
    )
}

role_allowed_phi(role) {
    allowed_phi_roles := {"founder", "agency_admin", "ems", "clinical_provider", "billing"}
    allowed_phi_roles[role]
}

# Deny sensitive export unless explicit approval exists
deny[msg] {
    input.action == "export"
    input.resource_type == "phi"
    not input.export_approved
    msg := sprintf(
        "PHI export requires pre-approval: user %s, resource %s",
        [input.user_id, input.resource_id]
    )
}
