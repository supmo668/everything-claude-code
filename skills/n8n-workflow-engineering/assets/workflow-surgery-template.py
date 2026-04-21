#!/usr/bin/env python3
"""
n8n workflow SQL surgery template.

Usage:
    1. Edit the TODO sections with your mutations.
    2. Run: python3 workflow-surgery-template.py <workflow_id>
    3. Verify the change before running again (script prints before/after).

Assumes docker container names `n8n` and `n8n-postgres-1`. Adapt to your setup.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


# --- Config: change to match your environment ----------------------------------
PG_CONTAINER = "n8n-postgres-1"
PG_USER = "n8n_xeos"
PG_DB = "n8n"


def pg(sql: str, capture: bool = True) -> str:
    """Run SQL in the n8n postgres container. Returns stdout."""
    args = ["docker", "exec", PG_CONTAINER, "psql", "-U", PG_USER, "-d", PG_DB, "-t", "-c", sql]
    result = subprocess.run(args, capture_output=capture, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"psql failed: {result.stderr}")
    return result.stdout.strip()


def dump_workflow(workflow_id: str) -> tuple[list, dict]:
    """Pull the current nodes + connections for a workflow."""
    nodes_raw = pg(f"SELECT nodes::text FROM workflow_entity WHERE id='{workflow_id}';")
    conn_raw = pg(f"SELECT connections::text FROM workflow_entity WHERE id='{workflow_id}';")
    return json.loads(nodes_raw), json.loads(conn_raw)


def push_workflow(workflow_id: str, nodes: list, connections: dict) -> None:
    """Push updated nodes + connections back via a dollar-quoted SQL file."""
    nodes_json = json.dumps(nodes)
    conn_json = json.dumps(connections)
    sql = (
        f"UPDATE workflow_entity SET "
        f"nodes = $nodes${nodes_json}$nodes$::json, "
        f"connections = $conn${conn_json}$conn$::json "
        f"WHERE id='{workflow_id}';"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as f:
        f.write(sql)
        sql_path = Path(f.name)
    try:
        subprocess.run(["docker", "cp", str(sql_path), f"{PG_CONTAINER}:/tmp/apply.sql"], check=True)
        out = pg("\\i /tmp/apply.sql") if False else subprocess.run(
            ["docker", "exec", PG_CONTAINER, "psql", "-U", PG_USER, "-d", PG_DB, "-f", "/tmp/apply.sql"],
            capture_output=True, text=True, check=True
        ).stdout
        print("psql:", out.strip() or "(applied)")
    finally:
        sql_path.unlink(missing_ok=True)


# --- TODO: put your mutations here ---------------------------------------------

def mutate(nodes: list, connections: dict) -> tuple[list, dict]:
    """Edit this function. Examples below."""

    # Example 1: Change a Code node's jsCode
    # for n in nodes:
    #     if n["name"] == "My Code Node":
    #         n["parameters"]["jsCode"] = "// new code here"

    # Example 2: Rewire an OpenAI node credential
    # for n in nodes:
    #     if n["name"] == "OpenAI Call":
    #         n["credentials"] = {"openAiApi": {"id": "CRED_ID", "name": "OpenAI"}}

    # Example 3: Add an env-backed field to the Config node
    # for n in nodes:
    #     if n["name"] == "Config: Workflow Parameters":
    #         existing = {a["name"] for a in n["parameters"]["assignments"]["assignments"]}
    #         if "NEW_VAR" not in existing:
    #             n["parameters"]["assignments"]["assignments"].append({
    #                 "id": "cfg-new-var", "name": "NEW_VAR", "type": "string",
    #                 "value": "={{ $env.NEW_VAR }}"
    #             })

    # Example 4: Fix Google Sheets schema drift (sync schema to actual columns)
    # FULL_SCHEMA = [
    #     {"id": col, "type": "string", "display": True, "required": False,
    #      "displayName": col, "defaultMatch": False, "canBeUsedToMatch": True}
    #     for col in ["IMAGE NAME", "IMAGE URL", "STATUS", "URL VIDEO FINAL"]
    # ]
    # for n in nodes:
    #     if n["type"] == "n8n-nodes-base.googleSheets" \
    #        and n["parameters"].get("operation") == "appendOrUpdate":
    #         n["parameters"]["columns"]["schema"] = FULL_SCHEMA

    # Example 5: Rewire connections
    # connections["Source Node"] = {
    #     "main": [[{"node": "Dest Node", "type": "main", "index": 0}]]
    # }

    return nodes, connections


# --- Main ----------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: workflow-surgery-template.py <workflow_id>")
        sys.exit(1)
    wid = sys.argv[1]

    print(f"Dumping workflow {wid} …")
    nodes, connections = dump_workflow(wid)
    print(f"  {len(nodes)} nodes, {len(connections)} connection edges")

    new_nodes, new_conn = mutate(nodes, connections)

    # Sanity check: fail loudly if the mutation dropped everything
    assert len(new_nodes) > 0, "mutate() returned empty nodes list"

    print(f"Pushing updated workflow {wid} …")
    push_workflow(wid, new_nodes, new_conn)
    print("Done.")


if __name__ == "__main__":
    main()
