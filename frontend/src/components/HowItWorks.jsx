import { HOW_IT_WORKS, METRICS } from "../data";

export default function HowItWorks({ modelName }) {
  return (
    <section id="how-it-works" aria-labelledby="how-title" className="scroll-mt-24">
      <div className="max-w-2xl">
        <p className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">Under the hood</p>
        <h2 id="how-title" className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
          The model reads. The rules decide.
        </h2>
        <p className="mt-3 text-slate-600 dark:text-slate-400">
          Language models are good at understanding messy text, but business decisions should be
          predictable. So the work is split into four steps, each doing what it is best at.
        </p>
      </div>

      <ol className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {HOW_IT_WORKS.map(function (step, index) {
          const Icon = step.icon;
          return (
            <li key={step.title} className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white">
                  <Icon className="h-4.5 w-4.5" aria-hidden="true" />
                </span>
                <span className="text-xs font-semibold text-slate-400">Step {index + 1}</span>
              </div>
              <h3 className="mt-4 font-semibold">{step.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{step.text}</p>
            </li>
          );
        })}
      </ol>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h3 className="font-semibold">Evaluated on 60 hand-labeled customer messages</h3>
        <dl className="mt-5 grid grid-cols-2 gap-6 lg:grid-cols-4">
          {METRICS.map(function (metric) {
            return (
              <div key={metric.label}>
                <dt className="text-sm text-slate-500 dark:text-slate-400">{metric.label}</dt>
                <dd className="mt-1 text-3xl font-semibold tracking-tight">{metric.value}</dd>
              </div>
            );
          })}
        </dl>
        <p className="mt-5 text-xs text-slate-500 dark:text-slate-400">
          Measured with the local model (Qwen3.5-4B via Ollama), which keeps customer data on the bank's own
          servers. This public demo runs on {modelName ? <strong className="font-medium">{modelName}</strong> : "a hosted model"} for speed.
          The full evaluation report is on GitHub.
        </p>
      </div>
    </section>
  );
}
