/* 신고하기 흐름의 전역 스토어.
   - p: 0 입력 전 → 1 분석 중(S2) → 2 항목 선택(S3) → 3 신고 건 진행 → 10 완료(S9)
   - p === 3일 때 reports[cur] 한 건씩 서버의 sequence 순서로 진행한다. rstage가 그 건의 단계다.
       evidence   S4·S5 증거 체크리스트와 사진 검수 (쓰레기, 광고물, 시설물)
       rehearsal  S6 불법주정차 사전 점검과 본촬영 안내, 타이머
       guide      S7 접수 안내 (GET /guide). 불법주정차는 사진 단계에서 타이머를 돌린다
       next       S8 다음 항목 안내
   - API 호출은 화면을 떠나거나 새로 시작하면(req 증가) 늦게 온 응답을 버린다. */
import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { createAnalysis, createReports, getAnalysis, type Analysis, type Category, type ReportRef, type TypeId } from "../api/analyses";
import { getEvidence, getGuide, getReport, makeDraft, patchReport, rehearse, uploadPhoto, type Evidence, type Guide, type GuideStep, type Rehearsal, type SceneReview, type Tone } from "../api/reports";
import { ApiError, errorMessage } from "../api/client";

export type Scenario = "A" | "B";
export type ResultChoice = "수용" | "불수용" | "아직 모름";
export type ReportStage = "evidence" | "rehearsal" | "guide" | "next";

