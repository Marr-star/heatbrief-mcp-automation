import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUp,
  ArrowUpRight,
  Check,
  ChevronRight,
  Download,
  ExternalLink,
  FileText,
  History,
  Info,
  LayoutDashboard,
  Loader2,
  MessageCircle,
  Plus,
  RotateCcw,
  Search,
  ShieldCheck,
  Sun,
  TriangleAlert,
  X,
} from "lucide-react";
import { api, ApiError, downloadPdf, downloadText, setCsrf } from "./api";
import { RequestDetails } from "./components/RequestDetails";
import { demoTimeIssue } from "./demo";
import { comparisonSummary } from "./analysis";
import {
  ClientBriefing,
  ComparisonCards,
  displayDate,
  Evidence,
  Finding,
  RunTimeline,
  statusLabel,
} from "./components/Results";
import { SiteMap } from "./components/SiteMap";
import type {
  Bootstrap,
  Briefing,
  BriefingRequest,
  ChatMessage,
  ChatReply,
  Draft,
  HistoryItem,
  Run,
} from "./types";
import type { ReactNode } from "react";

const emptyDraft = (): Draft => ({
  question: "",
  client_name: "Acme Demo Events (fictional)",
  date: "",
  time: "",
  timezone: "",
  locations: [],
});
const requestDraft = (value: Draft): Draft => ({
  question: value.question,
  client_name: value.client_name,
  date: value.date,
  time: value.time.slice(0, 5),
  timezone: value.timezone,
  locations: value.locations,
});
const welcome =
  "Tell me which sites, date, time and timezone to compare. I’ll run the comparison directly and show both highest and lowest readings. You can also ask questions about the result.";
const message = (role: "assistant" | "user", content: string): ChatMessage => ({
  id: crypto.randomUUID(),
  role,
  content,
});
const statusTitle = (value: string) =>
  value === "approved_for_manual_send"
    ? "Approved"
    : value === "rejected"
      ? "Rejected"
      : "Awaiting review";

