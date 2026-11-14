// S10 신고 조회 (/mine), S11 상세 (/mine/:id). GET /api/reports, GET·PATCH /api/reports/{id}
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useStore } from "../app/store";
import { MINE_FILTERS } from "../data/content";
import { Chips, Photo, Thinking } from "../components/ui";
import { AppBar } from "../components/AppBar";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { EmptyListArt } from "../components/motifs/Illustrations";
import { ChevronRight, Share } from "../components/icons/Icons";
import { getReport, listReports, patchReport, type Report, type ReportListItem, type ReportStatus, type ResultValue } from "../api/reports";
import { errorMessage } from "../api/client";
import { unshareCase } from "../api/cases";

const FILTER_STATUS: Record<string, ReportStatus | undefined> = { "전체": undefined, "준비 중": "preparing", "접수 완료": "filed", "처리 완료": "resolved" };
const PILL: Record<ReportStatus, string> = { resolved: "pill-ok", preparing: "pill-warn", filed: "pill-mute" };
const RESULTS: [ResultValue, string][] = [["accepted", "수용"], ["rejected", "불수용"], ["unknown", "아직 모름"]];

/** "2026-11-14T14:02:00+09:00" → "11월 14일" */
const monthDay = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : `${d.getMonth() + 1}월 ${d.getDate()}일`;
};
const place = (district: string | null, dong: string | null, iso: string) =>
  [[district, dong].filter(Boolean).join(" "), monthDay(iso)].filter(Boolean).join(" · ");

