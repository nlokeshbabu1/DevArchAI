
resource "aws_s3_bucket" "public" {
  bucket = "my-public-bucket"
  acl    = "public-read"
}


terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}


resource "aws_db_instance" "secrets" {
  password = "supersecret123"
}
