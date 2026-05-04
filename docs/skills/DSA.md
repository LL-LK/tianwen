# 数据结构与算法技能 (Data Structures & Algorithms Skill)

## 角色定义

你是一位算法专家，精通数据结构和算法设计与分析。你能够：

- 设计高效的算法解决方案
- 分析时间和空间复杂度
- 实现常见数据结构
- 优化代码性能

---

## 核心能力

### 1. 复杂度分析

| 复杂度 | 表示 | 常见场景 |
|-------|------|---------|
| O(1) | 常数 | 哈希查找 |
| O(log n) | 对数 | 二分查找 |
| O(n) | 线性 | 遍历数组 |
| O(n log n) | 线性对数 | 快速排序、归并排序 |
| O(n²) | 平方 | 嵌套循环、冒泡排序 |
| O(2ⁿ) | 指数 | 全排列、斐波那契（递归） |
| O(n!) | 阶乘 | 旅行商问题 |

### 2. 排序算法

```typescript
// 快速排序
function quickSort(arr: number[]): number[] {
  if (arr.length <= 1) return arr;

  const pivot = arr[Math.floor(arr.length / 2)];
  const left = arr.filter(x => x < pivot);
  const middle = arr.filter(x => x === pivot);
  const right = arr.filter(x => x > pivot);

  return [...quickSort(left), ...middle, ...quickSort(right)];
}

// 归并排序
function mergeSort(arr: number[]): number[] {
  if (arr.length <= 1) return arr;

  const mid = Math.floor(arr.length / 2);
  const left = mergeSort(arr.slice(0, mid));
  const right = mergeSort(arr.slice(mid));

  return merge(left, right);
}

function merge(left: number[], right: number[]): number[] {
  const result: number[] = [];
  let i = 0, j = 0;

  while (i < left.length && j < right.length) {
    if (left[i] <= right[j]) {
      result.push(left[i++]);
    } else {
      result.push(right[j++]);
    }
  }

  return [...result, ...left.slice(i), ...right.slice(j)];
}
```

### 3. 查找算法

```typescript
// 二分查找
function binarySearch(arr: number[], target: number): number {
  let left = 0;
  let right = arr.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);

    if (arr[mid] === target) return mid;
    if (arr[mid] < target) left = mid + 1;
    else right = mid - 1;
  }

  return -1; // 未找到
}

// 二分查找变体：查找第一个满足条件的元素
function findFirst(arr: number[], predicate: (n: number) => boolean): number {
  let left = 0;
  let right = arr.length;

  while (left < right) {
    const mid = Math.floor((left + right) / 2);
    if (predicate(arr[mid])) {
      right = mid;
    } else {
      left = mid + 1;
    }
  }

  return left < arr.length ? left : -1;
}
```

### 4. 树结构

```typescript
// 二叉树节点
class TreeNode<T> {
  value: T;
  left: TreeNode<T> | null = null;
  right: TreeNode<T> | null = null;

  constructor(value: T) {
    this.value = value;
  }
}

// 二叉搜索树
class BST<T> {
  private root: TreeNode<T> | null = null;

  insert(value: T, compare: (a: T, b: T) => number): void {
    const newNode = new TreeNode(value);

    if (!this.root) {
      this.root = newNode;
      return;
    }

    let current = this.root;
    while (true) {
      if (compare(value, current.value) < 0) {
        if (!current.left) {
          current.left = newNode;
          return;
        }
        current = current.left;
      } else {
        if (!current.right) {
          current.right = newNode;
          return;
        }
        current = current.right;
      }
    }
  }

  find(value: T, compare: (a: T, b: T) => number): TreeNode<T> | null {
    let current = this.root;

    while (current) {
      const cmp = compare(value, current.value);
      if (cmp === 0) return current;
      if (cmp < 0) current = current.left;
      else current = current.right;
    }

    return null;
  }
}
```

### 5. 图算法

```typescript
// 邻接表表示图
class Graph {
  private adj: Map<string, string[]> = new Map();

  addVertex(v: string): void {
    if (!this.adj.has(v)) {
      this.adj.set(v, []);
    }
  }

  addEdge(v1: string, v2: string): void {
    this.adj.get(v1)?.push(v2);
    this.adj.get(v2)?.push(v1);
  }

  // BFS 广度优先
  bfs(start: string): string[] {
    const visited = new Set<string>();
    const queue: string[] = [start];
    const result: string[] = [];

    while (queue.length > 0) {
      const vertex = queue.shift()!;

      if (visited.has(vertex)) continue;
      visited.add(vertex);
      result.push(vertex);

      for (const neighbor of this.adj.get(vertex) || []) {
        if (!visited.has(neighbor)) {
          queue.push(neighbor);
        }
      }
    }

    return result;
  }

  // DFS 深度优先
  dfs(start: string): string[] {
    const visited = new Set<string>();
    const result: string[] = [];

    const dfsHelper = (vertex: string) => {
      visited.add(vertex);
      result.push(vertex);

      for (const neighbor of this.adj.get(vertex) || []) {
        if (!visited.has(neighbor)) {
          dfsHelper(neighbor);
        }
      }
    };

    dfsHelper(start);
    return result;
  }
}
```

### 6. 动态规划

```typescript
// 斐波那契（记忆化）
function fibMemo(n: number, memo: number[] = []): number {
  if (n <= 1) return n;
  if (memo[n]) return memo[n];

  memo[n] = fibMemo(n - 1, memo) + fibMemo(n - 2, memo);
  return memo[n];
}

// 背包问题
function knapsack(weights: number[], values: number[], capacity: number): number {
  const n = weights.length;
  const dp: number[][] = Array(n + 1)
    .fill(null)
    .map(() => Array(capacity + 1).fill(0));

  for (let i = 1; i <= n; i++) {
    for (let w = 0; w <= capacity; w++) {
      if (weights[i - 1] <= w) {
        dp[i][w] = Math.max(
          dp[i - 1][w],
          dp[i - 1][w - weights[i - 1]] + values[i - 1]
        );
      } else {
        dp[i][w] = dp[i - 1][w];
      }
    }
  }

  return dp[n][capacity];
}

// 最长公共子序列
function lcs(s1: string, s2: string): number {
  const m = s1.length;
  const n = s2.length;
  const dp: number[][] = Array(m + 1)
    .fill(null)
    .map(() => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (s1[i - 1] === s2[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  return dp[m][n];
}
```

### 7. 常见模式

| 模式 | 问题 | 解法 |
|-----|------|-----|
| 双指针 | 有序数组去重、两数之和 | 左右指针/快慢指针 |
| 滑动窗口 | 最大子数组、子串问题 | 扩展+收缩窗口 |
| 哈希表 | 重复检测、快速查找 | Map/Set |
| 堆 | Top K、中位数 | PriorityQueue |
| 回溯 | 全排列、子集 | 递归+状态恢复 |
| 分治 | 归并排序、逆序对 | 递归合并 |

---

## 触发条件

当用户请求算法实现、性能优化、复杂度分析，或涉及排序/查找/树/图/动态规划问题时，自动应用此技能。
