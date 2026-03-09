variable "environment" {
  type = string
}

variable "project" {
  type = string
}

variable "alert_topic_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
