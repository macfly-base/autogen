import argparse
import logging
import subprocess
from typing import List, Tuple
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import PythonLexer

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

MODULES_TO_CHECK = ["autogen_agentchat", "autogen_core", "autogen_ext"]

def extract_python_code_blocks(markdown_file_path: str) -> List[Tuple[str, int]]:
    """Extract Python code blocks from a Markdown file."""
    with open(markdown_file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    code_blocks: List[Tuple[str, int]] = []
    in_code_block = False
    current_block: List[str] = []

    for i, line in enumerate(lines):
        if line.strip().startswith("```python"):
            in_code_block = True
            current_block = []
        elif line.strip().startswith("```") and in_code_block:
            in_code_block = False
            code_blocks.append(("\n".join(current_block), i - len(current_block) + 1))
        elif in_code_block:
            current_block.append(line)

    return code_blocks

def check_code_blocks(markdown_file_paths: List[str]) -> None:
    """Check Python code blocks in Markdown files for syntax errors."""
    files_with_errors = []

    for markdown_file_path in markdown_file_paths:
        code_blocks = extract_python_code_blocks(markdown_file_path)
        had_errors = False

        for code_block, line_no in code_blocks:
            markdown_file_path_with_line_no = f"{markdown_file_path}:{line_no}"
            logger.info("Checking a code block in %s...", markdown_file_path_with_line_no)

            if all(module not in code_block for module in MODULES_TO_CHECK):
                logger.info(" " + "OK[ignored]")
                continue

            try:
                result = subprocess.run(
                    ["pyright", "-"], input=code_block, capture_output=True, text=True, check=False
                )
                if result.returncode != 0:
                    logger.info(" " + "FAIL")
                    highlighted_code = highlight(code_block, PythonLexer(), TerminalFormatter())
                    logger.error(
                        f"Error in {markdown_file_path_with_line_no}:\n"
                        f"Code:\n{highlighted_code}\n"
                        f"Pyright Output:\n{result.stdout.strip()}"
                    )
                    had_errors = True
                else:
                    logger.info(" " + "OK")
            except FileNotFoundError:
                logger.error("Pyright is not installed or not in PATH.")
                raise RuntimeError("Pyright missing; install it to proceed.")

        if had_errors:
            files_with_errors.append(markdown_file_path)

    if files_with_errors:
        raise RuntimeError("Syntax errors found in the following files:\n" + "\n".join(files_with_errors))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check code blocks in Markdown files for syntax errors.")
    parser.add_argument("markdown_files", nargs="+", help="Markdown files to check.")
    args = parser.parse_args()
    check_code_blocks(args.markdown_files)
