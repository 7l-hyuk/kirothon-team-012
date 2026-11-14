// 신고 대화(/chat) 장식. 홈(S0)과 같은 구성입니다.
//   ChatHero    머리 아래 남색 띠. 창살 모서리, 구름, 청해파·卍자문 원, 꽃, 아치를 넣고, 아래쪽은 대화 패널 뒤로 살짝 가려집니다.
//   SheetCorners 밝은 대화 패널 아래 양쪽의 옅은 창살 모서리
// 대화를 아래로 스크롤하면(compact) 띠를 얇게 줄여 대화 공간을 넓힙니다.
import "../../styles/landing.css";
import { Arch, CloudBand, FretCircle, Flower, LatticeCorner, WaveCircle } from "./LandingMotifs";

export function ChatHero({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`chat-hero ${compact ? "compact" : ""}`} aria-hidden>
      <div className="chat-hero-frame" />
      <div className="chat-hero-art">
        <div className="ld-deco" style={{ left: 12, top: 0 }}><LatticeCorner size={42} /></div>
        <div className="ld-deco" style={{ right: 12, top: 0 }}><LatticeCorner size={42} flipX /></div>
        <div className="ld-deco" style={{ left: "21%", top: 8 }}><CloudBand width={66} /></div>
        <div className="ld-deco" style={{ left: "49%", top: 22 }}><CloudBand width={58} mirror /></div>
        <div className="ld-deco" style={{ right: "7%", top: 48 }}><CloudBand width={54} /></div>
        <div className="ld-deco" style={{ left: "4%", top: 56 }}><CloudBand width={50} /></div>

        <div className="ld-deco" style={{ left: "-3%", bottom: 6 }}><Arch width={64} /></div>
        <div className="ld-deco" style={{ left: "12%", bottom: -6 }}><Arch width={72} /></div>
        <div className="ld-deco" style={{ left: "29%", bottom: 22 }}><WaveCircle size={62} /></div>
        <div className="ld-deco chat-hero-flower" style={{ bottom: 22 }}><Flower size={30} /></div>
        <div className="ld-deco" style={{ right: "29%", bottom: 22 }}><FretCircle size={60} /></div>
        <div className="ld-deco" style={{ right: "12%", bottom: -6 }}><Arch width={72} /></div>
        <div className="ld-deco" style={{ right: "-3%", bottom: 6 }}><Arch width={64} /></div>
      </div>
    </div>
  );
}

const SHEET_LINE = "var(--navy-line)";

export function SheetCorners() {
  return (
    <div className="chat-sheet-corners" aria-hidden>
      <div className="ld-deco" style={{ left: 12, bottom: 10 }}><LatticeCorner size={44} color={SHEET_LINE} flipY /></div>
      <div className="ld-deco" style={{ right: 12, bottom: 10 }}><LatticeCorner size={44} color={SHEET_LINE} flipX flipY /></div>
    </div>
  );
}
