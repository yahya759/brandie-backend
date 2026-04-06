import os
import json
import logging

from openai import AsyncOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import all_tools
from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    image_path: str | None
    pending_post: dict | None


FALLBACK_MODELS = [
    "meta-llama/llama-3-8b-instruct",
    "google/gemini-pro-1.5",
    "mistralai/mistral-7b-instruct",
]


def call_openrouter_chat(messages: list, tools=None) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if not api_key:
        raise Exception("OPENROUTER_API_KEY not set")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    for model in FALLBACK_MODELS:
        try:
            logger.info(f"Trying model: {model}")

            openai_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    openai_messages.append(msg)
                elif isinstance(msg, (HumanMessage, AIMessage)):
                    openai_messages.append({
                        "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                        "content": msg.content
                    })

            payload = {
                "model": model,
                "messages": openai_messages,
                "temperature": 0.7,
            }

            if tools:
                payload["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": "generate_caption_tool",
                            "description": "Generate a professional Instagram caption with hashtags.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "topic": {"type": "string", "description": "The topic or theme of the post"},
                                    "tone": {"type": "string", "description": "The tone (engaging, inspirational, professional, humorous)", "default": "engaging"}
                                },
                                "required": ["topic"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "generate_image_prompt_tool",
                            "description": "Generate an English image prompt for AI image generators",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "topic": {"type": "string", "description": "The topic of the post in Arabic or English"}
                                },
                                "required": ["topic"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "publish_now_tool",
                            "description": "Publish a post to Instagram immediately.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "caption": {"type": "string", "description": "The post caption"},
                                    "hashtags": {"type": "string", "description": "Hashtags string"}
                                },
                                "required": ["caption", "hashtags"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "schedule_post_tool",
                            "description": "Schedule a post to be published at a specific time.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "caption": {"type": "string", "description": "The post caption"},
                                    "hashtags": {"type": "string", "description": "Hashtags string"},
                                    "scheduled_time_str": {"type": "string", "description": "Time string like 'tomorrow 8am' or '2025-01-15 08:00'"}
                                },
                                "required": ["caption", "hashtags", "scheduled_time_str"]
                            }
                        }
                    }
                ]

            import asyncio
            response = asyncio.run(client.chat.completions.create(**payload))
            return {
                "choices": [{
                    "message": {
                        "content": response.choices[0].message.content or "",
                        "tool_calls": [
                            {"function": {"name": tc.function.name, "arguments": json.dumps(tc.function.arguments)}, "id": tc.id}
                            for tc in response.choices[0].message.tool_calls or []
                        ]
                    }
                }]
            }

        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            continue

    raise Exception("All fallback models failed")


def agent_node(state: AgentState) -> AgentState:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            if hasattr(msg, "content") and msg.content:
                messages.append({"role": "assistant", "content": msg.content})
    
    context = []
    if state.get("image_path"):
        context.append(f"[المستخدم رفع صورة: {state['image_path']}]")
    if state.get("pending_post"):
        context.append(f"[منشور معلق للموافقة: {state['pending_post']}]")
    
    if context:
        messages.append({"role": "user", "content": "\n".join(context)})
    
    try:
        result = call_openrouter_chat(messages, tools=all_tools)
        
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        tool_calls = result.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
        
        response = AIMessage(content=content)
        if tool_calls:
            response.tool_calls = [
                {"name": tc["function"]["name"], "args": json.loads(tc["function"]["arguments"]), "id": tc.get("id", "")}
                for tc in tool_calls
            ]
        
        return {
            "messages": [response],
            "user_id": state["user_id"],
            "image_path": state.get("image_path"),
            "pending_post": state.get("pending_post")
        }
    except Exception as e:
        logger.error(f"Agent node error: {e}")
        error_msg = AIMessage(content="عذراً، حدث خطأ. حاول مرة ثانية.")
        return {
            "messages": [error_msg],
            "user_id": state["user_id"],
            "image_path": state.get("image_path"),
            "pending_post": state.get("pending_post")
        }


def tools_node(state: AgentState) -> AgentState:
    from langchain_core.messages import ToolMessage
    from app.agent.tools import (
        publish_now_tool,
        schedule_post_tool,
        generate_caption_tool,
        generate_image_prompt_tool,
    )

    tool_map = {
        "publish_now_tool": publish_now_tool,
        "schedule_post_tool": schedule_post_tool,
        "generate_caption_tool": generate_caption_tool,
        "generate_image_prompt_tool": generate_image_prompt_tool,
    }

    last_message = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = dict(tool_call["args"])

        if tool_name in ["publish_now_tool", "schedule_post_tool"]:
            tool_args["user_id"] = state["user_id"]
            if state.get("image_path"):
                tool_args["image_path"] = state["image_path"]

        tool_fn = tool_map.get(tool_name)
        if tool_fn:
            try:
                result = tool_fn.invoke(tool_args)
            except Exception as e:
                result = f"خطأ في تنفيذ الأداة: {str(e)}"
        else:
            result = f"أداة غير موجودة: {tool_name}"

        tool_messages.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )

    return {
        "messages": tool_messages,
        "user_id": state["user_id"],
        "image_path": state.get("image_path"),
        "pending_post": state.get("pending_post")
    }


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"