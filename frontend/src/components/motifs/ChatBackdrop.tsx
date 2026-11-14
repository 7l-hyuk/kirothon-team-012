// 신고 대화(/chat) 배경: 홈(S0)과 같은 남색 바탕에 창살 모서리, 구름, 청해파·卍자문 원, 꽃, 아치.
// 대화 영역 뒤에 고정되어 스크롤해도 움직이지 않습니다. 글과 카드가 잘 읽히도록 선을 홈보다 옅게 둡니다.
import "../../styles/landing.css";
import { Arch, CloudBand, FretCircle, Flower, LatticeCorner, WaveCircle } from "./LandingMotifs";

const LINE = "rgba(255,255,255,.32)";
const FAINT = "rgba(255,255,255,.26)";

export function ChatBackdrop() {
  return (
    <div className="chat-bd" aria-hidden>
      <div className="chat-bd-frame" />
      <div className="ld-deco" style={{ left: 10, top: 10 }}><LatticeCorner size={48} color={LINE} /></div>
      <div className="ld-deco" style={{ right: 10, top: 10 }}><LatticeCorner size={48} color={LINE} flipX /></div>
      <div className="ld-deco" style={{ left: "17%", top: 30 }}><CloudBand width={74} color={LINE} /></div>
      <div className="ld-deco" style={{ right: "12%", top: 78 }}><CloudBand width={64} color={LINE} mirror /></div>
      <div className="ld-deco" style={{ left: "6%", top: "44%" }}><CloudBand width={60} color={FAINT} /></div>
      <div className="ld-deco" style={{ right: "5%", top: "52%" }}><CloudBand width={68} color={FAINT} mirror /></div>

      {/* 아래쪽 문양 묶음: 화면 너비에 맞춰 늘고 줄어듭니다(390px 기준 비율) */}
      <div className="chat-bd-art">
        <div className="ld-fit" style={{ left: "12%", bottom: "26%", width: "30%", aspectRatio: "1" }}><WaveCircle size={122} color={FAINT} /></div>
        <div className="ld-fit" style={{ right: "12%", bottom: "26%", width: "30%", aspectRatio: "1" }}><FretCircle size={120} color={FAINT} /></div>
        <div className="ld-fit chat-bd-flower" style={{ width: "11%", aspectRatio: "1" }}><Flower /></div>
        <div className="ld-fit" style={{ left: "-2%", bottom: "6%", width: "20%", aspectRatio: "1 / .85" }}><Arch width={76} color={LINE} /></div>
        <div className="ld-fit" style={{ left: "15%", bottom: 0, width: "22%", aspectRatio: "1 / .85" }}><Arch width={84} color={LINE} /></div>
        <div className="ld-fit" style={{ right: "15%", bottom: 0, width: "22%", aspectRatio: "1 / .85" }}><Arch width={84} color={LINE} /></div>
        <div className="ld-fit" style={{ right: "-2%", bottom: "6%", width: "20%", aspectRatio: "1 / .85" }}><Arch width={76} color={LINE} /></div>
      </div>
    </div>
  );
}
