"""ESP custom window: forwards each incoming event to an Azure AI Foundry agent over A2A and publishes the agent's reply as a new event on OUTPUT_WINDOW.
"""

import json
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor


import esp
import requests

LOGGING_CONTEXT = "DF.ESP.CUSTOM.A2A"
AZURE_CLIENT_ID = None
AZURE_TENANT_ID = None
AZURE_CLIENT_SECRET = None
FOUNDRY_PROJECT_ENDPOINT = None
OUTPUT_WINDOW = None
REQUEST_TIMEOUT = 120

TOKEN_URL = None
TOKEN_SCOPE = "https://ai.azure.com/.default"

output_id = 1
output_id_lock = threading.Lock()
token_lock = threading.Lock()
token_cache = {"access_token": None, "expires_at": 0.0}

# Bounds how many Foundry calls run concurrently so one slow agent call can't stall the window.
EXECUTOR = ThreadPoolExecutor(max_workers=4)


def init(settings):
    """ESP lifecycle hook: read window properties and fail fast if required settings are missing."""
    global AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET
    global FOUNDRY_PROJECT_ENDPOINT, OUTPUT_WINDOW, TOKEN_URL

    AZURE_TENANT_ID = settings.get("AZURE_TENANT_ID")
    AZURE_CLIENT_ID = settings.get("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = settings.get("AZURE_CLIENT_SECRET")
    FOUNDRY_PROJECT_ENDPOINT = settings.get("FOUNDRY_PROJECT_ENDPOINT")
    OUTPUT_WINDOW = settings.get("OUTPUT_WINDOW")

    required = {
        "AZURE_TENANT_ID": AZURE_TENANT_ID,
        "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
        "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
        "FOUNDRY_PROJECT_ENDPOINT": FOUNDRY_PROJECT_ENDPOINT,
        "OUTPUT_WINDOW": OUTPUT_WINDOW,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing required window settings: {', '.join(missing)}")

    TOKEN_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"


def log(message, level="info"):
    """Write a message to the ESP project log under the log context."""
    esp.logMessage(
        logcontext=LOGGING_CONTEXT,
        message=message,
        level=level,
    )


def get_access_token():
    """Return a cached Entra ID access token, requesting a new one via client credentials if expired."""
    now = time.time()

    with token_lock:
        if token_cache["access_token"] and now < token_cache["expires_at"]:
            return token_cache["access_token"]

        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": AZURE_CLIENT_ID,
                "client_secret": AZURE_CLIENT_SECRET,
                "scope": TOKEN_SCOPE,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        token_info = response.json()
        token = token_info.get("access_token")
        if not token:
            raise ValueError("Access token not found")

        token_cache["access_token"] = token
        token_cache["expires_at"] = now + max(
            int(token_info.get("expires_in", 3600)) - 60,
            0,
        )

        return token


def build_rpc_request(data):
    """Wrap an ESP event as an A2A JSON-RPC message/send request, blocking until the agent replies."""
    message_id = uuid.uuid4().hex

    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": json.dumps(data),
                    },
                ],
            },
            "configuration": {
                "blocking": True,
            },
        },
    }


def extract_agent_text(result):
    """Pull the agent's reply text out of an A2A result, trying artifacts, then history, then parts."""
    if not isinstance(result, dict):
        return None

    for artifact in result.get("artifacts") or []:
        for part in artifact.get("parts") or []:
            text = part.get("text")
            if text:
                return text

    for message in reversed(result.get("history") or []):
        if message.get("role") == "agent":
            for part in message.get("parts") or []:
                text = part.get("text")
                if text:
                    return text

    for part in result.get("parts") or []:
        text = part.get("text")
        if text:
            return text

    return None


def call_to_agent(data):
    """Send one event to the Foundry agent and publish its reply to OUTPUT_WINDOW; runs on a worker thread."""
    global output_id

    # Generate a short correlation ID for logging purposes
    correlation_id = str(uuid.uuid4())[:8]

    try:
        log(f"[{correlation_id}] Sending event to Foundry")

        token = get_access_token()
        rpc_request = build_rpc_request(data)

        response = requests.post(
            FOUNDRY_PROJECT_ENDPOINT,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=rpc_request,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        rpc_response = response.json()
        if rpc_response.get("error"):
            raise ValueError(f"A2A error: {rpc_response['error']}")

        agent_text = extract_agent_text(rpc_response.get("result"))
        if agent_text is None:
            log(
                f"[{correlation_id}] No text in Foundry response",
                level="warning",
            )
            agent_text = ""

        log(f"[{correlation_id}] Foundry response: {agent_text}")

        with output_id_lock:
            event_id = output_id
            output_id += 1

        esp.publish(
            window=OUTPUT_WINDOW,
            events={
                "id": event_id,
                "input_body": json.dumps(data),
                "message": str(agent_text)
            },
        )

    except Exception as error:
        log(
            f"[{correlation_id}] Foundry error: "
            f"{type(error).__name__}: {error}",
            level="error",
        )


def create(data, context):
    """ESP events callback: hand the event off to a worker thread so the window never blocks on Foundry."""
    EXECUTOR.submit(call_to_agent, data)
    return data


def destroy():
    """ESP lifecycle hook: stop accepting new work and let in-flight Foundry calls finish in the background."""
    EXECUTOR.shutdown(wait=False)



_espconfig_ = {
    "settings" : {
        "desc" : "",
        "expand_parms" : False,
        "process_blocks" : False,
        "encode_binary" : False
    },
    "initialization" : {
        "desc" : "",
        "fields" : [
            {
                "name": "AZURE_TENANT_ID",
                "desc": "The Directory (tenant) ID of the Microsoft Entra ID application registration created for this agent."
            },
            {
                "name": "AZURE_CLIENT_ID",
                "desc": "The Application (client) ID of the Microsoft Entra ID application registration created for this agent."
            },
            {
                "name": "AZURE_CLIENT_SECRET",
                "desc": "The client secret Value (not the Secret ID) generated under Certificates & secrets for the application registration."
            },
            {
                "name": "FOUNDRY_PROJECT_ENDPOINT",
                "desc": "The A2A endpoint copied from the published agent's Details page in Azure AI Foundry."
            },
            {
                "name": "OUTPUT_WINDOW",
                "desc": "The ESP window that receives the agent's response as a new event.",
                "default": "cq1/Source"
            }
        ]
    }
}
'''metadata start
{
    "name": "A2A Azure Foundry Agent Call",
    "description": "Connects ESP to any of your own Azure AI Foundry agents over the A2A protocol. Just fill in your Azure and Foundry project details in the window's properties, and it sends each incoming event to your agent and publishes the response as a new event.",
    "libraries": [
        {
            "name": "requests",
            "operator": "~=",
            "version": "2.34"
        }
    ]
}
metadata end'''