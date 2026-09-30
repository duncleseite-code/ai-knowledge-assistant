from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings
from app.db import list_documents, list_notes, save_note


class LocalLLM:
    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=settings.lm_studio_base_url,
            api_key=settings.lm_studio_api_key,
        )

    def resolve_model(self) -> str:
        if settings.lm_studio_model:
            return settings.lm_studio_model
        models = self.client.models.list()
        if not models.data:
            raise RuntimeError("LM Studio server is running, but no model is loaded")
        return models.data[0].id

    def answer(self, question: str, context: str, history: list[dict]) -> str:
        model = self.resolve_model()
        system = (
            "You are a knowledge-base assistant. Answer using only the supplied CONTEXT. "
            "If the context does not contain enough information, clearly say that the knowledge base "
            "does not contain the answer. Do not invent facts. Answer in the same language as the user."
        )
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for item in history[-6:]:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append(
            {
                "role": "user",
                "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}",
            }
        )
        result = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        return (result.choices[0].message.content or "").strip()

    def agent(self, message: str, history: list[dict]) -> str:
        model = self.resolve_model()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_indexed_documents",
                    "description": "List documents currently indexed in the local knowledge base.",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_saved_notes",
                    "description": "List notes previously saved in the local SQLite database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "minimum": 1, "maximum": 50}
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "save_note",
                    "description": "Save a short user-requested note to the local SQLite database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["title", "content"],
                        "additionalProperties": False,
                    },
                },
            },
        ]
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a local assistant with tools. Use tools only when they are useful. "
                    "Only call save_note when the user explicitly asks to save or remember a note. "
                    "Answer in the user's language."
                ),
            }
        ]
        messages.extend({"role": x["role"], "content": x["content"]} for x in history[-6:])
        messages.append({"role": "user", "content": message})

        first = self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
        )
        assistant_message = first.choices[0].message
        if not assistant_message.tool_calls:
            return (assistant_message.content or "").strip()

        messages.append(assistant_message.model_dump(exclude_none=True))
        for tool_call in assistant_message.tool_calls:
            args = json.loads(tool_call.function.arguments or "{}")
            if tool_call.function.name == "list_indexed_documents":
                result: Any = list_documents()
            elif tool_call.function.name == "list_saved_notes":
                result = list_notes(limit=int(args.get("limit", 20)))
            elif tool_call.function.name == "save_note":
                result = save_note(args["title"], args["content"])
            else:
                result = {"error": "Unknown tool"}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

        final = self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=0.2,
        )
        return (final.choices[0].message.content or "").strip()


local_llm = LocalLLM()