/** 이번 세션에 장면별로 마지막으로 올린 사진(미리보기)과 검수 결과. */
export interface Shot { preview: string; review: SceneReview | null }
export interface Finished { id: string; label: string; category: Category; receipt: string; to: string }

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
  /** 같은 분석에서 만든 신고 건 수. 이어서 하기로 들어오면 reports보다 클 수 있다 */
  total: number;
  evidence: Evidence | null; evError: string; uploading: string; shots: Record<string, Shot>;
  rehearsal: Rehearsal | null; rhBusy: boolean; rhError: string; rhNeedsPhoto: boolean;
  finished: Finished[];
  /** S7: 접수 안내, 지금 보는 단계(steps의 인덱스), 대필 문구 */
  guide: Guide | null; gIdx: number; gError: string; filing: boolean;
  draftText: string; draftTone: Tone; draftBusy: boolean; draftError: string;
  receipt: string;
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
  cur: 0, rstage: "evidence", total: 0, evidence: null, evError: "", uploading: "", shots: {},
  rehearsal: null, rhBusy: false, rhError: "", rhNeedsPhoto: false, finished: [],
  guide: null, gIdx: 0, gError: "", filing: false, draftText: "", draftTone: "default", draftBusy: false, draftError: "", receipt: "",
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
  loadGuide: () => void;
  gPrev: () => void;
  /** 지금 단계의 버튼 동작. 성공하면 다음 단계로 간다 */
  gAction: () => void;
  /** 지금 단계를 동작 없이 넘긴다(사진 저장을 직접 한 경우 등) */
  gNext: () => void;
  redraft: (t: Tone) => void;
  startTimer: () => void;
  cancelTimer: () => void;
  timerShot: () => void;
  later: () => void;
  openShare: (from: "done" | "detail") => void;
  doShare: () => void;
  startFromCase: () => void;
  /** 신고 조회나 S1에서 준비 중인 건을 이어서 한다 */
  resume: (reportId: string) => void;
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
      guide: null, gIdx: 0, gError: "", filing: false, draftText: "", draftTone: "default", draftBusy: false, draftError: "", receipt: "",
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
      set({ reports, total: r.total, creating: false, p: 3, finished: [] });
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


  // ── S7 접수 안내 ────────────────────────────────────────────
  const redraft = useCallback(async (tone: Tone) => {
    const r = sr.current.reports[sr.current.cur];
    if (!r || sr.current.draftBusy) return;
    const id = req.current;
    set({ draftBusy: true, draftError: "", draftTone: tone });
    try {
      const d = await makeDraft(r.id, tone);
      if (alive(id)) set({ draftText: d.text, draftBusy: false });
    } catch (e) {
      if (alive(id)) set({ draftBusy: false, draftError: errorMessage(e) });
    }
  }, [set]);

  const loadGuide = useCallback(async () => {
    const r = sr.current.reports[sr.current.cur];
    if (!r) return;
    const id = req.current;
    set({ rstage: "guide", guide: null, gError: "" });
    try {
      const g = await getGuide(r.id);
      if (!alive(id)) return;
      // 앞 건에서 끝낸 단계와, 이 건에서 이미 지난 단계는 건너뛴다.
      let gIdx = g.steps.findIndex((st) => !st.skipped && st.order > g.current_step);
      if (gIdx < 0) gIdx = g.steps.findIndex((st) => !st.skipped);
      set({ guide: g, gIdx: Math.max(gIdx, 0) });
      // 문구 대필은 몇 초 걸리므로 안내를 여는 즉시 미리 받아 둔다.
      const copy = g.steps.find((st) => st.action.kind === "copy_text");
      if (copy && !copy.action.text) void redraft("default");
      else if (copy?.action.text) set({ draftText: copy.action.text });
    } catch (e) {
      if (alive(id)) set({ gError: errorMessage(e) });
    }
  }, [set, redraft]);
  const toGuide = loadGuide;

  const finish = useCallback(() => { set({ p: 10 }); nav("/done"); }, [set, nav]);

  const completeReport = useCallback(() => {
    const cur = sr.current;
    const r = cur.reports[cur.cur];
    if (!r) return;
    const ch = cur.guide?.channel;
    const to = ch ? [ch.name, ch.menu_path[0]].filter(Boolean).join(" > ") : "안전신문고";
    const done: Finished = { id: r.id, ...labelOf(r.type_id), receipt: cur.receipt.trim(), to };
    set((prev) => ({ finished: [...prev.finished, done] }));
    if (cur.cur + 1 < cur.reports.length) set({ rstage: "next" });
    else finish();
  }, [set, labelOf, finish]);

  /** 건너뛰지 않은 단계 중 i 다음(dir=1) 또는 이전(dir=-1) 단계의 인덱스. 없으면 -1 */
  const stepFrom = (steps: GuideStep[], i: number, dir: 1 | -1) => {
    for (let j = i + dir; j >= 0 && j < steps.length; j += dir) if (!steps[j].skipped) return j;
    return -1;
  };

  const gNext = useCallback(() => {
    const cur = sr.current;
    const r = cur.reports[cur.cur];
    const g = cur.guide;
    if (!r || !g) return;
    const step = g.steps[cur.gIdx];
    // 진행 단계 저장. 실패해도 안내는 계속한다(다음 단계에서 다시 저장된다).
    patchReport(r.id, { current_step: step.order }).catch(() => {});
    const next = stepFrom(g.steps, cur.gIdx, 1);
    if (next >= 0) set({ gIdx: next });
    else completeReport();
  }, [set, completeReport]);

  const gPrev = useCallback(() => {
    const cur = sr.current;
    if (!cur.guide) return;
    const prev = stepFrom(cur.guide.steps, cur.gIdx, -1);
    if (prev >= 0) set({ gIdx: prev });
  }, [set]);

  const gAction = useCallback(async () => {
    const cur = sr.current;
    const r = cur.reports[cur.cur];
    const step = cur.guide?.steps[cur.gIdx];
    if (!r || !step) return;
    const a = step.action;
    if (a.kind === "open_link") {
      if (a.url) window.open(a.url, "_blank", "noopener");
      gNext();
    } else if (a.kind === "copy_text") {
      const text = cur.draftText || a.text || "";
      if (!text) return;
      try { await navigator.clipboard.writeText(text); toast("글을 복사했어요"); } catch { toast("글을 길게 눌러 복사해 주세요"); return; }
      gNext();
    } else if (a.kind === "save_photos") {
      const ok = await savePhotos(a.photos ?? []);
      if (ok === "saved") { toast("사진을 저장했어요"); gNext(); }
      else if (ok === "failed") toast("사진을 길게 눌러 저장한 뒤 \"직접 저장했어요\"를 눌러 주세요");
    } else if (a.kind === "submit") {
      if (cur.filing) return;
      const id = req.current;
      set({ filing: true });
      try {
        await patchReport(r.id, { status: "filed", current_step: step.order, receipt_number: cur.receipt.trim() || null });
        if (!alive(id)) return;
        set({ filing: false });
        completeReport();
      } catch (e) {
        if (!alive(id)) return;
        set({ filing: false });
        toast(errorMessage(e));
      }
    } else {
      gNext();
    }
  }, [set, toast, gNext, completeReport]);

  const nextReport = useCallback(() => enterReport(sr.current.cur + 1), [enterReport]);

  /** 사전 점검에서 금지구역이 아니라고 나온 건처럼 접수하지 않고 넘길 때 */
  const skipReport = useCallback(() => {
    const cur = sr.current;
    if (cur.cur + 1 < cur.reports.length) enterReport(cur.cur + 1);
    else if (cur.finished.length) finish();
    else goHome();
  }, [enterReport, finish, goHome]);

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
  // 불법주정차: 안내의 사진 단계에서 타이머를 마치면 다음 단계로 간다.
  const timerShot = useCallback(() => { set({ timer: false, timerDone: false }); gNext(); }, [set, gNext]);

  /** S8에서 "나중에": 남은 건은 준비 중으로 둔다. 서버에 이미 preparing으로 저장돼 있다. */
  const later = useCallback(() => {
    const cur = sr.current;
    const next = cur.reports[cur.cur + 1];
    nav("/mine");
    if (next) toast(`${labelOf(next.type_id).label}은 준비 중으로 남겨 뒀어요`);
  }, [nav, toast, labelOf]);

  const resume = useCallback(async (reportId: string) => {
    const id = ++req.current;
    clear();
    try {
      const first = await getReport(reportId);
      const a = await getAnalysis(first.analysis_id);
      // 이 건부터 같은 분석의 남은 건을 next_report_id로 따라간다.
      const chain = [first];
      for (let nx = first.next_report_id; nx && chain.length < 8; ) {
        const r = await getReport(nx);
        chain.push(r);
        nx = r.next_report_id;
      }
      if (!alive(id)) return;
      const reports = chain.map((r) => ({ id: r.id, type_id: r.type_id, sequence: r.sequence, status: r.status }));
      const next: FlowState = {
        ...base(), helped: sr.current.helped, analysis: a, scen: "A", p: 3, total: first.total,
        sent: a.input.text || "이거 신고할 수 있나요?", selected: reports.map((r) => r.type_id), reports,
      };
      setS(next);
      sr.current = next;
      nav("/chat");
      const done = first.evidence_progress.required > 0 && first.evidence_progress.done >= first.evidence_progress.required;
      // 증거를 다 모은 건은 접수 안내로 바로 간다(안내는 current_step 다음 단계부터 보여 준다).
      if (done && first.type_id === "illegal_parking") void loadGuide();
      else enterReport(0);
    } catch (e) {
      if (alive(id)) toast(errorMessage(e));
    }
  }, [clear, nav, toast, loadGuide, enterReport]);

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
    loadGuide, gPrev, gAction, gNext, redraft, startTimer, cancelTimer, timerShot, later, openShare, doShare, startFromCase, resume, n,
  }), [s, set, toast, send, retry, toggleItem, goHome, toLanding, startPrep, current, reloadEvidence, shoot, toGuide, runRehearsal,
    rehearsalPhoto, completeReport, nextReport, skipReport, loadGuide, gPrev, gAction, gNext, redraft, startTimer, cancelTimer, timerShot, later, openShare, doShare, startFromCase, resume, n]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/** 사진을 기기에 저장한다. 공유 시트(모바일)나 내려받기(PC)를 쓰고, 둘 다 안 되면 "failed".
 *  사용자가 공유 시트를 닫으면 "cancelled". */
async function savePhotos(photos: { id: string; url: string }[]): Promise<"saved" | "cancelled" | "failed"> {
  if (!photos.length) return "saved";
  try {
    const files = await Promise.all(photos.map(async (p, i) => {
      const res = await fetch(p.url);
      if (!res.ok) throw new Error(String(res.status));
      const blob = await res.blob();
      return new File([blob], `shingomate-${i + 1}.${blob.type.split("/")[1] || "jpg"}`, { type: blob.type || "image/jpeg" });
    }));
    if (navigator.canShare?.({ files })) {
      try {
        await navigator.share({ files });
        return "saved";
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return "cancelled";
        // 공유를 쓸 수 없으면(권한, 미지원 형식 등) 내려받기로 넘어간다.
      }
    }
    for (const f of files) {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(f);
      a.download = f.name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }
    return "saved";
  } catch (e) {
    return e instanceof DOMException && e.name === "AbortError" ? "cancelled" : "failed";
  }
}

export function useStore() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useStore must be used inside StoreProvider");
  return v;
}
