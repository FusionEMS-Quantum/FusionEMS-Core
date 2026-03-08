variable "environment" {
  type = string
}

variable "project" {
  type = string
}

variable "telnyx_api_key_secret_arn" {
  type        = string
  description = "Secrets Manager ARN that contains TELNYX_API_KEY JSON key"
}

variable "desired_tollfree_prefix" {
  type        = string
  default     = "800"
  description = "Preferred toll-free prefix (800/888/877/866/855/844/833)"
}

variable "existing_phone_e164" {
  type        = string
  default     = ""
  description = "Optional pre-provisioned centralized billing number. If set, purchase is skipped."
}

variable "tags" {
  type    = map(string)
  default = {}
}
