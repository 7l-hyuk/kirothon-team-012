import { useEffect, useRef, useState } from "react";
import { useStore } from "../app/store";
import { DRAFTS, SUBMIT_STEPS } from "../data/content";
import { Badge, Bot, Check, Fine, Mark, Photo, Thinking } from "../components/ui";
import { AppBar } from "../components/AppBar";
import { Stepper } from "../components/Stepper";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { NotReportableArt } from "../components/motifs/Illustrations";

export function Chat() {
  const st = useStore();
  const { s, set, n } = st;
  const A = s.scen === "A";
  const an = s.analysis;
  const [why, setWhy] = useState<Record<string, boolean>>({});
  const ref = useRef<HTMLDivElement>(null);

  const key = [s.p, s.busy, s.s7, s.draft, s.phase, s.analysisError].join("|");
  useEffect(() => {
    const go = () => { const el = ref.current; if (el) el.scrollTop = el.scrollHeight; };
    requestAnimationFrame(go); const t = setTimeout(go, 120); return () => clearTimeout(t);
  }, [key]);

  const stage = !A ? (s.p < 2 ? 0 : 1) : s.p <= 1 ? 0 : s.p === 2 ? 1 : s.p === 6 || s.p === 7 ? 3 : 2;
  const countLabel = A && s.p >= 3 ? `${s.p >= 8 && n === 2 ? 2 : 1}/${n}건` : "";
  const chk = s.p === 4 || s.p === 5;
  const slotOk = s.p >= 5 && !(s.p === 5 && s.busy);
  const cur = SUBMIT_STEPS[s.s7];

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
      <WaveBackdrop variant="corner" fill="var(--chat-bg)" />
      <div className="chat-head">
        <AppBar title="신고하기" onBack={st.goHome} right={countLabel ? <span className="ab-count">{countLabel}</span> : undefined} />
        <Stepper current={stage} compact={compact} />
      </div>

      <div ref={ref} className="chat-body" onScroll={onScroll}>
        <div className="me">
          {s.previews.length > 0 && (
            <div className="row" style={{ gap: 6, justifyContent: "flex-end", flexWrap: "wrap" }}>
              {s.previews.map((src, i) => <img key={src} src={src} alt={`올린 사진 ${i + 1}`} className="photo photo-chat" style={{ objectFit: "cover", padding: 0 }} />)}
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

        {/* 쓰레기·불법주정차 외 유형만 고른 경우: 증거 안내는 다음 연동 PR(feat/fe-evidence)에서 연결한다 */}
        {an && A && s.p >= 3 && !s.trash && !s.park && (
          <div className="panel">
            <div>신고 건을 만들었어요. 이 유형의 증거 안내는 곧 연결돼요.</div>
            <button className="btn btn-outline" onClick={st.goHome}>처음으로</button>
          </div>
        )}

        {/* S4 증거 안내 */}
        {A && s.trash && s.p >= 3 && (
          <>
            <Bot>쓰레기 무단투기부터 준비할게요. 사진이 1장 더 필요해요.</Bot>
            <div className="panel">
              <div className="strong">쓰레기 무단투기 · 필요한 사진 2장</div>
              <div style={{ display: "flex", gap: 10 }}><Mark kind="ok" /><div><div>쓰레기 전체가 보이는 사진</div><div className="small" style={{ color: "var(--ok)" }}>올리신 사진으로 충분해요</div></div></div>
              <div style={{ display: "flex", gap: 10 }}>
                {slotOk ? <Mark kind="ok" /> : <Mark kind="empty" />}
                <div style={{ flex: 1 }}><div>주변 건물이나 도로명이 보이는 사진</div><div className="small" style={{ color: slotOk ? "var(--ok)" : "var(--sub)" }}>{slotOk ? "새로 찍은 사진으로 충분해요" : "아직 없어요"}</div></div>
              </div>
              {s.p === 3 && <button className="btn btn-primary" onClick={() => st.step(4)}>촬영하기</button>}
            </div>
          </>
        )}

        {A && s.trash && s.p >= 4 && <Photo className="photo-chat" label="표지판이 잘린 주변 사진" />}
        {A && chk && s.busy && <Thinking>사진을 확인하고 있어요</Thinking>}

        {/* S5 불충분 */}
        {A && s.trash && s.p >= 4 && !(s.p === 4 && s.busy) && (
          <div className="panel" style={{ gap: 10 }}>
            <div className="row"><Mark kind="warn" /><span className="strong" style={{ color: "var(--warn-ink)" }}>불충분</span><span className="small sub">위치가 보이는 사진</span></div>
            <div style={{ textWrap: "pretty" }}>도로명 표지판이 잘려서 위치를 알기 어려워요. 두세 걸음 뒤로 물러나서 건물 간판이 함께 나오게 다시 찍어 주세요.</div>
            {s.p === 4 && !s.busy && <button className="btn btn-primary" onClick={() => st.step(5)}>다시 촬영하기</button>}
            {/* AI 고지는 아래 "충분" 카드가 나오면 그쪽에만 둔다 */}
            {s.p === 4 && <Fine />}
          </div>
        )}

        {A && s.trash && s.p >= 5 && <Photo className="photo-chat" label="건물 간판과 도로명이 보이는 사진" />}

        {/* S5 충분 */}
        {A && s.trash && s.p >= 5 && !(s.p === 5 && s.busy) && (
          <div className="panel" style={{ gap: 10 }}>
            <div className="row"><Mark kind="ok" /><span className="strong" style={{ color: "var(--ok)" }}>충분</span><span className="small sub">위치가 보이는 사진</span></div>
            <div>위치가 잘 보여요. 이 사진으로 충분합니다.</div>
            {s.p === 5 && !s.busy && <button className="btn btn-primary" onClick={() => set({ p: 6, s7: 0 })}>접수 방법 안내받기</button>}
            <Fine />
          </div>
        )}

        {/* S7 접수 안내 */}
        {A && s.p === 6 && (
          <>
            <Bot>사진 2장이 모두 준비됐어요. 한 단계씩 같이 접수해 볼게요.</Bot>
            <div className="panel" style={{ gap: 14 }}>
              {/* 상단 단계 표시와 겹치지 않게 진행은 한 줄로만 */}
              <div className="row small"><span className="sub" style={{ flex: 1 }}>쓰레기 무단투기 접수</span><span className="step-count"><strong>{s.s7 + 1}</strong> / {SUBMIT_STEPS.length}</span></div>
              <div key={s.s7} className="step-swap col" style={{ gap: 14 }}>
              <div className="stepline">{cur.pre}<strong>{cur.b}</strong>{cur.post}</div>
              {cur.sub && <div className="small sub" style={{ marginTop: -8 }}>{cur.sub}</div>}
              {s.s7 === 3 && <div className="row"><Photo className="photo-grow" label="쓰레기 전체" /><Photo className="photo-grow" label="간판·도로명" /></div>}
              {s.s7 === 5 && (
                <div className="col">
                  <div className="draft">{DRAFTS[s.draft]}</div>
                  <div className="row small sub">다시 써 줘
                    <button className={`chip ${s.draft === 1 ? "on" : ""}`} onClick={() => set({ draft: s.draft === 1 ? 0 : 1 })}>더 짧게</button>
                    <button className={`chip ${s.draft === 2 ? "on" : ""}`} onClick={() => set({ draft: s.draft === 2 ? 0 : 2 })}>더 정중하게</button>
                  </div>
                </div>
              )}
              {s.s7 === 6 && <input className="input" value={s.receipt} placeholder="접수번호 (선택)" onChange={(e) => set({ receipt: e.target.value })} />}
              </div>
              <div className="row">
                {s.s7 > 0 && <button className="btn btn-secondary" onClick={() => set({ s7: s.s7 - 1 })}>이전</button>}
                <button className="btn btn-primary btn-grow" onClick={st.s7Next}>{cur.btn}</button>
              </div>
            </div>
          </>
        )}

        {/* S8 다음 항목 */}
        {A && s.trash && s.p >= 7 && (
          <div className="panel">
            <div className="row"><Mark kind="ok" /><span className="strong">쓰레기 무단투기 접수 완료</span></div>
            {s.p === 7 && (
              <>
                <div className="divider" />
                <div className="small sub">다음</div>
                <div style={{ fontSize: 18, fontWeight: 700, marginTop: -8 }}>불법주정차 (인도)</div>
                <div className="col">
                  <div className="kv"><span className="k">안전신문고 로그인</span><span>이미 하셨어요, 건너뜁니다</span></div>
                  <div className="kv"><span className="k">위치 확인</span><span>같은 장소라 그대로 씁니다</span></div>
                  <div className="kv"><span className="k">사진</span><span className="strong">안전신문고 앱에서 새로 찍어야 해요</span></div>
                </div>
                <div className="row">
                  <button className="btn btn-secondary" onClick={st.later}>나중에</button>
                  <button className="btn btn-primary btn-grow" onClick={() => set({ p: 8 })}>이어서 하기</button>
                </div>
              </>
            )}
          </div>
        )}

        {/* S6 사전 점검 + 본촬영 가이드 */}
        {A && s.park && s.p >= 8 && (
          <>
            <Bot>불법주정차는 안전신문고 앱 안에서 찍은 사진만 인정돼요. 올리신 사진으로 미리 점검해 봤어요.</Bot>
            <div className="panel">
              <div className="strong">불법주정차 사전 점검</div>
              <div className="row" style={{ gap: 10 }}><Mark kind="ok" /><div>금지구역: 인도 위 주차</div></div>
              <div className="row" style={{ gap: 10 }}><Mark kind="ok" /><div>번호판이 식별돼요</div></div>
              <div style={{ display: "flex", gap: 10 }}><Mark kind="warn" /><div><div className="strong" style={{ color: "var(--warn-ink)" }}>주변 배경이 부족해요</div><div style={{ fontSize: 14, textWrap: "pretty" }}>차량만 크게 찍혔어요. 인도 경계석과 옆 건물이 함께 보이게 찍어야 합니다.</div></div></div>
              <Fine />
            </div>
            <div className="panel">
              <div className="strong">안전신문고 앱에서 이렇게 찍으세요</div>
              <div style={{ display: "flex", gap: 10 }}><Mark kind="num">1</Mark><div>차량 뒤쪽에서 번호판과 인도 경계석이 함께 나오게 1장</div></div>
              <div style={{ display: "flex", gap: 10 }}><Mark kind="num">2</Mark><div>그 자리에서 움직이지 말고 1분 기다리기</div></div>
              <div style={{ display: "flex", gap: 10 }}><Mark kind="num">3</Mark><div>같은 위치, 같은 방향으로 1장 더</div></div>
              <div className="warnbox"><strong>주의:</strong> 앞에서 1장, 옆에서 1장은 반려돼요.</div>
              {s.p === 8 && <button className="btn btn-primary" onClick={st.startTimer}>1분 타이머 시작</button>}
            </div>
          </>
        )}

        {A && s.p === 9 && (
          <>
            <Bot>1분 간격으로 2장을 찍으셨어요. 안전신문고 앱에서 그대로 제출해 주세요.</Bot>
            <button className="btn btn-primary" style={{ flex: "none" }} onClick={st.finish}>제출했어요</button>
          </>
        )}
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
