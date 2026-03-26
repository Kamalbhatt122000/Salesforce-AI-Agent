"""
Salesforce AI Agent — Web Server
═════════════════════════════════
Flask backend that powers the chatbot frontend.
Handles chat messages, Salesforce queries, and function calling.
"""

import os
import sys
import glob
import json
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types
from otp_manager import create_and_send_otp, verify_otp, cleanup_expired

# ── Load .env ────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salesforce")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SF_USERNAME = os.getenv("SF_USERNAME", "")
SF_PASSWORD = os.getenv("SF_PASSWORD", "")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN", "")

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

# ── Permission engine (lazy import after sf scripts are on path) ─
_permission_engine = None

def _get_permission_engine():
    global _permission_engine
    if _permission_engine is None:
        scripts_dir = os.path.join(SKILL_DIR, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import sf_permission_engine as _perm
        _permission_engine = _perm
    return _permission_engine

# ── Cached viewer context (refreshed per-session or on demand) ──
_viewer_context_cache = {}
_viewer_context_ttl = 300  # seconds
_viewer_context_fetched_at = 0

def get_cached_viewer_context():
    """Return cached viewer context, refreshing if stale."""
    global _viewer_context_cache, _viewer_context_fetched_at
    import time
    now = time.time()
    if not _viewer_context_cache or (now - _viewer_context_fetched_at) > _viewer_context_ttl:
        if sf.connected:
            try:
                engine = _get_permission_engine()
                _viewer_context_cache = engine.get_viewer_context(sf)
                _viewer_context_fetched_at = now
                print(f"  [PERM] Viewer context refreshed: persona={_viewer_context_cache.get('persona')}, scope={_viewer_context_cache.get('scope')}")
            except Exception as e:
                print(f"  [PERM] Failed to fetch viewer context: {e}")
                _viewer_context_cache = {"persona": "sales_rep", "scope": "self", "error": str(e)}
    return _viewer_context_cache


# ── Load Skill Knowledge ─────────────────────────────────────

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".agents", "skills")


def load_skill_registry():
    """Load skill metadata (name + description) from all SKILL.md frontmatter.
    This implements progressive disclosure: only metadata is loaded at startup."""
    import re
    registry = []
    if not os.path.isdir(SKILLS_DIR):
        return registry
    for skill_dir in sorted(os.listdir(SKILLS_DIR)):
        skill_md = os.path.join(SKILLS_DIR, skill_dir, "SKILL.md")
        if os.path.isfile(skill_md):
            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()
                # Parse YAML frontmatter
                fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if fm_match:
                    fm_text = fm_match.group(1)
                    name = ""
                    desc = ""
                    for line in fm_text.split("\n"):
                        if line.startswith("name:"):
                            name = line.split(":", 1)[1].strip()
                        elif line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip()
                    registry.append({"name": name, "description": desc, "path": skill_md})
            except Exception:
                pass
    return registry


def load_skill_files():
    """Load all markdown files from the salesforce knowledge directory."""
    knowledge = {}
    for md_file in glob.glob(os.path.join(SKILL_DIR, "**", "*.md"), recursive=True):
        relative_path = os.path.relpath(md_file, SKILL_DIR)
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                knowledge[relative_path] = f.read()
        except Exception:
            pass
    return knowledge


