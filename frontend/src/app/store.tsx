/* 신고하기 흐름의 전역 스토어.
   - p: 0 입력 전 → 1 분석 중(S2) → 2 항목 선택(S3) → 3 신고 건 진행 → 10 완료(S9)
   - p === 3일 때 reports[cur] 한 건씩 서버의 sequence 순서로 진행한다. rstage가 그 건의 단계다.
       evidence   S4·S5 증거 체크리스트와 사진 검수 (쓰레기, 광고물, 시설물)
       rehearsal  S6 불법주정차 사전 점검과 본촬영 안내, 타이머
       submit     불법주정차 본촬영 뒤 "제출했어요"
       guide      S7 접수 안내 (아직 대본. feat/fe-guide에서 GET /guide로 바꾼다)
       next       S8 다음 항목 안내
   - API 호출은 화면을 떠나거나 새로 시작하면(req 증가) 늦게 온 응답을 버린다. */
import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { DRAFTS, SUBMIT_STEPS } from "../data/content";
import { createAnalysis, createReports, type Analysis, type Category, type ReportRef, type TypeId } from "../api/analyses";
import { getEvidence, rehearse, uploadPhoto, type Evidence, type Rehearsal, type SceneReview } from "../api/reports";
import { ApiError, errorMessage } from "../api/client";

export type Scenario = "A" | "B";
export type ResultChoice = "수용" | "불수용" | "아직 모름";
export type ReportStage = "evidence" | "rehearsal" | "submit" | "guide" | "next";

/** 이번 세션에 장면별로 마지막으로 올린 사진(미리보기)과 검수 결과. */
export interface Shot { preview: string; review: SceneReview | null }
export interface Finished { id: string; label: string; category: Category; receipt: string }

/** 사전 점검에 쓸 사진을 따로 올릴 때 shots에 쓰는 키 */
export const REHEARSAL_SHOT = "_rehearsal";

export interface FlowState {
  text: string; sent: string; scen: Scenario;
  /** S1에서 고른 사진과 미리보기 주소(URL.createObjectURL). */
  files: File[]; previews: string[];
  /** S2~S3: 분석 응답, 오류 문구, 고른 항목(고른 순서 = 진행 순서), 만든 신고 건 */
  analysis: Analysis | null; analysisError: string; selected: TypeId[]; reports: ReportRef[]; creating: boolean;
  p: number; phase: 0 | 1;
  /** 신고 건 진행 */
  cur: number; rstage: ReportStage;
  evidence: Evidence | null; evError: string; uploading: string; shots: Record<string, Shot>;
  rehearsal: Rehearsal | null; rhBusy: boolean; rhError: string; rhNeedsPhoto: boolean;
  finished: Finished[];
  s7: number; draft: number; receipt: string;
  sec: number; timerTotal: number; timer: boolean; timerDone: boolean;
  filter: string; cfilter: string;
  item: number; art: number; result: ResultChoice; reason: string;
  agree: boolean; shareFrom: "done" | "detail"; helped: Record<number, boolean>;
  toast: string; fromCase: boolean;
}

