from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# This connects to your LiteLLM server (which routes to Gemini 1.5 Flash)
# LiteLLM typically runs locally on port 4000
llm = ChatOpenAI(
    api_key="your-api-key", # Can be anything if LiteLLM handles the real keys
    base_url="http://0.0.0.0:4000", 
    model="gemini-1.5-flash" # LiteLLM will map this to the correct provider
)

def orchestrator_node(state: dict):
    """Plans the presentation structure."""
    user_prompt = state.get("user_prompt", "")
    
    # 1. Define the Agent's Persona and Instructions
    system_prompt = SystemMessage(content=(
        "You are the Lead Presentation Architect for senior business managers. "
        "Your job is to read the user's request and output a strict 5-slide markdown outline. "
        "Do not write the actual content, just the titles and bullet points of what each slide should cover."
    ))
    
    # 2. Provide the specific user request
    human_prompt = HumanMessage(content=f"Here is the user request: {user_prompt}")
    
    # 3. Call the LLM
    response = llm.invoke([system_prompt, human_prompt])
    
    # 4. Return the updated state
    return {"outline": response.content}

def latex_designer_node(state: dict):
    """Drafts the Beamer LaTeX code based on the outline."""
    outline = state.get("outline", "")
    error_log = state.get("error_log", "")
    current_code = state.get("tex_code", "")
    
    # Determine if we are writing from scratch or fixing an error
    if error_log:
        task_instruction = (
            f"The LaTeX compiler threw this error: {error_log}\n"
            f"Here is the broken code:\n{current_code}\n"
            "Fix the syntax errors and return ONLY the corrected complete LaTeX code."
        )
    else:
        task_instruction = (
            f"Write a complete LaTeX document using the 'beamer' document class based on this outline:\n{outline}\n"
            "Include \\usepackage{graphicx} and use \\includegraphics for visual placeholders."
        )

    system_prompt = SystemMessage(content=(
        "You are an expert LaTeX developer. "
        "Output ONLY raw, valid LaTeX code. Do not include markdown formatting like ```latex. "
        "Do not include any introductory or concluding text."
    ))
    
    human_prompt = HumanMessage(content=task_instruction)
    
    response = llm.invoke([system_prompt, human_prompt])
    
    # Clean the output just in case the LLM adds markdown backticks
    clean_code = response.content.replace("```latex", "").replace("```", "").strip()
    
    return {"tex_code": clean_code}

def critic_node(state: dict):
    """Analyzes compilation errors and adds a recommendation to the message history."""
    error_log = state.get("error_log", "")
    revision_count = state.get("revision_count", 0)
    
    system_prompt = SystemMessage(content=(
        "You are a LaTeX debugging assistant. Read the compiler error and provide a "
        "1-sentence explanation of what went wrong and how to fix it."
    ))
    
    human_prompt = HumanMessage(content=f"Error log: {error_log}")
    
    response = llm.invoke([system_prompt, human_prompt])
    
    # We append this advice to the 'messages' list in our state so the Designer can read it,
    # and we increment the revision count to protect the budget.
    return {
        "messages": [("ai", f"Critic Advice: {response.content}")],
        "revision_count": revision_count + 1
    }