def build_system_prompt(knowledge, skill_registry=None):
    knowledge_text = ""
    for filepath, content in sorted(knowledge.items()):
        knowledge_text += f"\n\n{'='*60}\nFILE: {filepath}\n{'='*60}\n\n{content}"

    # Build skill registry section (progressive disclosure - metadata only)
    skills_section = ""
    if skill_registry:
        skills_section = "\n\nAVAILABLE SKILLS (Enterprise Agent Skills):\n"
        skills_section += "The following skills are available. Each skill is a focused, self-contained capability.\n"
        skills_section += "Use the appropriate skill's workflow when handling user requests.\n\n"
        for skill in skill_registry:
            skills_section += f"• **{skill['name']}**: {skill['description']}\n"

    return f"""You are a Salesforce Expert AI Agent connected to a LIVE Salesforce org.

RESPONSE STYLE (CRITICAL — FOLLOW STRICTLY):
- Be CONCISE and DIRECT. Short sentences, no filler.
- NEVER mention internal tool names (run_soql_query, update_record, create_record, describe_object, analyze_field_data, generate_chart, get_analytics_dashboard, etc.) to the user. The user doesn't care about your tools — just DO the action and show results.
- NEVER echo or quote raw tool responses (JSON, success messages, internal confirmations) to the user. When a tool returns a success/status message, DO NOT include it in your reply. Instead, describe the outcome naturally.
- Instead of "use update_record with the record ID", say "I can update that for you — just tell me the lead name or ID and what to change."
- Instead of showing '{{"success": true, "message": "Chart generated..."}}', just describe the data insights — the chart is automatically displayed.
- Instead of "use delete_record", say "I can delete that — which lead do you want removed?"
- Use bullet points and tables — avoid long paragraphs.
- For data queries: show the data table and a 1-2 sentence summary.
- For analytical questions: show actual records + brief insights. Max 3-5 bullet points.
- For "how to" questions: briefly explain how, then SHOW the relevant records so user can pick one, then offer to do it for them.
- For advisory questions (e.g. "which leads should I call/invest in?"): query the actual lead records FIRST, show them in a table, THEN give a brief recommendation.
- NEVER repeat yourself. Say it once, clearly.
- Keep total response under 200 words unless showing a data table.

DATA-FIRST RULE (CRITICAL — NEVER SKIP THIS):
- When the user asks ANYTHING about leads, contacts, accounts, or any records — ALWAYS query the actual data FIRST and SHOW real records in a table.
- NEVER give generic advice, summaries, or tips WITHOUT showing actual data from the org.
- UNDERSTAND THE DIFFERENCE:
  • "Which lead SOURCE should I invest in?" → Compare sources using GROUP BY. Show source-level stats.
  • "Among [source] leads, which LEAD should I invest in?" or "which leads to prioritize?" → Show INDIVIDUAL lead records (Name, Company, Status, Rating, Phone, Email, etc.) so the user can see actual people. Sort by Rating (Hot first).
  • When in doubt, ALWAYS show individual lead records. Users want to see actual data.
- If the user mentions a specific source (e.g. "web leads", "among web leads") → query WHERE LeadSource = 'Web' and show INDIVIDUAL leads with key fields.
- For invest/prioritize questions: show leads sorted by Rating (Hot > Warm > Cold), include Name, Company, Status, Rating, Phone, Email. Then add 1-line reasoning why those top leads are worth investing in.
- If combining data + text analysis: first show the data table, then add brief insights.

PROACTIVE ACTION RULE (CRITICAL — STOP ASKING, START DOING):
- When the conversation already contains relevant data (e.g. you just showed a list of inactive accounts, at-risk deals, or leads), USE that data directly for follow-up actions. Do NOT ask the user for IDs or details you already have.
- Example: User says "Create follow-up tasks for inactive accounts" after you showed 15 inactive accounts → Immediately create Task records for ALL those accounts using the Account IDs from the previous query. Use sensible defaults (Subject = "Follow-up: Inactive Account", Status = "Not Started").
- Example: User says "Call him 28-April" referring to the accounts → Create Task records with Subject = "Call", ActivityDate = "2026-04-28", WhatId = AccountId for each account.
- When the user gives a date like "28-April" or "next Monday", convert it to YYYY-MM-DD format and proceed.
- When creating bulk tasks/records from a list: just DO it. Create all the records in sequence. Show a confirmation table when done.
- NEVER ask for a Lead ID, Contact ID, or Account ID when you already have them from a previous query in this conversation.
- NEVER ask "what subject/due date?" — use the user's words directly. If they said "Call him", Subject = "Call". If they said "Follow up next week", Subject = "Follow Up", ActivityDate = next Monday.
- For Tasks linked to Accounts, use WhatId (not WhoId). WhoId is for Leads/Contacts.

YOUR CAPABILITIES:
1. Query and search live Salesforce data
2. Create, update, and delete records
3. Describe object schemas and fields
4. Fetch all fields for any record by ID
5. Create and delete custom fields
6. Generate charts and visualizations
7. Analyze text fields using AI (sentiment, themes, patterns)
8. Check calendar availability and book meetings/calls
9. Answer any Salesforce platform question
10. Get permission-aware analytics dashboards (security-trimmed, persona-specific)
11. Render interactive creation forms in the chat (Lead, Account, Contact, Opportunity)
12. Render interactive UPDATE forms pre-populated with existing record values

FORM RENDERING RULE (CRITICAL — ALWAYS FOLLOW FOR CREATE AND UPDATE REQUESTS):
- When the user asks to "create a new lead", "add an account", "create a contact", "new opportunity", etc.
  and does NOT provide all the required field values in their message → ALWAYS call render_create_form.
  This renders an interactive form directly in the chat where the user can fill in fields and submit.
- If the user DOES provide all required fields inline (e.g. "create a lead: John Doe at Acme Corp, email john@acme.com")
  → Use create_record directly with the provided values.
- When the user asks to "update this lead", "edit this account", "modify the record", etc.
  → ALWAYS call render_update_form with the object_name and record_id.
  This fetches the current field values and renders a pre-populated form so the user can see
  existing values, modify what they need, and submit. The user does NOT need to re-type unchanged fields.
- If the user provides a specific field change inline (e.g. "change the status to Working")
  → Use update_record directly, no form needed.
- NEVER ask the user to type out each field value one by one. Just render the form.
- After calling render_create_form or render_update_form, keep your response SHORT (under 30 words). The form speaks for itself.
- Supported objects for forms: Lead, Account, Contact, Opportunity. For other objects, use create_record/update_record.

PERMISSION-AWARE ANALYTICS (CRITICAL — ALWAYS USE FOR THESE INTENTS):
- When the user asks about pipeline, deals at risk, tasks, team performance, forecast,
  inactive accounts, SLA risk, or data quality → ALWAYS call get_analytics_dashboard.
- This tool automatically detects who is logged in, what they can see, and returns
  only security-trimmed data. NEVER bypass it by running raw SOQL for these intents.
- Supporting intents: my_pipeline | deals_at_risk | tasks_today | team_performance |
  forecast | no_activity_accounts | sla_risk_cases | data_quality
- For the structured payload returned by get_analytics_dashboard:
  • Start with the summary line (1 sentence).
  • Show the KPI cards next — use the kpis array.
  • Reference the chart config so the frontend can render it.
  • Show the table (top 5-15 actionable records).
  • List the suggested actions from the actions array.
  • End with the metadata line showing timeRange, ownerScope, and dataAsOf.
  • If access_blocked is non-empty, tell the user clearly what they cannot see.

PERSONA-SPECIFIC DEFAULT RESPONSES:
- sales_rep    → my_pipeline, tasks_today, deals_at_risk focused
- sales_manager→ team_performance, forecast, no_activity_accounts focused
- exec         → forecast, team_performance, data_quality focused
- sales_ops    → data_quality, team_performance, no_activity_accounts focused
- service_manager → sla_risk_cases, data_quality focused

WHEN TO USE CHART vs TABLE:
- metric/gauge  → "How am I doing against target?"
- line chart    → trends over time
- bar/column    → compare reps, regions, products, stages
- pie/donut     → simple composition (2-5 categories)
- table         → record-level action needed
- horizontalBar → long labels or 8+ categories

CALENDAR & MEETING BOOKING:
- When user asks to "book a call", "schedule a meeting", or "set up a meeting" → FIRST check_calendar to see availability, THEN suggest available time slots, THEN book_meeting once user confirms or if they specified a time.
- When a Lead/Contact ID is provided (e.g. 00Qxxx), link the event to that person using who_id.
- If user says "book a 15-min call with 00Qxxx" → check calendar for today/tomorrow, pick the first available 15-min slot, and book it. Show the confirmed booking details.
- If user asks to "suggest times" → check_calendar for 2-3 days ahead, then show available slots in a table.
- Always confirm: subject, date, time, duration, and who it's with.

SMART QUERY PATTERNS — USE THESE FOR COMMON QUESTIONS:

1. "Which lead SOURCES should we invest in?" → Run aggregate: SELECT LeadSource, COUNT(Id) cnt FROM Lead GROUP BY LeadSource ORDER BY cnt DESC. Also query converted by source. Compare volume AND conversion rate.

2. "Among [source] leads, which LEAD to invest in?" or "which leads to prioritize/call?" → Run: SELECT Id, Name, Company, Status, Rating, Phone, Email, CreatedDate FROM Lead WHERE LeadSource = '[source]' ORDER BY Rating ASC, CreatedDate DESC — show ALL individual leads in a table. Hot-rated leads first. Then add 1-line recommendation.

3. "Which leads should I call today?" → Query leads with Status = 'Open - Not Contacted' or 'Working - Contacted', sort by CreatedDate DESC or Rating = 'Hot'. Prioritize hot leads, recently created, with phone numbers.

4. "Where are we losing leads in the funnel?" → Run: SELECT Status, COUNT(Id) cnt FROM Lead GROUP BY Status ORDER BY cnt DESC — identify bottleneck stages.

5. "Show leads created in last 30 days" → WHERE CreatedDate = LAST_N_DAYS:30
   "...but not converted" → AND IsConverted = false
   "...but converted" → AND IsConverted = true

6. "Show leads where industry is X" → WHERE Industry = 'X'

7. "How do I edit/delete a lead?" → First show recent leads in a table (SELECT Id, Name, Company, Status FROM Lead ORDER BY CreatedDate DESC LIMIT 10), then say: "Tell me which lead and what to change — I'll handle it for you." or "Which lead do you want to delete?"

8. "Assign leads to users/queues" → Show current lead assignments, then say: "Tell me which lead and who to assign it to — I'll update it."

9. "Track lead status" → Show status breakdown (GROUP BY Status) and offer to show individual leads for any status.

10. "Merge duplicate leads" → Explain: Salesforce UI merge (Setup > Merge Leads). Cannot be done via API directly.

11. "High quality vs low quality leads" → Query by Rating field (Hot/Warm/Cold) or use analyze_field_data on Description/Sales_Insight__c.

12. "Lead score for this lead" → Use get_record_all_fields to check if a lead score field exists.

13. "Which sources generate most leads?" → SELECT LeadSource, COUNT(Id) cnt FROM Lead GROUP BY LeadSource ORDER BY cnt DESC

14. "Conversion rate by source" → Query total leads and converted leads by source, calculate percentage.

15. "Leads with no activity in X days" → SELECT Id, Name, LastActivityDate FROM Lead WHERE LastActivityDate < LAST_N_DAYS:X OR LastActivityDate = null

16. "Unassigned leads" → SELECT Id, Name FROM Lead WHERE OwnerId = null (or check for queue ownership)

17. "Lead distribution across reps" → SELECT Owner.Name, COUNT(Id) cnt FROM Lead GROUP BY Owner.Name ORDER BY cnt DESC

18. "How quickly are leads being contacted?" → Compare CreatedDate vs LastActivityDate or first Task date.

19. "Leads overdue for follow-up" → SELECT Id, Name, LastActivityDate FROM Lead WHERE LastActivityDate < LAST_N_DAYS:7 AND Status != 'Closed - Converted'

20. "Calls/emails per lead" → SELECT WhoId, COUNT(Id) FROM Task WHERE WhoId IN (Lead IDs) GROUP BY WhoId

EMAIL / PHONE SEARCH (CRITICAL — ALWAYS FOLLOW):
- When the user provides an EMAIL ADDRESS to find a person:
  ALWAYS search Lead AND Contact FIRST (both have the standard "Email" field).
  Run: SELECT Id, Name, Company, Status, Email, Phone FROM Lead WHERE Email = 'the_email' LIMIT 5
  Run: SELECT Id, Name, Account.Name, Title, Email, Phone FROM Contact WHERE Email = 'the_email' LIMIT 5
  NEVER search Account by email. Account does NOT have a standard Email field.
  Only after finding in Lead/Contact, look up the related Account if needed.
- When the user provides a PHONE NUMBER: Search Lead and Contact first (both have Phone).
- When the user provides a RECORD ID (e.g. 00QgK00000CFx3GUAT):
  Use the ID prefix to determine the object (00Q=Lead, 003=Contact, 001=Account).
  Use the ID directly for update/delete. Do NOT search by name when ID is available.

FINDING RECORDS FOR UPDATE/DELETE:
- If user gives a name only (no ID): Search Lead first, then Contact. Show matches, ask to confirm.
- If user provides a record ID: Use it directly. No name search needed.

SIMPLE ANSWERS (CRITICAL):
- For yes/no questions: Just answer "No." or "Yes." Do NOT say "According to the record, the 'X' field is set to False."
- For single-value questions: Just give the value directly. E.g. "555-1234" or "Open - Not Contacted". No extra explanation.
- NEVER pad simple answers with filler like "According to the record", "Based on the data", "The field X shows". Just answer naturally and briefly.

RECORD SUMMARIES (CRITICAL):
- When the user asks to "summarize" an account, contact, lead, opportunity, or any record:
  - Write a SHORT, NATURAL-LANGUAGE paragraph (2-4 sentences). Do NOT list field names and values.
  - Weave the data into flowing prose. Example:
    GOOD: "**King Solutions Ltd** is a Technology company generating approximately **$4.2M** in annual revenue. Their website is www.kingsolutions.com."
    BAD: "Name: King Solutions Ltd / Industry: Technology / Annual Revenue: 4198912 / Description: ---"
  - Format currency values nicely (e.g. $4,198,912 or ~$4.2M), not raw numbers.
  - Skip fields that are null/empty. Only mention populated fields.
  - If the record has related data (e.g. contacts, opportunities), briefly mention counts if available.
  - Bold the record name and key metrics.
  - Keep it under 100 words.

IMPORTANT RULES:
- When the user provides a record ID, fetch ALL fields for that record immediately.
- When the user asks to see data, ALWAYS execute the query. NEVER just show query text.
- When user asks for "all" records, do NOT add LIMIT. Pagination is automatic.
- When user asks to CREATE/UPDATE/DELETE, just DO it. Don't explain the tool — confirm the action with key details.
- Use describe_object if unsure about fields.
- NEVER expose internal tool/function names in responses. Act naturally.
- NEVER ask the user for a record ID. You already have the IDs from previous queries. If records were shown to the user, use those IDs directly. If multiple matches exist, ask the user to choose by NAME or TYPE (e.g. "The Lead or the Contact?"), then use the corresponding ID you already have.
- When the user says "update the Contact" or "add phone to the Lead" after seeing search results, use the record ID from YOUR previous query results. The user should never need to know or type an ID.

ORG SETTINGS VERIFICATION (CRITICAL):
- NEVER answer questions about org features/settings based on general Salesforce knowledge alone. ALWAYS verify against the LIVE org first.
- For "does it allow multiple contacts?" or "is Contacts to Multiple Accounts enabled?":
  Run: SELECT Id FROM AccountContactRelation LIMIT 1
  If it returns results or no error: the feature IS enabled.
  If it errors (object not found): the feature is DISABLED. Answer "No."
- For any "is [feature] enabled?" question: try to query or describe the related object/field in the live org. Base your answer on the actual result, NOT on Salesforce defaults or general knowledge.
- When the org says something different from the default, trust the org.

AI-POWERED DATA ANALYSIS:
- For analytical questions about text fields (pain points, themes, sentiment, summaries) → use analyze_field_data.
- NEVER say "I cannot analyze text". Fetch the data, then analyze it yourself.
- Present analysis as ranked bullet points or a table. Keep it concise.

RECORD ID PREFIXES: 001=Account, 003=Contact, 00Q=Lead, 006=Opportunity, 500=Case, 00T=Task, 00U=Event

FIELD MAPPING: Map values to correct API names. Never swap fields.

TABLE DISPLAY: Null = "—". Same columns in every row. Show data ONCE, never duplicate.

LEAD CONVERSION: Status "Closed - Converted" auto-creates Account + Contact. Report the result.

CONVERTED LEADS: Hidden by default. Use WHERE IsConverted = true to query them.

COUNT QUERIES: Present count clearly (e.g. "There are **25** leads.").

KNOWLEDGE BASE:
{knowledge_text}
{skills_section}
"""


# ── Salesforce Connection ────────────────────────────────────

