// 하위 화면 상단: 뒤로 가기 · 가운데 제목 · 홈
import type { ReactNode } from "react";
import { useStore } from "../app/store";
import { Back, Home } from "./icons/Icons";

export function AppBar({ title, onBack, right, home = true }: { title: string; onBack?: () => void; right?: ReactNode; home?: boolean }) {
  const { toLanding } = useStore();
  return (
    <header className="appbar">
      <div>{onBack && <button className="ab-btn" aria-label="뒤로 가기" onClick={onBack}><Back /></button>}</div>
      <div className="ab-title">{title}</div>
      <div className="ab-right">
        {right}
        {home && <button className="ab-btn" aria-label="홈으로" onClick={toLanding}><Home /></button>}
      </div>
    </header>
  );
}
