import { ArrowRight, LoaderCircle, Lock } from "lucide-react";
import { EXAMPLES, MAX_LENGTH } from "../data";

function ExampleCard({ example, onPick, disabled }) {
  const Icon = example.icon;
  return (
    <button
      type="button"
      onClick={function () { onPick(example.text); }}
      disabled={disabled}
      className="group flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-sm disabled:pointer-events-none disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-indigo-500/50"
    >
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-300">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium">{example.title}</span>
        <span className="mt-0.5 line-clamp-1 text-xs text-slate-500 dark:text-slate-400">{example.text}</span>
      </span>
    </button>
  );
}

export default function Composer({ message, setMessage, onAnalyze, onPickExample, isLoading }) {
  const canSubmit = message.trim().length > 0 && !isLoading;

  function handleKeyDown(event) {
    // Cmd+Enter (Mac) or Ctrl+Enter (Windows) submits the message.
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey) && canSubmit) {
      onAnalyze();
    }
  }

  return (
    <section
      aria-labelledby="composer-title"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 dark:border-slate-800 dark:bg-slate-900"
    >
      <h2 id="composer-title" className="text-base font-semibold">Customer message</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Write it the way a customer would. Angry, messy or vague is fine.
      </p>

      <label htmlFor="message" className="sr-only">Customer message</label>
      <textarea
        id="message"
        value={message}
        onChange={function (event) { setMessage(event.target.value); }}
        onKeyDown={handleKeyDown}
        maxLength={MAX_LENGTH}
        rows={5}
        placeholder="e.g. There's a payment on my card from a website I've never used…"
        className="mt-4 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-[15px] leading-relaxed placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:focus:bg-slate-950"
      />

      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-xs text-slate-400">
          {message.length} / {MAX_LENGTH}
          <span className="hidden sm:inline"> · ⌘/Ctrl + Enter to send</span>
        </span>
        <button
          type="button"
          onClick={onAnalyze}
          disabled={!canSubmit}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 focus-visible:ring-4 focus-visible:ring-indigo-500/30 focus-visible:outline-none disabled:cursor-not-allowed disabled:bg-slate-300 dark:disabled:bg-slate-700 dark:disabled:text-slate-400"
        >
          {isLoading ? (
            <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : null}
          {isLoading ? "Analyzing…" : "Analyze message"}
          {isLoading ? null : <ArrowRight className="h-4 w-4" aria-hidden="true" />}
        </button>
      </div>

      <div className="mt-6">
        <h3 className="text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
          Or try an example
        </h3>
        <div className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {EXAMPLES.map(function (example) {
            return (
              <ExampleCard
                key={example.title}
                example={example}
                onPick={onPickExample}
                disabled={isLoading}
              />
            );
          })}
        </div>
      </div>

      <p className="mt-5 flex items-start gap-2 text-xs text-slate-500 dark:text-slate-400">
        <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        Demo for a fictional bank ("Nova Bank"). Please don't enter real personal or banking details;
        messages are processed by a third-party AI service.
      </p>
    </section>
  );
}
