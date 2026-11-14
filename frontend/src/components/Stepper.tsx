// 신고 진행 단계 표시: 번호 원 5개. current가 STAGES.length이면 모두 끝난 상태.
// 지금 단계 이름은 그 번호 원 바로 아래 가운데에 둔다(첫·마지막 단계도 같다. 행 양옆 여백이 이름 폭의 절반보다 넓어 잘리지 않는다).
// compact이면 번호 원 대신 얇은 막대와 단계 이름 한 줄로 줄인다(대화를 아래로 스크롤했을 때). 이때와 모두 끝났을 때는 이름을 가운데에 둔다.
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
              {i === current && <span className="st-under">{s}</span>}
            </span>
          </Fragment>
        ))}
      </div>
      <div className="st-bar" aria-hidden>
        {STAGES.map((s, i) => <i key={s} className={i < current ? "done" : i === current ? "now" : ""} />)}
      </div>
      {/* 번호 원 아래 이름을 쓰는 동안에도 높이를 그대로 두려고 자리만 남긴다 */}
      <div className={`st-label ${compact || done ? "" : "ghost"}`}>{compact && !done && <span className="st-pos">{pos}</span>}{label}</div>
    </div>
  );
}
