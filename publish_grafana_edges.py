import json
import os
import re
import requests

# ────────────────────────────────────────────────────────────────────────
# Env vars
# ────────────────────────────────────────────────────────────────────────

#  already set this, e.g.:
# $env:GRAFANA_URL = "http://localhost:8000"
GRAFANA_URL   = os.environ["GRAFANA_URL"]
GRAFANA_TOKEN = os.environ["GRAFANA_TOKEN"]

# NEW: flexible EDGE / TENANT parsing
# -----------------------------------
# Supports:
#   EDGE=edge-d
#   TENANT=p4
#
# or:
#   EDGE=edge-a,edge-b,edge-c
#   TENANT=edge-a:p1,edge-b:p2,edge-c:p3

EDGE_RAW = os.environ.get("EDGE")
if not EDGE_RAW:
    raise RuntimeError(
        "Please set EDGE env var.\n"
        "Examples:\n"
        "  EDGE=edge-d\n"
        "  EDGE=edge-a,edge-b,edge-c"
    )

EDGES = [e.strip() for e in EDGE_RAW.split(",") if e.strip()]
print("EDGES:", EDGES)

TENANT_RAW = os.environ.get("TENANT")
if not TENANT_RAW:
    raise RuntimeError(
        "Please set TENANT env var.\n"
        "Examples:\n"
        "  TENANT=p4\n"
        "  TENANT=edge-a:p1,edge-b:p2,edge-c:p3"
    )


# NEW: Parse TENANT into a mapping edge -> tenant id
def parse_tenant_mapping(edges, tenant_raw):
    """
    If TENANT is a single value (e.g. 'p4') and there is only one EDGE,
    map that edge to that tenant.

    If TENANT looks like 'edge-a:p1,edge-b:p2', parse into:
      {'edge-a': 'p1', 'edge-b': 'p2'}

    Validate that every edge has a tenant mapping.
    """
    tenant_raw = tenant_raw.strip()

    # Single-tenant mode (e.g. TENANT=p4)
    if ":" not in tenant_raw:
        if len(edges) > 1:
            raise RuntimeError(
                "Multiple edges supplied, but TENANT is not a mapping.\n"
                "Use TENANT=edge-a:p1,edge-b:p2 for multiple edges."
            )
        return {edges[0]: tenant_raw}

    # Multi-tenant mode
    mapping = {}
    entries = [x.strip() for x in tenant_raw.split(",") if x.strip()]
    for entry in entries:
        if ":" not in entry:
            raise RuntimeError(
                f"Invalid TENANT entry '{entry}'. Expected 'edge-name:tenant'."
            )
        edge, tenant = [x.strip() for x in entry.split(":", 1)]
        if not edge or not tenant:
            raise RuntimeError(
                f"Invalid TENANT entry '{entry}'. Edge or tenant is empty."
            )
        mapping[edge] = tenant

    # Validate that every edge has a tenant
    for edge in edges:
        if edge not in mapping:
            raise RuntimeError(
                f"No tenant mapping found for edge '{edge}' in TENANT env.\n"
                f"Provide it like: TENANT={tenant_raw},edge-d:pX"
            )

    return mapping


# NEW: derived mapping: edge -> tenant id (e.g. 'edge-a' -> 'p1')
EDGE_TENANTS = parse_tenant_mapping(EDGES, TENANT_RAW)


FOLDER_TITLE  = os.environ.get("FOLDER_TITLE", "Edges")
FOLDER_UID    = None  # discovered/created
FOLDER_ID     = None  # numeric folder id from Grafana

TEMPLATE_PATH = os.environ.get(
    "TEMPLATE_PATH", "central/grafana/dashboards/edge-template.json"
)

# prefix used when naming datasources, e.g. "Mimir - Edge A"
DATASOURCE_PREFIX = os.environ.get("DATASOURCE_PREFIX", "Mimir - ")

# central mimir URL from inside Grafana container
MIMIR_URL = os.environ.get("MIMIR_URL", "https://mimir:9009/prometheus")

# optional: paths to certs if you want to push mTLS config via API
CA_CERT_PATH     = os.environ.get("CA_CERT_PATH")      # e.g. "certs/ca.crt"
CLIENT_CERT_PATH = os.environ.get("CLIENT_CERT_PATH")  # e.g. "certs/grafana.crt"
CLIENT_KEY_PATH  = os.environ.get("CLIENT_KEY_PATH")   # e.g. "certs/grafana.key"

H = {
    "Authorization": f"Bearer {GRAFANA_TOKEN}",
    "Content-Type": "application/json",
}

