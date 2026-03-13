
resource "aws_ebs_volume" "unencrypted" {
  availability_zone = "us-west-2a"
  size              = 100
}
