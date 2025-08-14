# CLAUDE.md - Frontend

This file provides guidance for Claude Code when working with the frontend codebase.

## Frontend Architecture

### Technology Stack
- **Framework**: React 18.2 with TypeScript 5.2
- **Build Tool**: Vite 7.0 for fast development and building
- **Package Manager**: `pnpm` (workspace compatible)
- **State Management**: TanStack Query + Zustand
- **UI Library**: Shadcn UI with Tailwind CSS
- **Testing**: Vitest (unit) + Playwright (E2E)

### Application Architecture
InfiniteScribe frontend follows a modern React architecture with:
- **Component-Based Design**: Reusable UI components
- **Server State Management**: TanStack Query for API interactions
- **Client State Management**: Zustand for local state
- **Type Safety**: Full TypeScript coverage
- **Authentication**: Token-based with automatic refresh

### Directory Structure
```
apps/frontend/src/
├── components/           # Reusable UI Components
│   ├── ui/              # Shadcn UI base components
│   ├── auth/            # Authentication components
│   └── custom/          # Project-specific components
├── pages/               # Page components (route handlers)
│   ├── auth/            # Authentication pages
│   ├── dashboard/       # Dashboard pages
│   └── projects/        # Project-specific pages
├── hooks/               # Custom React hooks & TanStack Query hooks
│   ├── useAuth.ts       # Authentication hooks
│   ├── useAuthMutations.ts # Auth mutation hooks
│   └── useHealthCheck.ts    # Health check hooks
├── services/            # API clients and business logic
│   ├── auth/            # Authentication service layer
│   │   ├── auth-service.ts     # Core auth logic
│   │   ├── token-manager.ts    # JWT token management
│   │   ├── auth-api-client.ts  # Auth API calls
│   │   └── types.ts            # Auth type definitions
│   ├── api.ts           # Main API client
│   └── healthService.ts # Health check service
├── types/               # TypeScript type definitions
│   ├── api/             # API response types
│   ├── models/          # Domain model types
│   ├── events/          # Event type definitions
│   ├── enums/           # Enumeration types
│   └── auth.ts          # Authentication types
├── layouts/             # Layout components
├── lib/                 # Utility libraries
│   ├── queryClient.ts   # TanStack Query configuration
│   └── utils.ts         # Utility functions
├── utils/               # Helper utilities
└── config/              # Configuration files
    └── api.ts           # API configuration
```

## Development Commands

### Local Development
```bash
# Start development server
pnpm dev                 # Start on port 5173

# Alternative using make
make frontend-run

# Start with specific port
pnpm dev --port 3000
```

### Code Quality
```bash
# Lint and format
pnpm lint               # ESLint check
pnpm lint:fix           # Auto-fix ESLint issues
pnpm format             # Prettier formatting

# Type checking (via build)
pnpm build              # TypeScript compilation check
```

### Testing
```bash
# Unit tests (Vitest)
pnpm test               # Run unit tests
pnpm test:ci            # Run tests in CI mode

# E2E tests (Playwright)
pnpm test:e2e           # Run all E2E tests
pnpm test:e2e:ui        # Run with Playwright UI
pnpm test:e2e:debug     # Debug mode
pnpm test:e2e:auth      # Auth-specific tests only

# E2E test setup
pnpm test:e2e:install   # Install Playwright browsers

# E2E with email testing
pnpm test:e2e:with-maildev       # Start maildev and run auth tests
pnpm maildev:start               # Start maildev container
pnpm maildev:stop                # Stop maildev container
```

### Build & Deploy
```bash
# Production build
pnpm build              # Build for production
pnpm preview            # Preview production build locally
```

## Code Patterns & Conventions

### 1. Component Structure
Use functional components with TypeScript:

