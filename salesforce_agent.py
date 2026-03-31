"""
Salesforce AI Agent (with Live Query Execution)
════════════════════════════════════════════════
An AI-powered agent that reads the Salesforce skill files, answers
user questions, and can EXECUTE live SOQL queries on your Salesforce org.

All credentials loaded from .env file.

Usage:
    python salesforce_agent.py
"""

import os
import sys
import glob
import json
import uuid
from dotenv import load_dotenv
from openai import AzureOpenAI

# ── Load .env ────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salesforce")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
SF_USERNAME = os.getenv("SF_USERNAME", "")
SF_PASSWORD = os.getenv("SF_PASSWORD", "")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN", "")


# ── Load Skill Knowledge Base ────────────────────────────────

def load_skill_files():
    """Load all markdown files from the skill directory as knowledge."""
    knowledge = {}
    for md_file in glob.glob(os.path.join(SKILL_DIR, "**", "*.md"), recursive=True):
        relative_path = os.path.relpath(md_file, SKILL_DIR)
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            knowledge[relative_path] = content
        except Exception as e:
            print(f"  Warning: Could not load {relative_path}: {e}")
    return knowledge


def build_system_prompt(knowledge):
    """Build the system prompt with all skill knowledge."""
    knowledge_text = ""
    for filepath, content in sorted(knowledge.items()):
        knowledge_text += f"\n\n{'='*60}\nFILE: {filepath}\n{'='*60}\n\n{content}"

    return f"""You are a Salesforce Expert AI Agent connected to a LIVE Salesforce org.

RESPONSE STYLE (CRITICAL — FOLLOW STRICTLY):
- Be CONCISE and DIRECT. Short sentences, no filler.
- NEVER mention internal tool names (run_soql_query, update_record, create_record, describe_object, analyze_field_data, etc.) to the user. The user doesn't care about your tools — just DO the action and show results.
- Instead of "use update_record with the record ID", say "I can update that for you — just tell me the lead name or ID and what to change."
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
6. Analyze text fields using AI (sentiment, themes, patterns)
7. Check calendar availability and book meetings/calls
8. Answer any Salesforce platform question

CALENDAR & MEETING BOOKING:
- When user asks to "book a call", "schedule a meeting", or "set up a meeting" → FIRST check_calendar to see availability, THEN suggest available time slots, THEN book_meeting once user confirms or if they specified a time.
- When a Lead/Contact ID is provided (e.g. 00Qxxx), link the event to that person using who_id.
- If user says "book a 15-min call with 00Qxxx" → check calendar for today/tomorrow, pick the first available 15-min slot, and book it. Show the confirmed booking details.
- If user asks to "suggest times" → check_calendar for 2-3 days ahead, then show available slots in a table.
- Always confirm: subject, date, time, duration, and who it's with.

SMART QUERY PATTERNS — USE THESE FOR COMMON QUESTIONS:

1. "Which lead SOURCES should we invest in?" → Run aggregate: SELECT LeadSource, COUNT(Id) cnt FROM Lead GROUP BY LeadSource ORDER BY cnt DESC. Also query converted by source. Compare volume AND conversion rate.

2. "Among [source] leads, which LEAD to invest in?" or "which leads to prioritize/call?" → Run: SELECT Id, Name, Company, Status, Rating, Phone, Email, CreatedDate FROM Lead WHERE LeadSource = '[source]' ORDER BY Rating ASC, CreatedDate DESC — show ALL individual leads in a table. Hot-rated leads first. Then add 1-line recommendation.

3. "Which leads should I call today?" → SELECT Id, Name, Company, Phone, Rating, Status, CreatedDate FROM Lead WHERE Status IN ('Open - Not Contacted', 'Working - Contacted') ORDER BY Rating ASC, CreatedDate DESC — show leads with phone numbers, hot leads first.

4. "Where are we losing leads in the funnel?" → SELECT Status, COUNT(Id) cnt FROM Lead GROUP BY Status ORDER BY cnt DESC — show as table, identify bottleneck stage.

5. "Show leads created in last 30 days" → WHERE CreatedDate = LAST_N_DAYS:30
   "...but not converted" → AND IsConverted = false
   "...but converted" → AND IsConverted = true

6. "Show leads where industry is X" → WHERE Industry = 'X' — show individual records.

7. "How do I edit/delete a lead?" → First show recent leads in a table (SELECT Id, Name, Company, Status FROM Lead ORDER BY CreatedDate DESC LIMIT 10), then say: "Tell me which lead and what to change — I'll handle it for you." or "Which lead do you want to delete?"

8. "Assign leads to users/queues" → Show current lead assignments, then say: "Tell me which lead and who to assign it to — I'll update it."

9. "Track lead status" → Show status breakdown (GROUP BY Status) and offer to show individual leads for any status.

10. "Merge duplicate leads" → Explain: this must be done in Salesforce UI (Setup > Merge Leads). API doesn't support direct merging.

11. "High quality vs low quality leads" → SELECT Id, Name, Company, Rating, Status, LeadSource FROM Lead ORDER BY Rating ASC — show in table, grouped by rating.

12. "Lead score for this lead" → Fetch all fields to check if a lead score field exists.

13. "Which sources generate most leads?" → SELECT LeadSource, COUNT(Id) cnt FROM Lead GROUP BY LeadSource ORDER BY cnt DESC

14. "Conversion rate by source" → Query total and converted leads per source, calculate percentage, show table.

15. "Leads with no activity in X days" → SELECT Id, Name, Company, LastActivityDate FROM Lead WHERE LastActivityDate < LAST_N_DAYS:X OR LastActivityDate = null

16. "Unassigned leads" → Query leads with no owner or queue ownership.

17. "Lead distribution across reps" → SELECT Owner.Name, COUNT(Id) cnt FROM Lead GROUP BY Owner.Name ORDER BY cnt DESC

18. "Leads overdue for follow-up" → SELECT Id, Name, Company, LastActivityDate, Status FROM Lead WHERE LastActivityDate < LAST_N_DAYS:7 AND Status != 'Closed - Converted'

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
- For yes/no questions (e.g. "Does it allow multiple contacts?", "Is it active?", "Is the email verified?"):
  → Just answer "No." or "Yes." — ONE word is enough. Do NOT say "According to the record, the 'X' field is set to False." That is too verbose.
- For single-value questions (e.g. "What's the phone number?", "What's the status?"):
  → Just give the value directly. E.g. "555-1234" or "Open - Not Contacted". No extra explanation.
- NEVER pad simple answers with filler like "According to the record", "Based on the data", "The field X shows". Just answer naturally and briefly.

RECORD SUMMARIES (CRITICAL — FOLLOW FOR "summarize" REQUESTS):
- When the user asks to "summarize" an account, contact, lead, opportunity, or any record:
  → Write a SHORT, NATURAL-LANGUAGE paragraph (2-4 sentences). Do NOT list field names and values.
  → Weave the data into flowing prose. Example:
    GOOD: "**King Solutions Ltd** is a Technology company generating approximately **$4.2M** in annual revenue. Their website is [www.kingsolutions.com](http://www.kingsolutions.com). No description is on file."
    BAD: "Name: King Solutions Ltd\nIndustry: Technology\nAnnual Revenue: 4198912\nDescription: —"
  → Format currency values nicely (e.g. $4,198,912 or ~$4.2M), not raw numbers.
  → Skip fields that are null/empty — do NOT show them as "—". Only mention populated fields.
  → If the record has related data (e.g. contacts, opportunities), briefly mention counts if available.
  → Bold the record name and key metrics.
  → Keep it under 100 words.

IMPORTANT RULES:
- When the user provides a record ID, fetch ALL fields for that record immediately.
- When the user asks to see data, ALWAYS execute the query. NEVER just show query text.
- When user says "execute it" or "run it", execute immediately.
- When user asks for "all" records, do NOT add LIMIT. Pagination is automatic.
- When user asks to CREATE/UPDATE/DELETE, just DO it. Don't explain the tool — confirm the action with key details.
- Use describe_object if unsure about fields.
- NEVER expose internal tool/function names in responses. Act naturally.

ORG SETTINGS VERIFICATION (CRITICAL):
- NEVER answer questions about org features/settings based on general Salesforce knowledge alone. ALWAYS verify against the LIVE org first.
- For "does it allow multiple contacts?" or "is Contacts to Multiple Accounts enabled?":
  Run: SELECT Id FROM AccountContactRelation LIMIT 1
  If it returns results or no error: the feature IS enabled.
  If it errors (object not found): the feature is DISABLED. Answer "No."
- For any "is [feature] enabled?" question: try to query or describe the related object/field in the live org. Base your answer on the actual result, NOT on Salesforce defaults or general knowledge.
- When the org says something different from the default, trust the org.

AI-POWERED DATA ANALYSIS:
- For analytical questions about text fields (pain points, themes, sentiment, summaries) → fetch the text data, then analyze it yourself.
- NEVER say "I cannot analyze text". Fetch the data, then analyze it.
- Present analysis as ranked bullet points or a table. Keep it concise.

RECORD ID PREFIXES: 001=Account, 003=Contact, 00Q=Lead, 006=Opportunity, 500=Case, 00T=Task, 00U=Event

FIELD MAPPING: Map values to correct API names. Never swap fields.

TABLE DISPLAY: Null = "—". Same columns in every row. Show data ONCE, never duplicate.

CONVERTED LEADS: Hidden by default. Use WHERE IsConverted = true to query them.

COUNT QUERIES: Present count clearly (e.g. "There are **25** leads.").

KNOWLEDGE BASE:
{knowledge_text}
"""


