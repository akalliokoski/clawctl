terraform {
  required_version = ">= 1.1.5"
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.110"
    }
  }
}

# Authentication reads DATABRICKS_HOST + DATABRICKS_TOKEN from environment.
# For Free Edition, generate a PAT in:
#   Databricks workspace → User Settings → Developer → Access tokens
provider "databricks" {}

# Used to scope grants to the current user
data "databricks_current_user" "me" {}
