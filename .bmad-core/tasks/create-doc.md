# Create Document from Template Task

## Purpose

Generate documents from templates by EXECUTING (not just reading) embedded instructions from the perspective of the selected agent persona.

## CRITICAL RULES

1. **Templates are PROGRAMS** - Execute every [[LLM:]] instruction exactly as written
2. **NEVER show markup** - Hide all [[LLM:]], {{placeholders}}, @{examples}, and template syntax
3. **STOP and EXECUTE** - When you see "apply tasks#" or "execute tasks#", STOP and run that task immediately
4. **WAIT for user input** - At review points and after elicitation tasks

## Execution Flow

### 1. Identify Template

- Load from `templates#*` or `.bmad-core/templates directory`
- Agent-specific templates are listed in agent's dependencies
- If agent has `templates: [prd-tmpl, architecture-tmpl]`, offer to create "PRD" and "Architecture" documents

### 2. Ask Interaction Mode

> 1. **Incremental** - Section by section with reviews
> 2. **YOLO Mode** - Complete draft then review (user can type `/yolo` anytime to switch)

### 3. Execute Template

- Replace {{placeholders}} with real content
- Execute [[LLM:]] instructions as you encounter them
- Process <<REPEAT>> loops and ^^CONDITIONS^^
- Use @{examples} for guidance but never output them

### 4. Key Execution Patterns

**When you see:** `[[LLM: Draft X and immediately execute tasks#advanced-elicitation]]`

- Draft the content
- Present it to user
- IMMEDIATELY execute the task
- Wait for completion before continuing

**When you see:** `[[LLM: After section completion, apply tasks#Y]]`

- Finish the section
- STOP and execute the task
- Wait for user input

### 5. Validation & Final Presentation

- Run any specified checklists
- Present clean, formatted content only
- No truncation or summarization
- Begin directly with content (no preamble)
- Include any handoff prompts from template

## Common Mistakes to Avoid

❌ Skipping elicitation tasks
❌ Showing template markup to users
❌ Continuing past STOP signals
❌ Combining multiple review points

✅ Execute ALL instructions in sequence
✅ Present only clean, formatted content
✅ Stop at every elicitation point
✅ Wait for user confirmation when instructed

## Remember

Templates contain precise instructions for a reason. Follow them exactly to ensure document quality and completeness.