# ── Salesforce Connection ────────────────────────────────────

class SalesforceConnection:
    """Manages live Salesforce connection."""

    def __init__(self):
        self.auth = None
        self.connected = False

    def connect(self):
        scripts_dir = os.path.join(SKILL_DIR, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        from sf_auth import SalesforceAuth
        from sf_query import SalesforceQuery
        from sf_rest_client import SalesforceRESTClient

        self.auth = SalesforceAuth(
            username=SF_USERNAME,
            password=SF_PASSWORD,
            security_token=SF_SECURITY_TOKEN,
        )
        self.auth.authenticate_simple()
        self.query_executor = SalesforceQuery(self.auth)
        self.rest_client = SalesforceRESTClient(self.auth)
        self.connected = True
        return self.auth.instance_url

    def run_soql(self, soql):
        if not self.connected:
            return {"error": "Not connected to Salesforce. Connecting now..."}
        try:
            results = self.query_executor.soql_all(soql)
            # Clean up results (remove 'attributes' key)
            clean_results = []
            for r in results:
                clean = {k: v for k, v in r.items() if k != "attributes"}
                clean_results.append(clean)
            return {"records": clean_results, "count": len(clean_results)}
        except Exception as e:
            return {"error": str(e)}

    def run_sosl(self, sosl):
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            results = self.query_executor.sosl(sosl)
            clean_results = []
            for r in results:
                clean = {k: v for k, v in r.items() if k != "attributes"}
                clean_results.append(clean)
            return {"records": clean_results, "count": len(clean_results)}
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
        """Create a new record in Salesforce."""
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            print(f"  [CREATE {sobject}] Sending field_values: {json.dumps(field_values, indent=2)}")
            record_id = self.rest_client.create(sobject, field_values)
            return {"success": True, "id": record_id, "object": sobject, "fields_sent": field_values, "message": f"{sobject} record created successfully"}
        except Exception as e:
            return {"error": str(e)}

    def update_record(self, sobject, record_id, field_values):
        """Update an existing record in Salesforce."""
        if not self.connected:
            return {"error": "Not connected to Salesforce."}
        try:
            self.rest_client.update(sobject, record_id, field_values)
            return {"success": True, "id": record_id, "object": sobject, "message": f"{sobject} record updated successfully"}
        except Exception as e:
            return {"error": str(e)}

    def delete_record(self, sobject, record_id):
        """Delete a record from Salesforce."""
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
            field_name = field_label.replace(" ", "_") + "__c"
            metadata = {
                "label": field_label,
                "type": field_type,
                "description": description or "",
                "inlineHelpText": "",
            }
            if required:
                metadata["required"] = True

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
                metadata["type"] = field_type
                if length:
                    metadata["length"] = length

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
            if not field_name.endswith("__c"):
                field_name = field_name + "__c"

            query = f"SELECT Id, DeveloperName, TableEnumOrId FROM CustomField WHERE TableEnumOrId = '{object_name}' AND DeveloperName = '{field_name.replace('__c', '')}'"
            print(f"  [DELETE FIELD] Querying: {query}")

            result = self._tooling_request("GET", "/query/", params={"q": query})
            records = result.get("records", []) if result else []

            if not records:
                return {"error": f"Custom field '{field_name}' not found on {object_name}. Make sure this is a custom field (ending in __c)."}

            field_id = records[0]["Id"]
            print(f"  [DELETE FIELD] Found field ID: {field_id}")

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
            # NOTE: We do NOT filter with "!= null" in SOQL because Long Text Area
            # fields do not support comparison operators in WHERE clauses.
            # Instead, we fetch all records and filter nulls in Python.
            soql = f"SELECT Id, {field_name} FROM {object_name}"
            if where_clause:
                soql += f" WHERE {where_clause}"
            soql += f" LIMIT {limit}"

            print(f"  [ANALYZE] Fetching '{field_name}' from {object_name}: {soql}")
            results = self.query_executor.soql_all(soql)

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
                who = evt.pop("Who", None)
                if who and isinstance(who, dict):
                    evt["WhoName"] = who.get("Name", "\u2014")
                else:
                    evt["WhoName"] = "\u2014"
                events.append(evt)

            free_slots = []
            for day_offset in range(days_ahead):
                check_date = base_date + timedelta(days=day_offset)
                day_start = check_date.replace(hour=9, minute=0, second=0)
                day_end = check_date.replace(hour=17, minute=0, second=0)

                now = datetime.now()
                if check_date.date() == now.date() and now.hour >= 9:
                    if now.minute <= 30:
                        day_start = now.replace(minute=30, second=0, microsecond=0)
                    else:
                        day_start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

                if day_start >= day_end:
                    continue

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

                day_events.sort(key=lambda x: x[0])
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


# ── OpenAI Tool Definitions ──────────────────────────────────

TOOLS = [
    {"type": "function", "function": {"name": "run_soql_query", "description": "Execute a SOQL query on the live Salesforce org and return the results.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "The SOQL query to execute"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "run_sosl_search", "description": "Execute a SOSL search across multiple objects in the live Salesforce org.", "parameters": {"type": "object", "properties": {"search": {"type": "string", "description": "The SOSL search string"}}, "required": ["search"]}}},
    {"type": "function", "function": {"name": "list_org_objects", "description": "List all available objects in the connected Salesforce org.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "describe_object", "description": "Get all field names, types, and labels for a Salesforce object.", "parameters": {"type": "object", "properties": {"object_name": {"type": "string", "description": "Object API name, e.g. 'Account', 'Lead'"}}, "required": ["object_name"]}}},
    {"type": "function", "function": {"name": "create_record", "description": "Create a new record in the Salesforce org.", "parameters": {"type": "object", "properties": {"object_name": {"type": "string", "description": "Object API name"}, "field_values": {"type": "object", "description": "Field API names and their values"}}, "required": ["object_name", "field_values"]}}},
    {"type": "function", "function": {"name": "update_record", "description": "Update an existing record in the Salesforce org.", "parameters": {"type": "object", "properties": {"object_name": {"type": "string", "description": "Object API name"}, "record_id": {"type": "string", "description": "18-character Salesforce record ID"}, "field_values": {"type": "object", "description": "Field API names and new values"}}, "required": ["object_name", "record_id", "field_values"]}}},
    {"type": "function", "function": {"name": "delete_record", "description": "Delete a record from the Salesforce org.", "parameters": {"type": "object", "properties": {"object_name": {"type": "string", "description": "Object API name"}, "record_id": {"type": "string", "description": "18-character Salesforce record ID"}}, "required": ["object_name", "record_id"]}}},
    {"type": "function", "function": {"name": "get_record_all_fields", "description": "Fetch a single record with ALL its fields. Use when the user provides a record ID.", "parameters": {"type": "object", "properties": {"object_name": {"type": "string", "description": "Object API name. Infer from ID prefix: 00Q=Lead, 001=Account, 003=Contact"}, "record_id": {"type": "string", "description": "15 or 18-character Salesforce record ID"}}, "required": ["object_name", "record_id"]}}},
    {"type": "function", "function": {"name": "create_custom_field", "description": "Create a custom field on a Salesforce object using the Tooling API.", "parameters": {"type": "object", "properties": {"object_name": {"type": "string", "description": "Object API name"}, "field_label": {"type": "string", "description": "Label for the new field"}, "field_type": {"type": "string", "description": "Field type: Text, Number, Checkbox, Date, DateTime, Email, Phone, Url, Currency, Percent, TextArea, LongTextArea, Picklist"}, "length": {"type": "number", "description": "Optional length"}, "precision": {"type": "number", "description": "Optional precision"}, "scale": {"type": "number", "description": "Optional scale"}, "picklist_values": {"type": "array", "items": {"type": "string"}, "description": "Picklist values"}, "description": {"type": "string", "description": "Field description"}, "required": {"type": "boolean", "description": "Whether the field is required"}}, "required": ["object_name", "field_label", "field_type"]}}},
    {"type": "function", "function": {"name": "delete_custom_field", "description": "Delete a custom field from a Salesforce object using the Tooling API.", "parameters": {"type": "object", "properties": {"object_name": {"type": "string", "description": "Object API name"}, "field_name": {"type": "string", "description": "Custom field API name"}}, "required": ["object_name", "field_name"]}}},
    {"type": "function", "function": {"name": "analyze_field_data", "description": "Fetch raw text data from a field across records for AI analysis. Use for analytical questions about text fields.", "parameters": {"type": "object", "properties": {"object_name": {"type": "string", "description": "Object API name"}, "field_name": {"type": "string", "description": "Text field API name"}, "where_clause": {"type": "string", "description": "Optional WHERE clause (without WHERE keyword)"}, "limit": {"type": "number", "description": "Max records to fetch (default 200)"}}, "required": ["object_name", "field_name"]}}},
    {"type": "function", "function": {"name": "check_calendar", "description": "Check the user's Salesforce calendar for events and free slots.", "parameters": {"type": "object", "properties": {"date": {"type": "string", "description": "Date in YYYY-MM-DD format"}, "days_ahead": {"type": "number", "description": "Number of days to check (default 1)"}}}}},
    {"type": "function", "function": {"name": "book_meeting", "description": "Book a meeting/call by creating an Event in Salesforce.", "parameters": {"type": "object", "properties": {"subject": {"type": "string", "description": "Meeting subject"}, "start_datetime": {"type": "string", "description": "Start date/time in ISO format"}, "duration_minutes": {"type": "number", "description": "Duration in minutes (default 30)"}, "who_id": {"type": "string", "description": "Lead or Contact record ID"}, "description": {"type": "string", "description": "Meeting description"}, "location": {"type": "string", "description": "Meeting location"}}, "required": ["subject", "start_datetime"]}}},
]


# ── Chat Interface ───────────────────────────────────────────

def print_banner(instance_url):
    print()
    print("=" * 60)
    print("          SALESFORCE AI AGENT")
    print(f"  Connected to: {instance_url}")
    print("=" * 60)
    print()
    print("  Ask me anything about Salesforce!")
    print("  I can also query your live org data.")
    print()
    print("  Try:")
    print("    'Show me all leads'")
    print("    'How many accounts are there?'")
    print("    'What fields does the Contact object have?'")
    print("    'Write a SOQL query for open opportunities'")
    print()
    print("  Type /quit to exit")
    print()
    print("=" * 60)
    print()


def handle_function_call(name, args, sf):
    """Execute a function call from OpenAI and return the result."""
    args = args or {}

    if name == "run_soql_query":
        query = args.get("query", "")
        print(f"\n  [Executing SOQL] {query}")
        result = sf.run_soql(query)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Got {result['count']} records]")
        return result

    elif name == "run_sosl_search":
        search = args.get("search", "")
        print(f"\n  [Executing SOSL] {search}")
        result = sf.run_sosl(search)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Got {result['count']} results]")
        return result

    elif name == "list_org_objects":
        print("\n  [Listing org objects...]")
        result = sf.list_objects()
        if "error" not in result:
            print(f"  [Found {result['count']} objects]")
        return result

    elif name == "describe_object":
        obj_name = args.get("object_name", "")
        print(f"\n  [Describing {obj_name}...]")
        result = sf.describe(obj_name)
        if "error" not in result:
            print(f"  [{obj_name} has {result['count']} fields]")
        return result

    elif name == "create_record":
        obj_name = args.get("object_name", "")
        field_values = dict(args.get("field_values", {}))
        print(f"\n  [Creating {obj_name}] Fields: {json.dumps(field_values)}")
        result = sf.create_record(obj_name, field_values)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Created {obj_name}: {result['id']}]")
        return result

    elif name == "update_record":
        obj_name = args.get("object_name", "")
        record_id = args.get("record_id", "")
        field_values = dict(args.get("field_values", {}))
        print(f"\n  [Updating {obj_name} {record_id}] Fields: {json.dumps(field_values)}")

        # ── OTP GATE ──
        otp_ok = _cli_otp_verify(sf, f"Update {obj_name} ({record_id}): {json.dumps(field_values)}", obj_name, record_id)
        if not otp_ok:
            return {"error": "Operation denied — OTP verification failed."}

        result = sf.update_record(obj_name, record_id, field_values)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Updated {obj_name}: {record_id}]")
        return result

    elif name == "delete_record":
        obj_name = args.get("object_name", "")
        record_id = args.get("record_id", "")
        print(f"\n  [Deleting {obj_name} {record_id}]")

        # ── OTP GATE ──
        otp_ok = _cli_otp_verify(sf, f"Delete {obj_name} ({record_id})", obj_name, record_id)
        if not otp_ok:
            return {"error": "Operation denied — OTP verification failed."}

        result = sf.delete_record(obj_name, record_id)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Deleted {obj_name}: {record_id}]")
        return result

    elif name == "get_record_all_fields":
        obj_name = args.get("object_name", "")
        record_id = args.get("record_id", "")
        print(f"\n  [Fetching ALL fields for {obj_name} {record_id}...]")
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
        print(f"\n  [Creating custom field '{field_label}' ({field_type}) on {obj_name}...]")
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
        print(f"\n  [Deleting custom field '{field_name}' from {obj_name}...]")
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
        print(f"\n  [Analyzing '{field_name}' from {obj_name} (limit={limit})...]")
        result = sf.analyze_field_data(obj_name, field_name, where_clause=where_clause, limit=limit)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Fetched {result['total_records_with_data']} values for analysis]")
        return result

    elif name == "check_calendar":
        date_str = args.get("date")
        days_ahead = int(args.get("days_ahead", 1))
        print(f"\n  [Checking calendar for {date_str or 'today'}, {days_ahead} day(s)...]")
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
        print(f"\n  [Booking meeting: '{subject}' at {start_datetime}, {duration_minutes}min]")
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

    return {"error": f"Unknown function: {name}"}


