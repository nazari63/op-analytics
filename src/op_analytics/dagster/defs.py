from dagster import (
    AssetSelection,
    DefaultScheduleStatus,
    Definitions,
    ScheduleDefinition,
    load_assets_from_modules,
)

from .utils.k8sconfig import op_analytics_asset_job, OPK8sConfig

import importlib

MODULE_NAMES = [
    "blockbatch",
    "transform",
    "chains",
    "defillama",
    "github",
    "other",
]


ASSETS = [
    asset
    for name in MODULE_NAMES
    for asset in load_assets_from_modules(
        modules=[importlib.import_module(f"op_analytics.dagster.assets.{name}")],
        group_name=name,
        key_prefix=name,
    )
]


def create_schedule_for_group(
    group: str,
    cron_schedule: str,
    default_status: DefaultScheduleStatus,
):
    return ScheduleDefinition(
        name=group,
        job=op_analytics_asset_job(
            name=f"{group}_job",
            selection=AssetSelection.groups(group),
            custom_config=OPK8sConfig(
                mem_request="3Gi",
                mem_limit="6Gi",
                labels={
                    "op-analytics-dagster-group": group,
                },
            ),
        ),
        cron_schedule=cron_schedule,
        execution_timezone="UTC",
        default_status=default_status,
    )


defs = Definitions(
    assets=ASSETS,
    schedules=[
        create_schedule_for_group(
            group="chains",
            cron_schedule="0 3 * * *",  # Runs at 3 AM daily
            default_status=DefaultScheduleStatus.RUNNING,
        ),
        #
        create_schedule_for_group(
            group="blockbatch",
            cron_schedule="38 * * * *",  # Run every hour
            default_status=DefaultScheduleStatus.RUNNING,
        ),
        #
        create_schedule_for_group(
            group="transform",
            cron_schedule="17 */6 * * *",  # Run every 6 hours
            default_status=DefaultScheduleStatus.RUNNING,
        ),
        #
        create_schedule_for_group(
            group="defillama",
            cron_schedule="0 3 * * *",  # Runs at 3 AM daily
            default_status=DefaultScheduleStatus.RUNNING,
        ),
        #
        create_schedule_for_group(
            group="github",
            cron_schedule="0 2 * * *",  # Runs at 2 AM daily
            default_status=DefaultScheduleStatus.RUNNING,
        ),
        #
        create_schedule_for_group(
            group="other",
            # Runs at 10 AM daily.
            # GrowThePie is generally a little delayed in providing data for the previous day.
            cron_schedule="0 10 * * *",
            default_status=DefaultScheduleStatus.RUNNING,
        ),
    ],
)
