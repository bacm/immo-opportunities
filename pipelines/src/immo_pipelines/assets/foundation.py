import platform
import sys

from dagster import AssetExecutionContext, MetadataValue, asset


@asset(group_name="foundation", description="Verify that the Dagster code location can execute.")
def foundation_diagnostic(context: AssetExecutionContext) -> None:
    context.log.info("Foundation diagnostic executed successfully")
    context.add_output_metadata(
        {
            "status": "ok",
            "python_version": MetadataValue.text(platform.python_version()),
            "runtime": MetadataValue.text(sys.implementation.name),
        }
    )
