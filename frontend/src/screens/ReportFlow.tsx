// 신고 건 진행 (/chat, p === 3): S4 증거 안내, S5 사진 검수, S6 불법주정차 사전 점검, S7 접수 안내, S8 다음 항목
import { useRef } from "react";
import { REHEARSAL_SHOT, useStore } from "../app/store";
import { DRAFTS, SUBMIT_STEPS } from "../data/content";
import { LIMITS } from "../api/analyses";
import type { ReviewStatus } from "../api/reports";
import { Bot, Fine, Mark, Photo, Thinking } from "../components/ui";

const MARK: Record<ReviewStatus, "ok" | "warn"> = { sufficient: "ok", insufficient: "warn", undetermined: "warn" };
const TONE: Record<ReviewStatus, string> = { sufficient: "var(--ok)", insufficient: "var(--warn-ink)", undetermined: "var(--warn-ink)" };
const STATUS: Record<ReviewStatus, string> = { sufficient: "충분", insufficient: "불충분", undetermined: "판단 어려움" };

const interval = (sec: number) => (sec % 60 === 0 ? `${sec / 60}분` : `${sec}초`);

/** 사진 1장을 고르게 하는 숨은 입력. 모바일에서는 촬영과 앨범 중 고를 수 있다. */
function usePicker(onPick: (f: File) => void, toast: (m: string) => void) {
  const ref = useRef<HTMLInputElement>(null);
  const input = (
    <input ref={ref} type="file" accept={LIMITS.photoTypes.join(",")} hidden onChange={(e) => {
      const f = e.target.files?.[0];
      e.target.value = "";
      if (!f) return;
      if (!(LIMITS.photoTypes as readonly string[]).includes(f.type) || f.size > LIMITS.photoBytes) {
        toast("JPEG, PNG, WebP 사진만 10MB 이하로 올릴 수 있어요");
        return;
      }
      onPick(f);
    }} />
  );
  return { input, open: () => ref.current?.click() };
}

export function ReportFlow() {
  const st = useStore();
  const { s, current } = st;
  const target = useRef("");
  const scene = usePicker((f) => st.shoot(target.current, f), st.toast);
  const rhPick = usePicker((f) => st.rehearsalPhoto(f), st.toast);
  const next = s.reports[s.cur + 1];
  const nextLabel = next ? s.analysis?.items.find((i) => i.type_id === next.type_id)?.label ?? "" : "";

  return (
    <>
      {scene.input}
      {rhPick.input}

      {/* 앞서 끝낸 건 */}
      {s.finished.map((f) => (
        <div key={f.id} className="panel">
          <div className="row"><Mark kind="ok" /><span className="strong">{f.label} 접수 완료</span></div>
        </div>
      ))}

      {current && s.rstage === "evidence" && <Evidence pick={(id) => { target.current = id; scene.open(); }} />}
      {current && s.rstage === "rehearsal" && <ParkingCheck pick={rhPick.open} />}

      {current && s.rstage === "submit" && (
        <>
          <Bot>{interval(s.timerTotal)} 간격으로 2장을 찍으셨어요. 안전신문고 앱에서 그대로 제출해 주세요.</Bot>
          <button className="btn btn-primary" style={{ flex: "none" }} onClick={st.completeReport}>제출했어요</button>
        </>
      )}

      {current && s.rstage === "guide" && <Guide />}

      {/* S8 다음 항목 */}
      {s.rstage === "next" && next && (
        <div className="panel">
          <div className="small sub">다음</div>
          <div style={{ fontSize: 18, fontWeight: 700, marginTop: -8 }}>{nextLabel}</div>
          <div className="row">
            <button className="btn btn-secondary" onClick={st.later}>나중에</button>
            <button className="btn btn-primary btn-grow" onClick={st.nextReport}>이어서 하기</button>
          </div>
        </div>
      )}
    </>
  );
}

