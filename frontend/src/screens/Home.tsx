// S1 상황 입력 (/report): 신고하기 1단계
import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "../app/store";
import { TYPE_CARDS, type TypeIcon } from "../data/content";
import { Photo } from "../components/ui";
import { AppBar } from "../components/AppBar";
import { Stepper } from "../components/Stepper";
import { WaveBackdrop } from "../components/motifs/WaveBackdrop";
import { Camera, Car, ChevronRight, Cone, Gallery, Poster, Trash } from "../components/icons/Icons";

const TYPE_ICON: Record<TypeIcon, typeof Car> = { car: Car, trash: Trash, poster: Poster, cone: Cone };

export function Home() {
  const { s, set, send } = useStore();
  const nav = useNavigate();
  const canSend = !!s.text.trim() || s.hasPhoto;
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 유형 카드: 글만 대신 써 준다. 사진 상태는 건드리지 않는다.
  // 입력창으로 커서를 옮겨 장소 같은 내용을 바로 덧붙일 수 있게 한다.
  const fillText = (text: string) => {
    set({ text });
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(text.length, text.length);
    });
  };

  return (
    <div className="page">
      <WaveBackdrop variant="both" />
      <AppBar title="신고하기" onBack={() => nav("/")} />
      <Stepper current={0} />

      <div className="screen" style={{ gap: 18, paddingTop: 4 }}>
        <h1 className="h1" style={{ whiteSpace: "nowrap", fontSize: "clamp(20px, 6.6cqw, 26px)" }}>무슨 불편을 겪으셨나요?</h1>

        {s.fromCase && <div className="note">사례와 같은 유형(불법주정차)으로 시작해요.</div>}

        <button className="resume" onClick={() => nav("/mine")}>
          <Photo label="" className="photo-sm" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="xs sub">이어서 하기</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>불법 광고물 · 증거 1/3</div>
          </div>
          <span className="sub"><ChevronRight size={18} /></span>
        </button>

        <div className="composer">
          {s.hasPhoto && (
            <div className="row" style={{ gap: 10 }}>
              <Photo label="사진 1장" className="photo-md" />
              <button className="link" style={{ minHeight: 44, color: "var(--sub)" }} onClick={() => set({ hasPhoto: false })}>빼기</button>
            </div>
          )}
          <textarea ref={inputRef} rows={2} value={s.text} aria-label="상황 설명" placeholder="예: 인도에 차가 올라와 있어요" onChange={(e) => set({ text: e.target.value })} />
          <div className="row">
            <button className="btn btn-secondary btn-sm" onClick={() => set({ hasPhoto: !s.hasPhoto })}><Camera size={18} />카메라</button>
            <button className="btn btn-secondary btn-sm" onClick={() => set({ hasPhoto: !s.hasPhoto })}><Gallery size={18} />갤러리</button>
            <div style={{ flex: 1 }} />
            <button className="btn btn-primary" style={{ height: 44, fontSize: 14 }} disabled={!canSend} onClick={send}>보내기</button>
          </div>
        </div>

        <div className="col" style={{ gap: 10 }}>
          <div className="section-title">이런 걸 도와드려요</div>
          <div className="type-grid">
            {TYPE_CARDS.map((t) => {
              const Icon = TYPE_ICON[t.icon];
              return (
                <button key={t.title} className="type-card" onClick={() => fillText(t.example)}>
                  <span className="icon-circle tc-icon"><Icon size={22} /></span>
                  <span className="tc-title">{t.title}</span>
                  <span className="tc-desc">{t.desc}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
