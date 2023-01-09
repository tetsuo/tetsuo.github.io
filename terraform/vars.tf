variable "domain_name" {}

variable "aws_region" {}

variable "gandi_api_key" {
  sensitive = true
}

variable "bucket_policy_account_id" {
  # eu-central-1 (see: http://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-access-logs.html#attach-bucket-policy)
  default = "054676820928"
}

variable "logs_expiration_enabled" {
  default = true
}

variable "logs_expiration_days" {
  default = 60
}
