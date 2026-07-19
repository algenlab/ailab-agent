import React from 'react';
import { LogEntry } from '../types';

interface ActivityLogProps {
  entries: LogEntry[];
}

const typeConfig: Record<
  LogEntry['type'],
  { icon: string; color: string }
> = {
  navigation: { icon: '📍', color: 'text-blue-600' },
  'quiz-correct': { icon: '✅', color: 'text-emerald-600' },
  'quiz-incorrect': { icon: '❌', color: 'text-red-600' },
  hint: { icon: '💡', color: 'text-amber-600' },
  'show-answer': { icon: '👁️', color: 'text-purple-600' },
  reset: { icon: '🔄', color: 'text-gray-600' },
  'slider-change': { icon: '🎚️', color: 'text-indigo-600' },
};

function formatTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 5) return '刚刚';
  if (diffSec < 60) return `${diffSec}秒前`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  return `${diffHour}小时前`;
}

export const ActivityLog: React.FC<ActivityLogProps> = ({ entries }) => {
  return (
    <div className="card h-full flex flex-col">
      <div className="p-4 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          📜 活动日志
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto max-h-64 p-3 space-y-1">
        {entries.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-8">
            暂无活动记录。开始操作后将在此显示。
          </div>
        ) : (
          entries.map((entry) => {
            const config = typeConfig[entry.type];
            return (
              <div
                key={entry.id}
                className="flex items-start gap-2 px-2 py-1.5 rounded text-sm hover:bg-gray-50 animate-slide-up"
              >
                <span className={`${config.color} text-base flex-shrink-0 mt-0.5`}>
                  {config.icon}
                </span>
                <span className="text-gray-700 flex-1">{entry.message}</span>
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {formatTime(entry.timestamp)}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