class SalesforceConnection:
    def __init__(self):
        self.auth = None
        self.query_executor = None
        self.connected = False
        self.instance_url = ""

    def connect(self):
        scripts_dir = os.path.join(SKILL_DIR, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from sf_auth import SalesforceAuth
        from sf_query import SalesforceQuery
        from sf_rest_client import SalesforceRESTClient

        self.auth = SalesforceAuth(
            username=SF_USERNAME, password=SF_PASSWORD, security_token=SF_SECURITY_TOKEN
        )
        self.auth.authenticate_simple()
        self.query_executor = SalesforceQuery(self.auth)
        self.rest_client = SalesforceRESTClient(self.auth)
        self.connected = True
        self.instance_url = self.auth.instance_url
        return self.instance_url

    def run_soql(self, soql):
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            results = self.query_executor.soql_all(soql)
            clean = [{k: v for k, v in r.items() if k != "attributes"} for r in results]
            return {"records": clean, "count": len(clean)}
        except Exception as e:
            return {"error": str(e)}

    def run_sosl(self, sosl):
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            results = self.query_executor.sosl(sosl)
            clean = [{k: v for k, v in r.items() if k != "attributes"} for r in results]
            return {"records": clean, "count": len(clean)}
        except Exception as e:
            return {"error": str(e)}

    def list_objects(self):
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            objects = self.query_executor.list_objects()
            return {"objects": objects, "count": len(objects)}
        except Exception as e:
            return {"error": str(e)}

    def describe(self, sobject):
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            fields = self.query_executor.describe_fields(sobject)
            return {"object": sobject, "fields": fields, "count": len(fields)}
        except Exception as e:
            return {"error": str(e)}

    def get_all_fields_for_record(self, sobject, record_id):
        """Describe the object to get ALL field names, then query all of them for a single record."""
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            # Step 1: Describe the object to get every field name
            fields_meta = self.query_executor.describe_fields(sobject)
            all_field_names = [f["name"] for f in fields_meta]
            print(f"  [ALL FIELDS] {sobject} has {len(all_field_names)} fields")

            # Step 2: Build SOQL selecting all fields for this record
            field_csv = ", ".join(all_field_names)
            soql = f"SELECT {field_csv} FROM {sobject} WHERE Id = '{record_id}' LIMIT 1"

            # Step 3: Execute
            results = self.query_executor.soql(soql)
            if not results:
                return {"error": f"No {sobject} record found with Id = {record_id}"}

            record = {k: v for k, v in results[0].items() if k != "attributes"}
            return {
                "record": record,
                "object": sobject,
                "field_count": len(all_field_names),
                "message": f"Fetched all {len(all_field_names)} fields for {sobject} {record_id}"
            }
        except Exception as e:
            return {"error": str(e)}

    def create_record(self, sobject, field_values):
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            print(f"  [CREATE {sobject}] Sending field_values: {json.dumps(field_values, indent=2)}")
            record_id = self.rest_client.create(sobject, field_values)
            return {"success": True, "id": record_id, "object": sobject, "fields_sent": field_values, "message": f"{sobject} record created successfully"}
        except Exception as e:
            return {"error": str(e)}

    def update_record(self, sobject, record_id, field_values):
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            self.rest_client.update(sobject, record_id, field_values)
            result = {"success": True, "id": record_id, "object": sobject, "message": f"{sobject} record updated successfully"}

            # ── Auto Lead Conversion ─────────────────────────
            # When a Lead's status is set to "Closed - Converted",
            # automatically create an Account + Contact from the Lead data.
            new_status = field_values.get("Status", "")
            if sobject == "Lead" and new_status.lower() == "closed - converted":
                try:
                    conversion = self._convert_lead(record_id)
                    result["conversion"] = conversion
                    result["message"] += " | Lead auto-converted: Account & Contact created."
                except Exception as conv_err:
                    result["conversion_error"] = str(conv_err)
                    result["message"] += f" | Lead conversion failed: {conv_err}"

            return result
        except Exception as e:
            return {"error": str(e)}

    def _convert_lead(self, lead_id):
        """Fetch lead details and create an Account + Contact from them."""
        # 1. Fetch the lead's details
        lead = self.rest_client.read(
            "Lead", lead_id,
            fields=["FirstName", "LastName", "Company", "Email", "Phone",
                    "Title", "Street", "City", "State", "PostalCode", "Country",
                    "Website", "Industry", "Description"]
        )
        company = lead.get("Company") or f"{lead.get('LastName', 'Unknown')} (Converted Lead)"
        print(f"  [CONVERT LEAD] Lead data: {json.dumps({k: v for k, v in lead.items() if k != 'attributes'}, indent=2)}")

        # 2. Check if an Account with the same name already exists
        existing = self.query_executor.soql(
            f"SELECT Id, Name FROM Account WHERE Name = '{company.replace(chr(39), chr(92)+chr(39))}' LIMIT 1"
        )

        if existing:
            account_id = existing[0]["Id"]
            account_created = False
            print(f"  [CONVERT LEAD] Existing Account found: {account_id}")
        else:
            # Create the Account
            account_data = {"Name": company}
            if lead.get("Industry"):
                account_data["Industry"] = lead["Industry"]
            if lead.get("Website"):
                account_data["Website"] = lead["Website"]
            if lead.get("Phone"):
                account_data["Phone"] = lead["Phone"]
            if lead.get("Description"):
                account_data["Description"] = lead["Description"]
            # Billing address from lead
            if lead.get("Street"):
                account_data["BillingStreet"] = lead["Street"]
            if lead.get("City"):
                account_data["BillingCity"] = lead["City"]
            if lead.get("State"):
                account_data["BillingState"] = lead["State"]
            if lead.get("PostalCode"):
                account_data["BillingPostalCode"] = lead["PostalCode"]
            if lead.get("Country"):
                account_data["BillingCountry"] = lead["Country"]

            print(f"  [CONVERT LEAD] Creating Account: {json.dumps(account_data, indent=2)}")
            account_id = self.rest_client.create("Account", account_data)
            account_created = True

        # 3. Create the Contact linked to the Account
        contact_data = {
            "AccountId": account_id,
            "LastName": lead.get("LastName", "Unknown"),
        }
        if lead.get("FirstName"):
            contact_data["FirstName"] = lead["FirstName"]
        if lead.get("Email"):
            contact_data["Email"] = lead["Email"]
        if lead.get("Phone"):
            contact_data["Phone"] = lead["Phone"]
        if lead.get("Title"):
            contact_data["Title"] = lead["Title"]
        # Mailing address
        if lead.get("Street"):
            contact_data["MailingStreet"] = lead["Street"]
        if lead.get("City"):
            contact_data["MailingCity"] = lead["City"]
        if lead.get("State"):
            contact_data["MailingState"] = lead["State"]
        if lead.get("PostalCode"):
            contact_data["MailingPostalCode"] = lead["PostalCode"]
        if lead.get("Country"):
            contact_data["MailingCountry"] = lead["Country"]

        print(f"  [CONVERT LEAD] Creating Contact: {json.dumps(contact_data, indent=2)}")
        contact_id = self.rest_client.create("Contact", contact_data)

        return {
            "account_id": account_id,
            "account_name": company,
            "account_created": account_created,
            "contact_id": contact_id,
            "contact_name": f"{lead.get('FirstName', '')} {lead.get('LastName', '')}".strip(),
            "message": f"Account '{company}' {'created' if account_created else 'already existed'} and Contact created successfully."
        }

    def delete_record(self, sobject, record_id):
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            self.rest_client.delete(sobject, record_id)
            return {"success": True, "id": record_id, "object": sobject, "message": f"{sobject} record deleted successfully"}
        except Exception as e:
            return {"error": str(e)}

    # ── Custom Field Management (Tooling API) ────────────────

    def _tooling_request(self, method, endpoint, data=None, params=None):
        """Make an authenticated request to the Salesforce Tooling API."""
        import requests as req
        url = f"{self.auth.instance_url}/services/data/v62.0/tooling{endpoint}"
        headers = self.auth.get_headers()
        response = req.request(method=method, url=url, headers=headers, json=data, params=params)
        if response.status_code in (200, 201):
            return response.json()
        elif response.status_code == 204:
            return None
        else:
            error_msg = response.text
            try:
                error_msg = json.dumps(response.json(), indent=2)
            except Exception:
                pass
            raise Exception(f"Tooling API Error ({response.status_code}): {error_msg}")

    def create_custom_field(self, object_name, field_label, field_type, length=None, precision=None, scale=None, picklist_values=None, description=None, required=False):
        """Create a custom field on a Salesforce object using the Tooling API."""
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            # Build the field API name from the label
            field_name = field_label.replace(" ", "_") + "__c"

            # Build the metadata payload
            metadata = {
                "label": field_label,
                "type": field_type,
                "description": description or "",
                "inlineHelpText": "",
            }

            # Set required (via metadata)
            if required:
                metadata["required"] = True

            # Type-specific settings
            field_type_lower = field_type.lower()
            if field_type_lower == "text":
                metadata["type"] = "Text"
                metadata["length"] = length or 255
            elif field_type_lower == "number":
                metadata["type"] = "Number"
                metadata["precision"] = precision or 18
                metadata["scale"] = scale or 0
            elif field_type_lower == "checkbox":
                metadata["type"] = "Checkbox"
                metadata["defaultValue"] = False
            elif field_type_lower == "date":
                metadata["type"] = "Date"
            elif field_type_lower == "datetime":
                metadata["type"] = "DateTime"
            elif field_type_lower == "email":
                metadata["type"] = "Email"
            elif field_type_lower == "phone":
                metadata["type"] = "Phone"
            elif field_type_lower == "url":
                metadata["type"] = "Url"
            elif field_type_lower == "currency":
                metadata["type"] = "Currency"
                metadata["precision"] = precision or 18
                metadata["scale"] = scale or 2
            elif field_type_lower == "percent":
                metadata["type"] = "Percent"
                metadata["precision"] = precision or 5
                metadata["scale"] = scale or 2
            elif field_type_lower == "textarea":
                metadata["type"] = "TextArea"
            elif field_type_lower in ("longtextarea", "long text area"):
                metadata["type"] = "LongTextArea"
                metadata["length"] = length or 32768
                metadata["visibleLines"] = 5
            elif field_type_lower == "picklist":
                metadata["type"] = "Picklist"
                if picklist_values:
                    metadata["valueSet"] = {
                        "restricted": False,
                        "valueSetDefinition": {
                            "sorted": False,
                            "value": [{"fullName": v, "default": (i == 0), "label": v} for i, v in enumerate(picklist_values)]
                        }
                    }
            else:
                # Default fallback — use as-is
                metadata["type"] = field_type
                if length:
                    metadata["length"] = length

            # Full payload for Tooling API CustomField
            payload = {
                "FullName": f"{object_name}.{field_name}",
                "Metadata": metadata
            }

            print(f"  [CREATE FIELD] {object_name}.{field_name} ({field_type})")
            print(f"  [PAYLOAD] {json.dumps(payload, indent=2)}")

            result = self._tooling_request("POST", "/sobjects/CustomField/", data=payload)
            field_id = result.get("id", "") if result else ""

            return {
                "success": True,
                "field_id": field_id,
                "field_api_name": field_name,
                "field_label": field_label,
                "field_type": field_type,
                "object": object_name,
                "message": f"Custom field '{field_label}' ({field_name}) created on {object_name}"
            }
        except Exception as e:
            return {"error": str(e)}

    def delete_custom_field(self, object_name, field_name):
        """Delete a custom field from a Salesforce object using the Tooling API."""
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            # Ensure the field name has __c suffix
            if not field_name.endswith("__c"):
                field_name = field_name + "__c"

            # Step 1: Query the Tooling API to find the CustomField ID
            full_name = f"{object_name}.{field_name}"
            query = f"SELECT Id, DeveloperName, TableEnumOrId FROM CustomField WHERE TableEnumOrId = '{object_name}' AND DeveloperName = '{field_name.replace('__c', '')}'"
            print(f"  [DELETE FIELD] Querying: {query}")

            result = self._tooling_request("GET", "/query/", params={"q": query})
            records = result.get("records", []) if result else []

            if not records:
                return {"error": f"Custom field '{field_name}' not found on {object_name}. Make sure this is a custom field (ending in __c)."}

            field_id = records[0]["Id"]
            print(f"  [DELETE FIELD] Found field ID: {field_id}")

            # Step 2: Delete the field
            self._tooling_request("DELETE", f"/sobjects/CustomField/{field_id}")

            return {
                "success": True,
                "field_id": field_id,
                "field_api_name": field_name,
                "object": object_name,
                "message": f"Custom field '{field_name}' deleted from {object_name}"
            }
        except Exception as e:
            return {"error": str(e)}

    def analyze_field_data(self, object_name, field_name, where_clause=None, limit=200):
        """Fetch raw text data from a specific field across records for AI analysis."""
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            # Build SOQL to fetch the text field values
            # NOTE: We do NOT filter with "!= null" in SOQL because Long Text Area
            # fields do not support comparison operators in WHERE clauses.
            # Instead, we fetch all records and filter nulls in Python.
            soql = f"SELECT Id, {field_name} FROM {object_name}"
            if where_clause:
                soql += f" WHERE {where_clause}"
            soql += f" LIMIT {limit}"

            print(f"  [ANALYZE] Fetching '{field_name}' from {object_name}: {soql}")
            results = self.query_executor.soql_all(soql)

            # Extract just the text values (skip nulls/empty)
            text_values = []
            for r in results:
                val = r.get(field_name)
                if val and str(val).strip():
                    text_values.append(str(val).strip())

            return {
                "object": object_name,
                "field": field_name,
                "total_records_with_data": len(text_values),
                "values": text_values,
                "message": f"Fetched {len(text_values)} non-empty '{field_name}' values from {object_name}. Analyze these values to answer the user's question."
            }
        except Exception as e:
            return {"error": str(e)}

    def check_calendar(self, date_str=None, days_ahead=1):
        """Check the user's Salesforce calendar (Events) for a date range and find free slots."""
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            from datetime import datetime, timedelta

            # Default to today if no date provided
            if date_str:
                try:
                    base_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    base_date = datetime.now()
            else:
                base_date = datetime.now()

            start_dt = base_date.replace(hour=0, minute=0, second=0)
            end_dt = (base_date + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=59)

            start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Query existing events in the date range
            soql = (
                f"SELECT Id, Subject, StartDateTime, EndDateTime, WhoId, Who.Name, "
                f"Location, Description "
                f"FROM Event "
                f"WHERE StartDateTime >= {start_iso} AND StartDateTime <= {end_iso} "
                f"ORDER BY StartDateTime ASC"
            )
            print(f"  [CALENDAR] Querying events: {soql}")
            results = self.query_executor.soql_all(soql)
            events = []
            for r in results:
                evt = {k: v for k, v in r.items() if k != "attributes"}
                # Flatten Who.Name
                who = evt.pop("Who", None)
                if who and isinstance(who, dict):
                    evt["WhoName"] = who.get("Name", "—")
                else:
                    evt["WhoName"] = "—"
                events.append(evt)

            # Calculate free slots (business hours: 9 AM - 5 PM)
            free_slots = []
            for day_offset in range(days_ahead):
                check_date = base_date + timedelta(days=day_offset)
                day_start = check_date.replace(hour=9, minute=0, second=0)
                day_end = check_date.replace(hour=17, minute=0, second=0)

                # If checking today and it's past 9 AM, start from next half-hour
                now = datetime.now()
                if check_date.date() == now.date() and now.hour >= 9:
                    # Round up to next 30-min slot
                    if now.minute <= 30:
                        day_start = now.replace(minute=30, second=0, microsecond=0)
                    else:
                        day_start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

                if day_start >= day_end:
                    continue

                # Get events for this day
                day_events = []
                for evt in events:
                    evt_start_str = evt.get("StartDateTime", "")
                    evt_end_str = evt.get("EndDateTime", "")
                    if evt_start_str and evt_end_str:
                        try:
                            evt_start = datetime.fromisoformat(evt_start_str.replace("Z", "+00:00")).replace(tzinfo=None)
                            evt_end = datetime.fromisoformat(evt_end_str.replace("Z", "+00:00")).replace(tzinfo=None)
                            if evt_start.date() == check_date.date():
                                day_events.append((evt_start, evt_end))
                        except Exception:
                            pass

                # Sort events by start time
                day_events.sort(key=lambda x: x[0])

                # Find gaps
                cursor = day_start
                for evt_start, evt_end in day_events:
                    if cursor < evt_start:
                        gap_minutes = int((evt_start - cursor).total_seconds() / 60)
                        if gap_minutes >= 15:
                            free_slots.append({
                                "date": check_date.strftime("%Y-%m-%d"),
                                "start": cursor.strftime("%H:%M"),
                                "end": evt_start.strftime("%H:%M"),
                                "duration_minutes": gap_minutes
                            })
                    cursor = max(cursor, evt_end)

                # After last event
                if cursor < day_end:
                    gap_minutes = int((day_end - cursor).total_seconds() / 60)
                    if gap_minutes >= 15:
                        free_slots.append({
                            "date": check_date.strftime("%Y-%m-%d"),
                            "start": cursor.strftime("%H:%M"),
                            "end": day_end.strftime("%H:%M"),
                            "duration_minutes": gap_minutes
                        })

            return {
                "events": events,
                "event_count": len(events),
                "free_slots": free_slots,
                "date_range": f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
                "message": f"Found {len(events)} events and {len(free_slots)} free slots. Suggest available times to the user."
            }
        except Exception as e:
            return {"error": str(e)}

    def book_meeting(self, subject, start_datetime, duration_minutes=30, who_id=None, description=None, location=None):
        """Book a meeting/call by creating an Event in Salesforce."""
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            from datetime import datetime, timedelta

            # Parse start datetime
            try:
                start_dt = datetime.fromisoformat(start_datetime.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                start_dt = datetime.fromisoformat(start_datetime)

            end_dt = start_dt + timedelta(minutes=duration_minutes)

            event_data = {
                "Subject": subject,
                "StartDateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "EndDateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "DurationInMinutes": duration_minutes,
            }

            if who_id:
                event_data["WhoId"] = who_id
            if description:
                event_data["Description"] = description
            if location:
                event_data["Location"] = location

            print(f"  [BOOK MEETING] Creating event: {json.dumps(event_data, indent=2)}")
            event_id = self.rest_client.create("Event", event_data)

            # Fetch back to confirm
            confirm_soql = f"SELECT Id, Subject, StartDateTime, EndDateTime, WhoId FROM Event WHERE Id = '{event_id}' LIMIT 1"
            confirm_results = self.query_executor.soql(confirm_soql)
            booked_event = {}
            if confirm_results:
                booked_event = {k: v for k, v in confirm_results[0].items() if k != "attributes"}

            return {
                "success": True,
                "event_id": event_id,
                "subject": subject,
                "start": start_dt.strftime("%Y-%m-%d %H:%M"),
                "end": end_dt.strftime("%Y-%m-%d %H:%M"),
                "duration_minutes": duration_minutes,
                "who_id": who_id,
                "event_details": booked_event,
                "message": f"Meeting '{subject}' booked from {start_dt.strftime('%I:%M %p')} to {end_dt.strftime('%I:%M %p')} on {start_dt.strftime('%B %d, %Y')}."
            }
        except Exception as e:
            return {"error": str(e)}


# ── Gemini Tools ─────────────────────────────────────────────

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="run_soql_query",
            description="Execute a SOQL query on the live Salesforce org and return results.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"query": types.Schema(type="STRING", description="SOQL query string")},
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="run_sosl_search",
            description="Execute a SOSL search across multiple objects.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"search": types.Schema(type="STRING", description="SOSL search string")},
                required=["search"]
            )
        ),
        types.FunctionDeclaration(
            name="list_org_objects",
            description="List all available objects in the Salesforce org.",
            parameters=types.Schema(type="OBJECT", properties={})
        ),
        types.FunctionDeclaration(
            name="describe_object",
            description="Get all field names, types, and labels for a Salesforce object.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"object_name": types.Schema(type="STRING", description="Object API name")},
                required=["object_name"]
            )
        ),
        types.FunctionDeclaration(
            name="create_record",
            description="Create a new record in the Salesforce org. Use this when the user asks to create/add/insert a new record (Contact, Account, Lead, Opportunity, Case, or any object).",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(type="STRING", description="Object API name, e.g. 'Contact', 'Account'"),
                    "field_values": types.Schema(type="OBJECT", description="JSON object of field API names and values")
                },
                required=["object_name", "field_values"]
            )
        ),
        types.FunctionDeclaration(
            name="update_record",
            description="Update an existing record in the Salesforce org. Use this when the user asks to update/edit/modify a record.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(type="STRING", description="Object API name"),
                    "record_id": types.Schema(type="STRING", description="18-character Salesforce record ID"),
                    "field_values": types.Schema(type="OBJECT", description="JSON object of field API names and new values")
                },
                required=["object_name", "record_id", "field_values"]
            )
        ),
        types.FunctionDeclaration(
            name="delete_record",
            description="Delete a record from the Salesforce org. Use this when the user asks to delete/remove a record.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(type="STRING", description="Object API name"),
                    "record_id": types.Schema(type="STRING", description="18-character Salesforce record ID")
                },
                required=["object_name", "record_id"]
            )
        ),
        types.FunctionDeclaration(
            name="generate_chart",
            description="Generate a chart/graph visualization from data. Use this AFTER running a SOQL query that returns aggregated/grouped data. Choose chart type intelligently: bar for category comparisons, pie for 2-5 category proportions, doughnut for 3-6 categories, line for time trends, horizontalBar for long labels or 8+ categories.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "chart_type": types.Schema(type="STRING", description="Chart type: 'bar', 'pie', 'doughnut', 'line', or 'horizontalBar'"),
                    "title": types.Schema(type="STRING", description="Chart title"),
                    "labels": types.Schema(type="ARRAY", items=types.Schema(type="STRING"), description="Category labels or X-axis labels"),
                    "data": types.Schema(type="ARRAY", items=types.Schema(type="NUMBER"), description="Numeric values corresponding to each label"),
                    "dataset_label": types.Schema(type="STRING", description="Label for the dataset, e.g. 'Number of Leads'"),
                },
                required=["chart_type", "title", "labels", "data", "dataset_label"]
            )
        ),
        types.FunctionDeclaration(
            name="get_analytics_dashboard",
            description=(
                "Get a permission-aware, security-trimmed analytics dashboard for a specific business intent. "
                "Automatically detects who is logged in, their persona (sales_rep / sales_manager / exec / "
                "sales_ops / service_manager / service_agent), what Salesforce data they can see (based on "
                "profiles, permission sets, role hierarchy, OWDs), enforces record-level scope (self/team/global), "
                "and returns KPIs, chart config, and a drill-down table in a structured payload. "
                "ALWAYS call this instead of raw SOQL for: pipeline questions, at-risk deals, today's tasks, "
                "team performance, forecast, inactive accounts, SLA risk cases, data quality."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "intent": types.Schema(
                        type="STRING",
                        description=(
                            "The analytics intent. Allowed values: "
                            "'my_pipeline' (open opportunities, pipeline value, win rate), "
                            "'deals_at_risk' (overdue or stalled opportunities), "
                            "'tasks_today' (tasks due today for the logged-in user), "
                            "'team_performance' (rep leaderboard, pipeline by rep), "
                            "'forecast' (closed won vs open pipeline vs target), "
                            "'no_activity_accounts' (accounts with no activity in 30+ days), "
                            "'sla_risk_cases' (high-priority open cases at SLA risk), "
                            "'data_quality' (missing fields, incomplete records, hygiene issues)"
                        )
                    ),
                    "time_range": types.Schema(
                        type="STRING",
                        description="Salesforce date literal for the time filter. Default 'THIS_QUARTER'. Examples: THIS_QUARTER, THIS_MONTH, THIS_YEAR, LAST_QUARTER, LAST_N_DAYS:30."
                    ),
                },
                required=["intent"]
            )
        ),
        types.FunctionDeclaration(
            name="get_record_all_fields",
            description="Fetch a single record with ALL its fields (standard and custom). Automatically describes the object to discover every field, then queries them all. Use this when the user provides a record ID and asks about any field value (e.g. 'give me the mobile number for this lead').",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(
                        type="STRING",
                        description="The API name of the object, e.g. 'Lead', 'Account', 'Contact'. Infer from the record ID prefix: 00Q=Lead, 001=Account, 003=Contact, 006=Opportunity, 500=Case"
                    ),
                    "record_id": types.Schema(
                        type="STRING",
                        description="The 15 or 18-character Salesforce record ID"
                    )
                },
                required=["object_name", "record_id"]
            )
        ),
        types.FunctionDeclaration(
            name="create_custom_field",
            description="Create a new custom field on a Salesforce object using the Tooling API. Supports field types: Text, Number, Checkbox, Date, DateTime, Email, Phone, Url, Currency, Percent, TextArea, LongTextArea, Picklist. Use this when the user asks to add/create a new field on an object.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(type="STRING", description="The API name of the object to add the field to, e.g. 'Lead', 'Account', 'Contact', or a custom object like 'Invoice__c'"),
                    "field_label": types.Schema(type="STRING", description="The label for the new field, e.g. 'Middle Name', 'Priority Score'. The API name will be auto-generated with __c suffix."),
                    "field_type": types.Schema(type="STRING", description="The field type: 'Text', 'Number', 'Checkbox', 'Date', 'DateTime', 'Email', 'Phone', 'Url', 'Currency', 'Percent', 'TextArea', 'LongTextArea', or 'Picklist'"),
                    "length": types.Schema(type="NUMBER", description="Optional. Length for Text fields (default 255) or LongTextArea (default 32768)"),
                    "precision": types.Schema(type="NUMBER", description="Optional. Precision for Number/Currency/Percent fields (total digits, default 18)"),
                    "scale": types.Schema(type="NUMBER", description="Optional. Scale for Number/Currency/Percent fields (decimal places, default 0 for Number, 2 for Currency/Percent)"),
                    "picklist_values": types.Schema(type="ARRAY", items=types.Schema(type="STRING"), description="Optional. List of picklist values, required when field_type is 'Picklist'"),
                    "description": types.Schema(type="STRING", description="Optional description/help text for the field"),
                    "required": types.Schema(type="BOOLEAN", description="Optional. Whether the field is required (default false)")
                },
                required=["object_name", "field_label", "field_type"]
            )
        ),
        types.FunctionDeclaration(
            name="delete_custom_field",
            description="Delete a custom field from a Salesforce object using the Tooling API. Only custom fields (ending in __c) can be deleted. Use this when the user asks to remove/delete a custom field.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(type="STRING", description="The API name of the object the field belongs to, e.g. 'Lead', 'Account'"),
                    "field_name": types.Schema(type="STRING", description="The API name of the custom field to delete, e.g. 'Middle_Name__c' or 'Middle_Name' (the __c suffix will be added automatically if missing)")
                },
                required=["object_name", "field_name"]
            )
        ),
        types.FunctionDeclaration(
            name="analyze_field_data",
            description="Fetch raw text data from a specific field across multiple records for AI-powered analysis. Use this when the user asks analytical questions about text/long text fields like 'What are the top pain points?', 'Summarize insights', 'Common themes in feedback', 'Analyze descriptions', etc. The tool fetches the raw text values, then YOU (the AI) analyze them to extract themes, patterns, keywords, sentiments, and insights. ALWAYS use this instead of saying 'I cannot analyze text fields'.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(type="STRING", description="The API name of the Salesforce object, e.g. 'Lead', 'Case', 'Account', 'Opportunity'"),
                    "field_name": types.Schema(type="STRING", description="The API name of the text field to analyze, e.g. 'Sales_Insight__c', 'Description', 'Comments__c'. Use describe_object first if unsure."),
                    "where_clause": types.Schema(type="STRING", description="Optional SOQL WHERE clause to filter records, e.g. \"Status = 'Open'\" or \"CreatedDate = THIS_YEAR\". Do NOT include the WHERE keyword itself."),
                    "limit": types.Schema(type="NUMBER", description="Optional max records to fetch (default 200). Use higher for broader analysis, lower for quick summaries.")
                },
                required=["object_name", "field_name"]
            )
        ),
        types.FunctionDeclaration(
            name="check_calendar",
            description="Check the user's Salesforce calendar (Events) for a given date range. Returns existing events and available free time slots during business hours (9 AM - 5 PM). Use this when the user asks to book a meeting, schedule a call, check availability, or suggest times. ALWAYS check the calendar before booking to avoid conflicts.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "date": types.Schema(type="STRING", description="The date to check in YYYY-MM-DD format. Defaults to today if not specified."),
                    "days_ahead": types.Schema(type="NUMBER", description="Number of days to check from the start date (default 1). Use 2-3 for 'this week' or multi-day availability.")
                },
                required=[]
            )
        ),
        types.FunctionDeclaration(
            name="book_meeting",
            description="Book a meeting or call by creating an Event in Salesforce. Links the event to a Lead or Contact using their record ID. ALWAYS check_calendar first to suggest available times and avoid conflicts.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "subject": types.Schema(type="STRING", description="Meeting subject/title, e.g. 'Call with John Smith', 'Demo meeting', 'Follow-up call'"),
                    "start_datetime": types.Schema(type="STRING", description="Start date and time in ISO format, e.g. '2026-03-24T10:00:00'. Must be a specific date and time."),
                    "duration_minutes": types.Schema(type="NUMBER", description="Meeting duration in minutes (default 30). Common values: 15, 30, 45, 60."),
                    "who_id": types.Schema(type="STRING", description="The Salesforce record ID of the Lead (00Q...) or Contact (003...) this meeting is with."),
                    "description": types.Schema(type="STRING", description="Optional meeting description or agenda."),
                    "location": types.Schema(type="STRING", description="Optional meeting location (e.g. 'Zoom', 'Office', phone number).")
                },
                required=["subject", "start_datetime"]
            )
        ),
        types.FunctionDeclaration(
            name="render_create_form",
            description=(
                "Render an interactive creation form in the chat UI for a Salesforce object (Lead, Account, Contact, Opportunity, etc.). "
                "Use this INSTEAD of create_record when the user asks to 'create a new lead', 'add an account', 'create a contact', etc. "
                "and does NOT provide all the field values upfront. The form lets the user fill in fields and submit directly from the chat. "
                "If the user already provides ALL required field values in their message, use create_record directly instead."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(
                        type="STRING",
                        description="The Salesforce object API name to create. E.g. 'Lead', 'Account', 'Contact', 'Opportunity'"
                    ),
                },
                required=["object_name"]
            )
        ),
        types.FunctionDeclaration(
            name="render_update_form",
            description=(
                "Render an interactive UPDATE form in the chat UI for an existing Salesforce record. "
                "The form is pre-populated with the record's current field values so the user can see "
                "what was previously entered and edit any fields. Use this when the user asks to "
                "'update a lead', 'edit this account', 'modify the record', etc. "
                "You MUST provide the record_id of the record to update."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(
                        type="STRING",
                        description="The Salesforce object API name. E.g. 'Lead', 'Account', 'Contact', 'Opportunity'"
                    ),
                    "record_id": types.Schema(
                        type="STRING",
                        description="The Salesforce record ID (e.g. '00Q...' for Lead, '001...' for Account)"
                    ),
                },
                required=["object_name", "record_id"]
            )
        ),
    ])
]