```tsx
// Good: Well-structured component
interface UserProfileProps {
  userId: string;
  onUpdate?: (user: User) => void;
}

export function UserProfile({ userId, onUpdate }: UserProfileProps) {
  const { data: user, isLoading, error } = useUser(userId);
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!user) return <div>User not found</div>;

  return (
    <div className="user-profile">
      {/* Component content */}
    </div>
  );
}
```

### 2. TanStack Query Pattern
Use custom hooks for API interactions:

```tsx
// hooks/useAuth.ts - Server state hook
export function useUser(userId: string) {
  return useQuery({
    queryKey: ['user', userId],
    queryFn: () => authService.getUser(userId),
    enabled: !!userId,
  });
}

// hooks/useAuthMutations.ts - Mutation hook  
export function useCreateUser() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: authService.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

// Usage in component
function CreateUserForm() {
  const createUser = useCreateUser();
  
  const handleSubmit = (data: UserCreate) => {
    createUser.mutate(data);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Form content */}
    </form>
  );
}
```

### 3. State Management Pattern
Use Zustand for client-side state:

```tsx
// stores/authStore.ts
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  login: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  login: (user) => set({ isAuthenticated: true, user }),
  logout: () => set({ isAuthenticated: false, user: null }),
}));

// Usage in component
function Navbar() {
  const { isAuthenticated, user, logout } = useAuthStore();
  
  return (
    <nav>
      {isAuthenticated ? (
        <div>
          Welcome, {user?.username}
          <button onClick={logout}>Logout</button>
        </div>
      ) : (
        <Link to="/login">Login</Link>
      )}
    </nav>
  );
}
```

### 4. Form Handling
Use react-hook-form with Zod validation:

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email('Invalid email format'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginForm = z.infer<typeof loginSchema>;

function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    // Handle form submission
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('email')}
        type="email"
        placeholder="Email"
      />
      {errors.email && <span>{errors.email.message}</span>}
      
      <input
        {...register('password')}
        type="password"
        placeholder="Password"
      />
      {errors.password && <span>{errors.password.message}</span>}
      
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
}
```

### 5. Error Handling
Consistent error handling with React Error Boundaries:

```tsx
// components/ErrorBoundary.tsx
export class ErrorBoundary extends Component<
  PropsWithChildren<{}>,
  { hasError: boolean }
> {
  constructor(props: PropsWithChildren<{}>) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <button onClick={() => this.setState({ hasError: false })}>
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Usage
function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          {/* Your routes */}
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}
```

## Authentication Implementation

### Authentication Service
Located in `src/services/auth/`, the auth service handles:
- Token management (JWT access/refresh tokens)
- API authentication
- Automatic token refresh
- Secure storage

```tsx
// services/auth/auth-service.ts
class AuthService {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await this.apiClient.post('/auth/login', credentials);
    this.tokenManager.setTokens(response.data);
    return response.data;
  }
  
  async refreshToken(): Promise<void> {
    // Handle token refresh logic
  }
  
  logout(): void {
    this.tokenManager.clearTokens();
    // Redirect to login
  }
}
```

### Protected Routes
```tsx
// components/auth/RequireAuth.tsx
export function RequireAuth({ children }: PropsWithChildren) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <div>Loading...</div>;
  
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// Usage in routing
function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={
        <RequireAuth>
          <Dashboard />
        </RequireAuth>
      } />
    </Routes>
  );
}
```

## Testing Strategy

### 1. Unit Testing (Vitest)
Test components, hooks, and utilities:

```tsx
// __tests__/components/UserProfile.test.tsx
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UserProfile } from '../UserProfile';

describe('UserProfile', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  it('renders user information when loaded', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <UserProfile userId="123" />
      </QueryClientProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
    
    // Wait for data to load and assert
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });
  });
});
```

### 2. E2E Testing (Playwright)
Test complete user workflows:

```typescript
// e2e/auth/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('text=Welcome')).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('[name="email"]', 'invalid@example.com');
    await page.fill('[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });
});
```

### 3. Test Configuration
```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
});

// src/test/setup.ts
import '@testing-library/jest-dom';

