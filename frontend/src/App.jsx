import { useEffect, useRef, useState } from "react";
import { ArrowDown } from "lucide-react";
import { analyzeMessage, checkHealth } from "./api";
import { GITHUB_URL, STEPS } from "./data";
import Header from "./components/Header";
import Composer from "./components/Composer";
import ResultPanel from "./components/ResultPanel";
import HowItWorks from "./components/HowItWorks";

// On phones and small tablets the analysis panel is below the input form.
function scrollToAnalysisOnSmallScreens() {
  if (window.innerWidth < 1024) {
    document.getElementById("analysis").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

// Turn an API error into a sentence a visitor understands.
function errorText(status, data) {
  if (status === 429) {
    return data.detail || "Too many requests. Please wait a minute and try again.";
  }
  if (status === 422) {
    return "Please enter a message between 1 and 2000 characters.";
  }
  if (status === 0) {
    return "Could not reach the server. Check your connection and try again.";
  }
  return "The analysis service is temporarily unavailable. Please try again in a moment.";
}

export default function App() {
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [seconds, setSeconds] = useState(0);
  const [activeStep, setActiveStep] = useState(0);
  const [slow, setSlow] = useState(false);
  const [apiState, setApiState] = useState("checking"); // checking | waking | ready | down
  const [modelName, setModelName] = useState("");
  const stepTimer = useRef(null);

  // ---------------------------------------------------------------- wake the API on page load
  // The free server sleeps when idle. Pinging /health as soon as the page opens starts waking it,
  // so it is usually ready by the time the visitor has picked an example.
  useEffect(function () {
    let cancelled = false;
    const startedAt = Date.now();
    const wakingTimer = setTimeout(function () {
      if (!cancelled) { setApiState("waking"); }
    }, 2500);

    function tryHealth() {
      checkHealth()
        .then(function (info) {
          if (cancelled) { return; }
          clearTimeout(wakingTimer);
          setApiState("ready");
          if (info.model) { setModelName(info.model); }
        })
        .catch(function () {
          if (cancelled) { return; }
          if (Date.now() - startedAt < 120000) {
            setTimeout(tryHealth, 3000); // keep trying for up to 2 minutes
          } else {
            setApiState("down");
          }
        });
    }
    tryHealth();

    return function () {
      cancelled = true;
      clearTimeout(wakingTimer);
    };
  }, []);

  // ---------------------------------------------------------------- analysis
  async function runAnalysis(text) {
    const trimmed = text.trim();
    if (trimmed === "" || status === "loading") {
      return;
    }

    setStatus("loading");
    setError("");
    setSlow(false);
    setActiveStep(0);

    // The server does not report progress, so we step through the pipeline while waiting.
    clearInterval(stepTimer.current);
    stepTimer.current = setInterval(function () {
      setActiveStep(function (step) { return step < STEPS.length - 1 ? step + 1 : step; });
    }, 900);
    const slowTimer = setTimeout(function () { setSlow(true); }, 8000);

    // On phones the results are below the input: bring them into view.
    scrollToAnalysisOnSmallScreens();

    const startedAt = performance.now();
    let outcome;
    try {
      outcome = await analyzeMessage(trimmed);
    } catch {
      outcome = { ok: false, status: 0, data: {} };
    }
    clearInterval(stepTimer.current);
    clearTimeout(slowTimer);
    setSlow(false);
    setSeconds((performance.now() - startedAt) / 1000);

    if (outcome.ok) {
      setResult(outcome.data);
      setStatus("done");
      setApiState("ready");
    } else {
      setError(errorText(outcome.status, outcome.data));
      setStatus("error");
    }
    // Scroll again once the result is on screen (the layout height changed while loading).
    setTimeout(scrollToAnalysisOnSmallScreens, 50);
  }

  function pickExample(text) {
    setMessage(text);
    runAnalysis(text);
  }

  // ---------------------------------------------------------------- page
  return (
    <div id="top">
      <Header apiState={apiState} />

      <main className="mx-auto max-w-6xl px-5">
        {/* Hero */}
        <section className="pt-14 pb-10 sm:pt-20">
          <div className="max-w-3xl">
            <span className="inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300">
              AI for banking customer service
            </span>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              Turn customer messages into clear next steps.
            </h1>
            <p className="mt-5 text-lg text-pretty text-slate-600 dark:text-slate-400">
              Paste a message the way a customer would write it. In a few seconds you get what they want,
              how urgent it is, which team should handle it, and a reply drafted from the bank's own policies.
            </p>
            <a
              href="#how-it-works"
              className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
            >
              How it works
              <ArrowDown className="h-4 w-4" aria-hidden="true" />
            </a>
          </div>
        </section>

        {/* Demo */}
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[5fr_7fr]">
          <Composer
            message={message}
            setMessage={setMessage}
            onAnalyze={function () { runAnalysis(message); }}
            onPickExample={pickExample}
            isLoading={status === "loading"}
          />
          <ResultPanel
            status={status}
            result={result}
            error={error}
            seconds={seconds}
            activeStep={activeStep}
            slow={slow}
          />
        </div>

        <div className="py-24">
          <HowItWorks modelName={modelName} />
        </div>
      </main>

      <footer className="border-t border-slate-200 dark:border-slate-800">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between dark:text-slate-400">
          <p>Built by Waleed Abdellatif · PIO-TECH internship project</p>
          <p className="flex gap-4">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="hover:text-slate-900 dark:hover:text-white">GitHub</a>
            <a href={(import.meta.env.VITE_API_URL || "") + "/docs"} target="_blank" rel="noopener noreferrer" className="hover:text-slate-900 dark:hover:text-white">API docs</a>
          </p>
        </div>
      </footer>
    </div>
  );
}