# Global list to collect chart configs during a single request
_pending_charts = []
# Global list to collect A2UI surface messages during a single request
_pending_a2ui_surfaces = []

_chart_surface_counter = 0

# ── OTP Pending Operations Store ─────────────────────────────
# Stores operations waiting for OTP verification:
# { session_key: { "operation": "update"|"delete", "object_name": ..., "record_id": ..., "field_values": ... } }
_pending_operations = {}


def _build_a2ui_chart_surface(chart_config):
    """Build A2UI v0.8 messages for a chart surface."""
    global _chart_surface_counter
    _chart_surface_counter += 1
    surface_id = f"chart-surface-{_chart_surface_counter}"

    messages = [
        {
            "surfaceId": surface_id,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "root",
                        "component": {
                            "Column": {
                                "children": {"explicitList": ["chart_component"]}
                            }
                        }
                    },
                    {
                        "id": "chart_component",
                        "component": {
                            "Chart": {
                                "chartType": {"literalString": chart_config["chart_type"]},
                                "title": {"literalString": chart_config["title"]},
                                "labels": [{"literalString": str(l)} for l in chart_config["labels"]],
                                "data": [{"literalNumber": d} for d in chart_config["data"]],
                                "datasetLabel": {"literalString": chart_config["dataset_label"]},
                            }
                        }
                    }
                ]
            }
        },
        {
            "surfaceId": surface_id,
            "dataModelUpdate": {"contents": {}}
        },
        {
            "surfaceId": surface_id,
            "beginRendering": {"root": "root"}
        }
    ]
    return messages


