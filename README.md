# Infinite Scribe - Multi-Agent Novel Writing System
> 多智能体小说写作原型 (Multi-Agent Novel Writing Prototype)

An intelligent system that leverages multiple AI agents to collaboratively generate coherent, high-quality long-form narratives with human-in-the-loop supervision.

## 🎯 Project Overview

Infinite Scribe is an MVP prototype designed to validate the feasibility of automated long-form novel creation through a sophisticated multi-agent architecture. The system aims to solve the fundamental challenge of maintaining narrative coherence across extended storytelling while providing human supervisors with intuitive tools for quality control.

### Core Mission

To produce a **100,000-word** high-quality, logically consistent novel that serves as a benchmark for evaluating AI-driven content creation capabilities.

## 🎯 MVP Goals

1. **Technical Validation**: Prove that our "World Memory" system (Milvus + Neo4j) combined with multi-agent collaboration can effectively solve long-form narrative coherence challenges.

2. **Quality Validation**: Generate a professional-grade 100,000-word novel with consistent plot, character development, and world-building.

3. **Cost Validation**: Accurately measure and document token consumption and total API costs for generating content at scale.

4. **Process Validation**: Test and optimize the core automated workflow from plot planning to chapter generation to review and revision.

## 🛠️ Technology Stack

| Category | Technology |
|----------|------------|
| **Backend Language** | Python |
| **Backend Framework** | FastAPI |
| **Data Validation** | Pydantic |
| **Frontend Framework** | React + TypeScript |
| **Frontend UI** | shadcn/ui + Tailwind CSS |
| **Build/State/Routing** | Vite, Zustand, React Router, TanStack Query |
| **Workflow Orchestration** | Prefect |
| **Event Bus** | Kafka |
| **Databases** | PostgreSQL, Milvus, Neo4j |
| **Object Storage** | MinIO |
| **Cache** | Redis |
| **LLM Observability** | Langfuse |
| **LLM API Proxy** | LiteLLM |

## 🏗️ Architecture

### System Design
- **Repository Structure**: Monorepo using pnpm workspaces
- **Service Architecture**: Event-driven sidecar microservices pattern
- **Agent Communication**: Asynchronous messaging via Kafka
- **Memory System**: Dual-database approach for semantic (Milvus) and relational (Neo4j) memory

### Core Agents

1. **WriterAgent**: Generates chapter drafts based on instructions and world context
2. **CriticAgent**: Evaluates content quality, logic, and engagement; provides structured feedback
3. **RewriterAgent**: Revises drafts based on critic feedback and human input

### Key Components

- **World Memory System**: Maintains story consistency through vector embeddings and knowledge graphs
- **Human Supervision UI**: Professional dashboard for content review and approval
- **Workflow Engine**: Automated orchestration of the write-review-revise cycle
- **Cost Analytics**: Real-time token usage and API cost tracking

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ & pnpm
- Python 3.11+
- API keys for LLM providers (OpenAI, Anthropic, etc.)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/infinite-scribe.git
   cd infinite-scribe
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   ```

3. **Start infrastructure services**
   ```bash
   docker-compose up -d
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Run database migrations**
   ```bash
   pnpm migrate
   ```

6. **Start development servers**
   ```bash
   pnpm dev
   ```

## 📁 Project Structure

```
infinite-scribe/
├── apps/
│   ├── web/                 # React frontend application
│   ├── writer-agent/        # Chapter writing service
│   ├── critic-agent/        # Content evaluation service
│   ├── rewriter-agent/      # Revision service
│   ├── memory-service/      # World memory management
│   └── workflow-engine/     # Prefect orchestration
├── packages/
│   ├── shared-types/        # TypeScript type definitions
│   ├── ui-components/       # Shared React components
│   └── utils/              # Common utilities
├── docker-compose.yml       # Local infrastructure setup
├── pnpm-workspace.yaml     # Monorepo configuration
└── .taskmaster/            # Task management files
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
pnpm test

# Run frontend tests
pnpm test:frontend

# Run backend tests
pnpm test:backend
```

### Code Quality

```bash
# Lint code
pnpm lint

# Format code
pnpm format

# Type check
pnpm typecheck
```

### Building for Production

```bash
# Build all services
pnpm build

# Build Docker images
pnpm docker:build
```

## 🎯 Key Features

### For Supervisors
- **Intuitive Review Interface**: Side-by-side comparison of drafts, critiques, and revisions
- **Flexible Control**: Approve, reject, or request specific revisions with contextual feedback
- **Real-time Analytics**: Monitor token usage, costs, and generation performance
- **World Bible Editor**: Manage characters, settings, and story rules

### For the System
- **Narrative Coherence**: Advanced memory systems ensure story consistency
- **Quality Assurance**: Multi-stage review process with AI and human validation
- **Scalable Architecture**: Modular design supports future agent additions
- **Complete Observability**: Full tracing of AI decisions and content evolution

## 📊 Metrics & Success Criteria

- **Narrative Coherence**: No major plot contradictions or character inconsistencies
- **Content Quality**: Professional-grade prose suitable for publication
- **Cost Efficiency**: < $X per 1,000 words generated (to be determined)
- **Processing Speed**: Average chapter generation time < Y minutes

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Create a feature branch from `main`
2. Implement your changes with appropriate tests
3. Ensure all checks pass (`pnpm check`)
4. Submit a pull request with clear description

## 📄 License

This project is proprietary software. All rights reserved.

## 🔗 Links

- [Product Requirements Document](.taskmaster/docs/prd.txt)
- [Technical Documentation](docs/technical.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)

---

Built with ❤️ for the future of AI-assisted creative writing.