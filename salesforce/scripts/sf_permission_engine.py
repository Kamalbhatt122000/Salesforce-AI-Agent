"""
sf_permission_engine.py
══════════════════════════════════════════════════════════
Permission-aware analytics engine for the Salesforce AI Agent.

Detects the logged-in user's persona, queries their allowed objects/fields,
determines record visibility scope, and builds security-trimmed payload dicts
that the AI model can use to answer questions without ever touching raw data
the user cannot see.
"""

import json
from datetime import datetime, timezone


# ── Persona detection heuristics ────────────────────────────
# We map Salesforce profile/role names to canonical personas.
# The patterns are prefix-matched (case-insensitive).

PERSONA_PATTERNS = {
    "exec":          ["ceo", "cfo", "coo", "cto", "chief", "vp", "president", "executive", "director"],
    "sales_manager": ["sales manager", "regional manager", "area manager", "manager", "team lead", "sales lead"],
    "sales_rep":     ["sales rep", "account exec", "ae ", "sdr", "bdr", "sales executive", "inside sales"],
    "service_manager": ["service manager", "support manager", "cs manager", "customer success manager"],
    "sales_ops":     ["sales ops", "operations", "admin", "system admin", "salesforce admin", "data analyst"],
    "service_agent": ["service agent", "support agent", "case manager", "service rep", "support rep", "cs rep"],
}

def _detect_persona(profile_name: str, role_name: str) -> str:
    """Infer a canonical persona from profile/role names."""
    combined = f"{profile_name} {role_name}".lower()
    for persona, patterns in PERSONA_PATTERNS.items():
        for pat in patterns:
            if pat in combined:
                return persona
    return "sales_rep"   # safe default


# ── Scope resolution ─────────────────────────────────────────

def _resolve_scope(persona: str, has_view_all: bool, has_modify_all: bool) -> str:
    """Return 'global', 'team', or 'self' scope."""
    if has_view_all or has_modify_all or persona in ("exec", "sales_ops"):
        return "global"
    if persona in ("sales_manager", "service_manager"):
        return "team"
    return "self"


# ── Main viewer context builder ──────────────────────────────

def get_viewer_context(sf_conn) -> dict:
    """
    Fetch the logged-in Salesforce user's identity, role, profile, and
    object-level permissions.  Returns a viewer_context dict.

    sf_conn  — an instance of SalesforceConnection (app.py)
    """
    ctx = {
        "user_id": None,
        "username": None,
        "full_name": None,
        "email": None,
        "profile_name": None,
        "role_name": None,
        "persona": "sales_rep",
        "scope": "self",
        "currency": "USD",
        "timezone": "UTC",
        "locale": "en_US",
        "allowed_objects": [],
        "restricted_objects": [],
        "can_view_all_data": False,
        "can_modify_all_data": False,
        "error": None,
    }

    try:
        # ── 1. Who is logged in? ───────────────────────────
        result = sf_conn.run_soql(
            "SELECT Id, Name, Username, Email, ProfileId, UserRoleId, "
            "Profile.Name, UserRole.Name, TimeZoneSidKey, LocaleSidKey, "
            "DefaultCurrencyIsoCode "
            "FROM User WHERE Id = UserInfo.getUserId() LIMIT 1"
        )
        # Salesforce doesn't support UserInfo.getUserId() in SOQL outside Apex —
        # fall back to the /services/oauth2/userinfo endpoint via REST.
        if "error" in result:
            result = _get_user_via_rest(sf_conn)

        records = result.get("records", [])
        if not records:
            ctx["error"] = "Could not resolve current user."
            return ctx

        user = records[0]
        profile_obj = user.get("Profile") or {}
        role_obj    = user.get("UserRole") or {}

        profile_name = profile_obj.get("Name", "") if isinstance(profile_obj, dict) else ""
        role_name    = role_obj.get("Name", "")    if isinstance(role_obj, dict) else ""

        ctx.update({
            "user_id":      user.get("Id"),
            "username":     user.get("Username"),
            "full_name":    user.get("Name"),
            "email":        user.get("Email"),
            "profile_name": profile_name,
            "role_name":    role_name,
            "timezone":     user.get("TimeZoneSidKey", "UTC"),
            "locale":       user.get("LocaleSidKey", "en_US"),
            "currency":     user.get("DefaultCurrencyIsoCode", "USD"),
        })

        # ── 2. Detect persona ──────────────────────────────
        ctx["persona"] = _detect_persona(profile_name, role_name)

        # ── 3. Check high-privilege flags ─────────────────
        perm_result = sf_conn.run_soql(
            "SELECT PermissionsViewAllData, PermissionsModifyAllData "
            f"FROM Profile WHERE Id = '{user.get('ProfileId', '')}' LIMIT 1"
        )
        perm_records = perm_result.get("records", [])
        if perm_records:
            ctx["can_view_all_data"]   = bool(perm_records[0].get("PermissionsViewAllData"))
            ctx["can_modify_all_data"] = bool(perm_records[0].get("PermissionsModifyAllData"))

        # ── 4. Resolve record scope ────────────────────────
        ctx["scope"] = _resolve_scope(
            ctx["persona"],
            ctx["can_view_all_data"],
            ctx["can_modify_all_data"],
        )

        # ── 5. Allowed objects (lightweight check) ─────────
        core_objects = [
            "Lead", "Contact", "Account", "Opportunity", "Case",
            "Task", "Event", "Campaign", "User",
        ]
        allowed = []
        restricted = []
        for obj in core_objects:
            probe = sf_conn.run_soql(f"SELECT Id FROM {obj} LIMIT 1")
            if "error" not in probe:
                allowed.append(obj)
            else:
                restricted.append(obj)

        ctx["allowed_objects"]    = allowed
        ctx["restricted_objects"] = restricted

    except Exception as exc:
        ctx["error"] = str(exc)

    return ctx


