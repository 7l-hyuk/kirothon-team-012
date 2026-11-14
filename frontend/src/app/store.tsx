/* 목업의 DCLogic 상태를 그대로 옮긴 전역 스토어.
   - p: 시나리오 진행 단계 (1 분석중 → 2 항목선택 → 3 증거안내 → 4 불충분 → 5 충분 → 6 접수안내 → 7 다음항목 → 8 사전점검 → 9 제출 → 10 완료)
   - S1~S3(send, startPrep)은 실제 API를 부른다. S4 이후는 아직 스크립트이고, 분석 결과로 park/trash를 채워 이어 간다. */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { DRAFTS, SUBMIT_STEPS } from "../data/content";
import { createAnalysis, createReports, type Analysis, type ReportRef, type TypeId } from "../api/analyses";
import { errorMessage } from "../api/client";

export type Scenario = "A" | "B";
export type ResultChoice = "수용" | "불수용" | "아직 모름";

export interface FlowState {
  text: string; sent: string; scen: Scenario;
  /** S1에서 고른 사진과 미리보기 주소(URL.createObjectURL). */
  files: File[]; previews: string[];
  /** S2~S3: 분석 응답, 오류 문구, 고른 항목(고른 순서 = 진행 순서), 만든 신고 건 */
  analysis: Analysis | null; analysisError: string; selected: TypeId[]; reports: ReportRef[]; creating: boolean;
  p: number; busy: boolean; phase: 0 | 1;
  park: boolean; trash: boolean; whyPark: boolean; whyTrash: boolean;
  s7: number; draft: number; receipt: string;
  sec: number; timer: boolean; timerDone: boolean;
  filter: string; cfilter: string;
  item: number; art: number; result: ResultChoice; reason: string;
  agree: boolean; shareFrom: "done" | "detail"; helped: Record<number, boolean>;
  toast: string; fromCase: boolean;
}

const base = (): FlowState => ({
  text: "", sent: "", scen: "A", files: [], previews: [],
  analysis: null, analysisError: "", selected: [], reports: [], creating: false, p: 0, busy: false, phase: 0,
  park: true, trash: true, whyPark: false, whyTrash: false, s7: 0, draft: 0, receipt: "",
  sec: 60, timer: false, timerDone: false, filter: "전체", cfilter: "전체",
  item: 1, art: 1, result: "수용", reason: "", agree: false, shareFrom: "done", helped: {}, toast: "", fromCase: false,
});

const FAST = new URLSearchParams(window.location.search).has("fast");

interface Store {
  s: FlowState;
  set: (patch: Partial<FlowState> | ((s: FlowState) => Partial<FlowState>)) => void;
  toast: (m: string) => void;
  send: () => void;
  retry: () => void;
  toggleItem: (t: TypeId) => void;
  goHome: () => void;
  toLanding: () => void;
  step: (p: number) => void;
  startPrep: () => void;
  s7Next: () => void;
  startTimer: () => void;
  cancelTimer: () => void;
  timerShot: () => void;
  finish: () => void;
  later: () => void;
  openShare: (from: "done" | "detail") => void;
  doShare: () => void;
  startFromCase: () => void;
  n: number;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const nav = useNavigate();
  const [s, setS] = useState<FlowState>(base);
  const timers = useRef<number[]>([]);
  const iv = useRef<number | undefined>(undefined);
  const tt = useRef<number | undefined>(undefined);

  const set = useCallback<Store["set"]>((patch) => setS((prev) => ({ ...prev, ...(typeof patch === "function" ? patch(prev) : patch) })), []);
  const clear = useCallback(() => { timers.current.forEach(clearTimeout); timers.current = []; clearInterval(iv.current); }, []);
  const wait = useCallback((fn: () => void, ms: number) => { timers.current.push(window.setTimeout(fn, ms)); }, []);
  useEffect(() => () => { clear(); clearTimeout(tt.current); }, [clear]);

  const toast = useCallback((m: string) => {
    set({ toast: m }); clearTimeout(tt.current);
    tt.current = window.setTimeout(() => set({ toast: "" }), 1800);
  }, [set]);

  // 분석 요청. 화면을 떠났거나 새 요청을 보냈으면 늦게 온 응답은 버린다.
  const req = useRef(0);
  const analyze = useCallback(async (text: string, files: File[]) => {
    const id = ++req.current;
    clear();
    set({ p: 1, phase: 0, analysis: null, analysisError: "" });
    wait(() => set({ phase: 1 }), 3000);
    try {
      const a = await createAnalysis(text, files);
      if (id !== req.current) return;
      clear();
      set({ analysis: a, scen: a.reportable ? "A" : "B", selected: a.items.map((i) => i.type_id), p: 2 });
    } catch (e) {
      if (id !== req.current) return;
      clear();
      set({ analysisError: errorMessage(e) });
    }
  }, [clear, wait, set]);

