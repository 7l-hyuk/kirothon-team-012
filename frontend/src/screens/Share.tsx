// S14 공유 동의 (/share/:id). GET /api/reports/{id}/case-preview → POST /api/reports/{id}/case
import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useStore } from "../app/store";
import { AppBar } from "../components/AppBar";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { Check } from "../components/icons/Icons";
import { Thinking } from "../components/ui";
import { getCasePreview, shareCase, type CasePreview } from "../api/cases";
import { errorMessage } from "../api/client";

export function Share() {
  const { s, toast } = useStore();
  const nav = useNavigate();
  const { id = "" } = useParams();
  const back = (useLocation().state as { back?: string } | null)?.back ?? "/mine";
  const [tick, setTick] = useState(0);
  const key = `${id}|${tick}`;
  const [data, setData] = useState<{ key: string; p?: CasePreview; error?: string }>({ key: "" });
  const [agree, setAgree] = useState(false);
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    let live = true;
    getCasePreview(id)
      .then((p) => live && setData({ key, p }))
      .catch((e) => live && setData({ key, error: errorMessage(e) }));
    return () => { live = false; };
  }, [id, key]);
  const ready = data.key === key;
  const p = ready ? data.p : undefined;

  const cancel = () => nav(back);
  const share = async () => {
    if (!agree || sharing) return;
    setSharing(true);
    try {
      const c = await shareCase(id);
      toast("사례로 공유했어요");
      nav(`/cases/${c.id}`, { replace: true });
    } catch (e) {
      toast(errorMessage(e));
      setSharing(false);
    }
  };

  // S9에서 여러 건을 접수했으면 어느 건을 공유할지 고른다.
  const others = s.finished.length > 1 && s.finished.some((f) => f.id === id) ? s.finished : [];

  return (
    <div className="page">
      <WaveBackdrop variant="corner" />
      <AppBar title="사례로 공유하기" onBack={cancel} />
      <div className="screen" style={{ gap: 16 }}>
        <h1 className="h1-sm">공유하기 전에<br />이렇게 지워요</h1>

        {others.length > 0 && (
          <div className="chips">
            {others.map((f) => (
              <button key={f.id} className={`chip ${f.id === id ? "on" : ""}`} aria-pressed={f.id === id}
                onClick={() => { setAgree(false); nav(`/share/${f.id}`, { replace: true, state: { back } }); }}>{f.label}</button>
            ))}
          </div>
        )}

        {!ready && <Thinking>공유할 글을 만들고 있어요</Thinking>}
        {ready && data.error && (
          <div className="panel" role="alert">
            <div>{data.error}</div>
            <div className="row">
              <button className="btn btn-secondary" onClick={cancel}>돌아가기</button>
              <button className="btn btn-primary btn-grow" onClick={() => setTick(tick + 1)}>다시 시도</button>
            </div>
          </div>
        )}

        {p && (
          <>
            <div className="table">
              {p.removed.map((r) => <div key={r.label}><span className="k">{r.label}</span><span className="v">{r.treatment}</span></div>)}
            </div>
            {p.photo_notice && <div className="note">{p.photo_notice}</div>}

            <div className="xs strong" style={{ color: "var(--navy)", marginBottom: -8 }}>공유될 모습</div>
            <div className="card col" style={{ padding: 14, gap: 12 }}>
              <div style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.4, textWrap: "pretty" }}>{p.title}</div>
              <div className="row xs sub" style={{ flexWrap: "wrap", gap: 6, marginTop: -6 }}>
                <span className="pill pill-mute">{p.result_label}</span>
                {p.district && <span>{p.district}</span>}<span>·</span><span>{p.period}</span>
              </div>
              {p.photos.length > 0 && (
                <div className="row" style={{ flexWrap: "wrap" }}>
                  {p.photos.map((ph, i) => <img key={ph.id} src={ph.url} alt={`공개될 사진 ${i + 1}`} className="photo photo-grow" style={{ objectFit: "cover", padding: 0, minWidth: 96 }} />)}
                </div>
              )}
              {p.sections.map((sec) => (
                <div key={sec.heading} className="col" style={{ gap: 2 }}>
                  <div className="small strong">{sec.heading}</div>
                  <div className="small" style={{ textWrap: "pretty" }}>{sec.body}</div>
                </div>
              ))}
            </div>

            <button className="row" style={{ gap: 10, minHeight: 44, textAlign: "left" }} aria-pressed={agree} onClick={() => setAgree(!agree)}>
              <span className={`check ${agree ? "on" : ""}`}>{agree && <Check size={15} stroke={3} />}</span>위 내용으로 공유하는 데 동의합니다
            </button>
            <div className="row">
              <button className="btn btn-secondary" style={{ padding: "0 20px" }} onClick={cancel}>취소</button>
              <button className="btn btn-primary btn-grow" disabled={!agree || sharing} onClick={share}>{sharing ? "공유하고 있어요" : "공유하기"}</button>
            </div>
            <div className="xs sub">공유한 글은 신고 조회 상세에서 언제든 내릴 수 있어요.</div>
          </>
        )}
      </div>
    </div>
  );
}
