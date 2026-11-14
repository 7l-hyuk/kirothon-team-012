// 신고 진행 단계 표시: 번호 원 5개. current가 STAGES.length이면 모두 끝난 상태.
// compact이면 번호 원 대신 얇은 막대와 단계 이름 한 줄로 줄인다(대화를 아래로 스크롤했을 때).
import { Fragment } from "react";
import { STAGES } from "../data/content";
import { Check } from "./icons/Icons";

export function Stepper({ current, compact = false }: { current: number; compact?: boolean }) {
  const done = current >= STAGES.length;
  const label = done ? "모두 끝났어요" : STAGES[current];
  const pos = `${Math.min(current + 1, STAGES.length)}/${STAGES.length}`;
  return (
    <div className={`stepper ${compact ? "compact" : ""}`} role="group" aria-label={`진행 단계 ${pos}: ${label}`}>
      <div className="st-row" aria-hidden>
        {STAGES.map((s, i) => (
          <Fragment key={s}>
            {i > 0 && <span className={`st-line ${i <= current ? "done" : ""}`} />}
            <span className={`st-dot ${i < current ? "done" : i === current ? "now" : ""}`}>
              {i < current ? <Check size={14} stroke={3} /> : i + 1}
            </span>
          </Fragment>
        ))}
      </div>
      <div className="st-bar" aria-hidden>
        {STAGES.map((s, i) => <i key={s} className={i < current ? "done" : i === current ? "now" : ""} />)}
      </div>
      <div className="st-label">{compact && !done && <span className="st-pos">{pos}</span>}{label}</div>
    </div>
  );
}