  const send = useCallback(() => {
    const text = s.text.trim();
    if (!text && !s.files.length) return;
    setS({ ...base(), helped: s.helped, text: s.text, files: s.files, previews: s.previews, sent: text || "이거 신고할 수 있나요?" });
    nav("/chat");
    void analyze(text, s.files);
  }, [s.text, s.files, s.previews, s.helped, nav, analyze]);

  const retry = useCallback(() => { void analyze(s.text.trim(), s.files); }, [s.text, s.files, analyze]);

  const toggleItem = useCallback((t: TypeId) => set((prev) => ({
    selected: prev.selected.includes(t) ? prev.selected.filter((x) => x !== t) : [...prev.selected, t],
  })), [set]);

  const goHome = useCallback(() => { req.current++; clear(); set({ timer: false, creating: false }); nav("/report"); }, [clear, set, nav]);
  const toLanding = useCallback(() => { req.current++; clear(); set({ timer: false, timerDone: false, creating: false }); nav("/"); }, [clear, set, nav]);
  const step = useCallback((p: number) => { set({ p, busy: true }); wait(() => set({ busy: false }), 1100); }, [set, wait]);
  const finish = useCallback(() => { set({ p: 10 }); nav("/done"); }, [set, nav]);
  const n = s.selected.length;
  // 고른 항목으로 신고 건을 만든다. S4 이후 스크립트는 아직 쓰레기·불법주정차 두 유형만 그린다.
  const startPrep = useCallback(async () => {
    if (!s.analysis || !n || s.creating) return;
    const id = req.current;
    set({ creating: true });
    try {
      const r = await createReports(s.analysis.id, s.selected);
      if (id !== req.current) return;
      const trash = s.selected.includes("trash_dumping");
      const park = s.selected.includes("illegal_parking");
      set({ reports: r.reports, trash, park, creating: false, p: trash ? 3 : park ? 8 : 3 });
    } catch (e) {
      if (id !== req.current) return;
      set({ creating: false });
      toast(errorMessage(e));
    }
  }, [s.analysis, s.selected, s.creating, n, set, toast]);

  const s7Next = useCallback(() => {
    const cur = SUBMIT_STEPS[s.s7];
    if (cur.msg) toast(cur.msg);
    if (s.s7 === 5) navigator.clipboard?.writeText(DRAFTS[s.draft]).catch(() => {});
    if (s.s7 < 6) set({ s7: s.s7 + 1 });
    else if (s.park) set({ p: 7 });
    else finish();
  }, [s.s7, s.draft, s.park, set, toast, finish]);

  const startTimer = useCallback(() => {
    set({ timer: true, sec: 60, timerDone: false });
    clearInterval(iv.current);
    iv.current = window.setInterval(() => {
      setS((prev) => {
        if (prev.sec <= 1) { clearInterval(iv.current); try { navigator.vibrate?.(200); } catch { /* noop */ } return { ...prev, sec: 0, timerDone: true }; }
        return { ...prev, sec: prev.sec - 1 };
      });
    }, FAST ? 100 : 1000);
  }, [set]);
  const cancelTimer = useCallback(() => { clearInterval(iv.current); set({ timer: false }); }, [set]);
  const timerShot = useCallback(() => set({ timer: false, timerDone: false, p: 9 }), [set]);

  const later = useCallback(() => { nav("/mine"); toast("불법주정차는 준비 중으로 남겨 뒀어요"); }, [nav, toast]);
  const openShare = useCallback((from: "done" | "detail") => { set({ shareFrom: from, agree: false }); nav("/share"); }, [set, nav]);
  const doShare = useCallback(() => { if (!s.agree) return; nav("/cases"); toast("사례로 공유했어요"); }, [s.agree, nav, toast]);
  const startFromCase = useCallback(() => {
    setS({ ...base(), helped: s.helped, fromCase: true, text: "인도에 차가 올라와 있어요" });
    nav("/report");
  }, [s.helped, nav]);

  const value = useMemo<Store>(() => ({ s, set, toast, send, retry, toggleItem, goHome, toLanding, step, startPrep, s7Next, startTimer, cancelTimer, timerShot, finish, later, openShare, doShare, startFromCase, n }),
    [s, set, toast, send, retry, toggleItem, goHome, toLanding, step, startPrep, s7Next, startTimer, cancelTimer, timerShot, finish, later, openShare, doShare, startFromCase, n]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useStore must be used inside StoreProvider");
  return v;
}
