/**
 * Generate all steps of the fast power modulo algorithm for visualization.
 * Returns an array of state snapshots, starting with initial state (step 0)
 * and then one state after processing each bit of the exponent (LSB first).
 */
export function generateSteps(base, exponent, mod) {
  const steps = [];
  const origExponent = exponent;

  let answer = 1;
  let cur = base % mod;
  let e = exponent;

  // Initial state (before processing any bit)
  steps.push({
    stepIndex: 0,
    answer: 1,
    cur,
    e,
    bit: null,
    description: 'Initial state: answer = 1, cur = base % mod'
  });

  let bitPos = 0;
  let remainingExp = e;

  while (remainingExp > 0) {
    const bit = remainingExp & 1;
    const prevAnswer = answer;
    const prevCur = cur;

    if (bit === 1) {
      answer = (answer * cur) % mod;
    }
    e = remainingExp >> 1; // after shift for next iteration

    let description = `Bit ${bitPos} (LSB: ${bitPos}): `;
    if (bit === 1) {
      description += `bit = 1, multiply: answer = (${prevAnswer} * ${cur}) % ${mod} = ${answer}`;
    } else {
      description += `bit = 0, answer unchanged`;
    }

    // After handling this bit, cur is squared for the next bit (but recorded after current step)
    // For the step state, we show the cur before squaring? We'll show cur value at this position
    // and then in the next step, cur will be squared.
    const curForThisStep = cur;
    cur = (cur * cur) % mod;

    remainingExp = e;

    steps.push({
      stepIndex: bitPos + 1,
      answer,
      cur: cur, // cur for the *next* power (but we'll display as current cur after squaring)
      curBeforeSquare: curForThisStep,
      e: remainingExp,
      bit,
      bitPos,
      description
    });

    bitPos++;
  }

  // Add a final step showing the result after loop ends
  steps.push({
    stepIndex: steps.length,
    answer: answer,
    cur: cur,
    e: 0,
    bit: null,
    description: `Loop finished. Final result: ${answer}`
  });

  return steps;
}

export function computeResult(base, exponent, mod) {
  let answer = 1;
  let cur = base % mod;
  let e = exponent;
  while (e > 0) {
    if (e & 1) {
      answer = (answer * cur) % mod;
    }
    cur = (cur * cur) % mod;
    e >>= 1;
  }
  return answer;
}

/**
 * Create binary string representation of original exponent with highlighted bits.
 */
export function getBinaryRepresentation(exponent) {
  const binary = exponent.toString(2);
  return binary;
}

export function getBitPositions(exponent) {
  const binary = exponent.toString(2);
  const positions = [];
  for (let i = 0; i < binary.length; i++) {
    const pos = binary.length - 1 - i;
    if (binary[i] === '1') {
      positions.push(pos);
    }
  }
  return positions; // LSB first order? We'll return in LSB order: smallest to largest
}
