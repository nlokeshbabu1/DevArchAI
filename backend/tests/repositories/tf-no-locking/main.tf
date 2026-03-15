
terraform {
  backend "s3" {
    bucket = "tf-state"
    key    = "state.tfstate"
    region = "us-east-1"
  }
}
