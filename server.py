from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
from e2b import Sandbox

app = FastAPI(title="Agentic Presentation Backend")

# Run the server using this command: uvicorn server:app --reload
# You can view the automatic interactive documentation by navigating to http://127.0.0.1:8000/docs

# --- Data Models ---
class TexRequest(BaseModel):
    tex_code: str

class CodeRequest(BaseModel):
    python_code: str
    dataset_path: str

# --- Tool 1: The LaTeX Compiler (Tectonic) ---
@app.post("/compile-latex")
def compile_latex(request: TexRequest):
    """Takes raw LaTeX code, saves it, and compiles it using Tectonic."""
    
    # 1. Save the code to a temporary file
    with open("temp_presentation.tex", "w") as f:
        f.write(request.tex_code)
        
    # 2. Run Tectonic via subprocess
    try:
        # Tectonic automatically downloads missing packages
        result = subprocess.run(
            ["tectonic", "temp_presentation.tex"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return {"status": "success", "pdf_path": "temp_presentation.pdf", "logs": result.stdout}
        
    except subprocess.CalledProcessError as e:
        # 3. If it fails, capture the error log for the Critic Agent
        return {"status": "error", "error_log": e.stderr}


# --- Tool 2: Safe Python Execution (E2B) ---
@app.post("/run-analysis")
def run_data_analysis(request: CodeRequest):
    """Executes the Data Analyst agent's pandas code in a secure E2B sandbox."""
    
    try:
        # Initialize a secure cloud sandbox
        sandbox = Sandbox()
        
        # Upload the CSV to the sandbox
        with open(request.dataset_path, "rb") as f:
            sandbox.filesystem.write("/home/user/sales_data.csv", f.read())
            
        # Run the agent's Python code
        execution = sandbox.process.start_and_wait(f"python -c '{request.python_code}'")
        
        sandbox.close()
        
        if execution.exit_code == 0:
            return {"status": "success", "output": execution.stdout}
        else:
            return {"status": "error", "error_log": execution.stderr}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))