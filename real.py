import openai
import os
import subprocess
import tempfile
from docx import Document
from docx.shared import Inches
import sys

# Configuration
OPENAI_API_KEY = 'paste-key-here'  # Replace with your OpenAI API key
MODEL = 'gpt-4o-mini'  # You can use other models like 'gpt-3.5-turbo' if needed
TEMPDIR = tempfile.gettempdir()

# Set OpenAI API key
client = openai.Client(api_key=OPENAI_API_KEY)

def read_questions(file_path):
    """
    Reads questions from a text file. Each question should be separated by a blank line.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    questions = [q.strip() for q in content.split('\n\n') if q.strip()]
    return questions

def generate_solution(question):
    """
    Uses OpenAI's API to generate a solution for the given C programming question.
    Returns the solution code and explanation.
    """
    prompt = f"""
    You are an expert C programmer. Provide a clear and concise solution to the following programming problem. Include the C code with proper formatting. Only output the code. DO NOT WRITE ANYTHING ELSE LIKE EXPLAINATION.

    Problem:
    {question}

    Solution:
    """

    try:
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are ChatGPT, an AI language model that provides detailed and accurate programming solutions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.2,
        )
        solution = response.choices[0].message.content.strip()
        return solution
    except Exception as e:
        print(f"Error generating solution for question: {question}\nError: {e}")
        return None

def extract_code(solution_text):
    """
    Extracts C code from the solution text enclosed within code blocks.
    """
    import re
    code_pattern = re.compile(r'```c(.*?)```', re.DOTALL)
    match = code_pattern.search(solution_text)
    if match:
        return match.group(1).strip()
    else:
        # Try without specifying language
        code_pattern = re.compile(r'```(.*?)```', re.DOTALL)
        match = code_pattern.search(solution_text)
        if match:
            return match.group(1).strip()
    return None

def compile_and_run_c_code(c_code):
    """
    Compiles and runs the provided C code.
    Returns the output or error messages.
    """
    return "" # this won't work because programs require input
    with tempfile.NamedTemporaryFile(delete=False, suffix='.c', dir=TEMPDIR) as c_file:
        c_file_name = c_file.name
        c_file.write(c_code.encode('utf-8'))

    exe_file = c_file_name.replace('.c', '.exe') if os.name == 'nt' else c_file_name.replace('.c', '')

    # Compile the C code
    compile_cmd = ['gcc', c_file_name, '-o', exe_file]
    try:
        compile_process = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=10)
        if compile_process.returncode != 0:
            os.unlink(c_file_name)
            error_message = f"Compilation failed:\n{compile_process.stderr}"
            return error_message
    except subprocess.TimeoutExpired:
        os.unlink(c_file_name)
        error_message = "Compilation timed out."
        return error_message

    # Run the executable
    run_cmd = [exe_file]
    try:
        run_process = subprocess.run(run_cmd, capture_output=True, text=True, timeout=10)
        output = run_process.stdout
        if run_process.stderr:
            output += f"\nRuntime Errors:\n{run_process.stderr}"
    except subprocess.TimeoutExpired:
        output = "Execution timed out."
    except Exception as e:
        output = f"Error during execution: {e}"

    # Clean up temporary files
    os.unlink(c_file_name)
    if os.path.exists(exe_file):
        os.unlink(exe_file)

    return output.strip()

def create_docx(qa_list, output_path):
    """
    Creates a Word document with questions, solutions, and outputs.
    """
    document = Document()
    document.add_heading('C Programming Solutions', 0)

    for idx, qa in enumerate(qa_list, 1):
        question = qa['question']
        solution = qa['solution']
        output = qa['output']

        document.add_heading(f'Question {idx}', level=1)
        document.add_paragraph(question)

        document.add_heading('Solution', level=2)
        # Split solution into code and explanation
        code = extract_code(solution)
        if code:
            explanation = solution.replace(f'```c\n{code}\n```', '').strip()
            document.add_paragraph(explanation)
            document.add_paragraph('C Code:')
            code_paragraph = document.add_paragraph()
            # code_paragraph.style = 'Preformatted'
            code_paragraph.add_run(code)
        else:
            # If no code block found, add entire solution as explanation
            document.add_paragraph(solution)

        document.add_heading('Output', level=2)
        output_paragraph = document.add_paragraph()
        # output_paragraph.style = 'Preformatted'
        output_paragraph.add_run(output)

        document.add_page_break()

    document.save(output_path)
    print(f"Document saved to {output_path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_solutions.py questions.txt")
        sys.exit(1)

    questions_file = sys.argv[1]
    if not os.path.exists(questions_file):
        print(f"File not found: {questions_file}")
        sys.exit(1)

    questions = read_questions(questions_file)
    print(f"Found {len(questions)} questions.")

    qa_list = []
    for idx, question in enumerate(questions, 1):
        print(f"Processing Question {idx}: {question[:60]}...")
        solution = generate_solution(question)
        if not solution:
            solution = "Failed to generate solution."
            output = "N/A"
        else:
            code = extract_code(solution)
            if code:
                output = compile_and_run_c_code(code)
            else:
                output = "No executable code found in the solution."
        qa_list.append({
            'question': question,
            'solution': solution,
            'output': output
        })

    output_docx = 'C_Programming_Solutions.docx'
    create_docx(qa_list, output_docx)

if __name__ == '__main__':
    main()