# ── CLI OTP Verification Helper ──────────────────────────────

def _cli_otp_verify(sf, operation_summary, object_name=None, record_id=None):
    """
    Send OTP via Salesforce email and prompt the user in the terminal.
    Sends to the record's email if available, otherwise falls back to SF_USERNAME.
    Returns True if verified, False if denied.
    """
    from otp_manager import create_and_send_otp, verify_otp

    # Try to get the record's email via smart resolution chain
    DIRECT_EMAIL_OBJECTS = {"Lead", "Contact", "Case", "CampaignMember"}
    recipient_email = SF_USERNAME
    if object_name and record_id:
        try:
            # 1. Direct Email field (Lead, Contact, Case)
            if object_name in DIRECT_EMAIL_OBJECTS:
                soql = f"SELECT Email FROM {object_name} WHERE Id = '{record_id}' LIMIT 1"
                result = sf.run_soql(soql)
                if "error" not in result:
                    records = result.get("records", [])
                    if records and records[0].get("Email"):
                        recipient_email = records[0]["Email"]
                        print(f"  [OTP] Found {object_name} email: {recipient_email}")

            # 2. Account → find linked Contact's email
            elif object_name == "Account":
                soql = f"SELECT Id, Email FROM Contact WHERE AccountId = '{record_id}' AND Email != null ORDER BY CreatedDate ASC LIMIT 1"
                result = sf.run_soql(soql)
                if "error" not in result:
                    records = result.get("records", [])
                    if records and records[0].get("Email"):
                        recipient_email = records[0]["Email"]
                        print(f"  [OTP] Found Contact email for Account: {recipient_email}")

            # 3. Opportunity → Account → linked Contact's email
            elif object_name == "Opportunity":
                soql = f"SELECT AccountId FROM Opportunity WHERE Id = '{record_id}' LIMIT 1"
                result = sf.run_soql(soql)
                if "error" not in result:
                    records = result.get("records", [])
                    account_id = records[0].get("AccountId") if records else None
                    if account_id:
                        soql2 = f"SELECT Id, Email FROM Contact WHERE AccountId = '{account_id}' AND Email != null ORDER BY CreatedDate ASC LIMIT 1"
                        result2 = sf.run_soql(soql2)
                        if "error" not in result2:
                            records2 = result2.get("records", [])
                            if records2 and records2[0].get("Email"):
                                recipient_email = records2[0]["Email"]
                                print(f"  [OTP] Found Contact email for Opportunity→Account: {recipient_email}")

            # 4. Other objects → try Email field if it exists
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
                                recipient_email = records[0]["Email"]
                                print(f"  [OTP] Found {object_name} email: {recipient_email}")
                except Exception:
                    pass

        except Exception as e:
            print(f"  [OTP] Could not fetch email for {object_name} {record_id}: {e}")

    session_key = f"cli_{uuid.uuid4().hex[:12]}"

    print(f"\n  \033[93m⚠️  Security verification required for: {operation_summary}\033[0m")
    print(f"  Sending OTP to {recipient_email}...")

    result = create_and_send_otp(sf.auth, recipient_email, session_key, operation_summary)
    if "error" in result:
        print(f"  \033[91m❌ Failed to send OTP: {result['error']}\033[0m")
        return False

    print(f"  \033[92m📧 Verification code sent to {recipient_email}\033[0m")

    # Allow up to 3 attempts
    for attempt in range(3):
        try:
            user_otp = input(f"  Enter 6-digit OTP (attempt {attempt + 1}/3): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  \033[91m❌ Verification cancelled.\033[0m")
            return False

        vresult = verify_otp(session_key, user_otp)
        if vresult.get("verified"):
            print(f"  \033[92m✅ Verified! Proceeding with operation...\033[0m")
            return True
        else:
            print(f"  \033[91m❌ {vresult.get('error', 'Invalid OTP.')}\033[0m")

    print(f"  \033[91m🚫 Verification failed — operation denied.\033[0m")
    return False


