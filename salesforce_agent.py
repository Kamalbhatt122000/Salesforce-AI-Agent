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
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ── Load .env ────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salesforce")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
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

    return f"""You are a Salesforce Expert AI Agent. You have deep knowledge of the entire Salesforce platform and you are connected to a LIVE Salesforce org.

YOUR CAPABILITIES:
1. Answer questions about any Salesforce API (REST, SOAP, Bulk, Metadata, Tooling, Streaming)
2. Write and explain SOQL/SOSL queries
3. EXECUTE live SOQL queries on the connected Salesforce org using the run_soql_query tool
4. EXECUTE live SOSL searches on the connected org using the run_sosl_search tool
5. List all objects in the org using list_org_objects tool
6. Describe any object's fields using describe_object tool
7. CREATE new records using the create_record tool
8. UPDATE existing records using the update_record tool
9. DELETE records using the delete_record tool
10. Write Apex code, explain Flows, guide on security, and explain governor limits

IMPORTANT RULES:
- When the user asks to see data, run a query, or asks about their org's data, ALWAYS use the run_soql_query tool to execute it. Do NOT just show the query text.
- When the user says "execute it" or "run it", use the run_soql_query tool immediately.
- When the user asks to CREATE a record (contact, account, lead, etc.), ALWAYS use the create_record tool to actually create it. Do NOT just show the API call or curl command.
- When the user asks to UPDATE a record, ALWAYS use the update_record tool to actually update it.
- When the user asks to DELETE a record, ALWAYS use the delete_record tool to actually delete it.
- After getting query results, present them in a clean, readable format (table or list).
- If the query returns no results, tell the user and suggest alternatives.
- If unsure about available fields, use describe_object first to check.
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
            results = self.query_executor.soql(soql)
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


# ── Gemini Function Definitions ──────────────────────────────

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="run_soql_query",
            description="Execute a SOQL query on the live Salesforce org and return the results. Use this whenever the user wants to see data from their Salesforce org.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(
                        type="STRING",
                        description="The SOQL query to execute, e.g. 'SELECT Id, Name FROM Account LIMIT 10'"
                    )
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="run_sosl_search",
            description="Execute a SOSL search across multiple objects in the live Salesforce org.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "search": types.Schema(
                        type="STRING",
                        description="The SOSL search string, e.g. 'FIND {Acme} IN ALL FIELDS RETURNING Account(Name, Id)'"
                    )
                },
                required=["search"]
            )
        ),
        types.FunctionDeclaration(
            name="list_org_objects",
            description="List all available objects in the connected Salesforce org.",
            parameters=types.Schema(
                type="OBJECT",
                properties={}
            )
        ),
        types.FunctionDeclaration(
            name="describe_object",
            description="Get all field names, types, and labels for a specific Salesforce object.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(
                        type="STRING",
                        description="The API name of the object to describe, e.g. 'Account', 'Lead', 'Contact'"
                    )
                },
                required=["object_name"]
            )
        ),
        types.FunctionDeclaration(
            name="create_record",
            description="Create a new record in the Salesforce org. Use this when the user asks to create/add/insert a new record (Contact, Account, Lead, Opportunity, Case, or any object).",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "object_name": types.Schema(
                        type="STRING",
                        description="The API name of the object to create, e.g. 'Contact', 'Account', 'Lead', 'Opportunity'"
                    ),
                    "field_values": types.Schema(
                        type="OBJECT",
                        description="A JSON object of field API names and their values. E.g. {\"FirstName\": \"John\", \"LastName\": \"Doe\", \"Email\": \"john@example.com\", \"AccountId\": \"001xx...\"}"
                    )
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
                    "object_name": types.Schema(
                        type="STRING",
                        description="The API name of the object, e.g. 'Contact', 'Account'"
                    ),
                    "record_id": types.Schema(
                        type="STRING",
                        description="The 18-character Salesforce record ID to update"
                    ),
                    "field_values": types.Schema(
                        type="OBJECT",
                        description="A JSON object of field API names and their new values. E.g. {\"Phone\": \"555-1234\", \"Title\": \"VP Sales\"}"
                    )
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
                    "object_name": types.Schema(
                        type="STRING",
                        description="The API name of the object, e.g. 'Contact', 'Account'"
                    ),
                    "record_id": types.Schema(
                        type="STRING",
                        description="The 18-character Salesforce record ID to delete"
                    )
                },
                required=["object_name", "record_id"]
            )
        ),
    ])
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


def handle_function_call(function_call, sf):
    """Execute a function call from Gemini and return the result."""
    name = function_call.name
    args = function_call.args or {}

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
        result = sf.delete_record(obj_name, record_id)
        if "error" in result:
            print(f"  [Error] {result['error']}")
        else:
            print(f"  [Deleted {obj_name}: {record_id}]")
        return result

    return {"error": f"Unknown function: {name}"}


def main():
    """Main chat loop."""

    if not GEMINI_API_KEY:
        print("\nNo GEMINI_API_KEY found in .env file.")
        print("Get one at: https://aistudio.google.com/apikey")
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

    # Step 2: Configure Gemini
    print("Loading Salesforce knowledge base...")
    knowledge = load_skill_files()
    print(f"  Loaded {len(knowledge)} knowledge files")

    print("Initializing AI model...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    system_prompt = build_system_prompt(knowledge)

    chat = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=TOOLS,
        ),
    )
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
            chat = client.chats.create(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=TOOLS,
                ),
            )
            print("Conversation cleared.\n")
            continue

        try:
            response = chat.send_message(user_input)

            # Handle function calls (tool use)
            while response.candidates and response.candidates[0].content.parts:
                has_function_call = False
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        has_function_call = True
                        result = handle_function_call(part.function_call, sf)

                        # Send function result back to Gemini
                        func_response_part = types.Part(
                            function_response=types.FunctionResponse(
                                name=part.function_call.name,
                                response=result
                            )
                        )
                        response = chat.send_message(func_response_part)
                        break  # Process one function call at a time

                if not has_function_call:
                    break

            # Print the final text response
            if response.text:
                print(f"\nAgent > {response.text}\n")

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
