/**
 * Problem: Number of Provinces
 * Algorithm family: Union Find
 *
 * In a large enterprise network, the physical connections between computers are
 * represented by a symmetric matrix isConnected, where isConnected[i][j] = 1
 * indicates that computers i and j are directly connected, and 0 indicates they
 * are not; diagonal elements are all 1 (each computer is connected to itself).
 * If two computers can communicate through a series of direct connections, they
 * belong to the same network area (called a "province"). Calculate the total
 * number of distinct provinces in the entire network.
 */

export interface ProblemInput {
  isConnected: number[][];
}

export const problemInput: ProblemInput = {
  isConnected: [
    [1, 1, 0],
    [1, 1, 0],
    [0, 0, 1],
  ],
};

export const expectedAnswer: number = 2;

export interface AlgorithmStep {
  /** Step index (0-based) */
  index: number;
  /** Description of this step */
  description: string;
  /** i, j being processed (or -1 for initial/final states) */
  i: number;
  j: number;
  /** State of parent array at this step */
  parent: number[];
  /** Whether a union was performed in this step */
  unionPerformed: boolean;
  /** Which nodes were unioned */
  unionedNodes: [number, number] | null;
  /** Number of distinct provinces after this step */
  provinceCount: number;
}

/**
 * Generate all algorithm steps by simulating Union-Find.
 * Includes initial state (step 0) and one step per matrix cell checked,
 * plus a final state encapsulating the answer.
 */
export function generateSteps(input: ProblemInput): AlgorithmStep[] {
  const { isConnected } = input;
  const n = isConnected.length;

  // Initialize parent: each node is its own parent.
  const parent: number[] = [];
  for (let k = 0; k < n; k++) parent.push(k);

  const find = (x: number, p: number[]): number => {
    while (p[x] !== x) {
      p[x] = p[p[x]]; // Path compression
      x = p[x];
    }
    return x;
  };

  const countProvinces = (p: number[]): number => {
    let count = 0;
    for (let k = 0; k < n; k++) {
      if (p[k] === k) count++;
    }
    return count;
  };

  const steps: AlgorithmStep[] = [];

  // Step 0: initial state
  steps.push({
    index: 0,
    description: 'Initial state: each computer is its own province. The parent array is initialized so that parent[i] = i for all computers.',
    i: -1,
    j: -1,
    parent: [...parent],
    unionPerformed: false,
    unionedNodes: null,
    provinceCount: n,
  });

  let stepIdx = 1;

  // Iterate over the upper triangle (excluding diagonal)
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (isConnected[i][j] === 1) {
        const rootI = find(i, parent);
        const rootJ = find(j, parent);

        if (rootI !== rootJ) {
          // Union: attach rootJ under rootI
          parent[rootJ] = rootI;

          const newParent = [...parent];
          const newCount = countProvinces(newParent);

          steps.push({
            index: stepIdx,
            description: `Computers ${i} and ${j} are connected (isConnected[${i}][${j}] = 1). find(${i}) = ${rootI}, find(${j}) = ${rootJ}. Since roots differ, union is performed: parent[${rootJ}] = ${rootI}. The number of provinces decreases.`,
            i,
            j,
            parent: newParent,
            unionPerformed: true,
            unionedNodes: [i, j],
            provinceCount: newCount,
          });
          stepIdx++;
        } else {
          const newParent = [...parent];
          const newCount = countProvinces(newParent);

          steps.push({
            index: stepIdx,
            description: `Computers ${i} and ${j} are connected (isConnected[${i}][${j}] = 1). find(${i}) = ${rootI}, find(${j}) = ${rootJ}. Roots are the same, so no union is needed. They already belong to the same province.`,
            i,
            j,
            parent: newParent,
            unionPerformed: false,
            unionedNodes: null,
            provinceCount: newCount,
          });
          stepIdx++;
        }
      } else {
        steps.push({
          index: stepIdx,
          description: `Computers ${i} and ${j} are not directly connected (isConnected[${i}][${j}] = 0). No action is taken.`,
          i,
          j,
          parent: [...parent],
          unionPerformed: false,
          unionedNodes: null,
          provinceCount: countProvinces(parent),
        });
        stepIdx++;
      }
    }
  }

  // Final step
  const finalParent = [...parent];
  const finalCount = countProvinces(finalParent);

  steps.push({
    index: stepIdx,
    description: `Algorithm complete. The final parent array shows ${finalCount} distinct root(s), meaning there are ${finalCount} province(s) in the network.`,
    i: -1,
    j: -1,
    parent: finalParent,
    unionPerformed: false,
    unionedNodes: null,
    provinceCount: finalCount,
  });

  return steps;
}

export const allSteps = generateSteps(problemInput);
