import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/global.css";

// 넓은 화면에서 아이폰 14(390×844) 틀이 창 안에 다 들어오도록 축소 비율을 계산합니다.
// 휴대폰 폭(600px 미만)에서는 CSS가 이 값을 쓰지 않습니다.
const FRAME_W = 390, FRAME_H = 844, MARGIN = 48;
function fitFrame() {
  const s = Math.min(1, (window.innerWidth - MARGIN) / FRAME_W, (window.innerHeight - MARGIN) / FRAME_H);
  document.documentElement.style.setProperty("--frame-scale", String(Math.max(s, 0.4)));
}
fitFrame();
window.addEventListener("resize", fitFrame);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