def _build_a2ui_kpi_surface(kpis: list, summary: str, meta: dict) -> list:
    """Build an A2UI surface containing KPI StatsCards + a metadata footer."""
    global _chart_surface_counter
    _chart_surface_counter += 1
    surface_id = f"kpi-surface-{_chart_surface_counter}"

    # Build component list: one StatsCard per KPI
    components = [
        {
            "id": "root",
            "component": {
                "Column": {
                    "gap": 12,
                    "children": {"explicitList": ["kpi_row"] + (["meta_text"] if meta else [])}
                }
            }
        },
        {
            "id": "kpi_row",
            "component": {
                "Row": {
                    "gap": 12,
                    "children": {"explicitList": [f"kpi_{i}" for i in range(len(kpis))]}
                }
            }
        },
    ]

    for i, kpi in enumerate(kpis):
        value = kpi.get("value", 0)
        unit  = kpi.get("unit", "")
        color = kpi.get("color", "#6366f1")

        # Format value nicely
        if unit == "currency":
            if value >= 1_000_000:
                display_val = f"{value/1_000_000:.1f}M"
            elif value >= 1_000:
                display_val = f"{value/1_000:.1f}K"
            else:
                display_val = f"{value:,.0f}" if isinstance(value, (int, float)) else str(value)
        elif unit == "%":
            display_val = f"{value}%"
        else:
            display_val = str(value)

        components.append({
            "id": f"kpi_{i}",
            "component": {
                "StatsCard": {
                    "label": {"literalString": kpi.get("label", "")},
                    "value": {"literalString": display_val},
                    "color": color,
                }
            }
        })

    if meta:
        data_as_of = meta.get("dataAsOf", "")
        note = meta.get("note", "")
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(data_as_of.replace("Z", "+00:00"))
            data_as_of = dt.strftime("%d %b %Y, %I:%M %p UTC")
        except Exception:
            pass
        meta_text = f"{note} · Refreshed {data_as_of}"
        components.append({
            "id": "meta_text",
            "component": {
                "Text": {
                    "text": {"literalString": meta_text},
                    "usageHint": "caption",
                }
            }
        })

    messages = [
        {
            "surfaceId": surface_id,
            "surfaceUpdate": {"components": components}
        },
        {
            "surfaceId": surface_id,
            "dataModelUpdate": {"contents": {}}
        },
        {
            "surfaceId": surface_id,
            "beginRendering": {"root": "root"}
        }
    ]
    return messages