# ────────────────────────────────────────────────────────────────────────
# Small wrappers around the Grafana API
# ────────────────────────────────────────────────────────────────────────

def gget(path):
    # verify=False for local dev with self-signed / Caddy certs
    r = requests.get(GRAFANA_URL + path, headers=H, verify=False)
    r.raise_for_status()
    return r.json()

def gpost(path, body):
    r = requests.post(GRAFANA_URL + path, headers=H,
                      data=json.dumps(body), verify=False)
    r.raise_for_status()
    return r.json()

def gput(path, body):
    # NEW: fixed json.dumps call; verify belongs to requests.put, not json.dumps
    r = requests.put(GRAFANA_URL + path, headers=H,
                     data=json.dumps(body), verify=False)
    r.raise_for_status()
    return r.json()


# ────────────────────────────────────────────────────────────────────────
# Folder helpers
# ────────────────────────────────────────────────────────────────────────

def ensure_folder():
    """
    Ensure a folder with title FOLDER_TITLE exists in Grafana.

    Behavior:
      - If a folder with that title already exists, reuse it (do NOT create a new one).
      - If it does not exist, create it and remember its uid and id.

    Sets the globals:
      FOLDER_UID, FOLDER_ID
    """
    global FOLDER_UID, FOLDER_ID

    # 1) Try to find an existing folder by title using the search API
    search_results = gget(f"/api/search?type=dash-folder&query={FOLDER_TITLE}")

    for item in search_results:
        if item.get("title") == FOLDER_TITLE:
            FOLDER_UID = item.get("uid")
            FOLDER_ID  = item.get("id")
            print(
                f"Folder '{FOLDER_TITLE}' already exists "
                f"(id={FOLDER_ID}, uid={FOLDER_UID})"
            )
            return

    # 2) No folder with that title found → create one
    body = {"title": FOLDER_TITLE}
    resp = gpost("/api/folders", body)

    FOLDER_UID = resp.get("uid")
    FOLDER_ID  = resp.get("id")

    print(
        f"Created folder '{FOLDER_TITLE}' -> {resp.get('url')} "
        f"(id={FOLDER_ID}, uid={FOLDER_UID})"
    )


# ────────────────────────────────────────────────────────────────────────
# Cert helpers (mTLS)
# ────────────────────────────────────────────────────────────────────────

