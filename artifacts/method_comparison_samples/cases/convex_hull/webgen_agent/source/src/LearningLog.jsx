export default function LearningLog({ entries }) {
  return (
    <div className="learning-log">
      <h3>📝 学习活动日志</h3>
      {entries.length === 0 ? (
        <p className="empty">暂无活动记录。使用导航或检查点开始学习。</p>
      ) : (
        <ul>
          {entries.map((entry, idx) => (
            <li key={idx}>
              <span className="time">{entry.time.toLocaleTimeString()}</span>
              <span className="message">{entry.message}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}