// Mock API calls for tests
vi.mock('./src/services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));
```

## UI Development

### Shadcn UI Components
Use pre-built components from Shadcn UI:

```tsx
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

function LoginCard() {
  return (
    <Card className="w-96">
      <CardHeader>
        <CardTitle>Login</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Input type="email" placeholder="Email" />
          <Input type="password" placeholder="Password" />
          <Button className="w-full">Login</Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Custom Components
Build reusable project-specific components:

```tsx
// components/custom/ProjectCard.tsx
interface ProjectCardProps {
  project: Project;
  onSelect?: (project: Project) => void;
}

export function ProjectCard({ project, onSelect }: ProjectCardProps) {
  return (
    <Card 
      className="cursor-pointer hover:shadow-lg transition-shadow"
      onClick={() => onSelect?.(project)}
    >
      <CardHeader>
        <CardTitle>{project.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-gray-600">{project.description}</p>
        <div className="mt-4 flex justify-between items-center">
          <Badge variant="secondary">{project.status}</Badge>
          <span className="text-sm text-gray-500">
            {formatDate(project.updatedAt)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Styling with Tailwind
Use Tailwind CSS for consistent styling:

```tsx
// Good: Consistent spacing and responsive design
function Dashboard() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  );
}
```

## Common Development Tasks

### Adding New Page
1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Create necessary hooks in `src/hooks/`
4. Add API calls in `src/services/`
5. Write tests

### Adding New API Integration
1. Define types in `src/types/api/`
2. Create service methods in `src/services/`
3. Create TanStack Query hooks in `src/hooks/`
4. Add error handling
5. Write tests

### Adding New Form
1. Define validation schema with Zod
2. Create form component with react-hook-form
3. Add mutation hook for submission
4. Style with Shadcn UI components
5. Add validation error handling

### Adding New Component
1. Create component in appropriate directory
2. Define TypeScript interfaces for props
3. Add Storybook story (if using Storybook)
4. Write unit tests
5. Document usage

## Performance Optimization

### Code Splitting
```tsx
// Lazy load pages for better performance
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Profile = lazy(() => import('./pages/Profile'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/profile" element={<Profile />} />
      </Routes>
    </Suspense>
  );
}
```

### TanStack Query Optimization
```tsx
// Prefetch data for better UX
function ProjectList() {
  const queryClient = useQueryClient();
  
  const prefetchProject = (projectId: string) => {
    queryClient.prefetchQuery({
      queryKey: ['project', projectId],
      queryFn: () => api.getProject(projectId),
    });
  };

  return (
    <div>
      {projects.map(project => (
        <div 
          key={project.id}
          onMouseEnter={() => prefetchProject(project.id)}
        >
          {project.title}
        </div>
      ))}
    </div>
  );
}
```

## Debugging & Troubleshooting

### Common Issues
1. **Build errors**: Check TypeScript types and imports
2. **API calls failing**: Verify backend is running and endpoints are correct
3. **Authentication issues**: Check token storage and refresh logic
4. **Styling issues**: Verify Tailwind classes and component structure

### Development Tools
- **React DevTools**: Component inspection
- **TanStack Query DevTools**: Query state inspection
- **Browser DevTools**: Network, console, performance
- **Playwright Test Runner**: E2E test debugging

### Logging
```tsx
// Development logging
const isDev = import.meta.env.DEV;

function debugLog(message: string, data?: any) {
  if (isDev) {
    console.log(`[Frontend Debug] ${message}`, data);
  }
}
```

## Security Considerations

### Token Security
- Store tokens securely (httpOnly cookies preferred)
- Implement automatic token refresh
- Clear tokens on logout
- Validate tokens on protected routes

### Input Validation
- Use Zod schemas for form validation
- Sanitize user inputs
- Validate on both client and server
- Handle validation errors gracefully

### API Security
- Use HTTPS in production
- Implement CORS properly
- Add request/response interceptors
- Handle authentication errors consistently