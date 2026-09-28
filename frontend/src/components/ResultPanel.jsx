import { useState } from "react";
import {
  ArrowUpRight,
  Building2,
  Check,
  ChevronDown,
  CircleCheck,
  Clock,
  Copy,
  FileText,
  MessageCircleQuestion,
  Reply,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { STEPS } from "../data";

// ---- styles

const PRIORITY_STYLES = {
  Low: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20",
  Medium: "bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20",
  High: "bg-orange-50 text-orange-700 ring-orange-600/20 dark:bg-orange-500/10 dark:text-orange-300 dark:ring-orange-400/20",
  Critical: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-400/20",
};

const ACTIONS = {
  Escalate: {
    icon: ArrowUpRight,
    style: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-400/20",
    help: "Needs a specialist or senior agent now.",
  },
  Respond: {
    icon: Reply,
    style: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20",
    help: "An agent can answer this directly.",
  },
  "Request more info": {
    icon: MessageCircleQuestion,
    style: "bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20",
    help: "Ask the customer what they need first.",
  },
};

// ---- building blocks

function Badge({ className, children }) {
  return (
    <span className={"inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-semibold ring-1 ring-inset " + className}>
      {children}
    </span>
  );
}

function Tile({ label, children, help }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <div className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-2">{children}</div>
      {help ? <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{help}</div> : null}
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <h3 className="text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">{children}</h3>
  );
}

function prettySource(filename) {
  // "duplicate_charges.md" -> "Duplicate charges"
  let words = filename.replace(".md", "").replace(/_/g, " ");
  words = words.replace(/\batm\b/g, "ATM");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// ---- pipeline steps

export function PipelineSteps({ activeStep, isDone }) {
  return (
    <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {STEPS.map(function (step, index) {
        const Icon = step.icon;
        const done = isDone || index < activeStep;
        const active = !isDone && index === activeStep;

        let style = "border-slate-200 text-slate-400 dark:border-slate-800 dark:text-slate-500";
        if (active) {
          style = "border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-500/40 dark:bg-indigo-500/10 dark:text-indigo-300";
        } else if (done) {
          style = "border-slate-200 text-slate-700 dark:border-slate-800 dark:text-slate-200";
        }

        return (
          <li key={step.title} className={"rounded-xl border px-3 py-2.5 transition-colors " + style}>
            <div className="flex items-center gap-2 text-sm font-semibold">
              {done ? (
                <CircleCheck className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              ) : (
                <Icon className={"h-4 w-4" + (active ? " animate-pulse" : "")} aria-hidden="true" />
              )}
              {step.title}
            </div>
            <div className="mt-0.5 text-xs opacity-80">{step.detail}</div>
          </li>
        );
      })}
    </ol>
  );
}

// ---- reply with citations

function ReplyCard({ text }) {
  const [copied, setCopied] = useState(false);

  // "…within 24 hours [duplicate_charges.md]." -> text and citation parts
  const parts = text.split(/(\[[a-z0-9_]+\.md\])/g);
  const plainText = text.replace(/\s*\[[a-z0-9_]+\.md\]/g, "");

  function copyReply() {
    navigator.clipboard.writeText(plainText).then(function () {
      setCopied(true);
      setTimeout(function () { setCopied(false); }, 1500);
    });
  }

  return (
    <div className="relative rounded-xl border border-slate-200 bg-slate-50 p-4 pr-12 text-[15px] leading-relaxed dark:border-slate-800 dark:bg-slate-950">
      {parts.map(function (part, index) {
        if (/^\[[a-z0-9_]+\.md\]$/.test(part)) {
          return (
            <span
              key={index}
              className="mx-0.5 inline-flex items-center gap-1 rounded-md bg-indigo-100 px-1.5 py-0.5 align-middle text-[11px] font-medium text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300"
              title={"Source: " + part.slice(1, -1)}
            >
              <FileText className="h-3 w-3" aria-hidden="true" />
              {prettySource(part.slice(1, -1))}
            </span>
          );
        }
        return <span key={index}>{part}</span>;
      })}
      <button
        type="button"
        onClick={copyReply}
        className="absolute top-3 right-3 rounded-lg p-1.5 text-slate-400 hover:bg-white hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        aria-label="Copy reply"
        title="Copy reply"
      >
        {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
      </button>
    </div>
  );
}

// ---- panel states

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">
        <Sparkles className="h-6 w-6" aria-hidden="true" />
      </div>
      <h3 className="mt-4 text-base font-semibold">Ready when you are</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-500 dark:text-slate-400">
        Pick an example or write your own message. You'll see the priority, the team it goes to,
        the next step, and a draft reply based on the bank's policies.
      </p>
    </div>
  );
}