def read_file_or_none(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

CA_CERT_PEM     = read_file_or_none(CA_CERT_PATH)
CLIENT_CERT_PEM = read_file_or_none(CLIENT_CERT_PATH)
CLIENT_KEY_PEM  = read_file_or_none(CLIENT_KEY_PATH)


# ────────────────────────────────────────────────────────────────────────
# Edge → tenant mapping / datasource helpers
# ────────────────────────────────────────────────────────────────────────

def tenant_for_edge(edge: str) -> str:
    return EDGE_TENANTS[edge]


def pretty_edge_name(edge: str) -> str:
    """
    Convert an internal edge id like 'edge-a' to a display name 'Edge A'.
    """
    return edge.replace("-", " ").title()


def datasource_name(edge: str) -> str:
    """
    For edge-a -> 'Mimir - Edge A'
    For edge-b -> 'Mimir - Edge B'
    For edge-c -> 'Mimir - Edge C'
    """
    return f"{DATASOURCE_PREFIX}{pretty_edge_name(edge)}"


def ensure_datasource_for_edge(edge: str) -> str:
    """
    Ensure a Prometheus/Mimir datasource exists for this edge/tenant.
    - Existing edges (from provisioning): just look them up by name.
    - New edges: create datasources dynamically.
    Returns the datasource UID.
    """
    name = datasource_name(edge)
    import requests as rq

    # try to look it up by name first
    try:
        data = gget(f"/api/datasources/name/{name}")
        print(f"Datasource '{name}' already exists (id={data['id']})")
        return data["uid"]
    except rq.HTTPError as e:
        if e.response is None or e.response.status_code != 404:
            raise
        print(f"Datasource '{name}' not found, creating…")

    tenant = tenant_for_edge(edge)  # p1 / p2 / p3 / ...

    # build datasource definition
    body = {
        "name": name,
        "type": "prometheus",
        "access": "proxy",
        "url": MIMIR_URL,
        "isDefault": False,
        "editable": True,
        "jsonData": {
            "httpHeaderName1": "X-Scope-OrgID",
            "tlsAuth": bool(CLIENT_CERT_PEM and CLIENT_KEY_PEM),
            "tlsAuthWithCACert": bool(CA_CERT_PEM),
        },
        "secureJsonData": {
            "httpHeaderValue1": tenant,
        },
    }

    if CA_CERT_PEM:
        body["secureJsonData"]["tlsCACert"] = CA_CERT_PEM
    if CLIENT_CERT_PEM:
        body["secureJsonData"]["tlsClientCert"] = CLIENT_CERT_PEM
    if CLIENT_KEY_PEM:
        body["secureJsonData"]["tlsClientKey"] = CLIENT_KEY_PEM

    created = gpost("/api/datasources", body)

    # Safely extract UID
    ds_uid = None
    if isinstance(created, dict):
        if "datasource" in created and isinstance(created["datasource"], dict):
            ds_uid = created["datasource"].get("uid")
        if ds_uid is None:
            ds_uid = created.get("uid")

    if not ds_uid:
        # Fallback: just fetch it again by name
        data = gget(f"/api/datasources/name/{name}")
        ds_uid = data["uid"]
        print(
            f"Created datasource '{name}' (id={data['id']}, uid={ds_uid}) "
            f"(uid fetched via lookup)"
        )
    else:
        print(
            f"Created datasource '{name}' (id={created.get('id')}, uid={ds_uid})"
        )

    return ds_uid


# ────────────────────────────────────────────────────────────────────────
# Dashboard helpers
# ────────────────────────────────────────────────────────────────────────

def uid_safe(edge: str) -> str:
    uid = re.sub(r"[^a-z0-9_-]", "-", edge.lower())
    return uid[:36]


# NEW: recursively force datasource UID into every panel / target
def apply_datasource(obj, ds_uid: str):
    """
    Recursively walk the dashboard JSON and set any 'datasource'
    fields to use this Prometheus datasource UID.
    """
    if isinstance(obj, dict):
        if "datasource" in obj:
            obj["datasource"] = {
                "type": "prometheus",
                "uid": ds_uid,
            }
        for v in obj.values():
            apply_datasource(v, ds_uid)
    elif isinstance(obj, list):
        for v in obj:
            apply_datasource(v, ds_uid)


def ensure_dashboard_for_edge(edge: str, ds_uid: str, template: str):
    """
    Render a dashboard for this edge and ensure it exists in the folder.

    Rules:
      - If the folder already exists, reuse it (ensure_folder() must be called first).
      - If a dashboard with the same title already exists in that folder, do NOT add it.
      - Otherwise create it in that folder.
      - If Grafana returns 412 (precondition failed), treat it as "already exists/conflict" and skip.
    """
    import requests as rq
    global FOLDER_UID, FOLDER_ID, FOLDER_TITLE

    if FOLDER_UID is None or FOLDER_ID is None:
        raise RuntimeError("Folder not initialized. Call ensure_folder() first.")

    # Render dashboard JSON from template
    uid_suffix = uid_safe(edge)
    rendered = (
        template
        .replace("${EDGE_NAME}", edge)
        .replace("${DATASOURCE_UID}", ds_uid)
        .replace("${UID_SUFFIX}", uid_suffix)
    )

    dashboard = json.loads(rendered)
    dash_title = dashboard.get("title", f"Edge {edge} dashboard")

    # NEW: force all panel/target datasources to this edge's Prometheus UID
    apply_datasource(dashboard, ds_uid)

    # 1) Check if a dashboard with this title already exists in the folder
    search_results = gget(
        f"/api/search?type=dash-db&folderIds={FOLDER_ID}&query={dash_title}"
    )
    for item in search_results:
        if item.get("title") == dash_title:
            print(
                f"Dashboard '{dash_title}' already exists in folder "
                f"'{FOLDER_TITLE}', skipping."
            )
            return

    # 2) Create the dashboard in that folder (no overwrite)
    payload = {
        "dashboard": dashboard,
        "folderUid": FOLDER_UID,
        "message": f"CI add for {edge}",
        "overwrite": False,
    }

    try:
        resp = gpost("/api/dashboards/db", payload)
        print(f"Created dashboard for {edge} -> {resp.get('url')}")
    except rq.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 412:
            # Precondition failed: usually version/uid conflict; treat as "already exists"
            print(
                f"Grafana returned 412 for dashboard '{dash_title}'. "
                f"Treating as 'already exists / conflict', skipping."
            )
            return
        raise


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main():
    print("GRAFANA_URL =", GRAFANA_URL)
    ensure_folder()

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    for edge in EDGES:
        ds_uid = ensure_datasource_for_edge(edge)
        ensure_dashboard_for_edge(edge, ds_uid, template)


if __name__ == "__main__":
    main()
