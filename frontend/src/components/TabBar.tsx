import { NavLink, useLocation } from "react-router-dom";
import { useStore } from "../app/store";

export function TabBar() {
  const { goHome } = useStore();
  const { pathname } = useLocation();
  const tab = pathname.startsWith("/mine") ? 1 : pathname.startsWith("/cases") ? 2 : 0;
  return (
    <nav className="tabs">
      <NavLink to="/report" className={tab === 0 ? "active" : ""} onClick={(e) => { e.preventDefault(); goHome(); }}>신고하기</NavLink>
      <NavLink to="/mine" className={tab === 1 ? "active" : ""}>내 신고</NavLink>
      <NavLink to="/cases" className={tab === 2 ? "active" : ""}>사례</NavLink>
    </nav>
  );
}
