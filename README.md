# AI Agent Skills

This repository stores a collection of skills, configurations, and tools for AI agents (specifically compatible with Gemini CLI and similar environments).

## Installation

To install these skills, you should clone this repository directly into your home directory's `.agents` folder. This ensures that the agent can automatically detect and load the installed skills.

**Run the following command in your terminal:**

```bash
git clone https://github.com/pedrobrantes/agents.git ~/.agents
```

## Structure

*   **skills/**: Contains individual skill definitions. Each subfolder represents a specific skill (e.g., `android-material3-expressive`) and contains a `SKILL.md` file.
*   **.skill-lock.json**: Lockfile to manage skill versions and dependencies.

## Usage

Once cloned, your AI agent will be able to read the instructions and contexts provided in the `skills/` directory to perform specialized tasks.
