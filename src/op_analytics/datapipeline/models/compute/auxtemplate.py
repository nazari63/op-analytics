from dataclasses import dataclass
from typing import Any

import duckdb
import polars as pl

from op_analytics.coreutils.duckdb_inmem.client import DuckDBContext

from .querybuilder import TemplatedSQLQuery


@dataclass
class AuxiliaryTemplate:
    template_name: str

    @property
    def name(self):
        return self.template_name

    @property
    def sanitized_name(self):
        return self.template_name.replace("/", "__")

    def render(self, context: dict[str, Any]):
        q = TemplatedSQLQuery(
            template_name=self.template_name,
            context=context,
        )
        rendered = q.render()
        return rendered.query

    def to_parquet(
        self,
        duckdb_context: DuckDBContext,
        template_parameters: dict[str, Any],
        partitions: list[str],
    ):
        parquet_path = duckdb_context.make_path(self.name + ".parquet")
        partition_str = ", ".join(partitions)

        statement = f"""
        COPY (
            {self.render(template_parameters)}
        )
        TO '{parquet_path}'
        
        (FORMAT PARQUET, CODEC 'zstd', PARTITION_BY ({partition_str}));
        """
        try:
            duckdb_context.client.sql(statement)
        except Exception as ex:
            raise Exception(f"sql error: {self.name!r}\n{str(ex)}\n\n{statement} ") from ex

    def to_relation(
        self,
        duckdb_context: DuckDBContext,
        template_parameters: dict[str, Any],
    ) -> duckdb.DuckDBPyRelation:
        statement = self.render(template_parameters)
        try:
            return duckdb_context.client.sql(statement)
        except Exception as ex:
            raise Exception(f"sql error: {self.name!r}\n{str(ex)}\n\n{statement} ") from ex

    def to_polars(
        self,
        duckdb_context: DuckDBContext,
        template_parameters: dict[str, Any],
    ) -> pl.DataFrame:
        return self.to_relation(duckdb_context, template_parameters).pl()

    def create_view_statement(self, template_parameters: dict[str, Any]) -> str:
        return (
            f"CREATE OR REPLACE VIEW {self.sanitized_name} AS\n{self.render(template_parameters)}"
        )

    def create_table_statement(self, template_parameters: dict[str, Any]) -> str:
        return (
            f"CREATE OR REPLACE TABLE {self.sanitized_name} AS\n{self.render(template_parameters)}"
        )

    def create_view(
        self,
        duckdb_context: DuckDBContext,
        template_parameters: dict[str, Any],
    ) -> str:
        statement = self.create_view_statement(template_parameters)
        try:
            duckdb_context.client.sql(statement)
        except Exception as ex:
            raise Exception(f"sql error: {self.name!r}\n{str(ex)}\n\n{statement} ") from ex

        duckdb_context.report_size()
        return self.name

    def create_table(
        self,
        duckdb_context: DuckDBContext,
        template_parameters: dict[str, Any],
    ) -> str:
        statement = self.create_table_statement(template_parameters)
        try:
            duckdb_context.client.sql(statement)
        except Exception as ex:
            raise Exception(f"sql error: {self.name!r}\n{str(ex)}\n\n{statement} ") from ex

        duckdb_context.report_size()
        return self.sanitized_name
