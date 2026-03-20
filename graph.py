from langgraph.graph import StateGraph, END
from state import PresentationState
from agents import (
    orchestrator_node, 
    data_analyst_node, 
    latex_designer_node, 
    compiler_node, 
    critic_node
)

def route_compilation(state: dict) -> str:
    """Traffic controller for the LaTeX compilation loop."""
    error_log = state.get("error_log", "")
    revision_count = state.get("revision_count", 0)
    
    if not error_log:
        print("✅ Compilation successful!")
        return "success" 
        
    if revision_count >= 3:
        print(f"🛑 Hit max revisions ({revision_count}). Aborting to protect budget.")
        return "max_revisions" 
        
    print(f"⚠️ Compilation failed. Sending to Critic (Attempt {revision_count + 1}/3)")
    return "critic"

# 1. Initialize the Graph
workflow = StateGraph(PresentationState)

# 2. Add Nodes
workflow.add_node("data_analyst", data_analyst_node)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("latex_designer", latex_designer_node)
workflow.add_node("compiler", compiler_node)
workflow.add_node("critic", critic_node)

# 3. Define the Flow
workflow.set_entry_point("data_analyst")
workflow.add_edge("data_analyst", "orchestrator")
workflow.add_edge("orchestrator", "latex_designer")
workflow.add_edge("latex_designer", "compiler")

# 4. The Conditional Loop
workflow.add_conditional_edges(
    "compiler",
    route_compilation,
    {
        "success": END,
        "max_revisions": END,
        "critic": "critic"
    }
)
workflow.add_edge("critic", "latex_designer")

# 5. Compile the App
app = workflow.compile()

# --- Test Execution Block ---
if __name__ == "__main__":
    print("🚀 Starting Agentic Presentation Workflow...")
    
    # Initial inputs
    initial_state = {
        "user_prompt": "Create a short presentation explaining the Q1 sales performance. Audience: senior business managers.",
        "csv_file_path": "./sales_data.csv",
        "revision_count": 0,
        "messages": []
    }
    
    # Run the graph
    for output in app.stream(initial_state):
        # Print the current node being executed
        for key, value in output.items():
            print(f"\n--- Finished Node: {key} ---")
            
    print("\n🎉 Workflow Complete!")