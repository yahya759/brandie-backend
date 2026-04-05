from langgraph.graph import StateGraph, END
from app.agent.nodes import AgentState, agent_node, tools_node, should_continue

def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )

    graph.add_edge("tools", "agent")

    return graph.compile()


agent = build_agent()