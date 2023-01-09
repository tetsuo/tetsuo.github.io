#
# DNS records
#

resource "aws_route53_record" "root" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.www.domain_name
    zone_id                = aws_cloudfront_distribution.www.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "CNAME"
  ttl     = "300"
  records = [var.domain_name]
}

#
# ACM cert
#

resource "aws_acm_certificate" "cert" {
  provider = aws.acm_provider # because ACM needs to be used in the "us-east-1" region

  domain_name       = var.domain_name
  validation_method = "DNS"

  tags = {
    Domain = var.domain_name
  }

  lifecycle {
    create_before_destroy = true
  }

  subject_alternative_names = ["www.${var.domain_name}"]
}

resource "aws_acm_certificate_validation" "cert_validation" {
  provider = aws.acm_provider

  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = aws_route53_record.cert_validation.*.fqdn

  depends_on = [null_resource.gandi]
}

resource "aws_route53_record" "cert_validation" {
  count = length(["www.${var.domain_name}"]) + 1

  zone_id         = aws_route53_zone.main.id
  allow_overwrite = true # this fixed the conflict resolution in DNS
  name            = element(aws_acm_certificate.cert.domain_validation_options.*.resource_record_name, count.index)
  type            = element(aws_acm_certificate.cert.domain_validation_options.*.resource_record_type, count.index)
  records         = [element(aws_acm_certificate.cert.domain_validation_options.*.resource_record_value, count.index)]
  ttl             = 60
}

#
# CloudFront
#

resource "aws_cloudfront_distribution" "www" {
  origin {
    domain_name = "${var.domain_name}-public.s3-website.${var.aws_region}.amazonaws.com"

    custom_origin_config {
      http_port              = "80"
      https_port             = "443"
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1", "TLSv1.1", "TLSv1.2"]
    }

    origin_id = var.domain_name
  }

  enabled             = true
  default_root_object = "index.html"

  default_cache_behavior {
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = var.domain_name # should match with origin_id
    min_ttl                = 0
    default_ttl            = 86400    # 3600
    max_ttl                = 31536000 # 86400

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  aliases = [var.domain_name, "www.${var.domain_name}"]

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.cert_validation.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2019"
  }

  logging_config {
    include_cookies = false
    bucket          = aws_s3_bucket.www_logs.bucket_domain_name
    prefix          = "cf"
  }

  # S3 has a default behavior of sending a 403 if content is locked, or doesnt exist. This allows public S3 buckets
  # some security, making a curious person snooping around unsure if a resource truly exists or not.
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/404.html"
  }
}

data "template_file" "log_bucket_policy" {
  template = <<EOF
{
  "Id": "log-bucket-policy",
  "Statement": [
    {
      "Action": "s3:PutObject",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::$${account_id}:root"
      },
      "Resource": "arn:aws:s3:::$${bucket}/*",
      "Sid": "log-bucket-policy"
    }
  ],
  "Version": "2012-10-17"
}

EOF

  vars = {
    bucket     = "${var.domain_name}-logs"
    account_id = var.bucket_policy_account_id
  }
}

resource "aws_s3_bucket" "www_logs" {
  bucket = "${var.domain_name}-logs"

  lifecycle_rule {
    id      = "logs-expiration"
    prefix  = ""
    enabled = var.logs_expiration_enabled

    expiration {
      days = var.logs_expiration_days
    }
  }

  tags = {
    Domain = var.domain_name
  }

  policy = data.template_file.log_bucket_policy.rendered
}
