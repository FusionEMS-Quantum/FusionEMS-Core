output "phone_e164" {
  value = data.external.purchase.result.phone_e164
}

output "number_id" {
  value = data.external.purchase.result.number_id
}

output "purchased_at" {
  value = data.external.purchase.result.purchased_at
}

output "cnam_display_name" {
  value = data.external.purchase.result.cnam_display_name
}

output "cnam_status" {
  value = data.external.purchase.result.cnam_status
}
