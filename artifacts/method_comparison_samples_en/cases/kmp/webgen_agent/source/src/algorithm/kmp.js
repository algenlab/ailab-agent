/**
 * Generates step-by-step trace for KMP string matching algorithm.
 * @param {string} pattern - The pattern to search for
 * @param {string} text - The text to search in
 * @returns {{ steps: Array, result: number, pi: Array }}
 */
export function generateKMPSteps(pattern, text) {
  const steps = [];
  const pi = new Array(pattern.length).fill(0);

  // ---- Build Prefix Table ----
  steps.push({
    id: 'prefix_init',
    type: 'prefix_init',
    title: 'Prefix Table Initialization',
    description: `Set pi[0] = 0. A single character pattern has no proper prefix that is also a suffix.`,
    state: { phase: 'prefix', i: 0, j: 0, pi: [0], matchStatus: null }
  });

  let j = 0; // length of previous longest prefix suffix
  for (let i = 1; i < pattern.length; i++) {
    // Record the comparison state
    steps.push({
      id: `prefix_compare_${i}`,
      type: 'prefix_compare',
      title: `Prefix Table Step: i=${i}, j=${j}`,
      description: `Compare pattern[${i}]='${pattern[i]}' with pattern[${j}]='${pattern[j]}'.`,
      state: { phase: 'prefix', i, j, pi: [...pi], matchStatus: 'comparing' }
    });

    while (j > 0 && pattern[i] !== pattern[j]) {
      const prevJ = j;
      j = pi[j - 1];
      steps.push({
        id: `prefix_backtrack_${i}`,
        type: 'prefix_backtrack',
        title: `Prefix Mismatch: pattern[${i}]='${pattern[i]}' ≠ pattern[${prevJ}]='${pattern[prevJ]}'`,
        description: `Mismatch at j=${prevJ}. Backtrack using pi[${prevJ - 1}]=${j}. Set j = ${j}.`,
        state: { phase: 'prefix', i, j, pi: [...pi], matchStatus: 'mismatch', backtrackFrom: prevJ, backtrackTo: j }
      });
    }

    if (pattern[i] === pattern[j]) {
      j++;
      pi[i] = j;
      steps.push({
        id: `prefix_match_${i}`,
        type: 'prefix_match',
        title: `Prefix Match: pattern[${i}]='${pattern[i]}' == pattern[${j - 1}]`,
        description: `Characters match! Increment j to ${j}. Set pi[${i}] = ${j}.`,
        state: { phase: 'prefix', i, j, pi: [...pi], matchStatus: 'match' }
      });
    } else {
      pi[i] = 0;
      steps.push({
        id: `prefix_mismatch_${i}`,
        type: 'prefix_mismatch',
        title: `Prefix Mismatch Final: pattern[${i}]='${pattern[i]}' ≠ pattern[${j}] and j=0`,
        description: `No match with the prefix start. Set pi[${i}] = 0.`,
        state: { phase: 'prefix', i, j, pi: [...pi], matchStatus: 'mismatch' }
      });
    }
  }

  steps.push({
    id: 'prefix_done',
    type: 'prefix_done',
    title: 'Prefix Table Complete',
    description: `Prefix table built successfully: pi = [${pi.join(', ')}]`,
    state: { phase: 'prefix', pi: [...pi], matchStatus: null }
  });

  // ---- Matching Phase ----
  steps.push({
    id: 'match_init',
    type: 'match_init',
    title: 'Start Matching',
    description: 'Initialize i=0 (text index), j=0 (pattern index). Begin scanning the text.',
    state: { phase: 'match', i: 0, j: 0, pi: [...pi], textIndex: 0, patternIndex: 0, matchStatus: null }
  });

  let i = 0; // index for text
  j = 0; // index for pattern

  while (i < text.length) {
    steps.push({
      id: `match_compare_${i}_${j}`,
      type: 'match_compare',
      title: `Compare: text[${i}]='${text[i]}' vs pattern[${j}]='${pattern[j]}'`,
      description: `Comparing characters at current positions.`,
      state: { phase: 'match', i, j, pi: [...pi], textIndex: i, patternIndex: j, matchStatus: 'comparing' }
    });

    if (text[i] === pattern[j]) {
      steps.push({
        id: `match_char_match_${i}_${j}`,
        type: 'match_char_match',
        title: `Match: text[${i}]='${text[i]}' == pattern[${j}]='${pattern[j]}'`,
        description: `Characters match! Advance i to ${i + 1}, j to ${j + 1}.`,
        state: { phase: 'match', i, j, pi: [...pi], textIndex: i, patternIndex: j, matchStatus: 'match' }
      });
      i++;
      j++;

      if (j === pattern.length) {
        const foundIndex = i - j;
        steps.push({
          id: 'match_found',
          type: 'match_found',
          title: 'Pattern Found!',
          description: `j=${j} equals the pattern length (${pattern.length}). Pattern found at index ${foundIndex} (i - j = ${i} - ${j}). Matching complete.`,
          result: foundIndex,
          state: { phase: 'match', i, j, pi: [...pi], textIndex: i, patternIndex: j, matchStatus: 'found', result: foundIndex }
        });
        return { steps, result: foundIndex, pi };
      }
    } else {
      // Mismatch
      if (j > 0) {
        const prevJ = j;
        j = pi[j - 1];
        steps.push({
          id: `match_mismatch_backtrack_${i}_${prevJ}`,
          type: 'match_mismatch_backtrack',
          title: `Mismatch: text[${i}]='${text[i]}' ≠ pattern[${prevJ}]='${pattern[prevJ]}'`,
          description: `Mismatch at j=${prevJ}. Backtrack using pi[${prevJ - 1}]=${j}. Set j = ${j}, keep i = ${i}.`,
          state: { phase: 'match', i, j, pi: [...pi], textIndex: i, patternIndex: j, matchStatus: 'mismatch_backtrack', backtrackFrom: prevJ, backtrackTo: j }
        });
      } else {
        steps.push({
          id: `match_mismatch_advance_${i}`,
          type: 'match_mismatch_advance',
          title: `Mismatch at j=0: text[${i}]='${text[i]}' ≠ pattern[0]='${pattern[0]}'`,
          description: `j is already 0, cannot backtrack. Advance i to ${i + 1}.`,
          state: { phase: 'match', i, j, pi: [...pi], textIndex: i, patternIndex: j, matchStatus: 'mismatch_advance' }
        });
        i++;
      }
    }
  }

  steps.push({
    id: 'match_not_found',
    type: 'match_not_found',
    title: 'Pattern Not Found',
    description: 'Reached the end of the text without matching the full pattern. Result: -1.',
    result: -1,
    state: { phase: 'match', i, j, pi: [...pi], textIndex: i, patternIndex: j, matchStatus: 'not_found', result: -1 }
  });

  return { steps, result: -1, pi };
}