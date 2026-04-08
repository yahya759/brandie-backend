import os
import json
import logging
import asyncio

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
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
]


async def call_openrouter_chat(messages: list, tools=None) -> dict:
    key1 = os.getenv("OPENROUTER_API_KEY")
    key2 = os.getenv("OPENAI_API_KEY")
    
    if key1 and str(key1).startswith("sk-or-v1-"):
        api_key = key1
    elif key2 and str(key2).startswith("sk-or-v1-"):
        api_key = key2
    else:
        api_key = key1 or key2 or ""
    
    if not api_key:
        raise Exception("OPENROUTER_API_KEY not set")

    extra_headers = {
        "HTTP-Referer": "https://huggingface.co/spaces/Yahya23112003/brandie-backend",
        "X-Title": "Brandie AI Assistant",
    }

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=extra_headers,
    )

    FALLBACK_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "deepseek/deepseek-r1-distill-llama-70b:free",
    ]

    TOOL_SUPPORTED_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
    ]

    models_to_try = TOOL_SUPPORTED_MODELS if tools else FALLBACK_MODELS

    for model in models_to_try:
        try:
            print(f"Trying {model}...")
            
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
                payload["tools"] = tools

            response = await client.chat.completions.create(**payload, timeout=45.0)
            
            return {
                "choices": [{
                    "message": {
                        "content": response.choices[0].message.content or "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                },
                                "id": tc.id
                            }
                            for tc in (response.choices[0].message.tool_calls or [])
                        ]
                    }
                }]
            }
            
        except Exception as inner_e:
            inner_str = str(inner_e)
            inner_status = getattr(getattr(inner_e, "response", None), "status_code", 0)
            
            if inner_status in [401, 429, 500, 503] or any(
                x in inner_str for x in ["429", "500", "503", "timeout", "404", "rate"]
            ):
                logger.warning(f"Model {model} failed: {inner_status} {inner_str[:100]}")
                if inner_status == 429:
                    await asyncio.sleep(3)
                continue
            raise

    raise Exception("All AI nodes are currently busy. Please try again later.")


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
    
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_msg = msg.get("content", "").lower()
            break
    
    wants_post = any(x in last_user_msg for x in ["نشر", "post", "publish", "انشر", "رفع"])
    
    for attempt in range(3):
        try:
            result = asyncio.run(call_openrouter_chat(messages, tools=all_tools))
            
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            tool_calls = result.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
            
            if wants_post and not tool_calls and attempt < 2:
                logger.warning(f"Text fallback detected on attempt {attempt + 1}, retrying...")
                messages.append({"role": "user", "content": content})
                messages.append({"role": "user", "content": "Please execute the Instagram tool to post this content."})
                continue
            
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
            if "All AI nodes" in str(e):
                error_content = str(e)
                error_msg = AIMessage(content=error_content)
                return {
                    "messages": [error_msg],
                    "user_id": state["user_id"],
                    "image_path": state.get("image_path"),
                    "pending_post": state.get("pending_post")
                }
            if attempt < 2:
                continue
    
    error_content = "عذراً، حدث خطأ. حاول مرة ثانية."
    error_msg = AIMessage(content=error_content)
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
        
        raw_args = tool_call.get("args")
        if raw_args is None:
            args_dict = {}
        elif isinstance(raw_args, dict):
            args_dict = raw_args
        elif isinstance(raw_args, str):
            try:
                args_dict = json.loads(raw_args)
            except json.JSONDecodeError:
                args_dict = {"caption": raw_args}
        else:
            args_dict = {}
        
        tool_args = {k: v for k, v in args_dict.items() if v is not None}

        if tool_name in ["publish_now_tool", "schedule_post_tool"]:
            if state.get("user_id"):
                tool_args["user_id"] = state["user_id"]
            if state.get("image_path"):
                tool_args["image_path"] = state["image_path"]

        if not tool_args:
            tool_messages.append(
                ToolMessage(content="خطأ: لا توجد بيانات للمعالجة", tool_call_id=tool_call["id"])
            )
            continue

        tool_fn = tool_map.get(tool_name)
        if tool_fn:
            try:
                result = tool_fn.invoke(tool_args)
            except Exception as e:
                logger.error(f"Tool {tool_name} error: {e}")
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