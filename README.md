# Infinite Scribe - Multi-Agent Collaboration Framework
> 多智能体小说写作原型 (Multi-Agent Novel Writing Prototype)

This repository contains the core configuration, knowledge base, and operational workflows for **Infinite Scribe**, an experimental framework designed to orchestrate multiple AI agents for complex, collaborative tasks like creative writing.

Rather than being a standalone software application, this project serves as the "brain" and "playbook" that guides a team of specialized AI agents. It defines their roles, rules of engagement, and the processes they follow to achieve sophisticated goals, such as generating a full-length novel.

## 🎯 Project Mission

To develop and refine a robust multi-agent framework capable of producing high-quality, coherent, long-form narratives, while validating the processes and configurations required for such a system to operate effectively.

## 核心理念 (Core Concepts)

- **Agent-Based Architecture**: The system is built around a team of specialized AI agents (e.g., Project Manager, Architect, Developer, QA), each with a distinct role and set of instructions.
- **Workflow Orchestration**: YAML files define the sequence of tasks and agent interactions required to complete complex processes, such as the `greenfield-fullstack.yml` workflow.
- **Knowledge-Driven**: The framework relies heavily on structured documentation, templates, and checklists to ensure quality and consistency. The `docs` and `.bmad-core` directories are central to its operation.
- **Tool-Agnostic**: Agent configurations are provided for multiple platforms (Claude, Cursor, etc.), allowing for flexibility in the underlying AI models used.

## 📁 Project Structure

This repository is organized as a central knowledge base and configuration hub for the multi-agent system.

```
infinite-scribe/
├── .bmad-core/          # Core framework for the "Build Me A Dream" agent system.
│   ├── agents/          # Prompt definitions for each specialized agent.
│   ├── tasks/           # Definitions of specific tasks the agents can perform.
│   ├── templates/       # Standard templates for documents (PRD, architecture, etc.).
│   └── workflows/       # YAML files defining multi-step agent collaborations.
├── .claude/             # Configuration and prompts specific to the Anthropic Claude model.
├── .clinerules/         # High-level rules and directives governing agent behavior.
├── .cursor/             # Configuration for the Cursor IDE environment.
├── .github/             # GitHub-specific files, including workflow instructions.
├── .taskmaster/         # Contains project management files, like PRDs and task lists.
├── .windsurf/           # Configuration for the Windsurf AI environment.
├── docs/                # Central repository for all project documentation.
│   ├── prd/             # Detailed epics and requirements for the novel generation.
│   └── architecture.md  # High-level system architecture documents.
└── web-bundles/         # Packaged agent prompts for distribution or use in web contexts.
```

## 🚀 Usage

This repository is not meant to be "run" in a traditional sense with a single command. Instead, it serves as a foundational resource for an external orchestration engine or a human operator directing AI agents.

**Typical Use Cases:**
1.  **Providing Context to AI**: An orchestrator loads the relevant agent definitions, rules, and task instructions from this repository to guide an AI model.
2.  **Executing Workflows**: The YAML workflow files are parsed by an engine that calls the appropriate agents in sequence to complete a task.
3.  **Manual Operation**: A human operator uses the prompts and templates in this repository to manually guide AI agents through a platform like Claude or a local model interface.

## 🤝 Contributing

Contributions to the agent prompts, workflow definitions, and documentation are welcome. Please follow the existing structure and conventions.

### Development Workflow

1.  Create a feature branch from `main`.
2.  Update or add new configuration files, prompts, or documents.
3.  Ensure changes are consistent with the overall architecture.
4.  Submit a pull request with a clear description of the changes.

## 📄 License

This project is proprietary software. All rights reserved.