# ── Form Schemas per Object (A2UI Component Definitions) ─────
# Each field maps to an A2UI component: TextField, DropDown, RadioGroup, DateTimeInput
# 'path' is used for form state binding, 'sfField' maps to Salesforce API name
_FORM_SCHEMAS = {
    "Lead": {
        "title": "New Lead",
        "pathPrefix": "/lead",
        "fields": [
            {"id": "fname",    "component": "TextField",     "label": "First Name",     "path": "/lead/firstName",   "sfField": "FirstName"},
            {"id": "lname",    "component": "TextField",     "label": "Last Name",      "path": "/lead/lastName",    "sfField": "LastName",      "required": True},
            {"id": "company",  "component": "TextField",     "label": "Company",        "path": "/lead/company",     "sfField": "Company",       "required": True},
            {"id": "currency", "component": "DropDown",      "label": "Lead Currency",  "path": "/lead/currency",    "sfField": "CurrencyIsoCode",
             "options": ["EUR", "USD"]},
            {"id": "status",   "component": "DropDown",      "label": "Lead Status",    "path": "/lead/status",      "sfField": "Status",        "required": True,
             "options": ["Open - Not Contacted", "Working - Contacted", "Closed - Converted", "Closed - Not Converted"]},
        ],
        "submitLabel": "Create Lead",
        "submitAction": "createLead",
    },
    "Account": {
        "title": "New Account",
        "pathPrefix": "/account",
        "fields": [
            {"id": "name",     "component": "TextField",     "label": "Account Name",    "path": "/account/name",     "sfField": "Name",            "required": True},
            {"id": "currency", "component": "DropDown",      "label": "Account Currency", "path": "/account/currency", "sfField": "CurrencyIsoCode", "required": True,
             "options": ["EUR", "USD", "GBP", "INR", "JPY", "AUD", "CAD", "CHF", "CNY", "SGD"]},
        ],
        "submitLabel": "Create Account",
        "submitAction": "createAccount",
    },
    "Contact": {
        "title": "New Contact",
        "pathPrefix": "/contact",
        "fields": [
            {"id": "fname",    "component": "TextField",     "label": "First Name",     "path": "/contact/firstName","sfField": "FirstName"},
            {"id": "lname",    "component": "TextField",     "label": "Last Name",      "path": "/contact/lastName", "sfField": "LastName",      "required": True},
            {"id": "email",    "component": "TextField",     "label": "Email",          "path": "/contact/email",    "sfField": "Email",         "inputType": "email"},
            {"id": "phone",    "component": "TextField",     "label": "Phone",          "path": "/contact/phone",    "sfField": "Phone",         "inputType": "tel"},
            {"id": "title",    "component": "TextField",     "label": "Title",          "path": "/contact/title",    "sfField": "Title"},
            {"id": "dept",     "component": "TextField",     "label": "Department",     "path": "/contact/dept",     "sfField": "Department"},
        ],
        "submitLabel": "Create Contact",
        "submitAction": "createContact",
    },
    "Opportunity": {
        "title": "New Opportunity",
        "pathPrefix": "/opp",
        "fields": [
            {"id": "name",     "component": "TextField",     "label": "Opportunity Name","path": "/opp/name",        "sfField": "Name",          "required": True},
            {"id": "closedate","component": "DateTimeInput",  "label": "Close Date",     "path": "/opp/closeDate",   "sfField": "CloseDate",     "required": True},
            {"id": "stage",    "component": "DropDown",      "label": "Stage",          "path": "/opp/stage",        "sfField": "StageName",     "required": True,
             "options": ["Prospecting", "Qualification", "Needs Analysis", "Value Proposition", "Id. Decision Makers", "Perception Analysis", "Proposal/Price Quote", "Negotiation/Review", "Closed Won", "Closed Lost"]},
            {"id": "amount",   "component": "TextField",     "label": "Amount",         "path": "/opp/amount",       "sfField": "Amount",        "inputType": "number"},
            {"id": "type",     "component": "DropDown",      "label": "Type",           "path": "/opp/type",         "sfField": "Type",
             "options": ["Existing Customer - Upgrade", "Existing Customer - Replacement", "Existing Customer - Downgrade", "New Customer"]},
        ],
        "submitLabel": "Create Opportunity",
        "submitAction": "createOpportunity",
    },
}


def _build_a2ui_form_surface(object_name: str, mode: str = "create", record_id: str = None, prefill: dict = None) -> list:
    """Build an A2UI surface with TextField, DropDown, RadioGroup, DateTimeInput, and
    Button components following the A2UI v0.8 spec.
    
    Args:
        object_name: Salesforce object API name (Lead, Account, etc.)
        mode: 'create' or 'update'
        record_id: Salesforce record ID (required for update)
        prefill: Dict of {SF_field_api_name: value} to pre-populate fields
    """
    global _chart_surface_counter
    _chart_surface_counter += 1
    surface_id = f"form-surface-{_chart_surface_counter}"

    schema = _FORM_SCHEMAS.get(object_name)
    if not schema:
        # Fallback: minimal form
        schema = {
            "title": f"New {object_name}",
            "pathPrefix": f"/{object_name.lower()}",
            "fields": [
                {"id": "name", "component": "TextField", "label": "Name",
                 "path": f"/{object_name.lower()}/name", "sfField": "Name", "required": True},
            ],
            "submitLabel": f"Create {object_name}",
            "submitAction": f"create{object_name}",
        }

    # Override title and button label for update mode
    if mode == "update":
        title = f"Update {object_name}"
        submit_label = f"Update {object_name}"
        submit_action = f"update{object_name}"
    else:
        title = schema["title"]
        submit_label = schema["submitLabel"]
        submit_action = schema["submitAction"]

    fields = schema["fields"]
    field_ids = [f["id"] for f in fields]
    all_child_ids = ["title"] + field_ids + ["submit"]

    # Build field mapping  { path -> SF API name }
    field_mapping = {}
    required_paths = []
    for f in fields:
        field_mapping[f["path"]] = f["sfField"]
        if f.get("required"):
            required_paths.append(f["path"])

    # ── Build components list ──
    components = [
        # Root Card (gives the form a premium card treatment)
        {
            "id": "root",
            "component": {
                "Card": {
                    "elevation": 2,
                    "children": {"explicitList": ["inner_col"]}
                }
            }
        },
        # Inner Column (holds title + fields + button)
        {
            "id": "inner_col",
            "component": {
                "Column": {
                    "gap": 16,
                    "children": {"explicitList": all_child_ids}
                }
            }
        },
        # Title Text
        {
            "id": "title",
            "component": {
                "Text": {
                    "text": {"literalString": title},
                    "usageHint": "h1",
                }
            }
        },
    ]

    # ── Field components ──
    for f in fields:
        comp_type = f["component"]
        comp_props = {}

        if comp_type == "TextField":
            comp_props = {
                "label": {"literalString": f["label"]},
                "path": f["path"],
                "placeholder": {"literalString": f.get("placeholder", "")},
            }
            if f.get("inputType"):
                comp_props["inputType"] = f["inputType"]
            if f.get("required"):
                comp_props["required"] = True

        elif comp_type == "DropDown":
            comp_props = {
                "label": {"literalString": f["label"]},
                "path": f["path"],
                "options": [{"literalString": opt} for opt in f.get("options", [])],
            }
            if f.get("required"):
                comp_props["required"] = True

        elif comp_type == "RadioGroup":
            comp_props = {
                "label": {"literalString": f["label"]},
                "path": f["path"],
                "options": [{"literalString": opt} for opt in f.get("options", [])],
            }

        elif comp_type == "DateTimeInput":
            comp_props = {
                "label": {"literalString": f["label"]},
                "path": f["path"],
            }
            if f.get("required"):
                comp_props["required"] = True

        components.append({
            "id": f["id"],
            "component": {comp_type: comp_props}
        })

    # ── Submit Button ──
    components.append({
        "id": "submit",
        "component": {
            "Button": {
                "label": {"literalString": submit_label},
                "action": {
                    "name": submit_action,
                    "dataBindings": [schema["pathPrefix"]],
                }
            }
        }
    })

    # ── Build _initialValues from prefill ──
    initial_values = {}
    if prefill:
        # Reverse map: SF field name -> path
        sf_to_path = {v: k for k, v in field_mapping.items()}
        for sf_field, value in prefill.items():
            if sf_field in sf_to_path and value is not None:
                initial_values[sf_to_path[sf_field]] = value

    # ── Build the 3-part A2UI message sequence ──
    data_model_contents = {
        "_formConfig": {
            "objectName": object_name,
            "fieldMapping": field_mapping,
            "requiredFields": required_paths,
            "mode": mode,
        }
    }
    if record_id:
        data_model_contents["_formConfig"]["recordId"] = record_id
    if initial_values:
        data_model_contents["_initialValues"] = initial_values

    # ── Build the 3-part A2UI message sequence ──
    messages = [
        {
            "surfaceId": surface_id,
            "surfaceUpdate": {"components": components}
        },
        {
            "surfaceId": surface_id,
            "dataModelUpdate": {
                "contents": data_model_contents
            }
        },
        {
            "surfaceId": surface_id,
            "beginRendering": {"root": "root"}
        }
    ]
    return messages




def _get_record_email(sf, object_name, record_id):
    """Fetch the email for OTP verification.

    Resolution chain:
    - Lead / Contact / Case → direct Email field
    - Account → find the primary Contact linked to the Account → use Contact.Email
    - Opportunity → find the related Account → find linked Contact → use Contact.Email
    - Other objects → try Email field, then fallback to SF_USERNAME
    """
    # Objects with a direct Email field
    DIRECT_EMAIL_OBJECTS = {"Lead", "Contact", "Case", "CampaignMember"}

    try:
        # ── 1. Direct Email field (Lead, Contact, Case, etc.) ──
        if object_name in DIRECT_EMAIL_OBJECTS:
            soql = f"SELECT Email FROM {object_name} WHERE Id = '{record_id}' LIMIT 1"
            result = sf.run_soql(soql)
            if "error" not in result:
                records = result.get("records", [])
                if records and records[0].get("Email"):
                    email = records[0]["Email"]
                    print(f"  [OTP] Found {object_name} email: {email}")
                    return email

        # ── 2. Account → find linked Contact's email ──
        elif object_name == "Account":
            soql = f"SELECT Id, Email FROM Contact WHERE AccountId = '{record_id}' AND Email != null ORDER BY CreatedDate ASC LIMIT 1"
            result = sf.run_soql(soql)
            if "error" not in result:
                records = result.get("records", [])
                if records and records[0].get("Email"):
                    email = records[0]["Email"]
                    print(f"  [OTP] Found Contact email for Account: {email}")
                    return email

        # ── 3. Opportunity → Account → linked Contact's email ──
        elif object_name == "Opportunity":
            # First get the AccountId from the Opportunity
            soql = f"SELECT AccountId FROM Opportunity WHERE Id = '{record_id}' LIMIT 1"
            result = sf.run_soql(soql)
            if "error" not in result:
                records = result.get("records", [])
                account_id = records[0].get("AccountId") if records else None
                if account_id:
                    # Now find a Contact linked to that Account
                    soql2 = f"SELECT Id, Email FROM Contact WHERE AccountId = '{account_id}' AND Email != null ORDER BY CreatedDate ASC LIMIT 1"
                    result2 = sf.run_soql(soql2)
                    if "error" not in result2:
                        records2 = result2.get("records", [])
                        if records2 and records2[0].get("Email"):
                            email = records2[0]["Email"]
                            print(f"  [OTP] Found Contact email for Opportunity→Account: {email}")
                            return email

        # ── 4. Other objects → try Email field if it exists ──
        else:
            try:
                desc = sf.describe(object_name)
                field_names = [f.get("name") for f in desc.get("fields", [])]
                if "Email" in field_names:
                    soql = f"SELECT Email FROM {object_name} WHERE Id = '{record_id}' LIMIT 1"
                    result = sf.run_soql(soql)
                    if "error" not in result:
                        records = result.get("records", [])
                        if records and records[0].get("Email"):
                            email = records[0]["Email"]
                            print(f"  [OTP] Found {object_name} email: {email}")
                            return email
            except Exception:
                pass

    except Exception as e:
        print(f"  [OTP] Could not fetch email for {object_name} {record_id}: {e}")

    # Fallback to Salesforce user email
    print(f"  [OTP] No email found in chain, falling back to {SF_USERNAME}")
    return SF_USERNAME


