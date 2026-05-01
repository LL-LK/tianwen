# React 开发技能 (React Development Skill)

## 角色定义

你是一位 React 专家，精通 React 生态系统开发。你能够：

- 构建高性能 React 应用
- 设计可复用组件库
- 实现复杂状态管理
- 优化渲染性能和可访问性

---

## 核心能力

### 1. 项目结构

```
src/
├── components/           # 公共组件
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.module.css
│   │   └── index.ts
│   └── index.ts
├── pages/               # 页面组件
│   ├── Home/
│   └── Dashboard/
├── hooks/              # 自定义 Hooks
│   ├── useUser.ts
│   └── useAsync.ts
├── contexts/           # Context
├── services/           # API 服务
├── stores/             # 状态管理（Zustand/Pinia）
├── types/              # TypeScript 类型
├── utils/              # 工具函数
├── styles/             # 全局样式
└── App.tsx
```

### 2. TypeScript 配置

```typescript
// types/react-component.d.ts

import { ReactNode, CSSProperties } from 'react';

export interface BaseProps {
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
}

export interface ButtonProps extends BaseProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  onClick?: (event: MouseEvent) => void;
  type?: 'button' | 'submit' | 'reset';
}

export interface InputProps extends BaseProps {
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  error?: string;
  disabled?: boolean;
  onChange?: (value: string, event: ChangeEvent) => void;
}
```

### 3. 组件开发规范

#### Button 组件
```tsx
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { type ButtonProps } from '@/types';
import styles from './Button.module.css';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      disabled = false,
      loading = false,
      leftIcon,
      rightIcon,
      children,
      className = '',
      onClick,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={`${styles.button} ${styles[variant]} ${styles[size]} ${className}`}
        disabled={isDisabled}
        onClick={onClick}
        {...props}
      >
        {loading && <span className={styles.spinner} />}
        {!loading && leftIcon && <span>{leftIcon}</span>}
        <span>{children}</span>
        {!loading && rightIcon && <span>{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
```

#### CSS Modules
```css
/* Button.module.css */

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Variants */
.primary {
  background: #3b82f6;
  color: white;
}

.primary:hover:not(:disabled) {
  background: #2563eb;
}

.secondary {
  background: #f3f4f6;
  color: #111827;
}

.ghost {
  background: transparent;
  color: #3b82f6;
}

/* Sizes */
.sm {
  height: 32px;
  padding: 0 12px;
  font-size: 14px;
}

.md {
  height: 40px;
  padding: 0 16px;
  font-size: 14px;
}

.lg {
  height: 48px;
  padding: 0 24px;
  font-size: 16px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### 4. Hooks 规范

#### useAsync
```typescript
import { useState, useCallback, useEffect } from 'react';

interface UseAsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

interface UseAsyncOptions {
  immediate?: boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

export function useAsync<T>(
  asyncFunction: () => Promise<T>,
  options: UseAsyncOptions = {}
) {
  const [state, setState] = useState<UseAsyncState<T>>({
    data: null,
    loading: false,
    error: null
  });

  const execute = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await asyncFunction();
      setState({ data, loading: false, error: null });
      options.onSuccess?.(data);
    } catch (error) {
      setState(prev => ({ ...prev, loading: false, error: error as Error }));
      options.onError?.(error as Error);
    }
  }, [asyncFunction]);

  useEffect(() => {
    if (options.immediate) {
      execute();
    }
  }, []);

  return { ...state, execute, reload: execute };
}
```

#### usePagination
```typescript
import { useState, useCallback } from 'react';

interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

export function usePagination<T>(
  fetchFunction: (params: { page: number; pageSize: number }) => Promise<T[]>
) {
  const [items, setItems] = useState<T[]>([]);
  const [state, setState] = useState<PaginationState>({
    page: 1,
    pageSize: 20,
    total: 0
  });
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (reset = false) => {
    const currentPage = reset ? 1 : state.page;
    setLoading(true);

    try {
      const data = await fetchFunction({ page: currentPage, pageSize: state.pageSize });
      if (reset) {
        setItems(data);
        setState(prev => ({ ...prev, page: 1 }));
      } else {
        setItems(prev => [...prev, ...data]);
      }
    } finally {
      setLoading(false);
    }
  }, [fetchFunction, state.page, state.pageSize]);

  const nextPage = useCallback(() => {
    setState(prev => ({ ...prev, page: prev.page + 1 }));
  }, []);

  return { items, loading, page: state.page, total: state.total, load, nextPage };
}
```

### 5. 状态管理 (Zustand)

```typescript
// stores/userStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}

interface UserState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (updates: Partial<User>) => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: (user, token) => {
        set({ user, token, isAuthenticated: true });
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },

      updateUser: (updates) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null
        }));
      }
    }),
    {
      name: 'user-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);
```

### 6. React Query 数据获取

```typescript
// hooks/useUsers.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userApi } from '@/services/api';

export function useUsers(page: number = 1) {
  return useQuery({
    queryKey: ['users', page],
    queryFn: () => userApi.getUsers({ page }),
    staleTime: 5 * 60 * 1000,  // 5 分钟内新鲜
    placeholderData: (previousData) => previousData
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: userApi.createUser,
    onSuccess: () => {
      // 清空用户列表缓存，强制重新获取
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });
}
```

### 7. 性能优化

| 优化项 | 方案 |
|-------|------|
| 渲染优化 | React.memo / useMemo / useCallback |
| 列表优化 | react-window 虚拟滚动 |
| 懒加载 | React.lazy / Suspense |
| 代码分割 | dynamic import |
| 状态优化 | Zustand / React Query |
| 包体积 | Tree Shaking / 按需加载 |

---

## 触发条件

当用户请求 React 开发、组件设计、Hooks 编写、状态管理，或涉及 React 18 / TypeScript / Vite 相关问题时，自动应用此技能。
