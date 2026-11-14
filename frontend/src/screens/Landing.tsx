// S0 홈(첫 화면): 남색 전통문양 배경 + 세 기능 진입 (신고하기 / 신고 조회 / 신고 사례)
import { useNavigate } from "react-router-dom";
import { Book, ChevronRight, Search } from "../components/icons/Icons";
import { Arch, CloudBand, FretCircle, Flower, LatticeCorner, WaveCircle } from "../components/motifs/LandingMotifs";
import "../styles/landing.css";

const PANEL_LINE = "#b9c4dc";

export function Landing() {
  const nav = useNavigate();

  return (
    <div className="landing">
      <section className="ld-hero">
        <div className="ld-frame" aria-hidden />
        <div className="ld-top" aria-hidden>
          <div className="ld-deco" style={{ left: 12, top: 18 }}><LatticeCorner /></div>
          <div className="ld-deco" style={{ right: 12, top: 18 }}><LatticeCorner flipX /></div>
          <div className="ld-deco" style={{ left: "18%", top: 52 }}><CloudBand width={80} /></div>
          <div className="ld-deco" style={{ left: "47.7%", top: 68 }}><CloudBand width={76} mirror /></div>
          <div className="ld-deco" style={{ right: "9%", top: 106 }}><CloudBand width={66} /></div>
        </div>

        <div className="ld-copy">
          <p className="ld-tagline"><span />민원 신고, 더 쉽고 빠르게<span /></p>
          <h1 className="ld-title">
            신고메이트
            <svg className="ld-spark" width="22" height="22" viewBox="0 0 22 22" aria-hidden>
              <path d="M4 8L1 1 M10 10L18 4 M10 16L20 17" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </h1>
          <p className="ld-desc">궁금한 민원부터 신고까지,<br />이제는 신고메이트와 함께하세요.</p>
        </div>

        {/* 문양 위치는 390×230 기준 비율(%)이라 화면 높이가 달라도 같은 배치를 유지합니다 */}
        <div className="ld-art" aria-hidden>
          <div className="ld-fit ld-w" style={{ left: "3.6%", top: 0, width: "18%" }}><CloudBand width={70} /></div>
          <div className="ld-fit ld-w" style={{ right: "3.6%", top: 0, width: "18%" }}><CloudBand width={70} mirror /></div>
          <div className="ld-fit" style={{ left: "14.9%", top: "9.6%", height: "53%", aspectRatio: "1" }}><WaveCircle size={122} /></div>
          <div className="ld-fit" style={{ right: "14.4%", top: "10.4%", height: "52%", aspectRatio: "1" }}><FretCircle size={120} /></div>
          <div className="ld-fit ld-flower" style={{ height: "20%", aspectRatio: "1" }}><Flower /></div>
          <div className="ld-fit" style={{ left: "-1.5%", bottom: "8.7%", height: "28%", aspectRatio: "1 / .85" }}><Arch width={76} /></div>
          <div className="ld-fit" style={{ left: "15.9%", bottom: 0, height: "31%", aspectRatio: "1 / .85" }}><Arch width={84} /></div>
          <div className="ld-fit" style={{ right: "15.9%", bottom: 0, height: "31%", aspectRatio: "1 / .85" }}><Arch width={84} /></div>
          <div className="ld-fit" style={{ right: "-1.5%", bottom: "8.7%", height: "28%", aspectRatio: "1 / .85" }}><Arch width={76} /></div>
        </div>
      </section>

      <section className="ld-panel">
        <button className="ld-card ld-main" onClick={() => nav("/report")}>
          <span className="ld-icon-lg" aria-hidden>
            <svg width="54" height="54" viewBox="0 0 54 54">
              <path d="M8 7h20l9 9v12" fill="none" stroke="#1b2240" strokeWidth="2.4" strokeLinejoin="round" />
              <path d="M8 7v38h22" fill="none" stroke="#1b2240" strokeWidth="2.4" strokeLinejoin="round" />
              <path d="M14 21h14 M14 28h10 M14 35h8" stroke="#1b2240" strokeWidth="2.4" strokeLinecap="round" />
              <circle cx="38" cy="39" r="11" fill="#2a4b8d" />
              <path d="M38 33v7" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
              <circle cx="38" cy="44.5" r="1.6" fill="#fff" />
            </svg>
          </span>
          <span className="ld-divider" aria-hidden />
          <span className="ld-main-text">
            <strong>신고하기</strong>
            <span>신고 가능 여부부터 접수까지<br />단계별로 알려 드려요</span>
          </span>
          <span className="ld-arrow" aria-hidden>
            <svg width="18" height="18" viewBox="0 0 18 18"><path d="M2 9h13 M10 4l5 5-5 5" fill="none" stroke="#1b2240" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </span>
        </button>

        <div className="ld-row">
          <button className="ld-card ld-sub" onClick={() => nav("/mine")}>
            <span className="ld-sub-icon"><Search size={24} stroke={2.2} /></span>
            <strong>신고 조회</strong>
            <span className="ld-chev"><ChevronRight size={18} /></span>
          </button>
          <button className="ld-card ld-sub" onClick={() => nav("/cases")}>
            <span className="ld-sub-icon"><Book size={24} stroke={2.2} /></span>
            <strong>신고 사례</strong>
            <span className="ld-chev"><ChevronRight size={18} /></span>
          </button>
        </div>

        <div className="ld-deco" style={{ left: 10, bottom: 10 }}><LatticeCorner size={48} color={PANEL_LINE} flipY /></div>
        <div className="ld-deco" style={{ right: 10, bottom: 10 }}><LatticeCorner size={48} color={PANEL_LINE} flipX flipY /></div>
      </section>
    </div>
  );
}