def handle_function_call(function_call, sf):
    global _pending_charts, _pending_a2ui_surfaces, _pending_operations
    name = function_call.name
    args = function_call.args or {}

    if name == "run_soql_query":
        return sf.run_soql(args.get("query", ""))
    elif name == "run_sosl_search":
        return sf.run_sosl(args.get("search", ""))
    elif name == "list_org_objects":
        return sf.list_objects()
    elif name == "describe_object":
        return sf.describe(args.get("object_name", ""))
    elif name == "create_record":
        return sf.create_record(args.get("object_name", ""), dict(args.get("field_values", {})))
    elif name == "update_record":
        # ── OTP GATE: Intercept update and require verification ──
        obj_name = args.get("object_name", "")
        record_id = args.get("record_id", "")
        field_values = dict(args.get("field_values", {}))
        session_key = f"update_{obj_name}_{record_id}_{uuid.uuid4().hex[:8]}"
        operation_summary = f"Update {obj_name} record ({record_id}): {json.dumps(field_values)}"

        # Store pending operation
        _pending_operations[session_key] = {
            "operation": "update",
            "object_name": obj_name,
            "record_id": record_id,
            "field_values": field_values,
        }

        # Send OTP to the record's registered email
        recipient_email = _get_record_email(sf, obj_name, record_id)
        otp_result = create_and_send_otp(sf.auth, recipient_email, session_key, operation_summary)

        if "error" in otp_result:
            _pending_operations.pop(session_key, None)
            return {"error": f"OTP verification failed to initiate: {otp_result['error']}"}

        return {
            "otp_required": True,
            "session_key": session_key,
            "message": f"⚠️ Security verification required. A verification code has been sent to {recipient_email}. Please enter the code to authorize this update.",
            "operation": "update",
            "object": obj_name,
            "record_id": record_id,
        }

    elif name == "delete_record":
        # ── OTP GATE: Intercept delete and require verification ──
        obj_name = args.get("object_name", "")
        record_id = args.get("record_id", "")
        session_key = f"delete_{obj_name}_{record_id}_{uuid.uuid4().hex[:8]}"
        operation_summary = f"Delete {obj_name} record ({record_id})"

        # Store pending operation
        _pending_operations[session_key] = {
            "operation": "delete",
            "object_name": obj_name,
            "record_id": record_id,
        }

        # Send OTP to the record's registered email
        recipient_email = _get_record_email(sf, obj_name, record_id)
        otp_result = create_and_send_otp(sf.auth, recipient_email, session_key, operation_summary)

        if "error" in otp_result:
            _pending_operations.pop(session_key, None)
            return {"error": f"OTP verification failed to initiate: {otp_result['error']}"}

        return {
            "otp_required": True,
            "session_key": session_key,
            "message": f"⚠️ Security verification required. A verification code has been sent to {recipient_email}. Please enter the code to authorize this deletion.",
            "operation": "delete",
            "object": obj_name,
            "record_id": record_id,
        }
    elif name == "generate_chart":
        chart_config = {
            "chart_type": args.get("chart_type", "bar"),
            "title": args.get("title", "Chart"),
            "labels": list(args.get("labels", [])),
            "data": [float(x) for x in args.get("data", [])],
            "dataset_label": args.get("dataset_label", "Count"),
        }
        _pending_charts.append(chart_config)

        # NOTE: Charts are rendered via the 'charts' pipeline in the frontend.
        # Do NOT also add to _pending_a2ui_surfaces — that causes duplicate
        # empty chart boxes (the second canvas never initialises properly).

        print(f"  [CHART] Generated {chart_config['chart_type']} chart: {chart_config['title']}")
        return {"status": "rendered", "_instruction": "The chart is automatically displayed to the user in the UI. Do NOT mention this tool response or show any JSON to the user. Instead, briefly describe the data insights or trends visible in the chart."}

    elif name == "get_analytics_dashboard":
        intent = args.get("intent", "my_pipeline")
        time_range = args.get("time_range", "THIS_QUARTER")
        print(f"  [ANALYTICS] Building dashboard: intent={intent}, time_range={time_range}")

        try:
            engine = _get_permission_engine()
            viewer_ctx = get_cached_viewer_context()
            payload = engine.build_analytics_payload(
                viewer_ctx=viewer_ctx,
                intent=intent,
                sf_conn=sf,
                time_range=time_range,
            )

            # Auto-render the chart from the payload
            if payload.get("chart") and payload["chart"].get("labels"):
                chart_cfg = payload["chart"]
                chart_config = {
                    "chart_type": chart_cfg.get("type", "bar"),
                    "title":      chart_cfg.get("title", intent),
                    "labels":     [str(l) for l in chart_cfg.get("labels", [])],
                    "data":       [float(d) for d in chart_cfg.get("data", [])],
                    "dataset_label": chart_cfg.get("dataset_label", "Count"),
                }
                _pending_charts.append(chart_config)
                # Chart is rendered via 'charts' pipeline — do NOT duplicate in a2ui_surfaces

            # Auto-render KPI cards as A2UI surface
            kpis = payload.get("kpis", [])
            if kpis:
                kpi_surface_messages = _build_a2ui_kpi_surface(kpis, payload.get("summary", ""), payload.get("meta", {}))
                _pending_a2ui_surfaces.append(kpi_surface_messages)

            print(f"  [ANALYTICS] Dashboard built: {len(kpis)} KPIs, chart={bool(payload.get('chart'))}, {len((payload.get('table') or {}).get('rows', []))} rows")
            return payload

        except Exception as e:
            print(f"  [ANALYTICS] Error: {e}")
            return {"error": str(e)}
    elif name == "get_record_all_fields":
        obj_name = args.get("object_name", "")
        record_id = args.get("record_id", "")
        print(f"  [Fetching ALL fields for {obj_name} {record_id}...]")
        result = sf.get_all_fields_for_record(obj_name, record_id)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Got {result['field_count']} fields for {record_id}]")
        return result
    elif name == "create_custom_field":
        obj_name = args.get("object_name", "")
        field_label = args.get("field_label", "")
        field_type = args.get("field_type", "Text")
        print(f"  [Creating custom field '{field_label}' ({field_type}) on {obj_name}...]")
        result = sf.create_custom_field(
            object_name=obj_name,
            field_label=field_label,
            field_type=field_type,
            length=args.get("length"),
            precision=args.get("precision"),
            scale=args.get("scale"),
            picklist_values=args.get("picklist_values"),
            description=args.get("description"),
            required=args.get("required", False)
        )
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Created field: {result['field_api_name']} on {obj_name}]")
        return result
    elif name == "delete_custom_field":
        obj_name = args.get("object_name", "")
        field_name = args.get("field_name", "")
        print(f"  [Deleting custom field '{field_name}' from {obj_name}...]")
        result = sf.delete_custom_field(obj_name, field_name)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Deleted field: {result['field_api_name']} from {obj_name}]")
        return result
    elif name == "analyze_field_data":
        obj_name = args.get("object_name", "")
        field_name = args.get("field_name", "")
        where_clause = args.get("where_clause")
        limit = int(args.get("limit", 200))
        print(f"  [Analyzing '{field_name}' from {obj_name} (limit={limit})...]")
        result = sf.analyze_field_data(obj_name, field_name, where_clause=where_clause, limit=limit)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Fetched {result['total_records_with_data']} values for analysis]")
        return result
    elif name == "check_calendar":
        date_str = args.get("date")
        days_ahead = int(args.get("days_ahead", 1))
        print(f"  [Checking calendar for {date_str or 'today'}, {days_ahead} day(s)...]")
        result = sf.check_calendar(date_str=date_str, days_ahead=days_ahead)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Found {result['event_count']} events, {len(result['free_slots'])} free slots]")
        return result
    elif name == "book_meeting":
        subject = args.get("subject", "Meeting")
        start_datetime = args.get("start_datetime", "")
        duration_minutes = int(args.get("duration_minutes", 30))
        who_id = args.get("who_id")
        description = args.get("description")
        location = args.get("location")
        print(f"  [Booking meeting: '{subject}' at {start_datetime}, {duration_minutes}min]")
        result = sf.book_meeting(
            subject=subject,
            start_datetime=start_datetime,
            duration_minutes=duration_minutes,
            who_id=who_id,
            description=description,
            location=location
        )
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Booked: {result['event_id']}]")
        return result
    elif name == "render_create_form":
        obj_name = args.get("object_name", "Lead")
        print(f"  [FORM] Rendering create form for {obj_name}")
        form_surface = _build_a2ui_form_surface(obj_name)
        _pending_a2ui_surfaces.append(form_surface)
        return {
            "status": "rendered",
            "_instruction": (
                f"An interactive {obj_name} creation form has been rendered in the chat UI. "
                f"Do NOT describe each field or repeat the form contents. Just tell the user briefly: "
                f"'Here's a form to create a new {obj_name}. Fill in the details and click the button to create it in Salesforce.' "
                f"Keep your response under 30 words."
            )
        }
    elif name == "render_update_form":
        obj_name = args.get("object_name", "Lead")
        record_id = args.get("record_id", "")
        print(f"  [FORM] Rendering update form for {obj_name} {record_id}")

        if not record_id:
            return {"error": "record_id is required for render_update_form."}

        # Fetch current field values to pre-populate the form
        prefill = {}
        try:
            schema = _FORM_SCHEMAS.get(obj_name)
            if schema:
                # Only fetch fields that are in the form schema
                sf_fields = [f["sfField"] for f in schema["fields"]]
                field_csv = ", ".join(sf_fields)
                soql = f"SELECT {field_csv} FROM {obj_name} WHERE Id = '{record_id}' LIMIT 1"
                print(f"  [FORM] Fetching current values: {soql}")
                result = sf.run_soql(soql)
                if "error" not in result and result.get("records"):
                    record = result["records"][0]
                    prefill = {k: v for k, v in record.items() if v is not None}
                    print(f"  [FORM] Pre-fill data: {json.dumps(prefill)}")
                else:
                    print(f"  [FORM] Could not fetch record, form will render empty")
            else:
                # No schema — try to get all fields
                all_fields_result = sf.get_all_fields_for_record(obj_name, record_id)
                if "error" not in all_fields_result and all_fields_result.get("record"):
                    prefill = {k: v for k, v in all_fields_result["record"].items() if v is not None}
        except Exception as e:
            print(f"  [FORM] Error fetching prefill data: {e}")

        form_surface = _build_a2ui_form_surface(
            obj_name, mode="update", record_id=record_id, prefill=prefill
        )
        _pending_a2ui_surfaces.append(form_surface)
        return {
            "status": "rendered",
            "_instruction": (
                f"An interactive {obj_name} update form has been rendered in the chat UI, "
                f"pre-populated with the record's current values. "
                f"Do NOT describe each field or repeat the form contents. Just tell the user briefly: "
                f"'Here's the update form for this {obj_name} — current values are pre-filled. "
                f"Edit what you need and click Update to save.' "
                f"Keep your response under 30 words."
            )
        }
    return {"error": f"Unknown function: {name}"}


# ── Initialize ───────────────────────────────────────────────

print("Loading Salesforce skill knowledge...")
knowledge = load_skill_files()
print(f"  Loaded {len(knowledge)} knowledge files")

print("Loading enterprise skill registry...")
skill_registry = load_skill_registry()
print(f"  Discovered {len(skill_registry)} enterprise skills:")
for s in skill_registry:
    print(f"    • {s['name']}")

system_prompt = build_system_prompt(knowledge, skill_registry)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Connect to Salesforce
sf = SalesforceConnection()
try:
    instance_url = sf.connect()
    print(f"  Connected to Salesforce: {instance_url}")
    # Warm up viewer context cache immediately after connection
    try:
        _engine = _get_permission_engine()
        _viewer_context_cache = _engine.get_viewer_context(sf)
        import time as _time
        _viewer_context_fetched_at = _time.time()
        print(f"  [PERM] Viewer: {_viewer_context_cache.get('full_name', '?')} | persona={_viewer_context_cache.get('persona')} | scope={_viewer_context_cache.get('scope')}")
    except Exception as _ve:
        print(f"  [PERM] Viewer context warmup skipped: {_ve}")
