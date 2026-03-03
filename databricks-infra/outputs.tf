output "catalog_name" {
  description = "Unity Catalog catalog name"
  value       = databricks_catalog.dev.name
}

output "schema_name" {
  description = "Unity Catalog schema name"
  value       = databricks_schema.openclaw.name
}

output "landing_volume_path" {
  description = "Files API upload path — paste this into DATABRICKS_VOLUME_PATH"
  value = "/Volumes/${databricks_catalog.dev.name}/${databricks_schema.openclaw.name}/${databricks_volume.landing.name}"
}

output "current_user" {
  description = "Databricks workspace user"
  value       = data.databricks_current_user.me.user_name
}
