import requests
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
load_dotenv()

# Connect to your local LiteLLM proxy to safely route to Gemini 1.5 Flash
llm = ChatOpenAI(
    api_key="<GEMINI_API_KEY>", 
    base_url="http://0.0.0.0:4000", 
    model="gemini-2.5-flash"
)

# Replace this with your backend server URL when deployed
BACKEND_URL = "http://127.0.0.1:8000"

def orchestrator_node(state: dict):
    """Plans the presentation structure."""
    user_prompt = state.get("user_prompt", "")
    data_summary = state.get("data_summary", "No data summary provided.")
    
    system_prompt = SystemMessage(content=(
        "You are the Lead Presentation Architect. "
        "Based on the user prompt and the data summary, output a strict 5-slide markdown outline. "
        "Provide only the titles and bullet points."
    ))
    human_prompt = HumanMessage(content=f"Prompt: {user_prompt}\nData Summary: {data_summary}")
    
    response = llm.invoke([system_prompt, human_prompt])
    return {"outline": response.content}


def data_analyst_node(state: dict):
    """Writes pandas code and sends it to the E2B sandbox backend for execution."""
    csv_path = state.get("csv_file_path", "")
    
    # 1. Ask the LLM to write the Python code
    system_prompt = SystemMessage(content=(
        "Write pure Python pandas code to analyze Q1 e-commerce sales. "
        "Assume the data is at '/home/user/sales_data.csv'. "
        "Print a short, factual summary of the top categories and regions. "
        "Do not output markdown, only the raw python code."
    ))
    code_response = llm.invoke([system_prompt, HumanMessage(content="Analyze the data.")])
    clean_code = code_response.content.replace("```python", "").replace("```", "").strip()
    
    # 2. Send the code to Member B's FastAPI server (E2B sandbox)
    try:
        res = requests.post(f"{BACKEND_URL}/run-analysis", json={
            "python_code": clean_code,
            "dataset_path": csv_path
        })
        result_data = res.json()
        summary = result_data.get("output", "Analysis failed.")
    except Exception as e:
        summary = f"Backend connection error: {e}"
        
    return {"data_summary": summary}


def latex_designer_node(state: dict):
    """Drafts or fixes the Beamer LaTeX code."""
    outline = state.get("outline", "")
    error_log = state.get("error_log", "")
    current_code = state.get("tex_code", "")
    
    if error_log:
        instruction = (
            f"The compiler threw this error: {error_log}\n"
            f"Broken code:\n{current_code}\n"
            "Fix the syntax errors and return ONLY the corrected complete LaTeX code."
        )
    else:
        instruction = (
            f"Write a complete Beamer LaTeX document based on this outline:\n{outline}\n"
            "Include \\usepackage{graphicx}."
        )

    system_prompt = SystemMessage(content=(
        "You are an expert LaTeX developer. Output ONLY raw, valid LaTeX code. "
        "Do not include markdown blocks or conversational text."
    ))
    
    response = llm.invoke([system_prompt, HumanMessage(content=instruction)])
    clean_code = response.content.replace("```latex", "").replace("```", "").strip()
    
    return {"tex_code": clean_code}


def compiler_node(state: dict):
    """Sends the LaTeX code to the Tectonic FastAPI endpoint."""
    tex_code = state.get("tex_code", "")
    revision_count = state.get("revision_count", 0)
    
    try:
        res = requests.post(f"{BACKEND_URL}/compile-latex", json={"tex_code": tex_code})
        data = res.json()
        
        if data.get("status") == "success":
            return {"error_log": "", "final_pdf_path": data.get("pdf_path"), "revision_count": revision_count + 1}
        else:
            return {"error_log": data.get("error_log", "Unknown error"), "revision_count": revision_count + 1}
    except Exception as e:
         return {"error_log": f"Compiler connection error: {e}", "revision_count": revision_count + 1}


def critic_node(state: dict):
    """Analyzes compilation errors to guide the designer."""
    error_log = state.get("error_log", "")
    
    system_prompt = SystemMessage(content="You are a LaTeX debugging assistant. Briefly explain how to fix this error.")
    response = llm.invoke([system_prompt, HumanMessage(content=f"Error log: {error_log}")])
    
    return {"messages": [f"Critic Advice: {response.content}"]}