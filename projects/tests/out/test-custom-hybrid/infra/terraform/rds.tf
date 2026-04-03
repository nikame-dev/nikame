
module "db" {
  source  = "terraform-aws-modules/rds/aws"
  identifier = "custom-hybrid-db-db"

  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t3.medium"
  allocated_storage = 20

  db_name  = "custom-hybrid-db"
  username = "postgres"
  port     = "5432"

  vpc_security_group_ids = [module.vpc.default_security_group_id]
  subnet_ids             = module.vpc.private_subnets
}
