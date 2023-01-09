resource "aws_route53_zone" "main" {
  name = var.domain_name
}

resource "null_resource" "gandi" {
  triggers = {
    name_servers = join(",", aws_route53_zone.main.name_servers)
  }

  provisioner "local-exec" {
    command = "../update-gandi \"${join(",", aws_route53_zone.main.name_servers)}\""
    environment = {
      YES           = 1
      DOMAIN_NAME   = var.domain_name
      GANDI_API_KEY = var.gandi_api_key
    }
  }

  depends_on = [aws_route53_zone.main]
}
