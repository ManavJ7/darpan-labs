"use client";

import { Fragment, useEffect, useState } from "react";
import { useStudyStore } from "@/store/studyStore";
import {
  listAvailableTwins,
  simulateTwins,
  listTwinSimulationResults,
  createValidationReport,
  getValidationReport,
  type AvailableTwin,
  type TwinSimulationResult,
  type SimulationJobItem,
  type ValidationReportDetail,
} from "@/lib/studyApi";

type Tab = "twins" | "results";

export default function SimulationView() {
  const { study } = useStudyStore();
  const [tab, setTab] = useState<Tab>("twins");
  const [twins, setTwins] = useState<AvailableTwin[]>([]);
  const [results, setResults] = useState<TwinSimulationResult[]>([]);
  const [selectedTwins, setSelectedTwins] = useState<Set<string>>(new Set());
  const [simulating, setSimulating] = useState(false);
  const [simJobs, setSimJobs] = useState<SimulationJobItem[]>([]);
  const [expandedTwin, setExpandedTwin] = useState<string | null>(null);
  const [validationStatus, setValidationStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const studyId = study?.id;

  useEffect(() => {
    if (!studyId) return;
    setLoading(true);
    Promise.all([
      listAvailableTwins(studyId).catch(() => []),
      listTwinSimulationResults(studyId).catch(() => []),
    ]).then(([t, r]) => {
      setTwins(t);
      setResults(r);
      if (r.length > 0) setTab("results");
      setLoading(false);
    });
  }, [studyId]);

  if (!study) return null;

  const isComplete =
    study.status === "complete" || study.status === "step_4_locked";
  if (!isComplete) {
    return (
      <div className="rounded-lg border border-darpan-border bg-darpan-surface p-6 text-center text-gray-400">
        Complete all 4 steps to run twin simulations.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-darpan-border bg-darpan-surface p-6 text-center text-gray-400">
        Loading twin data...
      </div>
    );
  }

  const completedResults = results.filter((r) => r.status === "completed");

  const toggleTwin = (id: string) => {
    const next = new Set(selectedTwins);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedTwins(next);
  };

  const selectAll = () => {
    if (selectedTwins.size === twins.length) setSelectedTwins(new Set());
    else setSelectedTwins(new Set(twins.map((t) => t.twin_id)));
  };

  const handleSimulate = async () => {
    if (!studyId || selectedTwins.size === 0) return;
    setSimulating(true);
    try {
      const res = await simulateTwins(studyId, Array.from(selectedTwins));
      setSimJobs(res.jobs);
      setTimeout(async () => {
        const r = await listTwinSimulationResults(studyId);
        setResults(r);
        setSimulating(false);
        setTab("results");
      }, 3000);
    } catch {
      setSimulating(false);
    }
  };

  const handleOpenDashboard = async (mode: "synthesis" | "comparison") => {
    if (!studyId) return;
    setValidationStatus(`Running ${mode} validation...`);
    try {
      const res = await createValidationReport(studyId, mode);
      // Poll until done
      const poll = setInterval(async () => {
        const report = await getValidationReport(studyId, res.report_id);
        if (report.status === "completed") {
          clearInterval(poll);
          setValidationStatus(null);
          // Open the validation dashboard in a new tab
          window.open("http://localhost:5173", "_blank");
        } else if (report.status === "failed") {
          clearInterval(poll);
          setValidationStatus("Validation failed. Check server logs.");
        } else {
          setValidationStatus(`Validation running... (${report.status})`);
        }
      }, 2000);
    } catch (e) {
      setValidationStatus(`Error: ${(e as Error).message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-gray-900 p-1">
        {(
          [
            ["twins", `Available Twins (${twins.length})`],
            ["results", `Simulation Results (${completedResults.length})`],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
              tab === key
                ? "bg-darpan-lime/20 text-darpan-lime"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Validation Dashboard buttons — always visible when results exist */}
      {completedResults.length > 0 && (
        <div className="rounded-lg border border-lime-800/50 bg-lime-950/20 p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">
                Validation Dashboard
              </h3>
              <p className="text-sm text-gray-400 mt-1">
                Generate the full validation report with radar charts, heatmaps,
                tier analysis, TURF, and individual twin accuracy — then open the
                dashboard.
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0 ml-6">
              <button
                onClick={() => handleOpenDashboard("synthesis")}
                disabled={!!validationStatus}
                className="rounded-md bg-darpan-lime px-5 py-2.5 text-sm font-semibold text-black hover:bg-lime-400 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Synthesis Report
              </button>
              <button
                onClick={() => handleOpenDashboard("comparison")}
                disabled={!!validationStatus}
                className="rounded-md bg-cyan-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-cyan-500 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Comparison (Real vs Twin)
              </button>
            </div>
          </div>
          {validationStatus && (
            <div className="mt-3 flex items-center gap-2 text-sm text-yellow-400">
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
              {validationStatus}
            </div>
          )}
        </div>
      )}

      {/* Tab: Available Twins */}
      {tab === "twins" && (
        <div className="rounded-lg border border-darpan-border bg-darpan-surface overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-darpan-border">
            <div>
              <h3 className="text-lg font-semibold text-white">
                Digital Twins
              </h3>
              <p className="text-sm text-gray-400">
                {twins.length} twins ready for simulation
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={selectAll}
                className="rounded-md bg-gray-800 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700 transition"
              >
                {selectedTwins.size === twins.length
                  ? "Deselect All"
                  : "Select All"}
              </button>
              <button
                onClick={handleSimulate}
                disabled={selectedTwins.size === 0 || simulating}
                className="rounded-md bg-darpan-lime px-4 py-1.5 text-sm font-semibold text-black hover:bg-lime-400 transition disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {simulating
                  ? "Simulating..."
                  : `Simulate ${selectedTwins.size} Twin${selectedTwins.size !== 1 ? "s" : ""}`}
              </button>
            </div>
          </div>

          {simJobs.length > 0 && (
            <div className="px-4 py-3 bg-gray-900/50 border-b border-darpan-border">
              <p className="text-sm text-gray-400 mb-2">Simulation status:</p>
              <div className="flex flex-wrap gap-2">
                {simJobs.map((j) => (
                  <span
                    key={j.twin_external_id}
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                      j.status === "already_completed"
                        ? "bg-green-900/30 text-green-400"
                        : j.status === "already_running"
                          ? "bg-yellow-900/30 text-yellow-400"
                          : "bg-blue-900/30 text-blue-400"
                    }`}
                  >
                    {j.twin_external_id}: {j.status}
                  </span>
                ))}
              </div>
            </div>
          )}

          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-darpan-border bg-gray-900/50">
                <th className="px-4 py-3 text-left w-10">
                  <input
                    type="checkbox"
                    checked={
                      selectedTwins.size === twins.length && twins.length > 0
                    }
                    onChange={selectAll}
                    className="accent-lime-500"
                  />
                </th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium">
                  Twin
                </th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium">
                  Participant
                </th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium">
                  Mode
                </th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">
                  Coherence
                </th>
                <th className="px-4 py-3 text-center text-gray-400 font-medium">
                  Simulated
                </th>
              </tr>
            </thead>
            <tbody>
              {twins.map((t) => {
                const hasResult = completedResults.some(
                  (r) =>
                    r.twin_id === t.twin_id ||
                    r.twin_external_id === t.twin_external_id,
                );
                return (
                  <tr
                    key={t.twin_id}
                    className="border-b border-darpan-border/50 hover:bg-gray-800/30"
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedTwins.has(t.twin_id)}
                        onChange={() => toggleTwin(t.twin_id)}
                        className="accent-lime-500"
                      />
                    </td>
                    <td className="px-4 py-3 font-mono text-lime-400">
                      {t.twin_external_id}
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {t.participant_name || t.participant_external_id}
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-400">
                        {t.mode}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-300">
                      {t.coherence_score != null
                        ? t.coherence_score.toFixed(2)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {hasResult ? (
                        <span className="text-green-400 text-xs font-medium">
                          Done
                        </span>
                      ) : (
                        <span className="text-gray-500 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Simulation Results */}
      {tab === "results" && (
        <div className="rounded-lg border border-darpan-border bg-darpan-surface overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-darpan-border">
            <div>
              <h3 className="text-lg font-semibold text-white">
                Simulation Results
              </h3>
              <p className="text-sm text-gray-400">
                {completedResults.length} completed simulations
              </p>
            </div>
            <button
              onClick={async () => {
                const r = await listTwinSimulationResults(studyId!);
                setResults(r);
              }}
              className="rounded-md bg-gray-800 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700 transition"
            >
              Refresh
            </button>
          </div>

          {completedResults.length === 0 ? (
            <div className="p-6 text-center text-gray-400">
              No completed simulations yet. Go to the Twins tab to run
              simulations.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-darpan-border bg-gray-900/50">
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">
                    Twin
                  </th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">
                    Mode
                  </th>
                  <th className="px-4 py-3 text-right text-gray-400 font-medium">
                    Questions
                  </th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">
                    Completed
                  </th>
                  <th className="px-4 py-3 text-center text-gray-400 font-medium">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody>
                {completedResults.map((r) => {
                  const isExpanded = expandedTwin === r.simulation_id;
                  const answered =
                    r.responses?.filter((resp: any) => !resp.skipped).length ??
                    0;
                  const total = r.responses?.length ?? 0;

                  return (
                    <Fragment key={r.simulation_id}>
                      <tr
                        className="border-b border-darpan-border/50 hover:bg-gray-800/30 cursor-pointer"
                        onClick={() =>
                          setExpandedTwin(
                            isExpanded ? null : r.simulation_id,
                          )
                        }
                      >
                        <td className="px-4 py-3 font-mono text-lime-400">
                          {r.twin_external_id}
                        </td>
                        <td className="px-4 py-3 text-gray-300">
                          {r.inference_mode}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-300">
                          {answered}/{total}
                        </td>
                        <td className="px-4 py-3 text-gray-400 text-xs">
                          {r.completed_at
                            ? new Date(r.completed_at).toLocaleString()
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-center text-gray-500 text-xs">
                          {isExpanded ? "collapse" : "expand"}
                        </td>
                      </tr>
                      {isExpanded && r.responses && (
                        <tr>
                          <td
                            colSpan={5}
                            className="bg-gray-900/40 px-4 py-3"
                          >
                            <div className="space-y-2 max-h-[400px] overflow-y-auto">
                              {r.responses.map((resp: any) => (
                                <div
                                  key={resp.question_id}
                                  className={`rounded-md border p-3 ${
                                    resp.skipped
                                      ? "border-gray-700 opacity-50"
                                      : "border-darpan-border"
                                  }`}
                                >
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="font-mono text-xs text-cyan-400">
                                      {resp.question_id}
                                    </span>
                                    <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-400">
                                      {resp.question_type}
                                    </span>
                                  </div>
                                  <p className="text-sm text-gray-300">
                                    {resp.question_text}
                                  </p>
                                  {!resp.skipped && (
                                    <div className="mt-1 text-sm">
                                      <span className="text-gray-500">
                                        Answer:{" "}
                                      </span>
                                      <span className="text-white font-medium">
                                        {typeof resp.structured_answer ===
                                        "object"
                                          ? JSON.stringify(
                                              resp.structured_answer,
                                            )
                                          : String(
                                              resp.structured_answer ?? "—",
                                            )}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
