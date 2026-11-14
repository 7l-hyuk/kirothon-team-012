// S14 공유 동의 (/share)
import { useNavigate } from "react-router-dom";
import { useStore } from "../app/store";
import { SHARE_RULES } from "../data/content";
import { AppBar } from "../components/AppBar";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { Check } from "../components/icons/Icons";

export function Share() {
  const { s, set, doShare } = useStore();
  const nav = useNavigate();
  const cancel = () => nav(s.shareFrom === "detail" ? `/mine/${s.item}` : "/done");
  return (
    <div className="page">
      <WaveBackdrop variant="corner" />
      <AppBar title="사례로 공유하기" onBack={cancel} />
      <div className="screen" style={{ gap: 16 }}>
        <h1 className="h1-sm">공유하기 전에<br />이렇게 지워요</h1>
        <div className="card row" style={{ alignItems: "stretch", padding: 12, gap: 10 }}>
          <div className="col" style={{ flex: 1, gap: 6 }}>
            <div className="xs sub">원본</div>
            <div className="photo" style={{ height: 120, flexDirection: "column", gap: 8 }}>차량 사진<span style={{ background: "#fff", border: "1px solid var(--ink)", padding: "1px 8px", borderRadius: 2 }}>12가 3456</span></div>
            <div className="xs" style={{ lineHeight: 1.5 }}>마포구 ○○로 12<br />11월 14일 오후 2시</div>
          </div>
          <div className="col" style={{ flex: 1, gap: 6 }}>
            <div className="xs strong" style={{ color: "var(--navy)" }}>공유될 모습</div>
            <div className="photo" style={{ height: 120, flexDirection: "column", gap: 8 }}>차량 사진<span style={{ background: "var(--ink)", color: "var(--ink)", padding: "1px 8px", borderRadius: 2 }}>00가 0000</span></div>
            <div className="xs" style={{ lineHeight: 1.5 }}>마포구<br />2026년 11월</div>
          </div>
        </div>
        <div className="table">
          {SHARE_RULES.map(([k, v]) => <div key={k}><span className="k">{k}</span><span className="v">{v}</span></div>)}
        </div>
        <button className="row" style={{ gap: 10, minHeight: 44, textAlign: "left" }} aria-pressed={s.agree} onClick={() => set({ agree: !s.agree })}>
          <span className={`check ${s.agree ? "on" : ""}`}>{s.agree && <Check size={15} stroke={3} />}</span>위 내용으로 공유하는 데 동의합니다
        </button>
        <div className="row">
          <button className="btn btn-secondary" style={{ padding: "0 20px" }} onClick={cancel}>취소</button>
          <button className="btn btn-primary btn-grow" disabled={!s.agree} onClick={doShare}>공유하기</button>
        </div>
        <div className="xs sub">공유한 글은 신고 조회 상세에서 언제든 내릴 수 있어요.</div>
      </div>
    </div>
  );
}