def _get_user_via_rest(sf_conn) -> dict:
    """
    Fallback: hit /services/data/vXX.0/query?q= with a fixed-user approach.
    We query the first active user whose username matches SF_USERNAME env var.
    """
    import os
    username = os.getenv("SF_USERNAME", "")
    if not username:
        return {"records": []}
    return sf_conn.run_soql(
        f"SELECT Id, Name, Username, Email, ProfileId, UserRoleId, "
        f"Profile.Name, UserRole.Name, TimeZoneSidKey, LocaleSidKey, "
        f"DefaultCurrencyIsoCode "
        f"FROM User WHERE Username = '{username}' LIMIT 1"
    )


# ── Security-trim helpers ────────────────────────────────────

def build_soql_owner_filter(viewer_ctx: dict, owner_field: str = "OwnerId") -> str:
    """
    Return a SOQL WHERE fragment that enforces the correct ownership scope.
    Returns empty string for global scope.
    """
    scope = viewer_ctx.get("scope", "self")
    user_id = viewer_ctx.get("user_id", "")

    if scope == "global" or not user_id:
        return ""
    if scope == "self":
        return f"{owner_field} = '{user_id}'"
    # 'team' scope — we'd need a sub-query for subordinate IDs.
    # For now return self; the AI can widen manually.
    return f"{owner_field} = '{user_id}'"   # TODO: expand to team subordinates


def restrict_fields(records: list, allowed_fields: list) -> list:
    """Strip fields not in allowed_fields from each record dict."""
    if not allowed_fields:
        return records
    return [{k: v for k, v in r.items() if k in allowed_fields} for r in records]


# ── Analytics payload builder ────────────────────────────────

