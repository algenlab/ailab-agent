import { useState, useCallback, useMemo, useRef, useEffect } from 'react';

class UnionFind {
  constructor(n) {
    this.parent = Array.from({ length: n }, (_, i) => i);
    this.rank = Array(n).fill(0);
    this.componentCount = n;
    this.history = [];
    this._recordSnapshot('初始化：每台计算机各自为一个省份，parent[i]=i，共 ' + n + ' 个省份');
  }

  _recordSnapshot(action) {
    this.history.push({
      parent: [...this.parent],
      rank: [...this.rank],
      componentCount: this.componentCount,
      action
    });
  }

  find(x) {
    if (this.parent[x] !== x) {
      const originalParent = this.parent[x];
      this.parent[x] = this.find(this.parent[x]);
      if (originalParent !== this.parent[x]) {
        this._recordSnapshot(
          `路径压缩优化：find(${x}) 发现其父节点是 ${originalParent}，但根节点是 ${this.parent[x]}，将其 parent 直接指向根节点 ${this.parent[x]}，加速后续查找`
        );
      }
    }
    return this.parent[x];
  }

  union(x, y) {
    const rootX = this.find(x);
    const rootY = this.find(y);

    if (rootX === rootY) {
      this._recordSnapshot(
        `union(${x}, ${y})：计算机 ${x} 和 ${y} 的根节点均为 ${rootX}，它们已在同一省份内，无需合并`
      );
      return false;
    }

    const description = `发现 isConnected[${x}][${y}]=1，但 find(${x})=${rootX}，find(${y})=${rootY}，根节点不同 → 需要合并两个省份`;

    if (this.rank[rootX] < this.rank[rootY]) {
      this.parent[rootX] = rootY;
      this._recordSnapshot(
        `${description}：将根 ${rootX} 指向 ${rootY}（rank[${rootX}]=${this.rank[rootX]} < rank[${rootY}]=${this.rank[rootY]}，按秩合并）`
      );
    } else if (this.rank[rootX] > this.rank[rootY]) {
      this.parent[rootY] = rootX;
      this._recordSnapshot(
        `${description}：将根 ${rootY} 指向 ${rootX}（rank[${rootY}]=${this.rank[rootY]} < rank[${rootX}]=${this.rank[rootX]}，按秩合并）`
      );
    } else {
      this.parent[rootY] = rootX;
      this.rank[rootX]++;
      this._recordSnapshot(
        `${description}：将根 ${rootY} 指向 ${rootX}（两者秩相等均为 ${this.rank[rootX] - 1}，提升 ${rootX} 的秩为 ${this.rank[rootX]}）`
      );
    }

    this.componentCount--;
    this._recordSnapshot(
      `合并完成！省份数量从 ${this.componentCount + 1} 减少为 ${this.componentCount}，当前共有 ${this.componentCount} 个省份`
    );
    return true;
  }

  getSnapshot(index) {
    if (index < 0 || index >= this.history.length) return null;
    return { ...this.history[index], step: index };
  }

  get totalSteps() {
    return this.history.length;
  }
}

function buildUnionFindSteps(isConnected) {
  const n = isConnected.length;
  const uf = new UnionFind(n);

  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (isConnected[i][j] === 1) {
        uf._recordSnapshot(`检查 isConnected[${i}][${j}]：发现计算机 ${i} 与 ${j} 之间存在直接物理连接（值为 1）`);
        uf.union(i, j);
      } else {
        uf._recordSnapshot(`检查 isConnected[${i}][${j}]：计算机 ${i} 与 ${j} 之间无直接连接（值为 0），跳过`);
      }
    }
  }

  uf._recordSnapshot(`算法完成！最终 parent 数组：${JSON.stringify(uf.parent)}，省份总数 = ${uf.componentCount}`);
  return uf;
}

export function useUnionFind(inputMatrix, addLog) {
  const ufRef = useRef(null);
  const [currentStep, setCurrentStep] = useState(0);
  const initializedRef = useRef(false);

  useEffect(() => {
    // Prevent duplicate initialization from React StrictMode double-mounting
    if (initializedRef.current) return;
    initializedRef.current = true;

    const uf = buildUnionFindSteps(inputMatrix);
    ufRef.current = uf;
    setCurrentStep(uf.totalSteps - 1);
    addLog(`🔧 并查集追踪系统已就绪，共 ${uf.totalSteps} 个步骤（包含初始化、检查连接、合并操作及最终结果）`, 'info');
  }, []);

  const totalSteps = ufRef.current ? ufRef.current.totalSteps : 0;

  const snapshot = useMemo(() => {
    if (!ufRef.current) return null;
    return ufRef.current.getSnapshot(currentStep);
  }, [currentStep, totalSteps]);

  const goToStep = useCallback((step) => {
    if (!ufRef.current) return;
    const clamped = Math.max(0, Math.min(step, ufRef.current.totalSteps - 1));
    if (clamped === currentStep) return;
    setCurrentStep(clamped);
    if (ufRef.current) {
      const snap = ufRef.current.getSnapshot(clamped);
      if (snap) {
        addLog(`📍 跳转到步骤 ${clamped + 1}/${ufRef.current.totalSteps}：${snap.action}`, 'info');
      }
    }
  }, [currentStep, addLog]);

  const stepForward = useCallback(() => {
    setCurrentStep(prev => {
      if (!ufRef.current) return prev;
      const next = Math.min(prev + 1, ufRef.current.totalSteps - 1);
      return next;
    });
  }, []);

  const stepBackward = useCallback(() => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  }, []);

  const reset = useCallback(() => {
    if (currentStep === 0) return;
    setCurrentStep(0);
    addLog('🔄 已重置到初始状态，所有计算机各自为一个省份', 'info');
  }, [addLog, currentStep]);

  const goToEnd = useCallback(() => {
    if (!ufRef.current) return;
    if (currentStep >= ufRef.current.totalSteps - 1) return;
    setCurrentStep(ufRef.current.totalSteps - 1);
    addLog('⏭ 已跳转到最终状态，可查看完整的 parent 数组和最终省份数量', 'info');
  }, [addLog, currentStep]);

  function getRootCount(parent) {
    const roots = new Set();
    for (let i = 0; i < parent.length; i++) {
      let x = i;
      while (parent[x] !== x) {
        x = parent[x];
      }
      roots.add(x);
    }
    return roots.size;
  }

  return {
    snapshot,
    currentStep,
    totalSteps,
    goToStep,
    stepForward,
    stepBackward,
    reset,
    goToEnd,
    getRootCount
  };
}