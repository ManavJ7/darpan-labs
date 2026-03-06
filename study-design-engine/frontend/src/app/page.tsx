"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, FlaskConical, ArrowRight, Clock } from "lucide-react";
import { toast } from "sonner";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Badge, statusToBadgeVariant } from "@/components/ui/Badge";
import { useStudyStore } from "@/store/studyStore";
import { stepName, getStepFromStatus } from "@/lib/utils";
import type { StudyStatus } from "@/types/study";

export default function LandingPage() {
  const router = useRouter();
  const { studies, fetchStudies, createStudy } = useStudyStore();

  const [showForm, setShowForm] = useState(false);
  const [question, setQuestion] = useState("");
  const [brandName, setBrandName] = useState("");
  const [category, setCategory] = useState("");
  const [notes, setNotes] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchStudies();
  }, [fetchStudies]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setCreating(true);
    try {
      const ctx: Record<string, string> = {};
      if (notes.trim()) ctx.notes = notes.trim();

      const study = await createStudy({
        question: question.trim(),
        brand_id: crypto.randomUUID(),
        brand_name: brandName.trim() || undefined,
        category: category.trim() || undefined,
        context: Object.keys(ctx).length > 0 ? ctx : undefined,
      });
      toast.success("Study created");
      router.push(`/study/${study.id}`);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">Studies</h1>
            <p className="text-sm text-white/50 mt-1">Create and manage research study designs</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-4 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Study
          </button>
        </div>

        {showForm && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Card className="mb-8">
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-1.5">
                    Research Question *
                  </label>
                  <textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="e.g. Which of these 3 snack concepts resonates most with health-conscious millennials?"
                    className="w-full h-20 px-4 py-3 bg-darpan-bg border border-darpan-border rounded-lg text-white placeholder-white/30 resize-none focus:outline-none focus:border-darpan-lime/50 focus:ring-1 focus:ring-darpan-lime/30 transition-colors text-sm"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-white/60 mb-1.5">
                      Brand Name
                    </label>
                    <input
                      value={brandName}
                      onChange={(e) => setBrandName(e.target.value)}
                      placeholder="e.g. NutriCrunch"
                      className="w-full px-4 py-2.5 bg-darpan-bg border border-darpan-border rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-darpan-lime/50 focus:ring-1 focus:ring-darpan-lime/30 transition-colors text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-white/60 mb-1.5">
                      Category
                    </label>
                    <input
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      placeholder="e.g. Health Snacks"
                      className="w-full px-4 py-2.5 bg-darpan-bg border border-darpan-border rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-darpan-lime/50 focus:ring-1 focus:ring-darpan-lime/30 transition-colors text-sm"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-1.5">
                    Additional Notes
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Any other context for the AI (budget, timeline, competitive landscape...)"
                    className="w-full h-16 px-4 py-3 bg-darpan-bg border border-darpan-border rounded-lg text-white placeholder-white/30 resize-none focus:outline-none focus:border-darpan-lime/50 focus:ring-1 focus:ring-darpan-lime/30 transition-colors text-sm"
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-sm text-white/50 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating || !question.trim()}
                    className="px-6 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {creating ? "Creating..." : "Create Study"}
                  </button>
                </div>
              </form>
            </Card>
          </motion.div>
        )}

        {studies.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-darpan-surface border border-darpan-border flex items-center justify-center mx-auto mb-4">
              <FlaskConical className="w-8 h-8 text-white/20" />
            </div>
            <p className="text-white/40 text-sm">No studies yet. Create your first one above.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {studies.map((study, i) => (
              <motion.div
                key={study.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <button
                  onClick={() => router.push(`/study/${study.id}`)}
                  className="w-full text-left"
                >
                  <Card className="hover:border-darpan-border-active transition-colors group cursor-pointer">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-sm group-hover:text-darpan-lime transition-colors truncate">
                          {study.title || study.question}
                        </h3>
                        <p className="text-xs text-white/40 mt-1 line-clamp-1">
                          {study.question}
                        </p>
                        <div className="flex items-center gap-3 mt-3">
                          {study.brand_name && (
                            <span className="text-xs text-white/40">{study.brand_name}</span>
                          )}
                          {study.category && (
                            <span className="text-xs text-white/30">{study.category}</span>
                          )}
                          <span className="flex items-center gap-1 text-xs text-white/30">
                            <Clock className="w-3 h-3" />
                            {new Date(study.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <div className="text-right">
                          <Badge variant={statusToBadgeVariant(study.status)}>
                            {study.status === "complete"
                              ? "Complete"
                              : `Step ${getStepFromStatus(study.status as StudyStatus)} — ${stepName(getStepFromStatus(study.status as StudyStatus))}`}
                          </Badge>
                        </div>
                        <ArrowRight className="w-4 h-4 text-white/20 group-hover:text-darpan-lime transition-colors" />
                      </div>
                    </div>
                  </Card>
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
