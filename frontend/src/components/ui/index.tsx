import type { ReactNode } from "react";
import { Bang, Check as CheckIcon, Minus } from "../icons/Icons";

export const Photo = ({ label, className = "" }: { label: string; className?: string }) => (
  <div className={`photo ${className}`}>{label}</div>
);

export const Mark = ({ kind, children }: { kind: "ok" | "warn" | "mute" | "empty" | "num"; children?: ReactNode }) => (
  <span className={`mark mark-${kind}`}>
    {children ?? (kind === "ok" ? <CheckIcon size={14} stroke={3} /> : kind === "warn" ? <Bang size={14} stroke={3} /> : kind === "mute" ? <Minus size={14} stroke={3} /> : null)}
  </span>
);

export const Check = ({ on, onClick, label }: { on: boolean; onClick?: () => void; label: string }) => (
  <button className="hit" aria-label={label} aria-pressed={on} onClick={onClick}>
    <span className={`check ${on ? "on" : ""}`}>{on && <CheckIcon size={15} stroke={3} />}</span>
  </button>
);

export const Badge = ({ kind }: { kind: "신고" | "민원" }) => (
  <span className={`badge ${kind === "신고" ? "badge-report" : "badge-civil"}`}>{kind}</span>
);

export const Fine = () => <div className="fine">참고용 안내이며 최종 판단은 담당 기관이 합니다.</div>;

export const Bot = ({ children }: { children: ReactNode }) => <div className="bot">{children}</div>;

export const Thinking = ({ children }: { children: ReactNode }) => (
  <div className="bot row" style={{ gap: 10 }}><span className="typing" aria-hidden><i /><i /><i /></span>{children}</div>
);

export const Chips = <T extends string>({ items, value, onChange }: { items: readonly T[]; value: T | string; onChange: (v: T) => void }) => (
  <div className="chips">
    {items.map((f) => <button key={f} className={`chip ${value === f ? "on" : ""}`} aria-pressed={value === f} onClick={() => onChange(f)}>{f}</button>)}
  </div>
);

export const Toast = ({ msg }: { msg: string }) => (msg ? <div key={msg} className="toast" role="status">{msg}</div> : null);
