"""Regenerate ../database/schema.sql from the SQLAlchemy models (MySQL dialect)."""
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable, CreateIndex

from app import create_app
from app.config import TestConfig
from app.extensions import db

app = create_app(TestConfig)
with app.app_context():
    out = ["-- ElimuPro MySQL schema (generated from backend/app/models by export_schema.py)",
           "-- Create the database first:  CREATE DATABASE elimupro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
           "SET FOREIGN_KEY_CHECKS = 0;", ""]
    for t in db.metadata.sorted_tables:
        out.append(str(CreateTable(t).compile(dialect=mysql.dialect())).strip() + " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
        for ix in t.indexes:
            out.append(str(CreateIndex(ix).compile(dialect=mysql.dialect())).strip() + ";")
        out.append("")
    out.append("SET FOREIGN_KEY_CHECKS = 1;")
    open("../database/schema.sql", "w").write("\n".join(out) + "\n")
    print(len(db.metadata.sorted_tables), "tables written")
