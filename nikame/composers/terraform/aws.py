"""Terraform AWS provider for NIKAME."""
from __future__ import annotations
import json
from typing import Any
from nikame.blueprint.engine import Blueprint
from nikame.composers.terraform.base import BaseTerraformProvider

class AWSTerraformProvider(BaseTerraformProvider):
    """AWS Terraform generator — EKS, RDS, ElastiCache, S3, VPC."""

    def generate(self, blueprint: Blueprint) -> dict[str, str]:
        files: dict[str, str] = {}
        project = blueprint.project_name
        
        # 1. main.tf
        files["main.tf"] = f"""
provider "aws" {{
  region = var.aws_region
}}

module "vpc" {{
  source = "terraform-aws-modules/vpc/aws"
  name   = "{project}-vpc"
  cidr   = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}}

module "eks" {{
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "{project}-cluster"
  cluster_version = "1.29"

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.intra_subnets

  eks_managed_node_groups = {{
    main = {{
      min_size     = 2
      max_size     = 5
      desired_size = 2
      instance_types = ["t3.medium"]
    }}
  }}
}}
"""
        # 2. Add RDS if Postgres is present
        if any(m.NAME == "postgres" for m in blueprint.modules):
            files["rds.tf"] = f"""
module "db" {{
  source  = "terraform-aws-modules/rds/aws"
  identifier = "{project}-db"

  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t3.medium"
  allocated_storage = 20

  db_name  = "{project}"
  username = "postgres"
  port     = "5432"

  vpc_security_group_ids = [module.vpc.default_security_group_id]
  subnet_ids             = module.vpc.private_subnets
}}
"""
        # 3. Add ElastiCache if Redis/Dragonfly is present
        if any(m.NAME in ["redis", "dragonfly"] for m in blueprint.modules):
            files["elasticache.tf"] = f"""
resource "aws_elasticache_cluster" "main" {{
  cluster_id           = "{project}-cache"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
}}

resource "aws_elasticache_subnet_group" "main" {{
  name       = "{project}-cache-subnet"
  subnet_ids = module.vpc.private_subnets
}}
"""
        # 4. Add S3 if MinIO/S3 is present
        if any(m.NAME == "minio" for m in blueprint.modules):
            files["s3.tf"] = f"""
resource "aws_s3_bucket" "uploads" {{
  bucket = "{project}-uploads"
}}

resource "aws_s3_bucket_public_access_block" "uploads" {{
  bucket = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}
"""

        # 5. variables.tf
        files["variables.tf"] = """
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
"""
        return files
