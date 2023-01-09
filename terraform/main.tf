terraform {
  backend "s3" {
    key     = "ogunz.tfstate.1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# https://docs.aws.amazon.com/acm/latest/userguide/acm-services.html
# "To use an ACM Certificate with CloudFront, you must request or import the certificate in the US East (N. Virginia) region."
# https://www.terraform.io/docs/configuration/providers.html#multiple-provider-instances
provider "aws" {
  alias  = "acm_provider"
  region = "us-east-1"
}
