import { GITHUB_URL } from "../data";
import GitHubIcon from "./GitHubIcon";

// Small pill in the top bar that tells the visitor whether the API is ready.
function ApiStatus({ apiState }) {
  let dot = "bg-slate-400";
  let label = "Connecting…";
  if (apiState === "ready") {
    dot = "bg-emerald-500";
    label = "Online";
  } else if (apiState === "waking") {
    dot = "bg-amber-500 animate-pulse";
    label = "Waking up server…";
  } else if (apiState === "down") {
    dot = "bg-rose-500";
    label = "Offline";
  }

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
      <span className={"h-2 w-2 rounded-full " + dot} aria-hidden="true" />
      {label}
    </span>
  );
}

export default function Header({ apiState }) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-slate-50/80 backdrop-blur dark:border-slate-800/70 dark:bg-slate-950/80">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <a href="#top" className="flex items-center gap-2.5 font-semibold tracking-tight">
          <img src="/favicon.svg" alt="" className="h-7 w-7" />
          <span>Customer Intelligence</span>
        </a>
        <div className="flex items-center gap-3">
          <ApiStatus apiState={apiState} />
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 sm:inline-flex dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white"
          >
            <GitHubIcon className="h-4 w-4" />
            Source code
          </a>
        </div>
      </div>
    </header>
  );
}
