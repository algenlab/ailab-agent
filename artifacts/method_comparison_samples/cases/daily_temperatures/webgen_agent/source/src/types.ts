export interface PopAction {
  index: number;
  answerValue: number;
}

export interface AlgorithmStep {
  id: number;
  processingIndex: number;
  processingTemp: number | null;
  stackBefore: number[];
  pops: PopAction[];
  stackAfter: number[];
  answerState: number[];
  description: string;
}

export interface LogEntry {
  id: number;
  timestamp: Date;
  type: 'navigation' | 'quiz-correct' | 'quiz-incorrect' | 'hint' | 'show-answer' | 'reset' | 'slider-change';
  message: string;
}

export type CellState = 'pending' | 'current' | 'in-stack' | 'resolved' | 'no-answer';

export interface QuizState {
  q1Answered: boolean;
  q1Correct: boolean | null;
  q2Answered: boolean;
  q2Correct: boolean | null;
  q3Answered: boolean;
  q3Correct: boolean | null;
  q4Revealed: boolean;
}
