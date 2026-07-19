import React, { useMemo } from 'react';
import { useAlgorithm } from './useAlgorithm';
import { TemperatureArray } from './components/TemperatureArray';
import { StackView } from './components/StackView';
import { AnswerArray } from './components/AnswerArray';
import { TraceTable } from './components/TraceTable';
import { QuizPanel } from './components/QuizPanel';
import { ActivityLog } from './components/ActivityLog';
import { NavigationControls } from './components/NavigationControls';
import { EXPECTED_ANSWER, DEFAULT_TEMPERATURES } from './algorithm';

const App: React.FC = () => {
  const algo = useAlgorithm();

  const cellStates = useMemo(
    () =>
      algo.temperatures.map((_, idx) => algo.getCellStateForIndex(idx)),
    [algo]
  );

  const isComplete = algo.currentStepIndex >= algo.maxStepIndex;

  const modifiedAnswer4 = useMemo(() => {
    if (algo.sliderModified) {
      const finalStep = algo.modifiedSteps[algo.modifiedSteps.length - 1];
      return finalStep?.answerState[4] ?? null;
    }
    return null;
  }, [algo.sliderModified, algo.modifiedSteps]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 flex items-center gap-2">
              🌱 每日温度
              <span className="text-sm font-normal text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                单调栈
              </span>
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              算法家族：栈 / 队列 / 单调栈
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full font-medium">
              农业温室场景
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        <div className="card p-4 sm:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-3 space-y-3">
              <h2 className="text-lg font-semibold text-gray-800">📖 问题描述</h2>
              <p className="text-gray-600 leading-relaxed">
                农业温室有一串未来每日温度预报 <code className="bg-gray-100 px-1.5 py-0.5 rounded text-emerald-700 font-mono text-sm">temperatures</code>，
                管理员想知道<strong>每一天之后还要等几天才会出现更高温度</strong>，以便安排自动通风和遮阳策略。
                如果之后都不会升温，则该位置为 <strong>0</strong>。
              </p>
              <div className="flex flex-wrap gap-4">
                <div className="bg-gray-50 rounded-lg p-3 flex-1 min-w-[200px]">
                  <span className="text-xs text-gray-500 uppercase font-semibold">输入</span>
                  <div className="font-mono text-sm text-gray-800 mt-1">
                    [{DEFAULT_TEMPERATURES.join(', ')}]
                  </div>
                </div>
                <div className="bg-emerald-50 rounded-lg p-3 flex-1 min-w-[200px]">
                  <span className="text-xs text-emerald-600 uppercase font-semibold">期望输出</span>
                  <div className="font-mono text-sm text-emerald-800 mt-1">
                    [{EXPECTED_ANSWER.join(', ')}]
                  </div>
                </div>
              </div>
              <details className="text-sm text-gray-500">
                <summary className="cursor-pointer font-medium text-emerald-700 hover:text-emerald-800">
                  参考策略
                </summary>
                <p className="mt-2 bg-gray-50 p-3 rounded">
                  维护温度单调递减的下标栈，遇到更高温度时弹栈并写答案。
                </p>
              </details>
            </div>
            <div className="lg:col-span-2">
              <ActivityLog entries={algo.activityLog} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-3">
            <TemperatureArray
              temperatures={algo.temperatures}
              cellStates={cellStates}
              currentIndex={algo.currentStep.processingIndex}
              answerState={algo.currentStep.answerState}
            />
          </div>
          <div className="lg:col-span-2">
            <StackView
              stack={algo.currentStep.stackAfter}
              temperatures={algo.temperatures}
              pops={algo.currentStep.pops}
              isProcessing={
                algo.currentStep.id > 0 &&
                algo.currentStep.id <= algo.maxStepIndex
              }
            />
          </div>
          <div className="lg:col-span-1">
            <AnswerArray
              answerState={algo.currentStep.answerState}
              expectedAnswer={EXPECTED_ANSWER}
              showFinalAnswer={algo.showFinalAnswer}
              isComplete={isComplete}
            />
          </div>
        </div>

        <NavigationControls
          currentStepIndex={algo.currentStepIndex}
          maxStepIndex={algo.maxStepIndex}
          onPrev={algo.prevStep}
          onNext={algo.nextStep}
          onReset={algo.reset}
          onRevealHint={algo.revealHint}
          onRevealAnswer={algo.revealAnswer}
          hintsRevealed={algo.hintsRevealed}
          showFinalAnswer={algo.showFinalAnswer}
        />

        <TraceTable
          steps={algo.steps}
          currentStepIndex={algo.currentStepIndex}
          temperatures={algo.temperatures}
          onStepClick={algo.goToStep}
        />

        <QuizPanel
          quizState={algo.quizState}
          sliderValue={algo.sliderValue}
          sliderModified={algo.sliderModified}
          modifiedAnswer={modifiedAnswer4}
          onSubmitQ1={(ans) => algo.submitQuizAnswer('q1', ans, 'A')}
          onSubmitQ2={(ans) => algo.submitQuizAnswer('q2', ans, 'A')}
          onSubmitQ3={(ans) => algo.submitQuizAnswer('q3', ans, 'same')}
          onRevealQ4={algo.revealQ4}
          onSliderChange={algo.handleSliderChange}
        />

        <div className="card p-4 sm:p-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            🎓 学习目标
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">✓</span>
              理解单调栈中存储的下标对应温度值保持严格递减，并能通过 trace 验证这一状态不变式。
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">✓</span>
              根据当前温度和栈顶温度，预测下一步是弹栈写答案还是压栈。
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">✓</span>
              在给定输入 temperatures 下，手动模拟弹出顺序并写出 answer 数组的最终值。
            </li>
          </ul>
        </div>
      </main>
    </div>
  );
};

export default App;
