import { useEffect, useRef, useState } from "react";
import { useStore } from "../app/store";
import { Badge, Bot, Check, Fine, Mark } from "../components/ui";
import { ReportFlow } from "./ReportFlow";
import { AppBar } from "../components/AppBar";
import { Stepper } from "../components/Stepper";
import { NotReportableArt } from "../components/motifs/Illustrations";

export function Chat() {
  const st = useStore();
  const { s, n } = st;
  const A = s.scen === "A";
  const an = s.analysis;
  const [why, setWhy] = useState<Record<string, boolean>>({});
  const ref = useRef<HTMLDivElement>(null);

  // 새 카드가 붙을 때마다 맨 아래로 스크롤한다.
  const key = [s.p, s.cur, s.rstage, s.gIdx, !!s.guide, s.draftBusy, s.phase, s.analysisError, !!s.evidence, s.uploading, s.rhBusy, !!s.rehearsal, s.finished.length].join("|");
  useEffect(() => {
    const go = () => { const el = ref.current; if (el) el.scrollTop = el.scrollHeight; };
    requestAnimationFrame(go); const t = setTimeout(go, 120); return () => clearTimeout(t);
  }, [key]);

  const stage = s.p <= 1 ? 0 : s.p === 2 ? 1 : s.rstage === "guide" || s.rstage === "next" ? 3 : 2;
  const r = s.reports[s.cur];
  const countLabel = s.p >= 3 && r ? `${r.sequence}/${s.total || s.reports.length}건` : "";
  // 이어서 하기로 들어오면 미리보기 대신 서버에 올린 사진을 보여 준다.
  const pics = s.previews.length ? s.previews : (an?.input.photos ?? []).map((p) => p.url);

  // 아래로 스크롤하면 단계 표시를 얇게 줄인다.
  // 줄이면 대화 영역이 약 40px 커지므로, 스크롤 여유가 충분할 때만 줄여 깜빡임을 막는다.
  const [compact, setCompact] = useState(false);
  const onScroll = () => {
    const el = ref.current;
    if (!el) return;
    const room = el.scrollHeight - el.clientHeight;
    setCompact((c) => (c ? el.scrollTop > 8 : el.scrollTop > 32 && room > 120));
  };

  return (
    <div className="chat">
      <div className="chat-head">
        <AppBar title="신고하기" onBack={st.goHome} right={countLabel ? <span className="ab-count">{countLabel}</span> : undefined} />
        <Stepper current={stage} compact={compact} />
      </div>

      <div ref={ref} className="chat-body" onScroll={onScroll}>
        <div className="me">
          {pics.length > 0 && (
            <div className="row" style={{ gap: 6, justifyContent: "flex-end", flexWrap: "wrap" }}>
              {pics.map((src, i) => <img key={src} src={src} alt={`올린 사진 ${i + 1}`} className="photo photo-chat" style={{ objectFit: "cover", padding: 0 }} />)}
            </div>
          )}
          <div className="bubble">{s.sent}</div>
        </div>

        {/* S2 분석 중: AI 응답까지 4~9초 */}
        {s.p === 1 && !s.analysisError && (
          <div className="bot">
            <div className="row" style={{ gap: 10 }}><span className="typing" aria-hidden><i /><i /><i /></span>살펴보고 있어요</div>
            <div className="small sub" style={{ marginTop: 4 }} aria-live="polite">{s.phase ? "신고할 수 있는 항목을 찾는 중" : "무엇이 찍혔는지 확인하는 중"}</div>
          </div>
        )}

        {/* S2 분석 실패: 서버가 준 문구(detail)를 그대로 보여 준다 */}
        {s.p === 1 && s.analysisError && (
          <div className="panel" role="alert">
            <div className="row"><Mark kind="warn" /><span className="strong" style={{ color: "var(--warn-ink)" }}>분석하지 못했어요</span></div>
            <div style={{ textWrap: "pretty" }}>{s.analysisError}</div>
            <div className="row">
              <button className="btn btn-secondary" onClick={st.goHome}>다시 입력</button>
              <button className="btn btn-primary btn-grow" onClick={st.retry}>다시 시도</button>
            </div>
          </div>
        )}

        {/* S3 신고 불가 */}
        {an && !A && s.p >= 2 && (
          <div className="panel">
            <div className="illu-wrap"><NotReportableArt /></div>
            <div className="row"><Mark kind="mute" /><span className="strong" style={{ fontSize: 16 }}>{an.not_reportable?.title ?? "신고가 어려운 상황이에요"}</span></div>
            <div style={{ textWrap: "pretty" }}>{an.not_reportable?.message ?? an.summary}</div>
            {an.not_reportable?.basis && <div className="note note-sub">{an.not_reportable.basis}</div>}
            {an.unsupported_items.length > 0 && <Unsupported items={an.unsupported_items} />}
            <button className="btn btn-outline" onClick={st.goHome}>다른 상황 입력하기</button>
            <Fine />
          </div>
        )}

        {/* S3 항목 선택 */}
        {an && A && s.p >= 2 && (
          <>
            <Bot>{an.summary}</Bot>
            <div className="panel" style={{ gap: 14 }}>
              {an.items.map((it, i) => {
                const on = s.selected.includes(it.type_id);
                const open = !!why[it.type_id];
                return (
                  <div key={it.type_id} className="col" style={{ gap: 14 }}>
                    {i > 0 && <div className="divider" />}
                    <div className="col">
                      <Badge kind={it.category === "report" ? "신고" : "민원"} />
                      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                        <Check on={on} label={`${it.label} 선택`} onClick={() => s.p === 2 && st.toggleItem(it.type_id)} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div className="strong">{it.label}</div>
                          <div className="small sub">{it.subtitle}</div>
                          <button className="link" aria-expanded={open} onClick={() => setWhy({ ...why, [it.type_id]: !open })}>왜 신고가 되나요?</button>
                          {open && <div className="note">{it.reason}</div>}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
              {an.unsupported_items.length > 0 && (<><div className="divider" /><Unsupported items={an.unsupported_items} /></>)}
              {s.p === 2 && (
                <button className="btn btn-primary" disabled={!n || s.creating} onClick={st.startPrep}>
                  {s.creating ? "준비하고 있어요" : n ? `${n}건 신고 준비하기` : "항목을 선택해 주세요"}
                </button>
              )}
              <Fine />
            </div>
          </>
        )}

        {s.p >= 3 && <ReportFlow />}
      </div>
    </div>
  );
}

function Unsupported({ items }: { items: { label: string; message: string }[] }) {
  return (
    <div className="col" style={{ gap: 4 }}>
      <div className="xs strong sub">신고가 어려운 항목</div>
      {items.map((u) => (
        <div key={u.label} style={{ display: "flex", gap: 12, color: "var(--sub)" }}>
          <span style={{ width: 22, textAlign: "center", flex: "none" }}>–</span>
          <div><div style={{ fontWeight: 500 }}>{u.label}</div><div className="small">{u.message}</div></div>
        </div>
      ))}
    </div>
  );
}
