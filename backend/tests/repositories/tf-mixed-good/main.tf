
terraform {
  backend "s3" {
    bucket = "tf-state"
    key    = "state.tfstate"
    region = "us-east-1"
  }
}


resource "aws_s3_bucket" "untagged" {
  bucket = "untagged-bucket"
}
