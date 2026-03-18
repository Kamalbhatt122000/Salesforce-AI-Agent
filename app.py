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
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types

# ── Load .env ────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salesforce")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SF_USERNAME = os.getenv("SF_USERNAME", "")
SF_PASSWORD = os.getenv("SF_PASSWORD", "")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN", "")

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)


# ── Load Skill Knowledge ─────────────────────────────────────

def load_skill_files():
    knowledge = {}
    for md_file in glob.glob(os.path.join(SKILL_DIR, "**", "*.md"), recursive=True):
        relative_path = os.path.relpath(md_file, SKILL_DIR)
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                knowledge[relative_path] = f.read()
        except Exception:
            pass
    return knowledge


def build_system_prompt(knowledge):
    knowledge_text = ""
    for filepath, content in sorted(knowledge.items()):
        knowledge_text += f"\n\n{'='*60}\nFILE: {filepath}\n{'='*60}\n\n{content}"

    return f"""You are a Salesforce Expert AI Agent. You have deep knowledge of the entire Salesforce platform and you are connected to a LIVE Salesforce org.

YOUR CAPABILITIES:
1. Answer questions about any Salesforce API (REST, SOAP, Bulk, Metadata, Tooling, Streaming)
2. Write and explain SOQL/SOSL queries
3. EXECUTE live SOQL queries using the run_soql_query tool
4. EXECUTE live SOSL searches using the run_sosl_search tool
5. List all objects using list_org_objects tool
6. Describe any object's fields using describe_object tool
7. CREATE new records using the create_record tool
8. UPDATE existing records using the update_record tool
9. DELETE records using the delete_record tool
10. Write Apex code, explain Flows, guide on security, explain governor limits

IMPORTANT RULES:
- When the user asks to see data, ALWAYS use run_soql_query to execute it. NEVER just show query text.
- When the user asks to CREATE a record (contact, account, lead, etc.), ALWAYS use the create_record tool to actually create it. Do NOT just show the API call or curl command.
- When the user asks to UPDATE a record, ALWAYS use the update_record tool to actually update it.
- When the user asks to DELETE a record, ALWAYS use the delete_record tool to actually delete it.
- After getting results, present them clearly with formatting.
- If unsure about fields, use describe_object first.
- Use markdown formatting in your responses for better readability.
- Use tables when presenting multiple records.
- After creating/updating/deleting a record, confirm the action and show relevant details.

CRITICAL RULES FOR CREATING/UPDATING RECORDS:
- Map user-provided values to the CORRECT Salesforce field API names. Double-check before calling the tool.
- "Last Name" MUST go into "LastName" field, "First Name" into "FirstName", "Company" into "Company", etc.
- NEVER swap field values. If the user says "Company is X, Last Name is Y", then field_values MUST be {{"Company": "X", "LastName": "Y"}}.
- After creating a record, run a SOQL query to fetch it back by ID and show the user the actual saved values as confirmation.

CRITICAL RULES FOR DISPLAYING QUERY RESULTS IN TABLES:
- When displaying results in a markdown table, if a field value is null or empty, display it as "—" (dash), NEVER skip the cell.
- Every row must have the SAME number of columns as the header row.
- Always align values to their correct column headers.
- NEVER repeat or duplicate the table. Present the query results EXACTLY ONCE. Do NOT show the same data twice.
- If results are truncated (a "note" field is present), inform the user of the total count and that only a subset is shown.

AUTOMATIC LEAD CONVERSION:
- When a Lead's status is updated to "Closed - Converted" via the update_record tool, the system AUTOMATICALLY creates an Account and Contact from the Lead's data.
- The update_record response will include a "conversion" field with account_id, contact_id, account_name, contact_name, and whether the account was newly created or already existed.
- After a lead conversion, ALWAYS inform the user about the Account and Contact that were created, including their names and IDs.
- If the conversion failed, the response will include "conversion_error" — inform the user about the failure.

KNOWLEDGE BASE:
{knowledge_text}
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
            results = self.query_executor.soql(soql)
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
    ])
]


# Global list to collect chart configs during a single request
_pending_charts = []


def handle_function_call(function_call, sf):
    global _pending_charts
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
        return sf.update_record(args.get("object_name", ""), args.get("record_id", ""), dict(args.get("field_values", {})))
    elif name == "delete_record":
        return sf.delete_record(args.get("object_name", ""), args.get("record_id", ""))
    elif name == "generate_chart":
        chart_config = {
            "chart_type": args.get("chart_type", "bar"),
            "title": args.get("title", "Chart"),
            "labels": list(args.get("labels", [])),
            "data": [float(x) for x in args.get("data", [])],
            "dataset_label": args.get("dataset_label", "Count"),
        }
        _pending_charts.append(chart_config)
        print(f"  [CHART] Generated {chart_config['chart_type']} chart: {chart_config['title']}")
        return {"success": True, "message": f"Chart '{chart_config['title']}' generated. It will be displayed to the user."}
    return {"error": f"Unknown function: {name}"}


# ── Initialize ───────────────────────────────────────────────

print("Loading Salesforce skill knowledge...")
knowledge = load_skill_files()
print(f"  Loaded {len(knowledge)} knowledge files")

system_prompt = build_system_prompt(knowledge)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Connect to Salesforce
sf = SalesforceConnection()
try:
    instance_url = sf.connect()
    print(f"  Connected to Salesforce: {instance_url}")
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


@app.route("/api/status")
def status():
    return jsonify({
        "connected": sf.connected,
        "instance_url": instance_url,
        "knowledge_files": len(knowledge),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    global conversation_history, _pending_charts

    data = request.json
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Reset pending charts for this request
    _pending_charts = []

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

        # Handle function calls loop
        max_iterations = 10
        iteration = 0
        while response.candidates and response.candidates[0].content.parts and iteration < max_iterations:
            parts = response.candidates[0].content.parts
            function_call_part = None
            for p in parts:
                if p.function_call:
                    function_call_part = p
                    break

            if not function_call_part:
                break

            iteration += 1

            # Record the tool call
            fc = function_call_part.function_call
            tool_calls.append({
                "name": fc.name,
                "args": dict(fc.args) if fc.args else {},
            })

            # Add model's function call to history
            conversation_history.append(response.candidates[0].content)

            # Execute the function
            result = handle_function_call(fc, sf)

            # Truncate large results so Gemini doesn't echo huge tables
            result_for_model = truncate_result(result)

            # Add function response to history
            conversation_history.append(types.Content(
                role="user",
                parts=[types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response=result_for_model
                    )
                )]
            ))

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

        reply = response.text if response.text else "I couldn't generate a response."

        return jsonify({
            "reply": reply,
            "tool_calls": tool_calls,
            "charts": _pending_charts,
        })

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