function Modal({
  title,
  onClose,
  children,
  className = "",
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${className}`}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
    >
      <div className="modal-heading">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          <X size={19} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
function ReviewDialog({
  decision,
  onClose,
  onSubmit,
  busy,
  error,
}: {
  decision: "approve" | "reject";
  onClose: () => void;
  onSubmit: (reviewer: string, key: string) => void;
  busy: boolean;
  error: string;
}) {
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  return (
    <Modal
      title={
        decision === "approve" ? "Review and approve" : "Record a rejection"
      }
      onClose={onClose}
    >
      <p className="modal-intro">
        {decision === "approve"
          ? "Confirm that you have reviewed the evidence and client draft. Approval records your decision for manual sending."
          : "Record your decision on this draft. A reviewed briefing is locked against further edits."}
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit(name, key);
        }}
        className="review-form"
      >
        <label>
          Your name
          <input
            autoFocus
            required
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Reviewer name"
            autoComplete="name"
          />
        </label>
        <label>
          Reviewer key
          <input
            type="password"
            required
            value={key}
            onChange={(event) => setKey(event.target.value)}
            placeholder="Enter the separate reviewer key"
            autoComplete="off"
          />
        </label>
        <p className="muted">
          Use the reviewer key configured by your workspace owner. It is
          separate from the automation credential.
        </p>
        {error ? (
          <p className="inline-error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="modal-actions">
          <button
            type="button"
            className="button button-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="button button-primary"
            disabled={busy || !name.trim() || !key.trim()}
          >
            {busy ? (
              <Loader2 size={15} className="spin" />
            ) : (
              <ShieldCheck size={15} />
            )}{" "}
            {decision === "approve" ? "Record approval" : "Record rejection"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default function App() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [bootError, setBootError] = useState("");
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [result, setResult] = useState<Briefing | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    message("assistant", welcome),
  ]);
  const [input, setInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [pendingAction, setPendingAction] = useState<
    "none" | "run" | "prepare"
  >("none");
  const [run, setRun] = useState<Run | null>(null);
  const [lastRequest, setLastRequest] = useState<BriefingRequest | null>(null);
  const [tab, setTab] = useState<"overview" | "evidence" | "client">(
    "overview",
  );
  const [selectedSite, setSelectedSite] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<"assistant" | "results">(
    "results",
  );
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [aboutOpen, setAboutOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<
    "approve" | "reject" | null
  >(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const messageList = useRef<HTMLDivElement>(null);
  const busy = run?.state === "queued" || run?.state === "running";
  const timeIssue =
    boot?.data_mode === "mock"
      ? demoTimeIssue(draft, boot.demo_coverage)
      : null;
  const ready =
    !timeIssue &&
    draft.question.trim().length >= 10 &&
    draft.locations.length >= 2 &&
    Boolean(draft.date && draft.time && draft.timezone);
  useEffect(() => {
    let disposed = false;
    api<Bootstrap>("/bootstrap")
      .then((data) => {
        if (disposed) return;
        setCsrf(data.csrf);
        setBoot(data);
        setHistory(data.history);
        if (data.latest) {
          setResult(data.latest);
          setDraft({
            ...requestDraft(data.latest.request),
            time: data.latest.request.time.slice(0, 5),
          });
          setFollowUp(data.latest.follow_up_draft);
          setMessages([
            message(
              "assistant",
              `Your latest saved briefing is ready. ${comparisonSummary(data.latest)} These are fictional demo readings. Ask for a new comparison or a detail about this result.`,
            ),
          ]);
        }
        if (data.latest_run) {
          setRun(data.latest_run);
          setLastRequest(data.latest_run.request);
          if (data.latest_run.state !== "completed") {
            setResult(null);
            setDraft({
              ...requestDraft(data.latest_run.request),
              time: data.latest_run.request.time.slice(0, 5),
            });
          }
        }
      })
      .catch((error) => {
        if (!disposed) setBootError(error.message);
      });
    return () => {
      disposed = true;
    };
  }, []);
  useEffect(() => {
    if (messageList.current)
      messageList.current.scrollTop = messageList.current.scrollHeight;
  }, [messages, chatBusy]);
  useEffect(() => {
    if (!run || !["queued", "running"].includes(run.state)) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await api<Run>("/runs/" + encodeURIComponent(run!.id));
        if (stopped) return;
        setRun(next);
        if (next.state === "completed" && next.result) {
          setResult(next.result);
          setFollowUp(next.result.follow_up_draft);
          setTab("overview");
          setMessages((previous) => [
            ...previous,
            message(
              "assistant",
              `${comparisonSummary(next.result!)} ${next.result!.replayed ? "I reused the saved briefing for this identical request." : "The report and follow-up draft are saved."} These are fictional demo readings. Ask me about either extreme, the average or the ranking.`,
            ),
          ]);
          setHistory(await api<HistoryItem[]>("/history"));
          return;
        }
        if (next.state === "failed") {
          setMessages((previous) => [
            ...previous,
            message(
              "assistant",
              next.error?.message || "The request could not be completed.",
            ),
          ]);
          return;
        }
        timer = setTimeout(poll, 650);
      } catch (error) {
        if (!stopped) {
          setToast(
            error instanceof Error
              ? error.message
              : "Cannot read the workflow status",
          );
          timer = setTimeout(poll, 2000);
        }
      }
    }
    timer = setTimeout(poll, 250);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [run?.id, run?.state]);

  async function sendChat(
    text: string,
    base: Draft = draft,
    briefingId: string | null = result?.request_id || null,
  ) {
    if (!text.trim() || chatBusy || busy) return;
    setMessages((previous) => [...previous, message("user", text.trim())]);
    setInput("");
    setChatBusy(true);
    try {
      const response = await api<ChatReply>("/chat", {
        method: "POST",
        body: JSON.stringify({
          message: text.trim(),
          draft: requestDraft(base),
          briefing_id: briefingId,
          pending_action: pendingAction,
          message_id: crypto.randomUUID(),
        }),
      });
      setDraft(response.draft);
      setPendingAction(response.pending_action);
      if (response.run) {
        setRun(response.run);
        setLastRequest(response.run.request);
        setResult(response.run.result || null);
        setFollowUp(response.run.result?.follow_up_draft || "");
        setTab("overview");
        setSelectedSite(null);
        // Keep chat in view; the completed answer arrives here automatically.
        setMobileView("assistant");
      }
      setMessages((previous) => [
        ...previous,
        message("assistant", response.message),
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        message(
          "assistant",
          error instanceof Error
            ? error.message
            : "Please use Request details to continue.",
        ),
      ]);
    } finally {
      setChatBusy(false);
    }
  }
  function newBriefing() {
    if (busy) return;
    setDraft(emptyDraft());
    setPendingAction("none");
    setResult(null);
    setRun(null);
    setLastRequest(null);
    setFollowUp("");
    setSelectedSite(null);
    setTab("overview");
    setMobileView("assistant");
    setMessages([message("assistant", welcome)]);
    setInput("");
  }
  function applyDemoTime(value: Pick<Draft, "date" | "time" | "timezone">) {
    setDraft((previous) => ({
      ...previous,
      date: value.date,
      time: value.time,
      timezone: value.timezone,
    }));
    setRun(null);
    setLastRequest(null);
    setToast("");
  }
  function loadDemo(complete = true) {
    if (!boot || busy || chatBusy) return;
    const next: Draft = {
      ...emptyDraft(),
      question:
        "Compare the highest and lowest temperatures across these three locations for our site visit",
      locations: boot.catalog,
      ...(complete ? boot.fixture : {}),
    };
    setResult(null);
    setRun(null);
    setLastRequest(null);
    setDraft(next);
    setPendingAction("none");
    setTab("overview");
    setMobileView("assistant");
    setSelectedSite(null);
    setMessages([message("assistant", welcome)]);
    void sendChat(
      complete
        ? "Compare the three demo sites for our site visit on 2025-09-20 at 14:00 America/Phoenix."
        : "Compare the three demo sites for our site visit.",
      next,
      null,
    );
  }
  async function startRun(requestOverride?: BriefingRequest) {
    if (busy) return;
    const request = requestOverride || {
      ...draft,
      request_id: "web-" + crypto.randomUUID().replaceAll("-", "").slice(0, 18),
    };
    setLastRequest(request);
    setToast("");
    try {
      const response = await api<Run>("/runs", {
        method: "POST",
        body: JSON.stringify(request),
      });
      setRun(response);
      setResult(null);
      setFollowUp("");
      setTab("overview");
      setMobileView("results");
    } catch (error) {
      setToast(
        error instanceof ApiError && error.details
          ? error.message +
              ": " +
              error.details.map((item) => item.message).join("; ")
          : error instanceof Error
            ? error.message
            : "Unable to start the workflow",
      );
    }
  }
  async function selectHistory(item: HistoryItem) {
    try {
      const saved = await api<Briefing>(
        "/briefings/" + encodeURIComponent(item.request_id),
      );
      setResult(saved);
      setDraft(requestDraft(saved.request));
      setFollowUp(saved.follow_up_draft);
      setRun(null);
      setLastRequest(saved.request);
      setSelectedSite(null);
      setHistoryOpen(false);
      setTab("overview");
      setMessages([
        message(
          "assistant",
          "This is a saved briefing. Its original coordinates, requested time and evidence are available below. You can review it or replay the identical request. Replays reuse the saved report.",
        ),
      ]);
    } catch (error) {
      setToast(
        error instanceof Error ? error.message : "Unable to open briefing",
      );
    }
  }
  async function saveDraft() {
    if (!result) return;
    setSaving(true);
    try {
      const saved = await api<Briefing>(
        "/briefings/" + encodeURIComponent(result.request_id) + "/draft",
        { method: "POST", body: JSON.stringify({ content: followUp }) },
      );
      setResult(saved);
      setToast("Follow-up draft saved.");
    } catch (error) {
      setToast(
        error instanceof Error ? error.message : "Draft could not be saved",
      );
    } finally {
      setSaving(false);
    }
  }
  async function review(reviewer: string, key: string) {
    if (!result || !reviewDecision) return;
    setReviewBusy(true);
    setReviewError("");
    try {
      const saved = await api<Briefing>(
        "/briefings/" + encodeURIComponent(result.request_id) + "/review",
        {
          method: "POST",
          headers: {
            Authorization: key.startsWith("Bearer ") ? key : "Bearer " + key,
          },
          body: JSON.stringify({ decision: reviewDecision, reviewer }),
        },
      );
      setResult(saved);
      setFollowUp(saved.follow_up_draft);
      setReviewDecision(null);
      setHistory(await api<HistoryItem[]>("/history"));
      setToast("Review decision recorded.");
    } catch (error) {
      setReviewError(
        error instanceof Error ? error.message : "Review could not be recorded",
      );
    } finally {
      setReviewBusy(false);
    }
  }
  async function pdf() {
    if (!result) return;
    setDownloading(true);
    try {
      await downloadPdf(result.request_id);
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  if (!boot)
    return (
      <div className="boot-screen">
        <div className="brand-mark">
          <Sun size={30} />
        </div>
        <h1>HeatBrief</h1>
        {bootError ? (
          <>
            <p role="alert">{bootError}</p>
            <button
              className="button button-primary"
              onClick={() => location.reload()}
            >
              Try again
            </button>
          </>
        ) : (
          <p>
            <Loader2 size={17} className="spin" /> Opening your briefing
            workspace…
          </p>
        )}
      </div>
    );
  const sites = result?.request.locations || draft.locations;
  const measurements = result?.measurements || [];
  const lowest = result?.comparison.lowest_locations || [];
  const filteredHistory = history.filter((item) =>
    (item.question + " " + item.client_name + " " + item.request_id)
      .toLowerCase()
      .includes(search.toLowerCase()),
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand-mark" href="/" aria-label="HeatBrief home">
          <Sun size={27} />
        </a>
        <div className="sidebar-divider" />
        <nav aria-label="Workspace navigation">
          <button
            className="nav-icon active"
            aria-label="Briefing workspace"
            title="Briefing workspace"
            onClick={() => setTab("overview")}
          >
            <LayoutDashboard size={21} />
          </button>
          <button
            className="nav-icon"
            aria-label="Saved briefings"
            title="Saved briefings"
            onClick={() => setHistoryOpen(true)}
          >
            <History size={21} />
          </button>
          <button
            className="nav-icon"
            aria-label="Client briefing"
            title="Client briefing"
            onClick={() =>
              result
                ? setTab("client")
                : setToast("Run a comparison to prepare a client briefing.")
            }
          >
            <FileText size={21} />
          </button>
        </nav>
        <div className="sidebar-bottom">
          <button
            className="nav-icon"
            aria-label="About the demo"
            title="About the demo"
            onClick={() => setAboutOpen(true)}
          >
            <Info size={21} />
          </button>
          <span className="workspace-avatar" title="Local workspace">
            HB
          </span>
        </div>
      </aside>
      <div className="workspace-shell">
        <header className="topbar">
          <a className="wordmark" href="/">
            HeatBrief<span className="wordmark-dot">.</span>
          </a>
          <span className="topbar-separator" />
          <span className="topbar-label">Briefing workspace</span>
          <div className="topbar-actions">
            <span
              className={`connection-label ${boot.automation_connected ? "connected" : ""}`}
            >
              <span className="status-dot" />
              {boot.automation_connected
                ? "Automation connected"
                : "Automation unavailable"}
            </span>
            <button
              className="tag tag-amber mock-badge"
              onClick={() => setAboutOpen(true)}
            >
              <span /> Mock data
            </button>
            <button
              className="icon-button"
              aria-label="Open briefing history"
              onClick={() => setHistoryOpen(true)}
            >
              <History size={19} />
            </button>
          </div>
        </header>
        <main className="workspace-main">
          <div className="workspace-heading">
            <div>
              <p className="eyebrow">A LITTLE CLARITY GOES A LONG WAY</p>
              <h1>
                Your next decision, <em>better informed.</em>
              </h1>
              <p>
                Compare places. Follow the evidence. Prepare the next
                conversation.
              </p>
            </div>
            <button
              className="button button-primary new-briefing"
              disabled={busy}
              onClick={newBriefing}
            >
              <Plus size={16} /> New briefing
            </button>
          </div>
          <div className="mobile-view-tabs" aria-label="Workspace panels">
            <button
              className={mobileView === "assistant" ? "selected" : ""}
              onClick={() => setMobileView("assistant")}
            >
              <MessageCircle size={15} /> Ask & plan
            </button>
            <button
              className={mobileView === "results" ? "selected" : ""}
              onClick={() => setMobileView("results")}
            >
              <FileText size={15} /> Your briefing
            </button>
          </div>
          <div className={`workspace-grid mobile-show-${mobileView}`}>
            <section className="analyst-panel" aria-label="Briefing assistant">
              <div className="analyst-heading">
                <span className="assistant-avatar">
                  <Sun size={21} />
                </span>
                <div>
                  <h2>Ask HeatBrief</h2>
                  <p>
                    <span className="status-dot" />
                    {boot.assistant_mode === "ai"
                      ? "AI intake assistant"
                      : "Guided demo assistant"}
                  </p>
                </div>
                <MessageCircle size={19} />
              </div>
              <div
                className="conversation"
                ref={messageList}
                role="log"
                aria-label="Conversation"
              >
                {messages.map((item) => (
                  <div className={`chat-message ${item.role}`} key={item.id}>
                    {item.role === "assistant" ? (
                      <span className="chat-avatar">
                        <Sun size={14} />
                      </span>
                    ) : null}
                    <div>{item.content}</div>
                  </div>
                ))}
                {chatBusy ? (
                  <div className="chat-message assistant">
                    <span className="chat-avatar">
                      <Sun size={14} />
                    </span>
                    <div
                      className="typing-indicator"
                      aria-label="Assistant is preparing a reply"
                    >
                      <i />
                      <i />
                      <i />
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="prompt-chips">
                <button
                  onClick={() => loadDemo(true)}
                  disabled={busy || chatBusy}
                >
                  <Sun size={13} /> Run the demo
                </button>
                <button
                  onClick={() => loadDemo(false)}
                  disabled={busy || chatBusy}
                >
                  Clarify a request
                  <ArrowUpRight size={12} />
                </button>
              </div>
              <form
                className="chat-composer"
                onSubmit={(event) => {
                  event.preventDefault();
                  void sendChat(input);
                }}
              >
                <label className="sr-only" htmlFor="chat-message">
                  Ask HeatBrief
                </label>
                <textarea
                  id="chat-message"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  maxLength={3000}
                  placeholder="What are you planning?"
                  rows={2}
                  disabled={chatBusy || busy}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void sendChat(input);
                    }
                  }}
                />
                <div>
                  <span>Shift + Enter for a new line</span>
                  <button
                    type="submit"
                    aria-label="Send message"
                    disabled={!input.trim() || chatBusy || busy}
                  >
                    {chatBusy ? (
                      <Loader2 size={17} className="spin" />
                    ) : (
                      <ArrowUp size={18} />
                    )}
                  </button>
                </div>
              </form>
              <RequestDetails
                draft={draft}
                catalog={boot.catalog}
                coverage={boot.demo_coverage}
                timeIssue={timeIssue}
                onUseDemoTime={() => applyDemoTime(boot.fixture)}
                onPreset={applyDemoTime}
                onChange={setDraft}
                disabled={Boolean(busy)}
              />
              <div className="run-button-area">
                <button
                  className="button button-primary run-button"
                  disabled={!ready || busy || chatBusy}
                  onClick={() => void startRun()}
                >
                  {busy ? (
                    <Loader2 size={17} className="spin" />
                  ) : (
                    <Activity size={17} />
                  )}{" "}
                  {busy ? "Preparing your briefing…" : "Run comparison"}
                  {!busy ? <ArrowRight size={16} /> : null}
                </button>
                <p>Runs the connected n8n workflow.</p>
              </div>
            </section>
            <section
              className="results-area"
              aria-label="Comparison and briefing"
            >
              <div className="results-toolbar">
                <div
                  className="results-tabs"
                  role="tablist"
                  aria-label="Briefing views"
                >
                  {(["overview", "evidence", "client"] as const).map(
                    (value) => (
                      <button
                        key={value}
                        role="tab"
                        aria-selected={tab === value}
                        className={tab === value ? "selected" : ""}
                        onClick={() => setTab(value)}
                      >
                        {value === "overview"
                          ? "Overview"
                          : value === "evidence"
                            ? "Evidence"
                            : "Client briefing"}
                        {value === "client" &&
                        result?.status === "draft_pending_review" ? (
                          <span className="tab-dot" />
                        ) : null}
                      </button>
                    ),
                  )}
                </div>
                {result ? (
                  <span
                    className={`review-status ${result.review ? "reviewed" : ""}`}
                  >
                    <span className="status-dot" />
                    {statusTitle(result.status)}
                  </span>
                ) : (
                  <span className="tag">New briefing</span>
                )}
              </div>
              <RunTimeline run={run} workflowUrl={boot.workflow_url} />
              {run?.state === "failed" ? (
                <div className="run-error" role="alert">
                  <TriangleAlert size={23} />
                  <div>
                    <strong>Let’s check that request.</strong>
                    <p>{run.error?.message}</p>
                    <button
                      className="text-button"
                      onClick={() => lastRequest && void startRun(lastRequest)}
                    >
                      <RotateCcw size={13} /> Retry the same request
                    </button>
                  </div>
                </div>
              ) : null}
              {tab === "overview" ? (
                <>
                  <SiteMap
                    sites={sites}
                    measurements={measurements}
                    lowest={lowest}
                    onSelect={setSelectedSite}
                    selected={selectedSite}
                  />
                  {result ? (
                    <>
                      <div className="results-meta">
                        <span>
                          {displayDate(result.request.date)} <i />{" "}
                          {result.request.time} {result.request.timezone}
                        </span>
                        <span>Temperature comparison</span>
                      </div>
                      <ComparisonCards
                        briefing={result}
                        onSelect={setSelectedSite}
                        selected={selectedSite}
                      />
                      <Finding briefing={result} />
                      <div className="briefing-ready">
                        <span className="document-icon">
                          <FileText size={23} />
                        </span>
                        <div>
                          <strong>
                            A client-ready draft, with a paper trail.
                          </strong>
                          <p>
                            {result.request.client_name} ·{" "}
                            {statusLabel(result.status)}
                          </p>
                        </div>
                        <button
                          className="button button-secondary"
                          onClick={() => setTab("client")}
                        >
                          Review briefing
                          <ArrowUpRight size={14} />
                        </button>
                      </div>
                      <div className="results-footer">
                        <span>
                          <ShieldCheck size={13} /> Every reading is traceable
                        </span>
                        <button
                          onClick={() => void startRun(result.request)}
                          disabled={busy}
                          className="text-button"
                        >
                          <RotateCcw size={12} /> Replay saved request
                        </button>
                      </div>
                    </>
                  ) : (
                    <div className="empty-results">
                      <div className="empty-sun">
                        <Sun size={28} />
                      </div>
                      <p className="eyebrow">START WITH A QUESTION</p>
                      <h2>
                        Good decisions begin
                        <br />
                        with a clearer picture.
                      </h2>
                      <p>
                        Choose your locations and requested time.
                        <br />
                        Your comparison, evidence and client draft will appear
                        here.
                      </p>
                      <button
                        className="button button-secondary"
                        onClick={() => loadDemo(true)}
                        disabled={busy || chatBusy}
                      >
                        Explore the demo
                        <ArrowRight size={14} />
                      </button>
                    </div>
                  )}
                </>
              ) : null}
              {tab === "evidence" ? (
                result ? (
                  <Evidence briefing={result} />
                ) : (
                  <div className="simple-empty">
                    <ShieldCheck size={35} />
                    <h2>The evidence goes here.</h2>
                    <p>
                      Run a comparison to inspect timestamps, coordinates, units
                      and source IDs.
                    </p>
                  </div>
                )
              ) : null}
              {tab === "client" ? (
                result ? (
                  <ClientBriefing
                    briefing={result}
                    draft={followUp}
                    setDraft={setFollowUp}
                    onSave={() => void saveDraft()}
                    saving={saving}
                    onReview={(decision) => {
                      setReviewDecision(decision);
                      setReviewError("");
                    }}
                    onDownload={() => void pdf()}
                    downloading={downloading}
                  />
                ) : (
                  <div className="simple-empty">
                    <FileText size={35} />
                    <h2>Your next conversation, prepared.</h2>
                    <p>
                      Complete a comparison to generate a report and follow-up
                      draft.
                    </p>
                  </div>
                )
              ) : null}
              {result && tab === "evidence" ? (
                <div className="evidence-download">
                  <button
                    className="button button-secondary"
                    onClick={() =>
                      downloadText(
                        result.report_markdown,
                        `heatbrief-${result.request_id}.md`,
                      )
                    }
                  >
                    <Download size={14} /> Download Markdown
                  </button>
                  <button
                    className="button button-primary"
                    onClick={() => void pdf()}
                    disabled={downloading}
                  >
                    {downloading ? (
                      <Loader2 size={14} className="spin" />
                    ) : (
                      <Download size={14} />
                    )}{" "}
                    Download PDF
                  </button>
                </div>
              ) : null}
            </section>
          </div>
          <footer className="page-footer">
            <span>
              HeatBrief · Thoughtful comparisons. Traceable briefings.
            </span>
            <button className="text-button" onClick={() => setAboutOpen(true)}>
              About this demo
              <ArrowUpRight size={12} />
            </button>
          </footer>
        </main>
      </div>
      {toast ? (
        <div className="toast" role="alert">
          <Info size={17} />
          <span>{toast}</span>
          <button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setToast("")}
          >
            <X size={15} />
          </button>
        </div>
      ) : null}
      {historyOpen ? (
        <Modal
          title="Your saved briefings"
          onClose={() => setHistoryOpen(false)}
          className="history-modal"
        >
          <p className="modal-intro">
            Previous comparisons and their original evidence, ready to revisit.
          </p>
          <label className="history-search">
            <Search size={17} />
            <input
              autoFocus
              aria-label="Search saved briefings"
              placeholder="Search a client, question or request ID"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <div className="history-list">
            {filteredHistory.length ? (
              filteredHistory.map((item) => (
                <button
                  className="history-item"
                  key={item.request_id}
                  onClick={() => void selectHistory(item)}
                  disabled={Boolean(busy)}
                >
                  <span className="document-icon">
                    <FileText size={20} />
                  </span>
                  <div>
                    <strong>{item.client_name}</strong>
                    <p>{item.question}</p>
                    <span>
                      {displayDate(item.date)} · {item.sites} sites ·{" "}
                      {statusTitle(item.status)}
                    </span>
                  </div>
                  <strong className="history-temp">
                    {item.lowest_c.toFixed(1)}°
                    {item.highest_c != null
                      ? `–${item.highest_c.toFixed(1)}°`
                      : ""}
                  </strong>
                  <ChevronRight size={16} />
                </button>
              ))
            ) : (
              <div className="simple-empty">
                <History size={30} />
                <p>No briefings found.</p>
              </div>
            )}
          </div>
        </Modal>
      ) : null}
      {aboutOpen ? (
        <Modal
          title="Built to show its work."
          onClose={() => setAboutOpen(false)}
        >
          <div className="about-icon">
            <Sun size={30} />
          </div>
          <p className="modal-intro">
            HeatBrief turns a location question into a temperature comparison
            and a client briefing, with the evidence kept in view.
          </p>
          <div className="about-facts">
            <div>
              <Check size={16} />
              <p>
                <strong>Real automation.</strong> Your requests run through the
                connected n8n workflow, Python calculations and SQLite history.
              </p>
            </div>
            <div>
              <Info size={16} />
              <p>
                <strong>Fictional measurements.</strong> The demo covers the
                three selected sites from {boot.demo_coverage.start_date} at{" "}
                {boot.demo_coverage.start_time} through{" "}
                {boot.demo_coverage.end_date} at {boot.demo_coverage.end_time}{" "}
                {boot.demo_coverage.timezone}, inclusive, every minute. Values
                are deterministic synthetic scenarios. Live FortyGuard is not
                connected.
              </p>
            </div>
            <div>
              <MessageCircle size={16} />
              <p>
                <strong>
                  {boot.assistant_mode === "ai"
                    ? "AI intake is enabled."
                    : "Guided intake is active."}
                </strong>{" "}
                {boot.assistant_mode === "ai"
                  ? "The configured model helps with request intake. Python determines every measurement and ranking."
                  : "No model key is needed. This mode extracts explicit request details and asks for missing inputs."}
              </p>
            </div>
            <div>
              <ShieldCheck size={16} />
              <p>
                <strong>A human makes the decision.</strong> Draft edits are
                saved before review. A separate reviewer key is needed to record
                approval or rejection.
              </p>
            </div>
          </div>
          <div className="modal-actions">
            <a
              className="button button-secondary"
              href={boot.workflow_url}
              target="_blank"
              rel="noreferrer"
            >
              Open n8n
              <ExternalLink size={14} />
            </a>
            <button
              className="button button-primary"
              onClick={() => setAboutOpen(false)}
            >
              Back to workspace
              <ArrowRight size={14} />
            </button>
          </div>
        </Modal>
      ) : null}
      {reviewDecision ? (
        <ReviewDialog
          decision={reviewDecision}
          busy={reviewBusy}
          error={reviewError}
          onClose={() => setReviewDecision(null)}
          onSubmit={(name, key) => void review(name, key)}
        />
      ) : null}
    </div>
  );
}
