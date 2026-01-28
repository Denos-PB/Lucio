from langgraph.graph import StateGraph
from .state import OverallState
from .configuration import Configuration
from .node import AgentNodes

def build_graph() -> StateGraph:
    config = Configuration()
    nodes = AgentNodes(config)

    graph = StateGraph(OverallState)

    graph.add_node("planning", nodes.planning_node)
    graph.add_node("perception", nodes.perception_node)
    graph.add_node("web" , nodes.web_node)
    graph.add_node("content", nodes.content_node)

    graph.set_entry_point("planning")
    graph.add_edge("planning", "perception")
    graph.add_edge("perception", "web")
    graph.add_edge("web", "content")

    return graph

    