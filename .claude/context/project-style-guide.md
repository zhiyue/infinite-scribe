---
created: 2025-08-28T12:10:36Z
last_updated: 2025-08-28T12:10:36Z
version: 1.0
author: Claude Code PM System
---

# Project Style Guide

## Development Philosophy

### Code Quality Standards
- **Readability Over Cleverness**: Code should be self-documenting and easily understood by team members
- **Consistency Over Personal Preference**: Follow established patterns rather than introducing new styles
- **Simplicity Over Complexity**: Choose the simplest solution that meets requirements
- **Testability**: All code should be designed with testing in mind

### Best Practices
- **SOLID Principles**: Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **DRY (Don't Repeat Yourself)**: Extract common functionality into reusable components
- **YAGNI (You Aren't Gonna Need It)**: Avoid over-engineering and premature optimization
- **Fail Fast**: Validate inputs early and provide clear error messages

## Naming Conventions

### General Principles
- **Descriptive Names**: Names should clearly indicate purpose and usage
- **Avoid Abbreviations**: Use full words unless abbreviation is widely accepted (e.g., `id`, `url`)
- **Consistent Terminology**: Use same terms throughout codebase for same concepts
- **Contextual Appropriateness**: Names should fit the context and abstraction level

### Language-Specific Conventions

**TypeScript/JavaScript**
```typescript
// Variables and functions: camelCase
const userProfile = getUserProfile();
const isAuthenticated = checkAuthStatus();

// Constants: SCREAMING_SNAKE_CASE
const MAX_RETRY_ATTEMPTS = 3;
const API_BASE_URL = 'https://api.infinitescribe.com';

// Classes and interfaces: PascalCase
class NovelService {
  // Private members: underscore prefix
  private _aiClient: AIClient;
  
  // Public methods: descriptive action verbs
  async generateChapter(prompt: string): Promise<Chapter> {}
}

interface UserPreferences {
  writingStyle: WritingStyle;
  preferredGenres: Genre[];
}

// Types: PascalCase with descriptive suffixes
type NovelGenerationState = 'idle' | 'generating' | 'complete' | 'error';
type AgentResponse<T> = {
  success: boolean;
  data: T;
  error?: string;
};

// Enums: PascalCase
enum WritingPhase {
  PLANNING = 'planning',
  DRAFTING = 'drafting',
  EDITING = 'editing',
  COMPLETE = 'complete'
}
```

**Python**
```python
# Variables and functions: snake_case
user_profile = get_user_profile()
is_authenticated = check_auth_status()

# Constants: SCREAMING_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
API_BASE_URL = "https://api.infinitescribe.com"

# Classes: PascalCase
class NovelService:
    # Private members: single underscore prefix
    def _validate_input(self, input_data: dict) -> bool:
        pass
    
    # Public methods: descriptive action verbs
    async def generate_chapter(self, prompt: str) -> Chapter:
        pass

# Type hints: use descriptive types
from typing import Dict, List, Optional, Union

UserPreferences = Dict[str, Union[str, List[str]]]
NovelGenerationState = Literal['idle', 'generating', 'complete', 'error']
```

### File and Directory Naming
```
# Directories: kebab-case
user-service/
novel-generation/
ai-agents/

# Python files: snake_case
user_service.py
novel_generator.py
character_agent.py

# TypeScript/React files: PascalCase for components, kebab-case for others
UserProfile.tsx
NovelEditor.tsx
api-client.ts
utils.ts

# Configuration files: kebab-case
docker-compose.yml
eslint-config.js
tsconfig.json
```

## Code Organization

### Project Structure
```
apps/
├── backend/
│   ├── src/
│   │   ├── api/          # API route handlers
│   │   ├── services/     # Business logic
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Request/response schemas
│   │   ├── utils/        # Shared utilities
│   │   └── tests/        # Test files
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── components/   # Reusable UI components
    │   ├── pages/        # Route-specific page components
    │   ├── hooks/        # Custom React hooks
    │   ├── services/     # API clients and external services
    │   ├── utils/        # Shared utilities
    │   ├── types/        # TypeScript type definitions
    │   └── __tests__/    # Test files
    └── package.json
```

### Import/Export Patterns

**TypeScript/React**
```typescript
// Named imports for utilities and services
import { validateInput, formatDate } from '../utils/helpers';
import { NovelService } from '../services/NovelService';

// Default imports for components
import UserProfile from '../components/UserProfile';

// Type-only imports when appropriate
import type { User, Novel } from '../types';

// Barrel exports in index files
export { default as UserProfile } from './UserProfile';
export { default as NovelEditor } from './NovelEditor';
export type { UserProfileProps } from './UserProfile';
```

**Python**
```python
# Explicit imports preferred over wildcards
from services.novel_service import NovelService
from models.user import User, UserPreferences
from typing import Dict, List, Optional

# Avoid relative imports beyond parent directory
from ..models.novel import Novel  # OK
from ....utils.helpers import validate_input  # Avoid
```

## Comment and Documentation Style

### Comment Guidelines
- **Why, Not What**: Comments should explain reasoning, not restate code
- **Keep Updated**: Comments must be maintained alongside code changes
- **Avoid Obvious Comments**: Don't comment what is clear from the code itself
- **Use TODO Comments**: Mark future improvements with TODO and your initials

```typescript
// Good: Explains why this approach is used
// Using exponential backoff to handle API rate limits gracefully
const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);

// Bad: States what the code obviously does
// Set delay to 1000 times 2 to the power of retryCount
const delay = 1000 * Math.pow(2, retryCount);

// TODO(username): Implement caching layer for better performance
const userData = await fetchUserData(userId);
```

### Function Documentation

**TypeScript/JavaScript (JSDoc)**
```typescript
/**
 * Generates a new chapter for the specified novel using AI assistance.
 * 
 * @param novelId - Unique identifier for the novel
 * @param prompt - User-provided prompt or context for chapter generation
 * @param options - Optional generation parameters
 * @returns Promise resolving to the generated chapter data
 * @throws {ValidationError} When prompt is empty or novel doesn't exist
 * @throws {AIServiceError} When AI service is unavailable or returns error
 * 
 * @example
 * ```typescript
 * const chapter = await generateChapter(
 *   'novel-123',
 *   'The protagonist discovers the hidden truth',
 *   { style: 'literary', maxWords: 2000 }
 * );
 * ```
 */
async function generateChapter(
  novelId: string,
  prompt: string,
  options?: GenerationOptions
): Promise<Chapter> {
  // Implementation
}
```

**Python (Docstring)**
```python
async def generate_chapter(
    self, 
    novel_id: str, 
    prompt: str, 
    options: Optional[GenerationOptions] = None
) -> Chapter:
    """
    Generate a new chapter for the specified novel using AI assistance.
    
    Args:
        novel_id: Unique identifier for the novel
        prompt: User-provided prompt or context for chapter generation
        options: Optional generation parameters including style and length
        
    Returns:
        Chapter object containing generated content and metadata
        
    Raises:
        ValidationError: When prompt is empty or novel doesn't exist
        AIServiceError: When AI service is unavailable or returns error
        
    Example:
        >>> chapter = await novel_service.generate_chapter(
        ...     'novel-123',
        ...     'The protagonist discovers the hidden truth',
        ...     GenerationOptions(style='literary', max_words=2000)
        ... )
    """
```

## Error Handling Standards

### Error Types and Hierarchy
```typescript
// Base error class for all application errors
class InfiniteScribeError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500
  ) {
    super(message);
    this.name = this.constructor.name;
  }
}

// Specific error types
class ValidationError extends InfiniteScribeError {
  constructor(message: string, public field?: string) {
    super(message, 'VALIDATION_ERROR', 400);
  }
}

class AIServiceError extends InfiniteScribeError {
  constructor(message: string, public provider: string) {
    super(message, 'AI_SERVICE_ERROR', 503);
  }
}
```

### Error Handling Patterns
```typescript
// Result pattern for operations that may fail
type Result<T, E = Error> = 
  | { success: true; data: T }
  | { success: false; error: E };

// Use consistent error handling in services
async function generateText(prompt: string): Promise<Result<string>> {
  try {
    const result = await aiService.generate(prompt);
    return { success: true, data: result };
  } catch (error) {
    return { 
      success: false, 
      error: error instanceof AIServiceError ? error : new AIServiceError(
        'Unexpected AI service error',
        'unknown'
      )
    };
  }
}

// Handle errors consistently in API routes
app.post('/api/generate', async (req, res) => {
  const result = await generateText(req.body.prompt);
  
  if (!result.success) {
    return res.status(result.error.statusCode).json({
      error: {
        code: result.error.code,
        message: result.error.message
      }
    });
  }
  
  res.json({ data: result.data });
});
```

## Testing Standards

### Test Organization
- **Co-located Tests**: Keep test files near the code they test
- **Descriptive Names**: Test names should describe the scenario and expected outcome
- **AAA Pattern**: Arrange, Act, Assert structure for clear test logic
- **Test Categories**: Unit tests for pure functions, integration tests for workflows

### Test File Naming
```
# TypeScript
UserService.test.ts        # Unit tests
UserService.integration.test.ts  # Integration tests
UserProfile.spec.tsx       # React component tests

# Python  
test_user_service.py       # Unit tests
test_user_service_integration.py  # Integration tests
```

### Test Structure Examples

**TypeScript (Jest)**
```typescript
describe('NovelService', () => {
  describe('generateChapter', () => {
    it('should generate chapter with valid prompt and novel ID', async () => {
      // Arrange
      const mockNovel = createMockNovel();
      const prompt = 'Generate exciting action scene';
      const expectedChapter = createMockChapter();
      
      jest.spyOn(novelRepository, 'findById').mockResolvedValue(mockNovel);
      jest.spyOn(aiService, 'generate').mockResolvedValue(expectedChapter.content);
      
      // Act
      const result = await novelService.generateChapter(mockNovel.id, prompt);
      
      // Assert
      expect(result.success).toBe(true);
      expect(result.data).toMatchObject(expectedChapter);
    });

    it('should return error when novel does not exist', async () => {
      // Arrange
      const nonExistentNovelId = 'invalid-id';
      jest.spyOn(novelRepository, 'findById').mockResolvedValue(null);
      
      // Act
      const result = await novelService.generateChapter(nonExistentNovelId, 'prompt');
      
      // Assert
      expect(result.success).toBe(false);
      expect(result.error).toBeInstanceOf(ValidationError);
    });
  });
});
```

**Python (pytest)**
```python
class TestNovelService:
    """Test cases for NovelService class."""
    
    async def test_generate_chapter_with_valid_input(self, novel_service, mock_novel):
        """Should generate chapter when provided with valid prompt and novel ID."""
        # Arrange
        prompt = "Generate exciting action scene"
        expected_chapter = create_mock_chapter()
        
        # Act
        result = await novel_service.generate_chapter(mock_novel.id, prompt)
        
        # Assert
        assert result.success is True
        assert result.data.content == expected_chapter.content
    
    async def test_generate_chapter_with_invalid_novel_id(self, novel_service):
        """Should return error when novel does not exist."""
        # Arrange
        invalid_id = "nonexistent-id"
        prompt = "Any prompt"
        
        # Act
        result = await novel_service.generate_chapter(invalid_id, prompt)
        
        # Assert
        assert result.success is False
        assert isinstance(result.error, ValidationError)
```

## Code Review Guidelines

### What to Look For
1. **Correctness**: Does the code do what it's supposed to do?
2. **Clarity**: Is the code easy to understand and maintain?
3. **Consistency**: Does it follow established patterns and conventions?
4. **Performance**: Are there obvious performance issues?
5. **Security**: Are there potential security vulnerabilities?
6. **Testing**: Are the changes adequately tested?

### Review Checklist
- [ ] Code follows naming conventions and style guide
- [ ] Functions and classes have appropriate documentation
- [ ] Error handling is comprehensive and consistent
- [ ] Tests cover new functionality and edge cases
- [ ] No obvious security vulnerabilities or performance issues
- [ ] Code is readable and maintainable by other team members