def build_analytics_payload(
    viewer_ctx: dict,
    intent: str,
    sf_conn,
    time_range: str = "THIS_QUARTER",
) -> dict:
    """
    Build a complete, security-trimmed analytics payload for the given intent.

    intent choices:
        my_pipeline | deals_at_risk | tasks_today | team_performance |
        forecast | no_activity_accounts | sla_risk_cases | data_quality

    Returns a dict matching the canonical payload shape described in the spec.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    user_id = viewer_ctx.get("user_id", "")
    scope = viewer_ctx.get("scope", "self")
    persona = viewer_ctx.get("persona", "sales_rep")
    currency = viewer_ctx.get("currency", "USD")

    # Owner filter clause (raw, without WHERE keyword)
    owner_filter = build_soql_owner_filter(viewer_ctx)

    payload = {
        "viewer": {
            "persona":   persona,
            "scope":     scope,
            "currency":  currency,
            "full_name": viewer_ctx.get("full_name", ""),
            "role":      viewer_ctx.get("role_name", ""),
        },
        "filters": {
            "timeRange": time_range,
            "owner":     "viewer" if scope == "self" else scope,
        },
        "kpis":    [],
        "chart":   None,
        "table":   None,
        "actions": [],
        "meta": {
            "dataAsOf": now_iso,
            "source": "Salesforce",
            "note": "Only records visible to this user are included.",
            "intent": intent,
        },
        "summary": "",
        "access_blocked": [],  # objects user cannot see
    }

    # Mark restricted objects
    payload["access_blocked"] = viewer_ctx.get("restricted_objects", [])

    allowed_objects = viewer_ctx.get("allowed_objects", [])

    # ── Delegate to intent-specific builder ───────────────
    try:
        if intent == "my_pipeline":
            _fill_pipeline(payload, sf_conn, user_id, owner_filter, time_range, allowed_objects, scope)
        elif intent == "deals_at_risk":
            _fill_at_risk(payload, sf_conn, user_id, owner_filter, allowed_objects)
        elif intent == "tasks_today":
            _fill_tasks_today(payload, sf_conn, user_id, owner_filter, allowed_objects)
        elif intent == "team_performance":
            _fill_team_performance(payload, sf_conn, user_id, owner_filter, time_range, allowed_objects)
        elif intent == "forecast":
            _fill_forecast(payload, sf_conn, user_id, owner_filter, time_range, allowed_objects)
        elif intent == "no_activity_accounts":
            _fill_no_activity(payload, sf_conn, user_id, owner_filter, allowed_objects)
        elif intent == "sla_risk_cases":
            _fill_sla_risk(payload, sf_conn, user_id, owner_filter, allowed_objects)
        elif intent == "data_quality":
            _fill_data_quality(payload, sf_conn, allowed_objects)
        else:
            payload["summary"] = f"Unknown intent: {intent}"
    except Exception as exc:
        payload["meta"]["error"] = str(exc)

    return payload


# ── Intent-specific fillers ──────────────────────────────────

def _where(owner_filter: str, extra: str = "") -> str:
    """Compose a safe WHERE clause from an owner filter and an optional extra condition."""
    parts = [p for p in [owner_filter, extra] if p]
    return ("WHERE " + " AND ".join(parts)) if parts else ""


def _fill_pipeline(payload, sf, user_id, owner_filter, time_range, allowed, scope):
    if "Opportunity" not in allowed:
        payload["access_blocked"].append("Opportunity")
        payload["summary"] = "You don't have access to Opportunities."
        return

    where = _where(owner_filter, f"IsClosed = false AND CloseDate = {time_range}")

    # KPI: total pipeline value
    agg = sf.run_soql(
        f"SELECT SUM(Amount) total, COUNT(Id) cnt "
        f"FROM Opportunity {where}"
    )
    agg_rec = (agg.get("records") or [{}])[0]
    total_val = agg_rec.get("total") or 0
    total_cnt = agg_rec.get("cnt") or 0

    # KPI: win rate (closed won / total closed this period)
    won = sf.run_soql(
        f"SELECT COUNT(Id) cnt FROM Opportunity "
        f"{_where(owner_filter, f'IsWon = true AND CloseDate = {time_range}')}"
    )
    lost = sf.run_soql(
        f"SELECT COUNT(Id) cnt FROM Opportunity "
        f"{_where(owner_filter, f'IsClosed = true AND IsWon = false AND CloseDate = {time_range}')}"
    )
    won_cnt  = (won.get("records") or [{}])[0].get("cnt") or 0
    lost_cnt = (lost.get("records") or [{}])[0].get("cnt") or 0
    total_closed = won_cnt + lost_cnt
    win_rate = round((won_cnt / total_closed * 100) if total_closed else 0, 1)

    avg_deal = round(total_val / total_cnt) if total_cnt else 0

    payload["kpis"] = [
        {"label": "Open Pipeline",    "value": total_val,  "unit": "currency", "color": "#6366f1"},
        {"label": "Open Deals",       "value": total_cnt,  "unit": "count",    "color": "#06b6d4"},
        {"label": "Win Rate",         "value": win_rate,   "unit": "%",        "color": "#10b981"},
        {"label": "Avg Deal Size",    "value": avg_deal,   "unit": "currency", "color": "#f59e0b"},
    ]

    # Chart: pipeline by stage
    stage_result = sf.run_soql(
        f"SELECT StageName, SUM(Amount) total FROM Opportunity "
        f"{_where(owner_filter, 'IsClosed = false')} "
        f"GROUP BY StageName ORDER BY total DESC LIMIT 8"
    )
    stage_records = stage_result.get("records", [])
    payload["chart"] = {
        "type": "bar",
        "title": f"Pipeline by Stage ({time_range.replace('_', ' ').title()})",
        "labels": [r.get("StageName", "Unknown") for r in stage_records],
        "data":   [float(r.get("total") or 0) for r in stage_records],
        "dataset_label": "Pipeline Value",
    }

    # Table: top open deals
    top_deals = sf.run_soql(
        f"SELECT Id, Name, Amount, StageName, CloseDate, Owner.Name "
        f"FROM Opportunity {where} ORDER BY Amount DESC LIMIT 10"
    )
    rows = []
    for r in top_deals.get("records", []):
        owner_obj = r.get("Owner") or {}
        rows.append({
            "id":       r.get("Id"),
            "name":     r.get("Name", "—"),
            "amount":   r.get("Amount"),
            "stage":    r.get("StageName", "—"),
            "close":    r.get("CloseDate", "—"),
            "owner":    owner_obj.get("Name", "—") if isinstance(owner_obj, dict) else "—",
        })

    payload["table"] = {
        "title":   "Top Open Opportunities",
        "columns": ["Name", "Amount", "Stage", "Close Date", "Owner"],
        "rows":    rows,
    }

    payload["actions"] = [
        {"label": "Open Opportunity", "action": "open_record", "id_field": "id"},
        {"label": "Create Task",      "action": "create_task"},
        {"label": "View Pipeline Report", "action": "open_report"},
    ]

    currency = payload["viewer"]["currency"]
    payload["summary"] = (
        f"You have {total_cnt} open deals totalling "
        f"{_fmt_currency(total_val, currency)} in pipeline this quarter. "
        f"Win rate is {win_rate}%."
    )


def _fill_at_risk(payload, sf, user_id, owner_filter, allowed):
    if "Opportunity" not in allowed:
        payload["access_blocked"].append("Opportunity")
        payload["summary"] = "You don't have access to Opportunities."
        return

    # At-risk = past close date, still open; or no activity in 30 days, value > 0
    where1 = _where(owner_filter, "IsClosed = false AND CloseDate < TODAY AND Amount > 0")
    overdue = sf.run_soql(
        f"SELECT Id, Name, Amount, StageName, CloseDate, LastActivityDate, Owner.Name "
        f"FROM Opportunity {where1} ORDER BY Amount DESC LIMIT 15"
    )

    rows = []
    for r in overdue.get("records", []):
        owner_obj = r.get("Owner") or {}
        rows.append({
            "id":           r.get("Id"),
            "name":         r.get("Name", "—"),
            "amount":       r.get("Amount"),
            "stage":        r.get("StageName", "—"),
            "close_date":   r.get("CloseDate", "—"),
            "last_activity": r.get("LastActivityDate") or "No activity",
            "owner":        owner_obj.get("Name", "—") if isinstance(owner_obj, dict) else "—",
            "risk":         "🔴 Overdue",
        })

    at_risk_cnt = len(rows)
    total_at_risk_val = sum(r.get("amount") or 0 for r in rows)
    currency = payload["viewer"]["currency"]

    payload["kpis"] = [
        {"label": "Overdue Deals",     "value": at_risk_cnt,        "unit": "count",    "color": "#ef4444"},
        {"label": "Value at Risk",     "value": total_at_risk_val,  "unit": "currency", "color": "#f59e0b"},
    ]

    payload["chart"] = {
        "type": "horizontalBar",
        "title": "At-Risk Deals by Amount",
        "labels": [r["name"][:30] for r in rows[:8]],
        "data":   [float(r.get("amount") or 0) for r in rows[:8]],
        "dataset_label": "Deal Value",
    }

    payload["table"] = {
        "title":   "At-Risk Opportunities",
        "columns": ["Name", "Amount", "Stage", "Close Date", "Last Activity", "Risk", "Owner"],
        "rows":    rows,
    }

    payload["actions"] = [
        {"label": "Open Deal",        "action": "open_record", "id_field": "id"},
        {"label": "Create Follow-up", "action": "create_task"},
        {"label": "Update Stage",     "action": "update_stage"},
    ]

    payload["summary"] = (
        f"You have {at_risk_cnt} overdue deals worth "
        f"{_fmt_currency(total_at_risk_val, currency)} that need immediate attention."
    )


def _fill_tasks_today(payload, sf, user_id, owner_filter, allowed):
    if "Task" not in allowed:
        payload["access_blocked"].append("Task")
        payload["summary"] = "You don't have access to Tasks."
        return

    where = _where(owner_filter, "ActivityDate = TODAY AND IsClosed = false")
    tasks = sf.run_soql(
        f"SELECT Id, Subject, ActivityDate, Priority, Status, Who.Name, What.Name "
        f"FROM Task {where} ORDER BY Priority DESC LIMIT 20"
    )

    rows = []
    for r in tasks.get("records", []):
        who_obj  = r.get("Who")  or {}
        what_obj = r.get("What") or {}
        rows.append({
            "id":       r.get("Id"),
            "subject":  r.get("Subject", "—"),
            "priority": r.get("Priority", "Normal"),
            "status":   r.get("Status", "—"),
            "who":      who_obj.get("Name", "—")  if isinstance(who_obj, dict)  else "—",
            "related":  what_obj.get("Name", "—") if isinstance(what_obj, dict) else "—",
        })

    high   = sum(1 for r in rows if r["priority"] == "High")
    normal = sum(1 for r in rows if r["priority"] == "Normal")
    low    = sum(1 for r in rows if r["priority"] == "Low")

    payload["kpis"] = [
        {"label": "Tasks Due Today", "value": len(rows), "unit": "count", "color": "#6366f1"},
        {"label": "High Priority",   "value": high,      "unit": "count", "color": "#ef4444"},
        {"label": "Normal",          "value": normal,    "unit": "count", "color": "#f59e0b"},
        {"label": "Low Priority",    "value": low,       "unit": "count", "color": "#10b981"},
    ]

    payload["chart"] = {
        "type": "doughnut",
        "title": "Tasks by Priority",
        "labels": ["High", "Normal", "Low"],
        "data":   [high, normal, low],
        "dataset_label": "Tasks",
    }

    payload["table"] = {
        "title":   "Tasks Due Today",
        "columns": ["Subject", "Priority", "Status", "Who", "Related To"],
        "rows":    rows,
    }

    payload["actions"] = [
        {"label": "Open Task",    "action": "open_record", "id_field": "id"},
        {"label": "Mark Done",    "action": "update_status"},
        {"label": "Create Task",  "action": "create_task"},
    ]

    payload["summary"] = (
        f"You have {len(rows)} tasks due today — "
        f"{high} high priority, {normal} normal, {low} low."
    )


def _fill_team_performance(payload, sf, user_id, owner_filter, time_range, allowed):
    if "Opportunity" not in allowed:
        payload["access_blocked"].append("Opportunity")
        payload["summary"] = "You don't have access to Opportunities."
        return

    rep_result = sf.run_soql(
        f"SELECT Owner.Name, COUNT(Id) deals, SUM(Amount) pipeline "
        f"FROM Opportunity "
        f"{_where(owner_filter, f'IsClosed = false AND CloseDate = {time_range}')} "
        f"GROUP BY Owner.Name ORDER BY pipeline DESC LIMIT 15"
    )

    rows = []
    for r in rep_result.get("records", []):
        owner_obj = r.get("Owner") or {}
        rows.append({
            "rep":      owner_obj.get("Name", "—") if isinstance(owner_obj, dict) else "—",
            "deals":    r.get("deals") or 0,
            "pipeline": r.get("pipeline") or 0,
        })

    payload["kpis"] = [
        {"label": "Reps Tracked",    "value": len(rows), "unit": "count", "color": "#6366f1"},
        {"label": "Total Pipeline",  "value": sum(r["pipeline"] for r in rows), "unit": "currency", "color": "#10b981"},
    ]

    payload["chart"] = {
        "type": "bar",
        "title": f"Team Pipeline by Rep ({time_range.replace('_', ' ').title()})",
        "labels": [r["rep"][:20] for r in rows],
        "data":   [float(r["pipeline"]) for r in rows],
        "dataset_label": "Pipeline Value",
    }

    payload["table"] = {
        "title":   "Rep Leaderboard",
        "columns": ["Rep", "Open Deals", "Pipeline Value"],
        "rows":    rows,
    }

    payload["actions"] = [
        {"label": "View Full Report", "action": "open_report"},
    ]

    payload["summary"] = (
        f"Team has {len(rows)} reps with combined pipeline of "
        f"{_fmt_currency(sum(r['pipeline'] for r in rows), payload['viewer']['currency'])}."
    )


def _fill_forecast(payload, sf, user_id, owner_filter, time_range, allowed):
    if "Opportunity" not in allowed:
        payload["summary"] = "You don't have access to Opportunities."
        return

    pipeline_res = sf.run_soql(
        f"SELECT SUM(Amount) total FROM Opportunity "
        f"{_where(owner_filter, f'IsClosed = false AND CloseDate = {time_range}')}"
    )
    won_res = sf.run_soql(
        f"SELECT SUM(Amount) total FROM Opportunity "
        f"{_where(owner_filter, f'IsWon = true AND CloseDate = {time_range}')}"
    )

    pipeline_val = (pipeline_res.get("records") or [{}])[0].get("total") or 0
    won_val      = (won_res.get("records") or [{}])[0].get("total") or 0
    currency = payload["viewer"]["currency"]

    payload["kpis"] = [
        {"label": "Open Pipeline",  "value": pipeline_val, "unit": "currency", "color": "#6366f1"},
        {"label": "Closed Won",     "value": won_val,      "unit": "currency", "color": "#10b981"},
    ]

    payload["chart"] = {
        "type": "bar",
        "title": f"Forecast Overview ({time_range.replace('_', ' ').title()})",
        "labels": ["Closed Won", "Open Pipeline"],
        "data":   [float(won_val), float(pipeline_val)],
        "dataset_label": "Amount",
    }

    payload["table"] = None
    payload["summary"] = (
        f"Closed Won: {_fmt_currency(won_val, currency)} | "
        f"Open Pipeline: {_fmt_currency(pipeline_val, currency)} this quarter."
    )


def _fill_no_activity(payload, sf, user_id, owner_filter, allowed):
    if "Account" not in allowed:
        payload["summary"] = "You don't have access to Accounts."
        return

    where = _where(owner_filter, "LastActivityDate < LAST_N_DAYS:30 OR LastActivityDate = null")
    result = sf.run_soql(
        f"SELECT Id, Name, Industry, LastActivityDate, Owner.Name "
        f"FROM Account {where} ORDER BY LastActivityDate ASC NULLS FIRST LIMIT 15"
    )

    rows = []
    for r in result.get("records", []):
        owner_obj = r.get("Owner") or {}
        rows.append({
            "id":            r.get("Id"),
            "name":          r.get("Name", "—"),
            "industry":      r.get("Industry", "—"),
            "last_activity": r.get("LastActivityDate") or "Never",
            "owner":         owner_obj.get("Name", "—") if isinstance(owner_obj, dict) else "—",
        })

    payload["kpis"] = [
        {"label": "Inactive Accounts (30d)", "value": len(rows), "unit": "count", "color": "#f59e0b"},
    ]

    payload["chart"] = {
        "type": "horizontalBar",
        "title": "Accounts with No Activity (30+ days)",
        "labels": [r["name"][:25] for r in rows[:10]],
        "data":   [1] * min(len(rows), 10),
        "dataset_label": "Inactive",
    }

    payload["table"] = {
        "title":   "Accounts with No Recent Activity",
        "columns": ["Account", "Industry", "Last Activity", "Owner"],
        "rows":    rows,
    }

    payload["actions"] = [
        {"label": "Open Account",  "action": "open_record", "id_field": "id"},
        {"label": "Log Activity",  "action": "create_task"},
    ]

    payload["summary"] = (
        f"{len(rows)} accounts have had no activity in 30+ days and may need follow-up."
    )


def _fill_sla_risk(payload, sf, user_id, owner_filter, allowed):
    if "Case" not in allowed:
        payload["summary"] = "You don't have access to Cases."
        return

    where = _where(owner_filter, "IsClosed = false AND Priority = 'High'")
    result = sf.run_soql(
        f"SELECT Id, CaseNumber, Subject, Priority, Status, CreatedDate, Owner.Name "
        f"FROM Case {where} ORDER BY CreatedDate ASC LIMIT 15"
    )

    rows = []
    for r in result.get("records", []):
        owner_obj = r.get("Owner") or {}
        rows.append({
            "id":          r.get("Id"),
            "case_number": r.get("CaseNumber", "—"),
            "subject":     r.get("Subject", "—"),
            "priority":    r.get("Priority", "—"),
            "status":      r.get("Status", "—"),
            "created":     r.get("CreatedDate", "—"),
            "owner":       owner_obj.get("Name", "—") if isinstance(owner_obj, dict) else "—",
        })

    payload["kpis"] = [
        {"label": "High-Priority Open Cases", "value": len(rows), "unit": "count", "color": "#ef4444"},
    ]

    payload["chart"] = {
        "type": "bar",
        "title": "Open Cases by Status",
        "labels": list({r["status"] for r in rows}),
        "data":   [sum(1 for r in rows if r["status"] == s) for s in list({r["status"] for r in rows})],
        "dataset_label": "Cases",
    }

    payload["table"] = {
        "title":   "High-Priority Open Cases",
        "columns": ["Case #", "Subject", "Priority", "Status", "Created", "Owner"],
        "rows":    rows,
    }

    payload["actions"] = [
        {"label": "Open Case",   "action": "open_record", "id_field": "id"},
        {"label": "Update Case", "action": "update_status"},
    ]

    payload["summary"] = (
        f"{len(rows)} high-priority cases are currently open and may be at SLA risk."
    )


def _fill_data_quality(payload, sf, allowed):
    issues = []

    if "Lead" in allowed:
        no_email = sf.run_soql(
            "SELECT COUNT(Id) cnt FROM Lead WHERE Email = null AND IsConverted = false"
        )
        cnt = (no_email.get("records") or [{}])[0].get("cnt") or 0
        if cnt:
            issues.append({"object": "Lead", "issue": "Missing Email", "count": cnt, "color": "#ef4444"})

    if "Contact" in allowed:
        no_phone = sf.run_soql(
            "SELECT COUNT(Id) cnt FROM Contact WHERE Phone = null"
        )
        cnt = (no_phone.get("records") or [{}])[0].get("cnt") or 0
        if cnt:
            issues.append({"object": "Contact", "issue": "Missing Phone", "count": cnt, "color": "#f59e0b"})

    if "Account" in allowed:
        no_industry = sf.run_soql(
            "SELECT COUNT(Id) cnt FROM Account WHERE Industry = null"
        )
        cnt = (no_industry.get("records") or [{}])[0].get("cnt") or 0
        if cnt:
            issues.append({"object": "Account", "issue": "Missing Industry", "count": cnt, "color": "#f59e0b"})

    if "Opportunity" in allowed:
        no_amount = sf.run_soql(
            "SELECT COUNT(Id) cnt FROM Opportunity WHERE Amount = null AND IsClosed = false"
        )
        cnt = (no_amount.get("records") or [{}])[0].get("cnt") or 0
        if cnt:
            issues.append({"object": "Opportunity", "issue": "Missing Amount", "count": cnt, "color": "#ef4444"})

    total_issues = sum(i["count"] for i in issues)

    payload["kpis"] = [
        {"label": "Total Data Issues", "value": total_issues, "unit": "count", "color": "#ef4444"},
        {"label": "Objects Checked",   "value": len(allowed),  "unit": "count", "color": "#6366f1"},
    ]

    payload["chart"] = {
        "type": "bar",
        "title": "Data Quality Issues by Object",
        "labels": [f"{i['object']} — {i['issue']}" for i in issues],
        "data":   [i["count"] for i in issues],
        "dataset_label": "Record Count",
    }

    payload["table"] = {
        "title":   "Data Quality Report",
        "columns": ["Object", "Issue", "Count"],
        "rows":    issues,
    }

    payload["summary"] = (
        f"Found {total_issues} data quality issues across {len(issues)} checks."
    )


# ── Currency formatter ───────────────────────────────────────

def _fmt_currency(value, currency_code: str = "USD") -> str:
    """Format a numeric value as a compact currency string."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    symbol_map = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "JPY": "¥"}
    sym = symbol_map.get(currency_code, currency_code + " ")

    if v >= 1_000_000:
        return f"{sym}{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{sym}{v/1_000:.1f}K"
    return f"{sym}{v:,.0f}"
