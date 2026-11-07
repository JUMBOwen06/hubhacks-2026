"""Source adapters. Each adapter maps one source format into the common schema.

An adapter is a function ``load(conn, path, ...) -> dict`` that inserts rows into
institution / record / record_date / entity / record_entity / record_relation and
returns a summary dict. The search index is rebuilt afterwards by app.build.
"""