def main():
    """Main chat loop."""

    if not AZURE_OPENAI_KEY or not AZURE_OPENAI_ENDPOINT:
        print("\nNo AZURE_OPENAI_KEY or AZURE_OPENAI_ENDPOINT found in .env file.")
        print("Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT in .env")
        return

    # Step 1: Connect to Salesforce
    print("\nConnecting to Salesforce...")
    sf = SalesforceConnection()
    try:
        instance_url = sf.connect()
    except Exception as e:
        print(f"Failed to connect to Salesforce: {e}")
        print("The agent will still work for knowledge questions.")
        instance_url = "Not connected"

    # Step 2: Configure Azure OpenAI
    print("Loading Salesforce knowledge base...")
    knowledge = load_skill_files()
    print(f"  Loaded {len(knowledge)} knowledge files")

    print("Initializing Azure OpenAI model...")
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    system_prompt = build_system_prompt(knowledge)

    # Conversation history for OpenAI
    messages = [{"role": "system", "content": system_prompt}]
    print("  AI agent ready!")

    # Step 3: Chat Loop
    print_banner(instance_url)

    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() == "/quit":
            print("\nGoodbye!")
            break

        if user_input.lower() == "/clear":
            messages = [{"role": "system", "content": system_prompt}]
            print("Conversation cleared.\n")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            # Handle function calls loop
            max_iterations = 10
            iteration = 0
            while msg.tool_calls and iteration < max_iterations:
                iteration += 1

                # Add the assistant message with tool_calls to history
                messages.append(msg.model_dump())

                # Execute all tool calls
                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)
                    result = handle_function_call(fn_name, fn_args, sf)

                    # Add tool response to history
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    })

                # Send back to OpenAI for next step
                response = client.chat.completions.create(
                    model=AZURE_OPENAI_DEPLOYMENT,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
                msg = response.choices[0].message

            # Add final assistant reply to history
            messages.append({"role": "assistant", "content": msg.content or ""})

            # Print the final text response
            if msg.content:
                print(f"\nAgent > {msg.content}\n")

            # Keep history manageable
            if len(messages) > 40:
                messages = [messages[0]] + messages[-38:]

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
