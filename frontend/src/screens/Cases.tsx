// S12 신고 사례 (/cases), S13 사례 상세 (/cases/:id)
import { useNavigate, useParams } from "react-router-dom";
import { useStore } from "../app/store";
import { ARTICLES, ARTICLE_HEADS, CASE_FILTERS } from "../data/content";
import { Chips, Photo } from "../components/ui";
import { AppBar } from "../components/AppBar";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { EmptyListArt } from "../components/motifs/Illustrations";
import { Heart } from "../components/icons/Icons";

export function Cases() {
  const { s, set } = useStore();
  const nav = useNavigate();
  const list = ARTICLES.filter((a) => s.cfilter === "전체" || a.cat === s.cfilter);
  return (
    <div className="page">
      <WaveBackdrop variant="corner" />
      <AppBar title="신고 사례" onBack={() => nav("/")} />
      <div className="screen" style={{ gap: 14 }}>
        <h1 className="h1-sm">다른 사람은 이렇게 신고했어요</h1>
        <Chips items={CASE_FILTERS} value={s.cfilter} onChange={(f) => set({ cfilter: f })} />

        <div className="col" style={{ gap: 12 }}>
          {list.length === 0 && <div className="empty" style={{ padding: "24px 0" }}><EmptyListArt /><div>이 유형의 사례가 아직 없어요</div></div>}
          {list.map((a) => (
            <button key={a.id} className="card col" style={{ textAlign: "left", padding: 12, gap: 10 }} onClick={() => { set({ art: a.id }); nav(`/cases/${a.id}`); }}>
              <Photo className="photo-wide" label={a.photo} />
              <div style={{ fontSize: 16, fontWeight: 700, lineHeight: 1.4, textWrap: "pretty", padding: "0 2px" }}>{a.title}</div>
              <div className="row xs sub" style={{ flexWrap: "wrap", gap: 6, padding: "0 2px" }}>
                <span className="pill pill-type">{a.type}</span>
                <span className="pill pill-ok">{a.result}</span>
                <span>{a.gu}</span><span>·</span>
                <span className="row" style={{ gap: 3 }}><Heart size={13} />도움돼요 {a.likes + (s.helped[a.id] ? 1 : 0)}</span>
              </div>
            </button>
          ))}
        </div>

        <button className="btn btn-outline btn-block" style={{ marginTop: 6 }} onClick={() => nav("/report")}>신고하러 가기</button>
      </div>
    </div>
  );
}

export function Article() {
  const { s, set, startFromCase } = useStore();
  const nav = useNavigate();
  const { id } = useParams();
  const a = ARTICLES[Number(id ?? s.art)] ?? ARTICLES[1];
  const helped = !!s.helped[a.id];
  return (
    <div className="page">
      <WaveBackdrop variant="corner" />
      <AppBar title="신고 사례" onBack={() => nav("/cases")} />
      <div className="screen" style={{ gap: 18 }}>
        <h1 style={{ fontSize: 22, lineHeight: 1.4, textWrap: "pretty" }}>{a.title}</h1>
        <div className="row xs sub" style={{ flexWrap: "wrap", gap: 6, marginTop: -8 }}>
          <span className="pill pill-type">{a.type}</span><span className="pill pill-ok">{a.result}</span><span>{a.gu}</span><span>·</span><span>{a.when}</span>
        </div>
        {a.sec.map((body, i) => (
          <div key={i} className="col" style={{ gap: 6 }}>
            <div className="row section-title" style={{ gap: 8 }}><span className="mark mark-num" style={{ width: 22, height: 22, fontSize: 12 }}>{i + 1}</span>{ARTICLE_HEADS[i]}</div>
            {i === 1 && <Photo className="photo-wide" label="가려진 사진" />}
            <div style={{ textWrap: "pretty" }}>{body}</div>
          </div>
        ))}
      </div>
      <div className="bottom-bar">
        <button className={`btn btn-sm ${helped ? "btn-primary" : "btn-secondary"}`} style={{ height: 50, padding: "0 14px" }} aria-pressed={helped} onClick={() => set({ helped: { ...s.helped, [a.id]: !helped } })}>
          <Heart size={16} />도움돼요 {a.likes + (helped ? 1 : 0)}
        </button>
        <button className="btn btn-primary btn-grow" onClick={startFromCase}>나도 비슷한 상황이에요</button>
      </div>
    </div>
  );
}
