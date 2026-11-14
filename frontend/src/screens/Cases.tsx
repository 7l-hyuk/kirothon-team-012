// S12 신고 사례 (/cases), S13 사례 상세 (/cases/:id). GET /api/cases, GET /api/cases/{id}, PUT·DELETE like
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useStore } from "../app/store";
import { CASE_FILTERS } from "../data/content";
import { Chips, Photo, Thinking } from "../components/ui";
import { AppBar } from "../components/AppBar";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { EmptyListArt } from "../components/motifs/Illustrations";
import { Heart } from "../components/icons/Icons";
import { getCase, listCases, setLike, type CaseDetail, type CaseListItem } from "../api/cases";
import type { TypeId } from "../api/analyses";
import { errorMessage } from "../api/client";

const FILTER_TYPE: Record<string, TypeId | undefined> = {
  "전체": undefined, "불법주정차": "illegal_parking", "쓰레기": "trash_dumping", "광고물": "illegal_ad", "시설물": "facility_damage",
};
const resultPill = (label: string) => (/^수용|재신고 수용/.test(label) ? "pill-ok" : label === "불수용" ? "pill-warn" : "pill-mute");

export function Cases() {
  const { s, set } = useStore();
  const nav = useNavigate();
  const [tick, setTick] = useState(0);
  const key = `${s.cfilter}|${tick}`;
  const [data, setData] = useState<{ key: string; items?: CaseListItem[]; error?: string }>({ key: "" });

  useEffect(() => {
    let live = true;
    listCases(FILTER_TYPE[s.cfilter])
      .then((r) => live && setData({ key, items: r.items }))
      .catch((e) => live && setData({ key, error: errorMessage(e) }));
    return () => { live = false; };
  }, [s.cfilter, key]);
  const ready = data.key === key;

  return (
    <div className="page">
      <WaveBackdrop variant="corner" />
      <AppBar title="신고 사례" onBack={() => nav("/")} />
      <div className="screen" style={{ gap: 14 }}>
        <h1 className="h1-sm">다른 사람은 이렇게 신고했어요</h1>
        <Chips items={CASE_FILTERS} value={s.cfilter} onChange={(f) => set({ cfilter: f })} />

        <div className="col" style={{ gap: 12 }}>
          {!ready && <Thinking>불러오고 있어요</Thinking>}
          {ready && data.error && (
            <div className="panel" role="alert"><div>{data.error}</div><button className="btn btn-primary" onClick={() => setTick(tick + 1)}>다시 시도</button></div>
          )}
          {ready && data.items?.length === 0 && <div className="empty" style={{ padding: "24px 0" }}><EmptyListArt /><div>이 유형의 사례가 아직 없어요</div></div>}
          {ready && data.items?.map((a) => (
            <button key={a.id} className="card col" style={{ textAlign: "left", padding: 12, gap: 10 }} onClick={() => nav(`/cases/${a.id}`)}>
              {a.cover_url
                ? <img src={a.cover_url} alt="" className="photo photo-wide" style={{ objectFit: "cover", padding: 0, width: "100%" }} />
                : <Photo className="photo-wide" label={a.type_label} />}
              <div style={{ fontSize: 16, fontWeight: 700, lineHeight: 1.4, textWrap: "pretty", padding: "0 2px" }}>{a.title}</div>
              <div className="row xs sub" style={{ flexWrap: "wrap", gap: 6, padding: "0 2px" }}>
                <span className="pill pill-type">{a.type_label}</span>
                <span className={`pill ${resultPill(a.result_label)}`}>{a.result_label}</span>
                {a.district && <><span>{a.district}</span><span>·</span></>}
                <span className="row" style={{ gap: 3 }}><Heart size={13} />도움돼요 {a.like_count}</span>
              </div>
            </button>
          ))}
        </div>

        <button className="btn btn-outline btn-block btn-roomy" style={{ marginTop: 10, marginBottom: 12 }} onClick={() => nav("/report")}>신고하러 가기</button>
      </div>
    </div>
  );
}

export function Article() {
  const { startFromCase, toast } = useStore();
  const nav = useNavigate();
  const { id = "" } = useParams();
  const [data, setData] = useState<{ id: string; c?: CaseDetail; error?: string }>({ id: "" });
  const [liking, setLiking] = useState(false);

  useEffect(() => {
    let live = true;
    getCase(id)
      .then((c) => live && setData({ id, c }))
      .catch((e) => live && setData({ id, error: errorMessage(e) }));
    return () => { live = false; };
  }, [id]);
  const a = data.id === id ? data.c : undefined;
  const error = data.id === id ? data.error : undefined;

  const like = async () => {
    if (!a || liking) return;
    setLiking(true);
    try {
      const r = await setLike(a.id, !a.liked_by_me);
      setData({ id, c: { ...a, ...r } });
    } catch (e) {
      toast(errorMessage(e));
    } finally {
      setLiking(false);
    }
  };

  const bar = <AppBar title="신고 사례" onBack={() => nav("/cases")} />;
  if (error) return <div className="page">{bar}<div className="screen"><div className="panel" role="alert"><div>{error}</div><button className="btn btn-primary" onClick={() => nav("/cases")}>목록으로</button></div></div></div>;
  if (!a) return <div className="page">{bar}<div className="screen"><Thinking>불러오고 있어요</Thinking></div></div>;

  return (
    <div className="page">
      <WaveBackdrop variant="corner" />
      {bar}
      <div className="screen" style={{ gap: 18 }}>
        <h1 style={{ fontSize: 22, lineHeight: 1.4, textWrap: "pretty" }}>{a.title}</h1>
        <div className="row xs sub" style={{ flexWrap: "wrap", gap: 6, marginTop: -8 }}>
          <span className="pill pill-type">{a.type_label}</span><span className={`pill ${resultPill(a.result_label)}`}>{a.result_label}</span>
          {a.district && <><span>{a.district}</span><span>·</span></>}<span>{a.period}</span>
          {a.is_mine && <><span>·</span><span className="strong" style={{ color: "var(--navy)" }}>내가 공유한 사례</span></>}
        </div>
        {a.sections.map((sec, i) => (
          <div key={sec.heading} className="col" style={{ gap: 6 }}>
            <div className="row section-title" style={{ gap: 8 }}><span className="mark mark-num" style={{ width: 22, height: 22, fontSize: 12 }}>{i + 1}</span>{sec.heading}</div>
            {sec.photos.map((ph, j) => <img key={ph.id} src={ph.url} alt={`${sec.heading} 사진 ${j + 1}`} className="photo photo-wide" style={{ objectFit: "cover", padding: 0, width: "100%" }} />)}
            <div style={{ textWrap: "pretty" }}>{sec.body}</div>
          </div>
        ))}
      </div>
      <div className="bottom-bar">
        <button className={`btn btn-sm ${a.liked_by_me ? "btn-primary" : "btn-secondary"}`} style={{ height: 50, padding: "0 14px" }} aria-pressed={a.liked_by_me} disabled={liking} onClick={like}>
          <Heart size={16} />도움돼요 {a.like_count}
        </button>
        <button className="btn btn-primary btn-grow" onClick={() => startFromCase(a.type_id, a.type_label)}>나도 비슷한 상황이에요</button>
      </div>
    </div>
  );
}
