// 화면 흐름: S0 홈(/)에서 세 기능으로 갈라집니다. 하단 탭은 없고, 각 화면 상단의 뒤로 가기·홈 아이콘으로 이동합니다.
//   신고하기  /report → /chat → /done
//   신고 조회 /mine → /mine/:id → /share
//   신고 사례 /cases → /cases/:id
import { Route, Routes } from "react-router-dom";
import { StoreProvider, useStore } from "./app/store";
import { Toast } from "./components/ui";
import { Home } from "./screens/Home";
import { Landing } from "./screens/Landing";
import { Chat } from "./screens/Chat";
import { Done } from "./screens/Done";
import { Mine, MineDetail } from "./screens/Mine";
import { Cases, Article } from "./screens/Cases";
import { Share } from "./screens/Share";
import { TimerOverlay } from "./screens/TimerOverlay";

function Shell() {
  const { s } = useStore();
  return (
    <div className="viewport">
    <div className="app">
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/report" element={<Home />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/done" element={<Done />} />
        <Route path="/mine" element={<Mine />} />
        <Route path="/mine/:id" element={<MineDetail />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/cases/:id" element={<Article />} />
        <Route path="/share" element={<Share />} />
      </Routes>
      <TimerOverlay />
      <Toast msg={s.toast} />
    </div>
    </div>
  );
}

export default function App() {
  return (
    <StoreProvider>
      <Shell />
    </StoreProvider>
  );
}
