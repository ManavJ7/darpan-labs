"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Filter, RotateCcw } from "lucide-react";

interface FilterGroup {
  label: string;
  items: { id: string; label: string }[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: () => void;
}

interface ResultsFiltersProps {
  twinFilter: FilterGroup;
  conceptFilter: FilterGroup;
  metricFilter: FilterGroup;
  onApply: () => void;
  onReset: () => void;
}

function FilterSection({ group }: { group: FilterGroup }) {
  const [open, setOpen] = useState(true);
  const allSelected = group.selected.size === group.items.length;

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-2 text-sm font-medium text-white/60 hover:text-white/80 transition-colors"
      >
        <span>
          {group.label}{" "}
          <span className="text-white/30 font-normal">
            ({group.selected.size}/{group.items.length})
          </span>
        </span>
        {open ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>

      {open && (
        <div className="pb-3 space-y-1">
          <button
            onClick={group.onToggleAll}
            className="text-xs text-darpan-lime/70 hover:text-darpan-lime transition-colors mb-1"
          >
            {allSelected ? "Deselect all" : "Select all"}
          </button>
          <div className="max-h-40 overflow-y-auto space-y-0.5">
            {group.items.map((item) => (
              <label
                key={item.id}
                className="flex items-center gap-2.5 py-1 px-1 rounded hover:bg-white/[0.03] cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={group.selected.has(item.id)}
                  onChange={() => group.onToggle(item.id)}
                  className="accent-[#C8FF00] w-3.5 h-3.5"
                />
                <span className="text-sm text-white/50">{item.label}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ResultsFilters({
  twinFilter,
  conceptFilter,
  metricFilter,
  onApply,
  onReset,
}: ResultsFiltersProps) {
  return (
    <div className="bg-darpan-surface border border-darpan-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-4 h-4 text-white/40" />
        <h3 className="text-sm font-medium text-white/70">Filters</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <FilterSection group={twinFilter} />
        <FilterSection group={conceptFilter} />
        <FilterSection group={metricFilter} />
      </div>

      <div className="flex items-center gap-3 mt-5 pt-4 border-t border-darpan-border">
        <button
          onClick={onApply}
          className="flex items-center gap-2 px-5 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors"
        >
          Apply Filters
        </button>
        <button
          onClick={onReset}
          className="flex items-center gap-2 px-4 py-2 text-sm text-white/40 hover:text-white/70 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset
        </button>
      </div>
    </div>
  );
}