export function Mine() {
  const { s, set, resume } = useStore();
  const nav = useNavigate();
  const [tick, setTick] = useState(0);
  // 응답을 요청 키(필터, 재시도 횟수)와 함께 둔다. 키가 다르면 아직 불러오는 중이다.
  const key = `${s.filter}|${tick}`;
  const [data, setData] = useState<{ key: string; items?: ReportListItem[]; any?: boolean; error?: string }>({ key: "" });

  useEffect(() => {
    let live = true;
    const status = FILTER_STATUS[s.filter];
    listReports(status)
      .then(async (r) => {
        // 필터 결과가 비었을 때 "아직 신고한 내역이 없어요"인지 "이 상태의 신고가 없어요"인지 가린다.
        const any = r.items.length > 0 || (!!status && (await listReports(undefined, 1)).items.length > 0);
        if (live) setData({ key, items: r.items, any });
      })
      .catch((e) => live && setData({ key, error: errorMessage(e) }));
    return () => { live = false; };
  }, [s.filter, key]);
  const ready = data.key === key;
  const items = ready ? data.items ?? null : null;
  const error = ready ? data.error ?? "" : "";
  const any = data.any ?? false;

  return (
    <div className="page">
      <WaveBackdrop variant="both" />
      <AppBar title="신고 조회" onBack={() => nav("/")} />
      <div className="screen" style={{ gap: 14 }}>
        <h1 className="h1-sm">내가 한 신고</h1>
        <Chips items={MINE_FILTERS} value={s.filter} onChange={(f) => set({ filter: f })} />

        {error ? (
          <div className="panel" role="alert">
            <div>{error}</div>
            <button className="btn btn-primary" onClick={() => setTick(tick + 1)}>다시 시도</button>
          </div>
        ) : !items ? (
          <Thinking>불러오고 있어요</Thinking>
        ) : items.length === 0 ? (
          <div className="empty">
            <EmptyListArt />
            <div>{any ? "이 상태의 신고가 없어요" : "아직 신고한 내역이 없어요"}</div>
            <button className="btn btn-primary" onClick={() => nav("/report")}>신고하러 가기</button>
          </div>
        ) : (
          <div className="col" style={{ gap: 10 }}>
            {items.map((m) => (
              <div key={m.id} className="col" style={{ gap: 4 }}>
                <button className="item" onClick={() => nav(`/mine/${m.id}`)}>
                  {m.thumbnail_url
                    ? <img src={m.thumbnail_url} alt="" className="photo photo-md" style={{ objectFit: "cover", padding: 0 }} />
                    : <Photo className="photo-md" label="사진 없음" />}
                  <div className="body">
                    <div className="strong">{m.label}</div>
                    <div className="small sub">{place(m.district, m.dong, m.created_at)}</div>
                    <div className="row" style={{ marginTop: 3, flexWrap: "wrap", gap: 6 }}>
                      <span className={`pill ${PILL[m.status]}`}>{m.status_label}</span>
                    </div>
                  </div>
                  <span className="sub"><ChevronRight size={18} /></span>
                </button>
                {m.resumable && <button className="link" style={{ alignSelf: "flex-end", color: "var(--navy)", fontWeight: 600 }} onClick={() => resume(m.id)}>이어서 하기</button>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function MineDetail() {
  const { openShare, resume, toast } = useStore();
  const [unsharing, setUnsharing] = useState(false);
  const nav = useNavigate();
  const { id = "" } = useParams();
  const [data, setData] = useState<{ id: string; report?: Report; error?: string }>({ id: "" });
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let live = true;
    getReport(id)
      .then((r) => { if (live) { setData({ id, report: r }); setReason(r.result_reason ?? ""); } })
      .catch((e) => live && setData({ id, error: errorMessage(e) }));
    return () => { live = false; };
  }, [id]);
  const d = data.id === id ? data.report ?? null : null;
  const error = data.id === id ? data.error ?? "" : "";
  const setD = (r: Report) => setData({ id, report: r });

  const save = async (result: ResultValue, why?: string) => {
    if (!d || saving) return;
    setSaving(true);
    try {
      const r = await patchReport(d.id, { result, result_reason: result === "rejected" ? (why ?? reason).trim() || null : null });
      setD(r);
      toast("처리 결과를 저장했어요");
    } catch (e) {
      toast(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const back = <AppBar title="신고 조회" onBack={() => nav("/mine")} />;
  if (error) {
    return (
      <div className="page">{back}
        <div className="screen"><div className="panel" role="alert"><div>{error}</div><button className="btn btn-primary" onClick={() => nav("/mine")}>목록으로</button></div></div>
      </div>
    );
  }
  if (!d) return <div className="page">{back}<div className="screen"><Thinking>불러오고 있어요</Thinking></div></div>;

  const to = [d.channel.name, ...d.channel.menu_path].join(" > ");
  const receipt = d.receipt_number ?? (d.status === "preparing" ? "접수 전" : "입력 안 함");
  const lastDone = d.timeline.reduce((acc, t, i) => (t.done ? i : acc), -1);

  return (
    <div className="page">
      <WaveBackdrop variant="corner" />
      {back}
      <div className="screen" style={{ gap: 18 }}>
        <div><h1 className="h1-sm">{d.label}</h1><div className="small sub">{place(d.location.district, d.location.dong, d.created_at)}</div></div>

        <div className="panel" style={{ gap: 0 }}>
          {d.timeline.map((t, i) => (
            <div key={t.key} className="tl">
              <div className="rail"><span className={`dot ${t.done ? "on" : ""}`} /><span className={`rule ${i < lastDone ? "" : "off"}`} /></div>
              <div className="txt"><div style={{ fontWeight: 600 }}>{t.label}</div><div className="small sub">{t.note}</div></div>
            </div>
          ))}
        </div>

        {d.status === "preparing" && <button className="btn btn-primary" onClick={() => resume(d.id)}>이어서 하기</button>}

        {d.photos.length > 0 && (
          <div className="col"><div className="section-title">첨부한 사진</div>
            <div className="row" style={{ flexWrap: "wrap" }}>
              {d.photos.map((p, i) => <img key={p.id} src={p.url} alt={`첨부 사진 ${i + 1}`} className="photo photo-grow" style={{ objectFit: "cover", padding: 0, minWidth: 96 }} />)}
            </div>
          </div>
        )}
        {d.draft_text && <div className="col"><div className="section-title">제출한 신고 문구</div><div className="draft">{d.draft_text}</div></div>}
        <div className="table">
          <div><span className="k sub">접수처</span><span>{to}</span></div>
          <div><span className="k sub">접수번호</span><span>{receipt}</span></div>
        </div>

        {d.status !== "preparing" && (
          <>
            <div className="col"><div className="section-title">처리 결과</div>
              <div className="small sub">안전신문고와 연동되지 않아요. 결과를 받으면 직접 골라 주세요.</div>
              <div className="row" style={{ gap: 6 }}>
                {RESULTS.map(([v, label]) => {
                  const on = (d.result ?? "unknown") === v;
                  return <button key={v} className={`btn btn-sm btn-grow ${on ? "btn-primary" : "btn-secondary"}`} aria-pressed={on} disabled={saving} onClick={() => save(v)}>{label}</button>;
                })}
              </div>
              {d.result === "rejected" && (
                <>
                  <textarea className="textarea" rows={2} maxLength={300} value={reason} placeholder="불수용 사유를 적어 두면 다음에 도움이 돼요" onChange={(e) => setReason(e.target.value)} />
                  {reason.trim() !== (d.result_reason ?? "") && <button className="btn btn-secondary btn-sm" style={{ alignSelf: "flex-end" }} disabled={saving} onClick={() => save("rejected", reason)}>사유 저장</button>}
                </>
              )}
            </div>
            {d.case_id ? (
              <div className="row">
                <button className="btn btn-secondary" disabled={unsharing} onClick={async () => {
                  setUnsharing(true);
                  try { await unshareCase(d.id); setD({ ...d, case_id: null }); toast("공유를 내렸어요"); }
                  catch (e) { toast(errorMessage(e)); }
                  finally { setUnsharing(false); }
                }}>공유 내리기</button>
                <button className="btn btn-outline btn-grow" onClick={() => nav(`/cases/${d.case_id}`)}>공유한 사례 보기</button>
              </div>
            ) : (
              <button className="btn btn-outline" onClick={() => openShare(d.id, `/mine/${d.id}`)}><Share size={16} />사례로 공유하기</button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
