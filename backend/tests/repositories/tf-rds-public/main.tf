
resource "aws_db_instance" "public" {
  identifier           = "public-db"
  engine               = "postgres"
  publicly_accessible  = true
}
