// S9 완료 (/done): 신고하기 마지막 단계
import { useNavigate } from "react-router-dom";
import { useStore } from "../app/store";
import { STAGES } from "../data/content";
import { AppBar } from "../components/AppBar";
import { Stepper } from "../components/Stepper";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { Check, Doc, Share } from "../components/icons/Icons";

const NONE = "입력 안 함";

export function Done() {
  const { s, openShare, toast, toLanding } = useStore();
  const n = s.finished.length;
  const nav = useNavigate();
  // 접수처는 접수 안내(GET /guide)의 channel에서 가져온다.
  const items = s.finished.map((f) => ({ type: f.label, kind: f.category === "report" ? "신고" : "민원", to: f.to, no: f.receipt || NONE }));

  const copy = (no: string) => {
    navigator.clipboard?.writeText(no).catch(() => {});
    toast("접수번호를 복사했어요");
  };

  return (
    <div className="page">
      <WaveBackdrop variant="both" />
      <AppBar title="신고하기" />
      <Stepper current={STAGES.length} />

      <div className="screen" style={{ gap: 18 }}>
        <div className="done-hero">
          <div className="done-check"><Check size={42} stroke={3} /></div>
          <h1 style={{ fontSize: 24, lineHeight: 1.35 }}>{n}건 접수를 마쳤어요!</h1>
        </div>

        <div className="card">
          {items.map((d) => (
            <div key={d.type} className="receipt">
              <span className="icon-circle"><Doc size={22} /></span>
              <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 2 }}>
                <div className="row" style={{ gap: 6 }}><span className={`badge ${d.kind === "신고" ? "badge-report" : "badge-civil"}`}>{d.kind}</span><span className="strong">{d.type}</span></div>
                <div className="xs sub">{d.to}</div>
                <div className="small">접수번호 <span className={d.no === NONE ? "sub" : "strong"}>{d.no}</span></div>
              </div>
              {d.no !== NONE && <button className="copy-btn" onClick={() => copy(d.no)}>복사</button>}
            </div>
          ))}
        </div>

        <div className="panel">
          <div className="small" style={{ textWrap: "pretty" }}>이 경험을 다른 사람에게 알려 주시겠어요? 개인정보는 지우고 공유돼요.</div>
          <button className="btn btn-outline btn-sm" disabled={!s.finished.length} onClick={() => s.finished[0] && openShare(s.finished[0].id, "/done")}><Share size={16} />사례로 공유하기</button>
        </div>

        <div className="col" style={{ marginTop: "auto" }}>
          <button className="btn btn-primary btn-block" onClick={() => nav("/mine")}>신고 조회에서 보기</button>
          <button className="btn btn-secondary btn-block" onClick={toLanding}>홈으로</button>
        </div>
      </div>
    </div>
  );
}