function LoadingState({ slow }) {
  return (
    <div className="mt-6">
      {slow ? (
        <p className="mb-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
          Waking up the server… The free hosting sleeps when nobody is using it, so the first request
          can take up to a minute. Thanks for your patience.
        </p>
      ) : null}
      <LoadingSkeleton />
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4" aria-hidden="true">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="h-20 rounded-xl bg-slate-100 dark:bg-slate-800" />
        <div className="h-20 rounded-xl bg-slate-100 dark:bg-slate-800" />
        <div className="h-20 rounded-xl bg-slate-100 dark:bg-slate-800" />
      </div>
      <div className="h-4 w-1/3 rounded bg-slate-100 dark:bg-slate-800" />
      <div className="h-24 rounded-xl bg-slate-100 dark:bg-slate-800" />
    </div>
  );
}

function ErrorState({ message }) {
  return (
    <div className="mt-6 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}

function Result({ result, seconds }) {
  const action = ACTIONS[result.suggested_action] || ACTIONS.Respond;
  const ActionIcon = action.icon;
  const priorityStyle = PRIORITY_STYLES[result.priority] || PRIORITY_STYLES.Medium;

  return (
    <div className="mt-6 space-y-6">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Tile label="Priority">
          <Badge className={priorityStyle}>{result.priority}</Badge>
        </Tile>
        <Tile label="Next step" help={action.help}>
          <Badge className={action.style}>
            <ActionIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {result.suggested_action}
          </Badge>
        </Tile>
        <Tile label="Route to">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Building2 className="h-4 w-4 text-slate-400" aria-hidden="true" />
            {result.routing}
          </div>
        </Tile>
      </div>

      <div className="space-y-3">
        <SectionLabel>What the customer wants</SectionLabel>
        <div className="flex flex-wrap gap-2">
          {result.intents.map(function (intent) {
            return (
              <span key={intent} className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">
                {intent}
              </span>
            );
          })}
        </div>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
          <dt className="text-slate-500 dark:text-slate-400">Issue</dt>
          <dd className="font-medium">{result.issue_type}</dd>
          <dt className="text-slate-500 dark:text-slate-400">Details found</dt>
          <dd className="flex flex-wrap gap-1.5">
            {result.entities.length === 0 ? (
              <span className="text-slate-400">None</span>
            ) : (
              result.entities.map(function (entity) {
                return (
                  <span key={entity} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    {entity}
                  </span>
                );
              })
            )}
          </dd>
        </dl>
      </div>

      <div className="space-y-3">
        <SectionLabel>Suggested reply</SectionLabel>
        <ReplyCard text={result.response} />
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500 dark:text-slate-400">
          {result.sources.length === 0 ? (
            <span>No policy needed: the customer is asked for more details first.</span>
          ) : (
            <span className="flex flex-wrap items-center gap-2">
              Based on:
              {result.sources.map(function (source) {
                return (
                  <span key={source} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-0.5 dark:border-slate-700">
                    <FileText className="h-3 w-3" aria-hidden="true" />
                    {prettySource(source)}
                  </span>
                );
              })}
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {seconds.toFixed(1)} s
          </span>
        </div>
      </div>

      <details className="group rounded-xl border border-slate-200 dark:border-slate-800">
        <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium text-slate-600 dark:text-slate-300">
          View API response (JSON)
          <ChevronDown className="h-4 w-4 transition group-open:rotate-180" aria-hidden="true" />
        </summary>
        <pre className="overflow-x-auto border-t border-slate-200 px-4 py-3 text-xs leading-relaxed text-slate-700 dark:border-slate-800 dark:text-slate-300">
          {JSON.stringify(result, null, 2)}
        </pre>
      </details>
    </div>
  );
}

// ---- panel

export default function ResultPanel({ status, result, error, seconds, activeStep, slow }) {
  return (
    <section
      id="analysis"
      aria-labelledby="analysis-title"
      aria-live="polite"
      className="scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 dark:border-slate-800 dark:bg-slate-900"
    >
      <h2 id="analysis-title" className="mb-4 text-base font-semibold">Analysis</h2>
      <PipelineSteps activeStep={status === "loading" ? activeStep : -1} isDone={status === "done"} />

      {status === "idle" ? <EmptyState /> : null}
      {status === "loading" ? <LoadingState slow={slow} /> : null}
      {status === "error" ? <ErrorState message={error} /> : null}
      {status === "done" && result ? <Result result={result} seconds={seconds} /> : null}
    </section>
  );
}
