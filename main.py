import os
import re
import requests
from flask import jsonify

# Configuration - Replace with your actual IDs or use Env Vars
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID") 
LABEL_BUG_ID = "YOUR_BUG_LABEL_UUID"  # Find in Linear Label Settings
LABEL_FEATURE_ID = "YOUR_FEATURE_LABEL_UUID"

LINEAR_URL = "https://api.linear.app/graphql"
HEADERS = {"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"}

def query_linear(query, variables=None):
    response = requests.post(LINEAR_URL, json={'query': query, 'variables': variables}, headers=HEADERS)
    return response.json()

def parse_metadata(text):
    """Simple parser for priority and labels based on keywords."""
    priority_map = {"urgent": 1, "high": 2, "medium": 3, "low": 4}
    found_priority = 0 # Default: No Priority
    found_labels = []

    # Check for priority keywords
    for word, val in priority_map.items():
        if word in text.lower():
            found_priority = val
            text = re.sub(word, "", text, flags=re.I).strip()
    
    # Auto-labeling logic
    if "bug" in text.lower():
        found_labels.append(LABEL_BUG_ID)
    if "feat" in text.lower() or "request" in text.lower():
        found_labels.append(LABEL_FEATURE_ID)
        
    return text, found_priority, found_labels

def handle_slash_command(event):
    cmd_id = event['message']['slashCommand']['commandId']
    text = event['message'].get('argumentText', '').strip()

    # /new (Command ID 1)
    if cmd_id == 1:
        clean_title, priority, labels = parse_metadata(text)
        mutation = """
        mutation Create($title: String!, $teamId: String!, $priority: Int, $labelIds: [String!]) {
          issueCreate(input: { title: $title, teamId: $teamId, priority: $priority, labelIds: $labelIds }) {
            success
            issue { identifier url }
          }
        }
        """
        res = query_linear(mutation, {"title": clean_title, "teamId": LINEAR_TEAM_ID, "priority": priority, "labelIds": labels})
        issue = res['data']['issueCreate']['issue']
        return f"🆕 Created *{issue['identifier']}*: {issue['url']}"

    # /list (Command ID 2)
    elif cmd_id == 2:
        query = """
        query Issues($teamId: String!) {
          issues(filter: { team: { id: { eq: $teamId } } }, first: 5) {
            nodes { identifier title url }
          }
        }
        """
        res = query_linear(query, {"teamId": LINEAR_TEAM_ID})
        issues = res['data']['issues']['nodes']
        list_text = "*Recent Issues:*\n" + "\n".join([f"• {i['identifier']}: {i['title']}" for i in issues])
        return list_text

    # /update (Command ID 3) - Format: /update [ID] [New Title]
    elif cmd_id == 3:
        parts = text.split(" ", 1)
        if len(parts) < 2: return "Usage: /update ENG-123 New Title"
        
        mutation = """
        mutation Update($id: String!, $title: String!) {
          issueUpdate(id: $id, input: { title: $title }) { success }
        }
        """
        query_linear(mutation, {"id": parts[0].upper(), "title": parts[1]})
        return f"✅ Updated {parts[0].upper()}"

    return "Unknown command."

def main(request):
    event = request.get_json()
    if event.get('type') == 'MESSAGE' and 'slashCommand' in event['message']:
        reply = handle_slash_command(event)
        return jsonify({"text": reply})
    return jsonify({"text": "Ready to help!"})