except Exception as e:
    print(f"  Salesforce connection failed: {e}")
    instance_url = "Not connected"

# Conversation history (per-session, single user for now)
conversation_history = []
MAX_HISTORY_TURNS = 20  # keep last N turns to avoid context bloat
MAX_RECORDS_TO_MODEL = 50  # cap records sent back to Gemini


def trim_history():
    """Keep conversation_history to a reasonable size."""
    global conversation_history
    if len(conversation_history) > MAX_HISTORY_TURNS * 2:
        conversation_history = conversation_history[-(MAX_HISTORY_TURNS * 2):]


def truncate_result(result):
    """Cap the number of records sent back to Gemini to avoid massive echoed output."""
    if isinstance(result, dict) and "records" in result:
        records = result["records"]
        total = result.get("count", len(records))
        if len(records) > MAX_RECORDS_TO_MODEL:
            result = {
                **result,
                "records": records[:MAX_RECORDS_TO_MODEL],
                "count": total,
                "note": f"Showing first {MAX_RECORDS_TO_MODEL} of {total} records. Inform the user about the total count.",
            }
    return result


# ── Routes ───────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


# ── OTP Verification Endpoints ───────────────────────────────

@app.route("/api/otp/verify", methods=["POST"])
def otp_verify():
    """Verify OTP and execute the pending operation if valid."""
    global _pending_operations

    data = request.json
    session_key = data.get("session_key", "")
    user_otp = data.get("otp", "")

    if not session_key or not user_otp:
        return jsonify({"error": "Missing session_key or otp."}), 400

    # Verify the OTP
    result = verify_otp(session_key, user_otp)

    if not result.get("verified"):
        return jsonify({
            "verified": False,
            "error": result.get("error", "Verification failed.")
        })

    # OTP verified — execute the pending operation
    pending = _pending_operations.pop(session_key, None)
    if not pending:
        return jsonify({"error": "Pending operation not found or already executed."}), 404

    operation = pending["operation"]
    obj_name = pending["object_name"]
    record_id = pending["record_id"]

    try:
        if operation == "update":
            field_values = pending.get("field_values", {})
            sf.update_record(obj_name, record_id, field_values)
            # Also add to conversation history so the AI knows
            conversation_history.append(
                types.Content(role="user", parts=[types.Part(text=f"[SYSTEM: OTP verified. {obj_name} record {record_id} has been updated successfully with fields: {json.dumps(field_values)}]")])
            )
            return jsonify({
                "verified": True,
                "success": True,
                "message": f"✅ Verified! {obj_name} record ({record_id}) updated successfully.",
                "operation": operation,
                "object": obj_name,
                "record_id": record_id,
            })
        elif operation == "delete":
            sf.delete_record(obj_name, record_id)
            conversation_history.append(
                types.Content(role="user", parts=[types.Part(text=f"[SYSTEM: OTP verified. {obj_name} record {record_id} has been deleted successfully.]")])
            )
            return jsonify({
                "verified": True,
                "success": True,
                "message": f"✅ Verified! {obj_name} record ({record_id}) deleted successfully.",
                "operation": operation,
                "object": obj_name,
                "record_id": record_id,
            })
        else:
            return jsonify({"error": f"Unknown operation: {operation}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/otp/resend", methods=["POST"])
def otp_resend():
    """Resend OTP for a pending operation."""
    data = request.json
    session_key = data.get("session_key", "")

    if not session_key:
        return jsonify({"error": "Missing session_key."}), 400

    pending = _pending_operations.get(session_key)
    if not pending:
        return jsonify({"error": "No pending operation found. Please retry the original operation."}), 404

    operation = pending["operation"]
    obj_name = pending["object_name"]
    record_id = pending["record_id"]
    field_values = pending.get("field_values", {})

    if operation == "update":
        operation_summary = f"Update {obj_name} record ({record_id}): {json.dumps(field_values)}"
    else:
        operation_summary = f"Delete {obj_name} record ({record_id})"

    recipient_email = SF_USERNAME
    otp_result = create_and_send_otp(sf.auth, recipient_email, session_key, operation_summary)

    if "error" in otp_result:
        return jsonify({"error": otp_result["error"]}), 500

    return jsonify({
        "success": True,
        "message": f"A new verification code has been sent to {recipient_email}."
    })



@app.route("/api/viewer-context")
def viewer_context_route():
    """Return the current viewer's permission context (persona, scope, allowed objects)."""
    ctx = get_cached_viewer_context()
    # Strip internal-only fields before sending to frontend
    safe_ctx = {
        "persona":          ctx.get("persona", "sales_rep"),
        "full_name":        ctx.get("full_name", ""),
        "email":            ctx.get("email", ""),
        "profile_name":     ctx.get("profile_name", ""),
        "role_name":        ctx.get("role_name", ""),
        "scope":            ctx.get("scope", "self"),
        "currency":         ctx.get("currency", "USD"),
        "timezone":         ctx.get("timezone", "UTC"),
        "allowed_objects":  ctx.get("allowed_objects", []),
        "restricted_objects": ctx.get("restricted_objects", []),
        "can_view_all_data":(ctx.get("can_view_all_data", False)),
        "error":            ctx.get("error"),
    }
    return jsonify(safe_ctx)


@app.route("/api/create-record-form", methods=["POST"])
def create_record_form():
    """Create a Salesforce record from an A2UI form submission."""
    data = request.json
    obj_name = data.get("object_name", "")
    field_values = data.get("field_values", {})

    if not obj_name:
        return jsonify({"error": "Missing object_name."}), 400
    if not field_values:
        return jsonify({"error": "No field values provided."}), 400

    try:
        result = sf.create_record(obj_name, field_values)
        if "error" in result:
            return jsonify({"error": result["error"]})

        # Add to conversation history so AI knows what happened
        conversation_history.append(
            types.Content(role="user", parts=[types.Part(text=
                f"[SYSTEM: User submitted a form and created a new {obj_name} record with ID: {result['id']}. "
                f"Fields: {json.dumps(field_values)}]"
            )])
        )

        return jsonify({
            "success": True,
            "id": result["id"],
            "object": obj_name,
            "message": f"{obj_name} created successfully."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/form-submit", methods=["POST"])
def form_submit():
    """Generic form submit endpoint for create and update operations."""
    data = request.json
    obj_name = data.get("object_name", "")
    field_values = data.get("field_values", {})
    action = data.get("action", "create")
    record_id = data.get("record_id", "")

    if not obj_name or not field_values:
        return jsonify({"error": "Missing object_name or field_values."}), 400

    try:
        if action == "" or action.startswith("create"):
            result = sf.create_record(obj_name, field_values)
            if "error" in result:
                return jsonify({"error": result["error"]})
            conversation_history.append(
                types.Content(role="user", parts=[types.Part(text=
                    f"[SYSTEM: User created a new {obj_name} record via form. ID: {result['id']}. "
                    f"Fields: {json.dumps(field_values)}]"
                )])
            )
            return jsonify({"success": True, "id": result["id"], "object": obj_name})
        elif action.startswith("update"):
            if not record_id:
                return jsonify({"error": "Missing record_id for update."}), 400
            result = sf.update_record(obj_name, record_id, field_values)
            if "error" in result:
                return jsonify({"error": result["error"]})
            conversation_history.append(
                types.Content(role="user", parts=[types.Part(text=
                    f"[SYSTEM: User updated {obj_name} record ({record_id}) via form. "
                    f"Updated fields: {json.dumps(field_values)}]"
                )])
            )
            return jsonify({"success": True, "id": record_id, "object": obj_name})
        else:
            return jsonify({"error": f"Unsupported action: {action}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def status():
    return jsonify({
        "connected": sf.connected,
        "instance_url": instance_url,
        "knowledge_files": len(knowledge),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    global conversation_history, _pending_charts, _pending_a2ui_surfaces

    data = request.json
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Reset pending charts and A2UI surfaces for this request
    _pending_charts = []
    _pending_a2ui_surfaces = []

    # Add user message to history
    conversation_history.append(
        types.Content(role="user", parts=[types.Part(text=user_message)])
    )

    try:
        # Trim history to avoid context overflow
        trim_history()

        # Send to Gemini
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=conversation_history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=TOOLS,
            ),
        )

        # Track tool calls for the frontend
        tool_calls = []
        # Track OTP verification requests triggered during this chat
        otp_requests = []

        # Handle function calls loop (supports parallel function calls)
        max_iterations = 10
        iteration = 0
        while response.candidates and response.candidates[0].content.parts and iteration < max_iterations:
            parts = response.candidates[0].content.parts

            # Collect ALL function calls from this turn
            function_calls = [p for p in parts if p.function_call]

            if not function_calls:
                break

            iteration += 1

            # Add model's function call turn to history
            conversation_history.append(response.candidates[0].content)

            # Execute ALL function calls and build response parts
            response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call

                # Record the tool call
                tool_calls.append({
                    "name": fc.name,
                    "args": dict(fc.args) if fc.args else {},
                })

                # Execute the function
                result = handle_function_call(fc, sf)

                # Check if this result requires OTP
                if isinstance(result, dict) and result.get("otp_required"):
                    otp_requests.append(result)
                    # Tell the model that OTP is required so it can inform the user
                    result_for_model = {
                        "otp_required": True,
                        "message": result["message"],
                    }
                else:
                    # Truncate large results so Gemini doesn't echo huge tables
                    result_for_model = truncate_result(result)

                # Build a FunctionResponse part for this call
                response_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response=result_for_model
                    )
                ))

            # Send ALL function responses back together as a single Content
            conversation_history.append(types.Content(
                role="user",
                parts=response_parts
            ))

            # If OTP is required, stop the loop — don't ask Gemini for more tool calls
            if otp_requests:
                # Give Gemini the OTP message so it can respond accordingly
                response = gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=conversation_history,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        tools=TOOLS,
                    ),
                )
                break

            # Send back to Gemini
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=conversation_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=TOOLS,
                ),
            )

        # Add final response to history
        if response.candidates:
            conversation_history.append(response.candidates[0].content)

        # Safely extract text, handling None and empty responses
        try:
            reply = response.text if response.text else "I couldn't generate a response."
        except Exception:
            # response.text can raise if there are no text parts
            reply = "I couldn't generate a response. Please try again."

        response_payload = {
            "reply": reply,
            "tool_calls": tool_calls,
            "charts": _pending_charts,
            "a2ui_surfaces": _pending_a2ui_surfaces,
        }

        # If OTP is required, include the OTP data so the frontend can show the modal
        if otp_requests:
            response_payload["otp_required"] = True
            response_payload["otp_session_key"] = otp_requests[0]["session_key"]
            response_payload["otp_operation"] = otp_requests[0].get("operation", "")
            response_payload["otp_object"] = otp_requests[0].get("object", "")
            response_payload["otp_record_id"] = otp_requests[0].get("record_id", "")

        return jsonify(response_payload)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear", methods=["POST"])
def clear():
    global conversation_history
    conversation_history = []
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    print(f"\n  Server starting at http://localhost:5000")
    print(f"  Salesforce: {instance_url}")
    print(f"  Knowledge: {len(knowledge)} files\n")
    app.run(debug=False, port=5000)
