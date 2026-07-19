export interface StepData {
  stepIndex: number;
  element: number;
  heapBefore: number[];
  heapAfter: number[];
  action: 'push' | 'push-and-pop' | 'ignore';
  heapTop: number | null;
  description: string;
  heapSize: number;
}

export interface ProblemInput {
  k: number;
  nums: number[];
}

export interface QuizQuestion {
  id: number;
  question: string;
  type: 'multiple-choice' | 'text';
  options: string[];
  correctAnswer: string;
  hint: string;
  explanation: string;
}

export interface LogEntry {
  id: number;
  timestamp: number;
  type:
    | 'step-nav'
    | 'quiz-attempt'
    | 'hint-request'
    | 'show-answer'
    | 'reset'
    | 'auto-play';
  detail: string;
  isCorrect?: boolean;
}