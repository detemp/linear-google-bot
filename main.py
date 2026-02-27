import os
import re
import requests
from flask import jsonify

# 1. Configuration & Secrets
# These are pulled from Google Secret Manager via your cloudbuild.yaml
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID")
LABEL_BUG_ID = os.getenv("LABEL_BUG_ID")       # Add this to Secret Manager
LABEL_FEATURE_ID = os.getenv("LABEL_FEATURE_ID") # Add this to Secret Manager

LINEAR_URL = "https://api.linear.app/graphql"
HEADERS = {
    "Authorization": LINEAR_API_KEY,
    "Content-Type": "application/json"
}

def query_linear(query, variables=None):
    """Utility to send GraphQL requests to Linear."""
    response = requests.post(
        LINEAR_URL, 
        json={'query': query, 'variables': variables}, 
        headers=HEADERS
    )
    return response.json()

def parse_metadata(text):
    """
    Parses text for priority and labels.
    Returns: (cleaned_text, priority_int, label_ids_list)
    """
    priority_map = {"urgent": 1, "high": 2, "medium": 3, "low": 4}
    found_priority = 0  # Default to 'No Priority'
    found_labels = []
    
    # Check for priority keywords
    for word, val in priority_map.items():
        if re.search(rf'\b{word}\b', text, re.IGNORECASE):
            found_priority = val
            # Strip keyword from title
            text = re.sub(rf'\b{word}\b', '', text, flags=re.IGNORECASE).strip()
            break # Take the first priority found

    # Auto-labeling logic
    if re.search(r'\bbug\b', text, re.IGNORECASE):
        if LABEL_BUG_ID: found_labels.append(LABEL_BUG_ID)
        text = re.sub(r'\bbug\b', '', text, flags=re.IGNORECASE).strip()
        
    if re.search(r'\b(feat|request|feature)\b', text, re.IGNORECASE):
        if LABEL_FEATURE_ID: found_labels.append(LABEL_FEATURE_ID)
        text = re.sub(r'\b(feat|request|feature)\b', '', text, flags=re.IGNORECASE).strip()

    # Clean up double spaces left behind by removals
    text = re.sub(r'\s+', ' ', text).strip()
    return text, found_priority, found_labels

def handle_slash_command(event):
    """Routes the Google Chat Command ID to the correct Linear action."""
    message = event.get('message', {})
    
    # Grab the text in case it was typed manually without the popup
    raw_text = message.get('text', '').strip()
    argument_text = message.get('argumentText', '').strip()
    
    # Safely get the command ID
    slash_command = message.get('slashCommand', {})
    command_id = str(slash_command.get('commandId', ''))

    # MANUAL OVERRIDE: If no command_id was sent, parse the raw text
    if not command_id:
        # Using 'in' instead of 'startswith' to bypass invisible @mentions
        if '/new' in raw_text:
            command_id = "1"
            # Extract everything after '/new'
            parts = raw_text.split('/new', 1)
            argument_text = parts[1].strip() if len(parts) > 1 else ""
        elif '/list' in raw_text:
            command_id = "2"
        elif '/update' in raw_text:
            command_id = "3"
            parts = raw_text.split('/update', 1)
            argument_text = parts[1].strip() if len(parts) > 1 else ""
        else:
            return "I'm not sure how to handle that command yet."

    # COMMAND 1: /new [Title] [Keywords]
    if command_id == "1":
        if not argument_text:
            return "⚠️ Please provide a title. Example: `/new urgent bug Permit API is down`"
        
        clean_title, priority, labels = parse_metadata(argument_text)
        
        mutation = """
        mutation CreateIssue($title: String!, $teamId: String!, $priority: Int, $labelIds: [String!]) {
          issueCreate(input: { title: $title, teamId: $teamId, priority: $priority, labelIds: $labelIds }) {
            success
            issue { identifier url title }
          }
        }
        """
        variables = {
            "title": clean_title,
            "teamId": LINEAR_TEAM_ID,
            "priority": priority,
            "labelIds": labels
        }
        
        res = query_linear(mutation, variables)
        if res.get('data', {}).get('issueCreate', {}).get('success'):
            issue = res['data']['issueCreate']['issue']
            return f"✅ *Created {issue['identifier']}*\n*{issue['title']}*\n{issue['url']}"
        return "❌ Failed to create issue. Check Linear Team ID or API Key."

    # COMMAND 2: /list
    elif command_id == "2":
        query = """
        query ListIssues($teamId: String!) {
          issues(filter: { team: { id: { eq: $teamId } } }, first: 5, orderBy: createdAt) {
            nodes { identifier title url }
          }
        }
        """
        res = query_linear(query, {"teamId": LINEAR_TEAM_ID})
        issues = res.get('data', {}).get('issues', {}).get('nodes', [])
        
        if not issues:
            return "No recent issues found for your team."
            
        list_output = "*Recent Permittable Issues:*\n"
        for i in issues:
            list_output += f"• <{i['url']}|{i['identifier']}>: {i['title']}\n"
        return list_output

    # COMMAND 3: /update [ID] [New Title]
    elif command_id == "3":
        parts = argument_text.split(" ", 1)
        if len(parts) < 2:
            return "⚠️ Usage: `/update ENG-123 New better title`"
        
        issue_id = parts[0].upper()
        new_title = parts[1]
        
        mutation = """
        mutation UpdateIssue($id: String!, $title: String!) {
          issueUpdate(id: $id, input: { title: $title }) {
            success
          }
        }
        """
        res = query_linear(mutation, {"id": issue_id, "title": new_title})
        if res.get('data', {}).get('issueUpdate', {}).get('success'):
            return f"✅ Updated title for *{issue_id}*."
        return f"❌ Could not find or update issue *{issue_id}*."

    return "I'm not sure how to handle that command yet."


def main(request):
    """Entry point for Google Cloud Function / Cloud Run."""
    if request.method != 'POST':
        return "Only POST requests accepted", 405
        
    event = request.get_json(silent=True)
    if not event:
        return "No JSON payload found", 400

    # Workspace Add-ons nest the Chat event inside a 'chat' object. 
    # This safely un-nests it.
    chat_data = event.get('chat', event)

    # Now we can properly check for the message
    if 'message' in chat_data:
        reply_text = handle_slash_command(chat_data)
    else:
        # Fallback for configuration pings or space joins
        reply_text = "Hello! Try using `/new`, `/list`, or `/update`."

    return jsonify({
        "hostAppDataAction": {
            "chatDataAction": {
                "createMessageAction": {
                    "message": {
                        "text": reply_text
                    }
                }
            }
        }
    })
            }
        }
    })
