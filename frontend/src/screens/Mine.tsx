// S10 신고 조회 (/mine), S11 상세 (/mine/:id)
import { useNavigate, useParams } from "react-router-dom";
import { useStore } from "../app/store";
import { MINE, MINE_FILTERS } from "../data/content";
import { Chips, Photo } from "../components/ui";
import { AppBar } from "../components/AppBar";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { EmptyListArt } from "../components/motifs/Illustrations";
import { ChevronRight, Share } from "../components/icons/Icons";

const pillClass = (g: string) => (g === "처리 완료" ? "pill-ok" : g === "준비 중" ? "pill-warn" : "pill-mute");

export function Mine() {
  const { s, set } = useStore();
  const nav = useNavigate();
  const list = MINE.filter((m) => s.filter === "전체" || m.g === s.filter);
  return (
    <div className="page">
      <WaveBackdrop variant="both" />
      <AppBar title="신고 조회" onBack={() => nav("/")} />
      <div className="screen" style={{ gap: 14 }}>
        <h1 className="h1-sm">내가 한 신고</h1>
        <Chips items={MINE_FILTERS} value={s.filter} onChange={(f) => set({ filter: f })} />

        {list.length === 0 ? (
          <div className="empty">
            <EmptyListArt />
            <div>{MINE.length === 0 ? "아직 신고한 내역이 없어요" : "이 상태의 신고가 없어요"}</div>
            <button className="btn btn-primary" onClick={() => nav("/report")}>신고하러 가기</button>
          </div>
        ) : (
          <div className="col" style={{ gap: 10 }}>
            {list.map((m) => (
              <button key={m.id} className="item" onClick={() => { set({ item: m.id }); nav(`/mine/${m.id}`); }}>
                <Photo className="photo-md" label="사진" />
                <div className="body">
                  <div className="strong">{m.type}</div>
                  <div className="small sub">{m.place}</div>
                  <div className="row" style={{ marginTop: 3, flexWrap: "wrap", gap: 6 }}>
                    <span className={`pill ${pillClass(m.g)}`}>{m.status}</span>
                    {m.cont && <span className="small strong" style={{ color: "var(--navy)" }}>이어서 하기</span>}
                  </div>
                </div>
                <span className="sub"><ChevronRight size={18} /></span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function MineDetail() {
  const { s, set, openShare } = useStore();
  const nav = useNavigate();
  const { id } = useParams();
  const d = MINE[Number(id ?? s.item)] ?? MINE[1];
  const timeline: [string, string][] = [["상황 입력", "11월 14일 오후 2:02"], ["증거 준비", "사진 2장 확인"], ["접수 완료", d.to], ["처리 결과", s.result]];

  return (
    <div className="page">
      <WaveBackdrop variant="corner" />
      <AppBar title="신고 조회" onBack={() => nav("/mine")} />
      <div className="screen" style={{ gap: 18 }}>
        <div><h1 className="h1-sm">{d.type}</h1><div className="small sub">{d.place}</div></div>

        <div className="panel" style={{ gap: 0 }}>
          {timeline.map(([label, note], i) => (
            <div key={label} className="tl">
              <div className="rail"><span className={`dot ${i < 3 || s.result !== "아직 모름" ? "on" : ""}`} /><span className={`rule ${i < 3 ? "" : "off"}`} /></div>
              <div className="txt"><div style={{ fontWeight: 600 }}>{label}</div><div className="small sub">{note}</div></div>
            </div>
          ))}
        </div>

        <div className="col"><div className="section-title">첨부한 사진</div><div className="row"><Photo className="photo-grow" label="첨부 사진 1" /><Photo className="photo-grow" label="첨부 사진 2" /></div></div>
        <div className="col"><div className="section-title">제출한 신고 문구</div>
          <div className="draft">서울시 마포구 ○○로 12 앞 전봇대 아래에 종량제 봉투를 쓰지 않은 생활쓰레기가 무단투기되어 있습니다. 2026년 11월 14일 오후 2시경 확인했으며, 악취와 통행 불편이 있어 수거와 단속을 요청드립니다.</div>
        </div>
        <div className="table">
          <div><span className="k sub">접수처</span><span>{d.to}</span></div>
          <div><span className="k sub">접수번호</span><span>{d.no}</span></div>
        </div>
        <div className="col"><div className="section-title">처리 결과</div>
          <div className="small sub">안전신문고와 연동되지 않아요. 결과를 받으면 직접 골라 주세요.</div>
          <div className="row" style={{ gap: 6 }}>
            {(["수용", "불수용", "아직 모름"] as const).map((r) => (
              <button key={r} className={`btn btn-sm btn-grow ${s.result === r ? "btn-primary" : "btn-secondary"}`} aria-pressed={s.result === r} onClick={() => set({ result: r })}>{r}</button>
            ))}
          </div>
          {s.result === "불수용" && <textarea className="textarea" rows={2} value={s.reason} placeholder="불수용 사유를 적어 두면 다음에 도움이 돼요" onChange={(e) => set({ reason: e.target.value })} />}
        </div>
        <button className="btn btn-outline" onClick={() => openShare("detail")}><Share size={16} />사례로 공유하기</button>
      </div>
    </div>
  );
}
