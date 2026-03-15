
resource "aws_s3_bucket" "public" {
  bucket = "my-public-bucket"
  acl    = "public-read"
}


resource "aws_s3_bucket" "unencrypted" {
  bucket = "my-unencrypted-bucket"
}
