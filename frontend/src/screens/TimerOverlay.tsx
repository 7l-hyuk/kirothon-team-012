// S6-3 1분 타이머
import { useStore } from "../app/store";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { Check, Clock } from "../components/icons/Icons";

export function TimerOverlay() {
  const { s, timerShot } = useStore();
  if (!s.timer) return null;
  const pct = (s.sec / (s.timerTotal || 60)) * 100;
  const clock = `${Math.floor(s.sec / 60)}:${String(s.sec % 60).padStart(2, "0")}`;
  // 10초 이하: 원을 강조. 0초: 맥박 효과 + 큰 버튼
  const phase = s.timerDone ? "done" : s.sec <= 10 ? "soon" : "";
  return (
    <div className={`timer ${phase}`}>
      <WaveBackdrop variant="both" />
      <div className="row" style={{ alignSelf: "stretch", justifyContent: "flex-end", height: 44 }}>
        {/* 이미 두 장을 찍었거나 기다릴 필요가 없으면 바로 다음 접수 단계로 넘어간다 */}
        {!s.timerDone && <button className="btn btn-sm btn-secondary" onClick={timerShot}>건너뛰기</button>}
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 28 }}>
        <div className="row small strong" style={{ color: "var(--navy)" }}><Clock size={18} />같은 위치에서 두 번째 사진까지</div>
        <div className="ring" style={{ background: `conic-gradient(var(--navy) ${pct}%, var(--navy-soft) 0)` }} role="timer" aria-label={`남은 시간 ${clock}`}>
          <div className="face">{s.timerDone ? <Check size={64} stroke={3} /> : clock}</div>
        </div>
        {!s.timerDone ? (
          <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1.45, textWrap: "balance" }}>그 자리에서 기다려 주세요. 자리를 옮기면 반려될 수 있어요.</div>
            {s.rehearsal?.capture_guide.interval_note && <div className="small sub">{s.rehearsal.capture_guide.interval_note}</div>}
          </div>
        ) : (
          <div className="timer-go" role="alert" style={{ fontSize: 22, fontWeight: 700, textAlign: "center" }}>지금 두 번째 사진을 찍으세요</div>
        )}
      </div>
      {s.timerDone && <button className="btn btn-primary btn-lg btn-block timer-go" onClick={timerShot}>찍었어요</button>}
    </div>
  );
}
