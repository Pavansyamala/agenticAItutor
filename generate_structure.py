import os

# --------------------------
# PROJECT STRUCTURE DEFINITION
# --------------------------

structure = {
    "agentic-tutor": {
        "backend": {
            "app": {
                "config": ["settings.py"],
                "core": [
                    "orchestrator.py",
                    "event_bus.py",
                    "agent_registry.py"
                ],
                "core/tools": [
                    "rag.py",
                    "math_solver.py",
                    "sympy_tool.py"
                ],
                "agents": [
                    "base_agent.py",
                    "tutor_agent.py",
                    "evaluator_agent.py",
                    "monitor_agent.py"
                ],
                "agents/agent_prompts": [
                    "tutor_prompt.txt",
                    "evaluator_prompt.txt",
                    "monitor_prompt.txt"
                ],
                "database": [
                    "models.py",
                    "session.py"
                ],
                "database/migrations": [],
                "routers": [
                    "tutor.py",
                    "evaluator.py",
                    "monitor.py",
                    "student.py",
                    "session_router.py"
                ],
                "schemas": [
                    "tutor_schemas.py",
                    "evaluator_schemas.py",
                    "monitor_schemas.py",
                    "student_schemas.py"
                ],
                "services": [
                    "lesson_service.py",
                    "evaluation_service.py",
                    "monitor_service.py"
                ],
                "utils": [
                    "logger.py",
                    "scoring_utils.py",
                    "content_utils.py",
                    "rag_utils.py"
                ],
                "__init__.py": "",
                "main.py": ""
            },
            "tests": [
                "test_agents.py",
                "test_routers.py",
                "test_orchestrator.py"
            ],
            "requirements.txt": "",
            "Dockerfile": "",
            "README.md": "# Agentic Tutor Backend\n"
        },
        "frontend": {
            "react-app": [],
            "components": []
        },
        "docs": [
            "architecture.md",
            "agent_designs.md",
            "api_design.md",
            "db_schema.md",
            "roadmap.md"
        ]
    }
}

# --------------------------
# FUNCTION: CREATE STRUCTURE
# --------------------------

def create_structure(base_path, structure):
    for name, content in structure.items():
        path = os.path.join(base_path, name)

        if isinstance(content, dict):
            # Create directory
            os.makedirs(path, exist_ok=True)
            # Recursively create subpaths
            create_structure(path, content)

        elif isinstance(content, list):
            # This is a folder containing files
            os.makedirs(path, exist_ok=True)
            for file in content:
                file_path = os.path.join(path, file)
                # Create empty file or placeholder text
                with open(file_path, "w", encoding="utf-8") as f:
                    if file.endswith(".md") or file.endswith(".txt"):
                        f.write(f"# {file}\n")
                    else:
                        f.write("")
        else:
            # Single file in the parent directory
            file_path = os.path.join(base_path, name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content if isinstance(content, str) else "")


# --------------------------
# EXECUTE SCRIPT
# --------------------------

if __name__ == "__main__":
    print("🔧 Creating Agentic Tutor Project Structure...")
    create_structure(".", structure)
    print("✅ Done! Folder structure created successfully!")
