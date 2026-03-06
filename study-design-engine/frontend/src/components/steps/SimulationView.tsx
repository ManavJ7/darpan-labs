"use client";

import { Fragment, useEffect, useState } from "react";
import { useStudyStore } from "@/store/studyStore";
import { getSimulationExportUrl } from "@/lib/studyApi";
import type { SimulationRun, TwinResult } from "@/types/study";

export default function SimulationView() {
  const { study, simulationRuns, fetchSimulationResults } = useStudyStore();
  const [expandedTwin, setExpandedTwin] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<SimulationRun | null>(null);

  useEffect(() => {
    fetchSimulationResults();
  }, [fetchSimulationResults]);

  useEffect(() => {
    if (simulationRuns.length > 0 && !selectedRun) {
      setSelectedRun(simulationRuns[0]);
    }
  }, [simulationRuns, selectedRun]);

  if (!study) return null;

  const isComplete = study.status === "complete" || study.status === "step_4_locked";

  if (!isComplete) {
    return (
      <div className="rounded-lg border border-darpan-border bg-darpan-surface p-6 text-center text-gray-400">
        Complete all 4 steps to run twin simulations.
      </div>
    );
  }

  if (simulationRuns.length === 0) {
    return (
      <div className="space-y-6">
        <div className="rounded-lg border border-darpan-border bg-darpan-surface p-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            Twin Survey Simulation
          </h3>
          <p className="text-gray-400 mb-4">
            No simulation results yet. Run the simulation from the CLI:
          </p>
          <div className="rounded-md bg-gray-900 p-4 font-mono text-sm text-lime-400 overflow-x-auto">
            <div className="text-gray-500 mb-1"># Navigate to twin-generator</div>
            <div>cd twin-generator</div>
            <div className="mt-2 text-gray-500"># Run simulation for all P01 twins</div>
            <div>
              python scripts/step5_survey_simulation.py \
            </div>
            <div className="pl-4">
              --study-id {study.id} \
            </div>
            <div className="pl-4">
              --twins P01_all \
            </div>
            <div className="pl-4">--mode combined</div>
          </div>
          <p className="text-gray-500 text-xs mt-3">
            Results will be uploaded to the SDE automatically and appear here.
          </p>
          <button
            onClick={() => fetchSimulationResults()}
            className="mt-4 rounded-md bg-darpan-surface border border-darpan-border px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition"
          >
            Refresh Results
          </button>
        </div>
      </div>
    );
  }

  const runData = selectedRun?.results;
  const twins: TwinResult[] = runData?.results || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">
            Twin Simulation Results
          </h3>
          <p className="text-sm text-gray-400">
            {selectedRun?.twin_count} twins, {selectedRun?.question_count} questions
            — {selectedRun?.inference_mode} mode
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Run selector */}
          {simulationRuns.length > 1 && (
            <select
              value={selectedRun?.id || ""}
              onChange={(e) => {
                const run = simulationRuns.find((r) => r.id === e.target.value);
                if (run) setSelectedRun(run);
              }}
              className="rounded-md bg-gray-900 border border-darpan-border px-3 py-1.5 text-sm text-gray-300"
            >
              {simulationRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {new Date(run.created_at).toLocaleDateString()} — {run.inference_mode} ({run.twin_count} twins)
                </option>
              ))}
            </select>
          )}

          {/* Download buttons */}
          {selectedRun && (
            <div className="flex gap-2">
              <a
                href={getSimulationExportUrl(study.id, selectedRun.id, "csv")}
                className="rounded-md bg-lime-600 px-3 py-1.5 text-sm font-medium text-black hover:bg-lime-500 transition"
              >
                CSV
              </a>
              <a
                href={getSimulationExportUrl(study.id, selectedRun.id, "json")}
                className="rounded-md bg-cyan-600 px-3 py-1.5 text-sm font-medium text-black hover:bg-cyan-500 transition"
              >
                JSON
              </a>
            </div>
          )}

          <button
            onClick={() => fetchSimulationResults()}
            className="rounded-md bg-darpan-surface border border-darpan-border px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700 transition"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Results Table */}
      <div className="rounded-lg border border-darpan-border bg-darpan-surface overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-darpan-border bg-gray-900/50">
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Twin</th>
              <th className="px-4 py-3 text-left text-gray-400 font-medium">Participant</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">Coherence</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">Answered</th>
              <th className="px-4 py-3 text-right text-gray-400 font-medium">Skipped</th>
              <th className="px-4 py-3 text-center text-gray-400 font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {twins.map((twin) => {
              const answered = twin.responses.filter((r) => !r.skipped).length;
              const skipped = twin.responses.filter((r) => r.skipped).length;
              const isExpanded = expandedTwin === twin.twin_id;

              return (
                <Fragment key={twin.twin_id}>
                  <tr
                    className="border-b border-darpan-border/50 hover:bg-gray-800/30 cursor-pointer"
                    onClick={() =>
                      setExpandedTwin(isExpanded ? null : twin.twin_id)
                    }
                  >
                    <td className="px-4 py-3 font-mono text-lime-400">
                      {twin.twin_id}
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {twin.participant_id || "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-300">
                      {twin.coherence_score != null
                        ? twin.coherence_score.toFixed(2)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-300">
                      {answered}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-400">
                      {skipped}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-gray-500 text-xs">
                        {isExpanded ? "collapse" : "expand"}
                      </span>
                    </td>
                  </tr>

                  {/* Expanded responses */}
                  {isExpanded && (
                    <tr>
                      <td colSpan={6} className="bg-gray-900/40 px-4 py-3">
                        <div className="space-y-3 max-h-[500px] overflow-y-auto">
                          {twin.responses.map((resp) => (
                            <div
                              key={resp.question_id}
                              className={`rounded-md border p-3 ${
                                resp.skipped
                                  ? "border-gray-700 opacity-50"
                                  : "border-darpan-border"
                              }`}
                            >
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="font-mono text-xs text-cyan-400">
                                      {resp.question_id}
                                    </span>
                                    <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-400">
                                      {resp.question_type}
                                    </span>
                                    {resp.skipped && (
                                      <span className="rounded-full bg-yellow-900/30 px-2 py-0.5 text-xs text-yellow-500">
                                        skipped
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-sm text-gray-300 mb-2">
                                    {resp.question_text}
                                  </p>
                                  {!resp.skipped && (
                                    <>
                                      <div className="text-sm">
                                        <span className="text-gray-500">Answer: </span>
                                        <span className="text-white font-medium">
                                          {typeof resp.structured_answer === "object"
                                            ? JSON.stringify(resp.structured_answer)
                                            : String(resp.structured_answer ?? "—")}
                                        </span>
                                      </div>
                                      {resp.raw_answer && (
                                        <details className="mt-2">
                                          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">
                                            Raw response ({resp.evidence_count} evidence, {resp.elapsed_s.toFixed(1)}s)
                                          </summary>
                                          <p className="mt-1 text-xs text-gray-400 whitespace-pre-wrap border-l-2 border-gray-700 pl-3">
                                            {resp.raw_answer}
                                          </p>
                                        </details>
                                      )}
                                    </>
                                  )}
                                </div>
                              </div>
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
      </div>
    </div>
  );
}