/** S4 증거 체크리스트 + S5 장면별 검수 */
function Evidence({ pick }: { pick: (sceneId: string) => void }) {
  const st = useStore();
  const { s } = st;
  const ev = s.evidence;

  if (s.evError) {
    return (
      <div className="panel" role="alert">
        <div className="row"><Mark kind="warn" /><span className="strong" style={{ color: "var(--warn-ink)" }}>불러오지 못했어요</span></div>
        <div>{s.evError}</div>
        <button className="btn btn-primary" onClick={st.reloadEvidence}>다시 시도</button>
      </div>
    );
  }
  if (!ev) return <Thinking>필요한 사진을 확인하고 있어요</Thinking>;

  return (
    <>
      <Bot>{ev.intro}</Bot>
      <div className="panel">
        <div className="strong">{ev.label} · 필요한 사진 {ev.required_count}장</div>
        {ev.scenes.map((sc) => {
          const shot = s.shots[sc.scene_id];
          const busy = s.uploading === sc.scene_id;
          const review = busy ? null : sc.review;
          const ok = review?.status === "sufficient";
          return (
            <div key={sc.scene_id} style={{ display: "flex", gap: 10 }}>
              {review ? <Mark kind={MARK[review.status]} /> : <Mark kind="empty" />}
              <div style={{ flex: 1, minWidth: 0 }} className="col">
                <div>{sc.label}{!sc.required && <span className="small sub"> (선택)</span>}</div>
                {shot && <img src={shot.preview} alt={`${sc.label} 사진`} className="photo photo-chat" style={{ objectFit: "cover", padding: 0 }} />}
                {busy && <div className="small sub" aria-live="polite">사진을 확인하고 있어요</div>}
                {review && (
                  <div className="small" style={{ color: TONE[review.status], textWrap: "pretty" }}>
                    {!ok && <strong>{STATUS[review.status]} · </strong>}{review.message}
                  </div>
                )}
                {review && !ok && review.retake_tip && <div className="note">{review.retake_tip}</div>}
                {!review && !busy && <div className="small sub">아직 없어요</div>}
                {!ok && !busy && (
                  <button className="btn btn-secondary btn-sm" style={{ alignSelf: "flex-start" }} disabled={!!s.uploading} onClick={() => pick(sc.scene_id)}>
                    {sc.photo || shot ? "다시 촬영하기" : "촬영하기"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
        {ev.complete && !s.uploading && <button className="btn btn-primary" onClick={st.toGuide}>접수 방법 안내받기</button>}
        <Fine />
      </div>
    </>
  );
}

/** S6 불법주정차 사전 점검과 본촬영 안내 */
function ParkingCheck({ pick }: { pick: () => void }) {
  const st = useStore();
  const { s } = st;
  const rh = s.rehearsal;
  const shot = s.shots[REHEARSAL_SHOT];
  const zoneBad = rh?.checks.find((c) => c.key === "zone")?.status === "insufficient";
  const hasNext = s.cur + 1 < s.reports.length;
  // 글만 보내서 아직 점검할 사진이 없다(오류가 아니라 요청 단계)
  const askFirst = s.rhNeedsPhoto && !s.rhError && !rh;

  return (
    <>
      <Bot>
        {askFirst
          ? "불법주정차는 안전신문고 앱 안에서 찍은 사진만 인정돼요. 차량 사진을 1장 올려 주시면 접수 전에 요건을 미리 점검해 드릴게요."
          : "불법주정차는 안전신문고 앱 안에서 찍은 사진만 인정돼요. 올리신 사진으로 미리 점검해 볼게요."}
      </Bot>
      {askFirst && !s.rhBusy && (
        <div className="panel">
          <div className="strong">점검할 사진</div>
          <div className="small sub" style={{ textWrap: "pretty" }}>번호판과 주변(인도 경계석, 건물 등)이 함께 보이면 좋아요.</div>
          <div className="row">
            <button className="btn btn-secondary" onClick={st.skipReport}>{hasNext ? "다음 항목으로" : "처음으로"}</button>
            <button className="btn btn-primary btn-grow" onClick={pick}>사진 올리기</button>
          </div>
        </div>
      )}
      {shot && <div className="me"><img src={shot.preview} alt="점검할 사진" className="photo photo-chat" style={{ objectFit: "cover", padding: 0 }} /></div>}
      {s.rhBusy && <Thinking>사진을 점검하고 있어요</Thinking>}

      {!s.rhBusy && s.rhError && (
        <div className="panel" role="alert">
          <div className="row"><Mark kind="warn" /><span className="strong" style={{ color: "var(--warn-ink)" }}>점검하지 못했어요</span></div>
          <div>{s.rhError}</div>
          <div className="row">
            {s.rhNeedsPhoto && <button className="btn btn-secondary" onClick={st.skipReport}>{hasNext ? "다음 항목으로" : "처음으로"}</button>}
            {s.rhNeedsPhoto
              ? <button className="btn btn-primary btn-grow" onClick={pick}>점검할 사진 올리기</button>
              : <button className="btn btn-primary btn-grow" onClick={st.runRehearsal}>다시 시도</button>}
          </div>
        </div>
      )}

      {!s.rhBusy && rh && (
        <>
          <div className="panel">
            <div className="strong">불법주정차 사전 점검</div>
            {rh.checks.map((c) => (
              <div key={c.key} style={{ display: "flex", gap: 10 }}>
                <Mark kind={MARK[c.status]} />
                <div>
                  <div className={c.status === "sufficient" ? "" : "strong"} style={{ color: c.status === "sufficient" ? undefined : "var(--warn-ink)" }}>{c.label}</div>
                  {c.detail && <div style={{ fontSize: 14, textWrap: "pretty" }}>{c.detail}</div>}
                </div>
              </div>
            ))}
            <Fine />
          </div>

          {zoneBad ? (
            <div className="panel">
              <div style={{ textWrap: "pretty" }}>주정차 금지구역이 아니면 주민신고로 과태료가 부과되지 않아요.</div>
              <div className="row">
                <button className="btn btn-secondary" onClick={pick}>다른 사진으로 점검</button>
                <button className="btn btn-primary btn-grow" onClick={st.skipReport}>{hasNext ? "다음 항목으로" : "처음으로"}</button>
              </div>
            </div>
          ) : (
            <div className="panel">
              <div className="strong">{rh.capture_guide.title}</div>
              {rh.capture_guide.steps.map((t, i) => (
                <div key={t} style={{ display: "flex", gap: 10 }}><Mark kind="num">{i + 1}</Mark><div>{t}</div></div>
              ))}
              <div className="warnbox"><strong>주의:</strong> {rh.capture_guide.warning}</div>
              {rh.capture_guide.interval_note && <div className="small sub">{rh.capture_guide.interval_note}</div>}
              <button className="btn btn-primary" onClick={st.startTimer}>{interval(rh.capture_guide.interval_seconds)} 타이머 시작</button>
              <button className="link" style={{ alignSelf: "center", color: "var(--sub)" }} onClick={pick}>다른 사진으로 다시 점검</button>
            </div>
          )}
        </>
      )}
    </>
  );
}

/** S7 접수 안내. 아직 대본(SUBMIT_STEPS)이다. feat/fe-guide에서 GET /api/reports/{id}/guide로 바꾼다. */
function Guide() {
  const st = useStore();
  const { s, current } = st;
  const step = SUBMIT_STEPS[s.s7];
  const photos = (s.evidence?.scenes ?? []).filter((sc) => sc.photo);
  return (
    <>
      <Bot>사진이 모두 준비됐어요. 한 단계씩 같이 접수해 볼게요.</Bot>
      <div className="panel" style={{ gap: 14 }}>
        <div className="row small"><span className="sub" style={{ flex: 1 }}>{current?.label} 접수</span><span className="step-count"><strong>{s.s7 + 1}</strong> / {SUBMIT_STEPS.length}</span></div>
        <div key={s.s7} className="step-swap col" style={{ gap: 14 }}>
          <div className="stepline">{step.pre}<strong>{step.b}</strong>{step.post}</div>
          {step.sub && <div className="small sub" style={{ marginTop: -8 }}>{step.sub}</div>}
          {s.s7 === 3 && (
            <div className="row">
              {photos.length
                ? photos.map((sc) => <img key={sc.scene_id} src={sc.photo!.url} alt={sc.label} className="photo photo-grow" style={{ objectFit: "cover", padding: 0 }} />)
                : <Photo className="photo-grow" label="준비한 사진" />}
            </div>
          )}
          {s.s7 === 5 && (
            <div className="col">
              <div className="draft">{DRAFTS[s.draft]}</div>
              <div className="row small sub">다시 써 줘
                <button className={`chip ${s.draft === 1 ? "on" : ""}`} onClick={() => st.set({ draft: s.draft === 1 ? 0 : 1 })}>더 짧게</button>
                <button className={`chip ${s.draft === 2 ? "on" : ""}`} onClick={() => st.set({ draft: s.draft === 2 ? 0 : 2 })}>더 정중하게</button>
              </div>
            </div>
          )}
          {s.s7 === 6 && <input className="input" value={s.receipt} placeholder="접수번호 (선택)" onChange={(e) => st.set({ receipt: e.target.value })} />}
        </div>
        <div className="row">
          {s.s7 > 0 && <button className="btn btn-secondary" onClick={() => st.set({ s7: s.s7 - 1 })}>이전</button>}
          <button className="btn btn-primary btn-grow" onClick={st.s7Next}>{step.btn}</button>
        </div>
      </div>
    </>
  );
}
