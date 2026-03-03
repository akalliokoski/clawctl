# ---------------------------------------------------------------------------
# Secret scope for Databricks jobs that need to call back to the VPS.
# ---------------------------------------------------------------------------
# NOTE: Databricks secrets are NOT accessible from outside Databricks compute.
# They are only for storing credentials that Databricks jobs use to call your VPS.
# For secrets on the VPS itself, use your .env file or a dedicated secrets manager.
#
# After 'terraform apply', set secret values with the Databricks CLI:
#   databricks secrets put-secret --scope openclaw-secrets --key vps-api-key

resource "databricks_secret_scope" "openclaw" {
  name = "openclaw-secrets"
}