const base = (): FlowState => ({
  text: "", sent: "", scen: "A", files: [], previews: [],
  analysis: null, analysisError: "", selected: [], reports: [], creating: false,
  p: 0, phase: 0,
  cur: 0, rstage: "evidence", evidence: null, evError: "", uploading: "", shots: {},
  rehearsal: null, rhBusy: false, rhError: "", rhNeedsPhoto: false, finished: [],
  s7: 0, draft: 0, receipt: "",
  sec: 60, timerTotal: 60, timer: false, timerDone: false, filter: "전체", cfilter: "전체",
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
  startPrep: () => void;
  /** 지금 진행 중인 신고 건의 이름과 분류 */
  current: { id: string; type_id: TypeId; label: string; category: Category } | null;
  reloadEvidence: () => void;
  shoot: (sceneId: string, file: File) => void;
  toGuide: () => void;
  runRehearsal: () => void;
  rehearsalPhoto: (file: File) => void;
  completeReport: () => void;
  nextReport: () => void;
  skipReport: () => void;
  s7Next: () => void;
  startTimer: () => void;
  cancelTimer: () => void;
  timerShot: () => void;
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
  // 비동기 처리 중에 최신 상태를 읽기 위한 참조
  const sr = useRef(s);
  useLayoutEffect(() => { sr.current = s; });
  const timers = useRef<number[]>([]);
  const iv = useRef<number | undefined>(undefined);
  const tt = useRef<number | undefined>(undefined);
  const req = useRef(0);

  const set = useCallback<Store["set"]>((patch) => setS((prev) => ({ ...prev, ...(typeof patch === "function" ? patch(prev) : patch) })), []);
  const clear = useCallback(() => { timers.current.forEach(clearTimeout); timers.current = []; clearInterval(iv.current); }, []);
  const wait = useCallback((fn: () => void, ms: number) => { timers.current.push(window.setTimeout(fn, ms)); }, []);
  useEffect(() => () => { clear(); clearTimeout(tt.current); }, [clear]);

  const toast = useCallback((m: string) => {
    set({ toast: m }); clearTimeout(tt.current);
    tt.current = window.setTimeout(() => set({ toast: "" }), 1800);
  }, [set]);

  /** 요청 시작 시점의 번호를 기억했다가, 응답이 왔을 때 그사이 화면을 떠났는지 확인한다. */
  const alive = (id: number) => id === req.current;

  // ── S1~S3 분석 ──────────────────────────────────────────────
  const analyze = useCallback(async (text: string, files: File[]) => {
    const id = ++req.current;
    clear();
    set({ p: 1, phase: 0, analysis: null, analysisError: "" });
    wait(() => set({ phase: 1 }), 3000);
    try {
      const a = await createAnalysis(text, files);
      if (!alive(id)) return;
      clear();
      set({ analysis: a, scen: a.reportable ? "A" : "B", selected: a.items.map((i) => i.type_id), p: 2 });
    } catch (e) {
      if (!alive(id)) return;
      clear();
      set({ analysisError: errorMessage(e) });
    }
  }, [clear, wait, set]);

  const send = useCallback(() => {
    const cur = sr.current;
    const text = cur.text.trim();
    if (!text && !cur.files.length) return;
    setS({ ...base(), helped: cur.helped, text: cur.text, files: cur.files, previews: cur.previews, sent: text || "이거 신고할 수 있나요?" });
    nav("/chat");
    void analyze(text, cur.files);
  }, [nav, analyze]);

  const retry = useCallback(() => { void analyze(sr.current.text.trim(), sr.current.files); }, [analyze]);

  const toggleItem = useCallback((t: TypeId) => set((prev) => ({
    selected: prev.selected.includes(t) ? prev.selected.filter((x) => x !== t) : [...prev.selected, t],
  })), [set]);

  const leave = useCallback(() => { req.current++; clear(); set({ timer: false, timerDone: false, creating: false }); }, [clear, set]);
  const goHome = useCallback(() => { leave(); nav("/report"); }, [leave, nav]);
  const toLanding = useCallback(() => { leave(); nav("/"); }, [leave, nav]);

  // ── 신고 건 진행 ────────────────────────────────────────────
  const labelOf = useCallback((t: TypeId) => {
    const it = sr.current.analysis?.items.find((i) => i.type_id === t);
    return { label: it?.label ?? t, category: it?.category ?? ("report" as Category) };
  }, []);

  const reloadEvidence = useCallback(async () => {
    const r = sr.current.reports[sr.current.cur];
    if (!r) return;
    const id = req.current;
    set({ evError: "" });
    try {
      const ev = await getEvidence(r.id);
      if (alive(id)) set({ evidence: ev });
    } catch (e) {
      if (alive(id)) set({ evError: errorMessage(e) });
    }
  }, [set]);

  const runRehearsal = useCallback(async (photoId?: string) => {
    const r = sr.current.reports[sr.current.cur];
    if (!r) return;
    const id = req.current;
    set({ rhBusy: true, rhError: "", rhNeedsPhoto: false });
    try {
      const rh = await rehearse(r.id, photoId);
      if (alive(id)) set({ rehearsal: rh, rhBusy: false });
    } catch (e) {
      if (!alive(id)) return;
      // 422: 분석 때 사진 없이 글만 올린 경우. 점검용 사진을 받는다.
      set({ rhBusy: false, rhError: errorMessage(e), rhNeedsPhoto: e instanceof ApiError && e.status === 422 });
    }
  }, [set]);

  const enterReport = useCallback((i: number) => {
    const r = sr.current.reports[i];
    if (!r) return;
    const parking = r.type_id === "illegal_parking";
    set({
      cur: i, rstage: parking ? "rehearsal" : "evidence",
      evidence: null, evError: "", uploading: "", shots: {},
      rehearsal: null, rhBusy: false, rhError: "", rhNeedsPhoto: false,
      s7: 0, draft: 0, receipt: "",
    });
    // set이 반영된 다음 cur를 읽도록 참조를 먼저 맞춘다.
    sr.current = { ...sr.current, cur: i };
    // 글만 보낸 경우 사전 점검을 바로 부르지 않고(서버는 422), 이 단계에서 사진을 요청한다.
    const noPhoto = !sr.current.analysis?.input.photos.length;
    if (parking && noPhoto) set({ rhNeedsPhoto: true });
    else if (parking) void runRehearsal();
    else void reloadEvidence();
  }, [set, runRehearsal, reloadEvidence]);

  const n = s.selected.length;
  const startPrep = useCallback(async () => {
    const cur = sr.current;
    if (!cur.analysis || !cur.selected.length || cur.creating) return;
    const id = req.current;
    set({ creating: true });
    try {
      const r = await createReports(cur.analysis.id, cur.selected);
      if (!alive(id)) return;
      const reports = [...r.reports].sort((a, b) => a.sequence - b.sequence);
      set({ reports, creating: false, p: 3, finished: [] });
      sr.current = { ...sr.current, reports };
      enterReport(0);
    } catch (e) {
      if (!alive(id)) return;
      set({ creating: false });
      toast(errorMessage(e));
    }
  }, [set, toast, enterReport]);

  const shoot = useCallback(async (sceneId: string, file: File) => {
    const r = sr.current.reports[sr.current.cur];
    if (!r || sr.current.uploading) return;
    const id = req.current;
    const preview = URL.createObjectURL(file);
    set((prev) => ({ uploading: sceneId, shots: { ...prev.shots, [sceneId]: { preview, review: null } } }));
    try {
      const up = await uploadPhoto(r.id, file, sceneId);
      if (!alive(id)) return;
      set((prev) => ({ uploading: "", shots: { ...prev.shots, [sceneId]: { preview, review: up.review } } }));
      void reloadEvidence();
    } catch (e) {
      if (!alive(id)) return;
      set((prev) => {
        const shots = { ...prev.shots };
        delete shots[sceneId];
        return { uploading: "", shots };
      });
      toast(errorMessage(e));
    }
  }, [set, toast, reloadEvidence]);

  const rehearsalPhoto = useCallback(async (file: File) => {
    const r = sr.current.reports[sr.current.cur];
    if (!r || sr.current.rhBusy) return;
    const id = req.current;
    const preview = URL.createObjectURL(file);
    set((prev) => ({ rhBusy: true, rhError: "", rhNeedsPhoto: false, shots: { ...prev.shots, [REHEARSAL_SHOT]: { preview, review: null } } }));
    try {
      const up = await uploadPhoto(r.id, file);
      if (!alive(id)) return;
      await runRehearsal(up.photo.id);
    } catch (e) {
      if (!alive(id)) return;
      set({ rhBusy: false, rhError: errorMessage(e), rhNeedsPhoto: true });
    }
  }, [set, runRehearsal]);

  const toGuide = useCallback(() => set({ rstage: "guide", s7: 0, draft: 0, receipt: "" }), [set]);

  const finish = useCallback(() => { set({ p: 10 }); nav("/done"); }, [set, nav]);

  const completeReport = useCallback(() => {
    const cur = sr.current;
    const r = cur.reports[cur.cur];
    if (!r) return;
    const done: Finished = { id: r.id, ...labelOf(r.type_id), receipt: cur.receipt.trim() };
    set((prev) => ({ finished: [...prev.finished, done] }));
    if (cur.cur + 1 < cur.reports.length) set({ rstage: "next" });
    else finish();
  }, [set, labelOf, finish]);

  const nextReport = useCallback(() => enterReport(sr.current.cur + 1), [enterReport]);

  /** 사전 점검에서 금지구역이 아니라고 나온 건처럼 접수하지 않고 넘길 때 */
  const skipReport = useCallback(() => {
    const cur = sr.current;
    if (cur.cur + 1 < cur.reports.length) enterReport(cur.cur + 1);
    else if (cur.finished.length) finish();
    else goHome();
  }, [enterReport, finish, goHome]);

  const s7Next = useCallback(() => {
    const cur = sr.current;
    const step = SUBMIT_STEPS[cur.s7];
    if (step.msg) toast(step.msg);
    if (cur.s7 === 5) navigator.clipboard?.writeText(DRAFTS[cur.draft]).catch(() => {});
    if (cur.s7 < SUBMIT_STEPS.length - 1) set({ s7: cur.s7 + 1 });
    else completeReport();
  }, [set, toast, completeReport]);

  const startTimer = useCallback(() => {
    const total = sr.current.rehearsal?.capture_guide.interval_seconds || 60;
    set({ timer: true, sec: total, timerTotal: total, timerDone: false });
    clearInterval(iv.current);
    iv.current = window.setInterval(() => {
      setS((prev) => {
        if (prev.sec <= 1) { clearInterval(iv.current); try { navigator.vibrate?.(200); } catch { /* noop */ } return { ...prev, sec: 0, timerDone: true }; }
        return { ...prev, sec: prev.sec - 1 };
      });
    }, FAST ? 100 : 1000);
  }, [set]);
  const cancelTimer = useCallback(() => { clearInterval(iv.current); set({ timer: false }); }, [set]);
  const timerShot = useCallback(() => set({ timer: false, timerDone: false, rstage: "submit" }), [set]);

  /** S8에서 "나중에": 남은 건은 준비 중으로 둔다. 서버에 이미 preparing으로 저장돼 있다. */
  const later = useCallback(() => {
    const cur = sr.current;
    const next = cur.reports[cur.cur + 1];
    nav("/mine");
    if (next) toast(`${labelOf(next.type_id).label}은 준비 중으로 남겨 뒀어요`);
  }, [nav, toast, labelOf]);

  const openShare = useCallback((from: "done" | "detail") => { set({ shareFrom: from, agree: false }); nav("/share"); }, [set, nav]);
  const doShare = useCallback(() => { if (!sr.current.agree) return; nav("/cases"); toast("사례로 공유했어요"); }, [nav, toast]);
  const startFromCase = useCallback(() => {
    setS({ ...base(), helped: sr.current.helped, fromCase: true, text: "인도에 차가 올라와 있어요" });
    nav("/report");
  }, [nav]);

  const r = s.p === 3 ? s.reports[s.cur] : undefined;
  const current = useMemo(() => {
    if (!r) return null;
    const it = s.analysis?.items.find((i) => i.type_id === r.type_id);
    return { id: r.id, type_id: r.type_id, label: it?.label ?? r.type_id, category: it?.category ?? ("report" as Category) };
  }, [r, s.analysis]);

  const value = useMemo<Store>(() => ({
    s, set, toast, send, retry, toggleItem, goHome, toLanding, startPrep, current,
    reloadEvidence, shoot, toGuide, runRehearsal: () => void runRehearsal(), rehearsalPhoto, completeReport, nextReport, skipReport,
    s7Next, startTimer, cancelTimer, timerShot, later, openShare, doShare, startFromCase, n,
  }), [s, set, toast, send, retry, toggleItem, goHome, toLanding, startPrep, current, reloadEvidence, shoot, toGuide, runRehearsal,
    rehearsalPhoto, completeReport, nextReport, skipReport, s7Next, startTimer, cancelTimer, timerShot, later, openShare, doShare, startFromCase, n]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useStore must be used inside StoreProvider");
  return v;
}
