"""
agent_client.py
Direct Line client for Copilot Studio agent.

Uses the Web channel security secret to authenticate.
Pure HTTP — no MSAL, no SDK dependencies.
"""

import time
import uuid
from typing import Generator, Optional

import requests


class DirectLineError(Exception):
    pass


class CopilotStudioAgent:
    """Talks to a Copilot Studio agent via Direct Line REST API."""

    # Microsoft's classic Direct Line endpoint — works for Copilot Studio agents
    # that have a Web channel security secret configured.
    DIRECTLINE_BASE = "https://directline.botframework.com/v3/directline"

    def __init__(self, secret: str, timeout: int = 30):
        self.secret = secret
        self.timeout = timeout
        self.conversation_id: Optional[str] = None
        self.token: Optional[str] = None
        self.watermark: Optional[str] = None

    def start_conversation(self):
        """Open a new Direct Line conversation. Returns conversation_id."""
        resp = requests.post(
            f"{self.DIRECTLINE_BASE}/conversations",
            headers={
                "Authorization": f"Bearer {self.secret}",
                "Content-Type": "application/json",
            },
            json={},
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise DirectLineError(
                f"start_conversation failed: {resp.status_code} {resp.text}"
            )
        data = resp.json()
        self.conversation_id = data["conversationId"]
        self.token = data.get("token", self.secret)
        self.watermark = None
        return self.conversation_id

    def _auth_header(self):
        # Use the conversation token if we have one, otherwise the secret
        bearer = self.token or self.secret
        return {"Authorization": f"Bearer {bearer}"}

    def send_message(self, text: str, user_id: str = "streamlit-user"):
        """Send a user message to the conversation."""
        if not self.conversation_id:
            self.start_conversation()

        activity = {
            "type": "message",
            "from": {"id": user_id, "name": user_id},
            "text": text,
        }
        resp = requests.post(
            f"{self.DIRECTLINE_BASE}/conversations/{self.conversation_id}/activities",
            headers={**self._auth_header(), "Content-Type": "application/json"},
            json=activity,
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise DirectLineError(
                f"send_message failed: {resp.status_code} {resp.text}"
            )
        return resp.json()

    def get_activities(self):
        """Get new activities from the bot since last watermark."""
        url = f"{self.DIRECTLINE_BASE}/conversations/{self.conversation_id}/activities"
        if self.watermark:
            url += f"?watermark={self.watermark}"

        resp = requests.get(url, headers=self._auth_header(), timeout=self.timeout)
        if resp.status_code >= 400:
            raise DirectLineError(
                f"get_activities failed: {resp.status_code} {resp.text}"
            )
        data = resp.json()
        self.watermark = data.get("watermark", self.watermark)
        return data.get("activities", [])

    def wait_for_bot_reply(
        self,
        user_id: str = "streamlit-user",
        max_wait_sec: int = 45,
        poll_interval_sec: float = 1.0,
    ) -> str:
        """
        Poll for bot responses until we get one or timeout.
        Returns the concatenated text of all bot messages.
        """
        end_at = time.time() + max_wait_sec
        collected = []
        saw_bot_reply = False

        # The bot typically sends 2+ activities: a typing indicator, then message(s).
        # We wait for at least one 'message' activity from someone other than us
        # that has text content. Then grab a little more in case of multi-part.

        while time.time() < end_at:
            activities = self.get_activities()
            for act in activities:
                if act.get("type") != "message":
                    continue
                from_id = (act.get("from") or {}).get("id", "")
                if from_id == user_id:
                    continue  # echo of our own message
                text = act.get("text")
                if text:
                    collected.append(text)
                    saw_bot_reply = True

            if saw_bot_reply:
                # Wait briefly for any trailing parts then stop
                time.sleep(1.5)
                extras = self.get_activities()
                for act in extras:
                    if act.get("type") != "message":
                        continue
                    from_id = (act.get("from") or {}).get("id", "")
                    if from_id == user_id:
                        continue
                    text = act.get("text")
                    if text:
                        collected.append(text)
                break

            time.sleep(poll_interval_sec)

        if not collected:
            raise DirectLineError(f"No bot reply within {max_wait_sec}s")

        return "\n\n".join(collected)

    def ask(self, prompt: str, max_wait_sec: int = 45) -> str:
        """Send a prompt, wait for the bot's reply, return the text."""
        if not self.conversation_id:
            self.start_conversation()
        self.send_message(prompt)
        return self.wait_for_bot_reply(max_wait_sec=max_wait_sec)

    def close(self):
        self.conversation_id = None
        self.token = None
        self.watermark = None


if __name__ == "__main__":
    import os
    import sys

    secret = os.environ.get("COPILOT_SECRET") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not secret:
        print("Usage: python agent_client.py <secret>  OR set COPILOT_SECRET")
        sys.exit(1)

    print("Starting agent...")
    agent = CopilotStudioAgent(secret)
    agent.start_conversation()
    print(f"Conversation: {agent.conversation_id}")

    print("\nSending: 'score BT-024'")
    reply = agent.ask("score BT-024", max_wait_sec=45)
    print("\n--- BOT REPLY ---")
    print(reply)
    print("--- END ---")
