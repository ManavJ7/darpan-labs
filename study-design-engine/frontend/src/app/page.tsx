"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Plus, Play, FlaskConical, Megaphone, LogIn, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/Sidebar";
import { useStudyStore } from "@/store/studyStore";
import { useAuthStore } from "@/store/authStore";
import type { StudyType, StudyResponse } from "@/types/study";

export default function LandingPage() {
  const router = useRouter();
  const { studies, fetchStudies, createStudy } = useStudyStore();
  const { user } = useAuthStore();

  const [studyType, setStudyType] = useState<StudyType>("concept_testing");
  const [question, setQuestion] = useState("");
  const [showExtra, setShowExtra] = useState(false);
  const [brandName, setBrandName] = useState("");
  const [category, setCategory] = useState("");
  const [notes, setNotes] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchStudies();
  }, [fetchStudies]);

  const handleRun = async () => {
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
        study_type: studyType,
      });
      toast.success("Study created");
      router.push(`/study/${study.id}`);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setCreating(false);
    }
  };

  const getInitials = () => {
    const str = user?.name || user?.email || "U";
    return str
      .split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const formatTimeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    return `${minutes}m ago`;
  };

  // The backend already filters by visibility — anon gets only public studies,
  // authenticated users get public + their own. Here we just split the payload
  // into two sections for the UI.
  const publicStudies = studies.filter((s) => s.is_public);
  const ownStudies = user
    ? studies.filter((s) => !s.is_public && s.created_by_user_id === user.id)
    : [];

  return (
    <div className="min-h-screen flex">
      <Sidebar activePage="Studies" />

      <div className="flex-1 ml-[60px] flex flex-col">
        <div className="flex items-center justify-between px-6 h-12 shrink-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-white/40">Studies</span>
            <span className="text-white/20">/</span>
            <span className="text-white/60 font-medium">
              {user ? "New Study" : "Public Demos"}
            </span>
          </div>
          {user ? (
            <div className="flex items-center gap-3">
              {user.picture_url ? (
                <img
                  src={user.picture_url}
                  alt=""
                  className="w-8 h-8 rounded-full"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-darpan-elevated border border-darpan-border flex items-center justify-center text-[10px] font-semibold text-white/70">
                  {getInitials()}
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={() => router.push("/login")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-darpan-lime text-black text-sm font-semibold hover:bg-darpan-lime-dim transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              Try It Out
            </button>
          )}
        </div>

        <main className="flex-1 flex items-center justify-center px-6 pb-12">
          <div className="w-full max-w-[640px]">
            {user ? (
              <AuthedHero
                studyType={studyType}
                setStudyType={setStudyType}
                question={question}
                setQuestion={setQuestion}
                showExtra={showExtra}
                setShowExtra={setShowExtra}
                brandName={brandName}
                setBrandName={setBrandName}
                category={category}
                setCategory={setCategory}
                notes={notes}
                setNotes={setNotes}
                creating={creating}
                onRun={handleRun}
              />
            ) : (
              <AnonHero onTry={() => router.push("/login")} />
            )}

            {/* Public demo studies — shown to everyone */}
            {publicStudies.length > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4, delay: 0.2 }}
                className="mt-10"
              >
                <p className="text-[11px] font-medium text-white/25 uppercase tracking-widest mb-4">
                  {user ? "Public Demo Studies" : "Explore Demo Studies"}
                </p>
                <div className="grid gap-2">
                  {publicStudies.map((s) => (
                    <StudyCard
                      key={s.id}
                      study={s}
                      onClick={() => router.push(`/study/${s.id}`)}
                      formatTimeAgo={formatTimeAgo}
                      badge="DEMO"
                    />
                  ))}
                </div>
              </motion.div>
            )}

            {user && ownStudies.length > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4, delay: 0.3 }}
                className="mt-8"
              >
                <p className="text-[11px] font-medium text-white/25 uppercase tracking-widest mb-4">
                  Your Studies
                </p>
                <div className="grid gap-2">
                  {ownStudies.slice(0, 10).map((s) => (
                    <StudyCard
                      key={s.id}
                      study={s}
                      onClick={() => router.push(`/study/${s.id}`)}
                      formatTimeAgo={formatTimeAgo}
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

function AnonHero({ onTry }: { onTry: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="text-center mb-2"
    >
      <div className="w-16 h-16 rounded-2xl bg-darpan-lime/10 border border-darpan-lime/20 flex items-center justify-center mx-auto mb-5">
        <FlaskConical className="w-8 h-8 text-darpan-lime" />
      </div>
      <h1 className="text-[28px] font-bold leading-tight mb-2.5">
        AI-powered research, run in minutes
      </h1>
      <p className="text-sm text-white/50 mb-7 max-w-md mx-auto">
        Darpan Labs builds a digital twin of your target audience, then runs your study
        against them. Browse the demos below, or sign in to design your own.
      </p>
      <button
        onClick={onTry}
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors"
      >
        Try It Out
        <ArrowRight className="w-4 h-4" />
      </button>
    </motion.div>
  );
}

interface AuthedHeroProps {
  studyType: StudyType;
  setStudyType: (t: StudyType) => void;
  question: string;
  setQuestion: (q: string) => void;
  showExtra: boolean;
  setShowExtra: (v: boolean) => void;
  brandName: string;
  setBrandName: (v: string) => void;
  category: string;
  setCategory: (v: string) => void;
  notes: string;
  setNotes: (v: string) => void;
  creating: boolean;
  onRun: () => void;
}

function AuthedHero(p: AuthedHeroProps) {
  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center mb-8"
      >
        <h1 className="text-[28px] font-bold leading-tight mb-2.5">
          What do you want to research today?
        </h1>
        <p className="text-sm text-white/35">
          Our AI-powered digital twins will run the study for you
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.05 }}
        className="grid grid-cols-2 gap-3 mb-6"
      >
        <button
          onClick={() => p.setStudyType("concept_testing")}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${
            p.studyType === "concept_testing"
              ? "bg-darpan-lime/[0.06] border-darpan-lime/30 text-white"
              : "bg-darpan-surface border-darpan-border text-white/40 hover:border-darpan-border-active hover:text-white/60"
          }`}
        >
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              p.studyType === "concept_testing" ? "bg-darpan-lime/15" : "bg-white/5"
            }`}
          >
            <FlaskConical
              className={`w-4 h-4 ${
                p.studyType === "concept_testing" ? "text-darpan-lime" : "text-white/30"
              }`}
            />
          </div>
          <div className="text-left">
            <p className="text-sm font-medium">Concept Testing</p>
            <p className="text-[11px] text-white/25">Product concepts & ideas</p>
          </div>
        </button>
        <button
          onClick={() => p.setStudyType("ad_creative_testing")}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${
            p.studyType === "ad_creative_testing"
              ? "bg-darpan-lime/[0.06] border-darpan-lime/30 text-white"
              : "bg-darpan-surface border-darpan-border text-white/40 hover:border-darpan-border-active hover:text-white/60"
          }`}
        >
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              p.studyType === "ad_creative_testing" ? "bg-darpan-lime/15" : "bg-white/5"
            }`}
          >
            <Megaphone
              className={`w-4 h-4 ${
                p.studyType === "ad_creative_testing" ? "text-darpan-lime" : "text-white/30"
              }`}
            />
          </div>
          <div className="text-left">
            <p className="text-sm font-medium">Ad Creative Testing</p>
            <p className="text-[11px] text-white/25">Creative territories & campaigns</p>
          </div>
        </button>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.08 }}
        className="bg-darpan-surface border border-darpan-border rounded-xl p-5"
      >
        <textarea
          value={p.question}
          onChange={(e) => p.setQuestion(e.target.value)}
          placeholder="I have ideated 5 body wash concepts for women aged 22-30, but I have budget to develop only one. Which one would drive the most revenue?"
          className="w-full h-[88px] bg-transparent text-white text-sm leading-relaxed placeholder-white/25 resize-none focus:outline-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              p.onRun();
            }
          }}
        />

        {p.showExtra && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            transition={{ duration: 0.2 }}
            className="space-y-3 mt-3 pt-3 border-t border-darpan-border"
          >
            <div className="grid grid-cols-2 gap-3">
              <input
                value={p.brandName}
                onChange={(e) => p.setBrandName(e.target.value)}
                placeholder="Brand Name"
                className="w-full px-3 py-2 bg-darpan-bg border border-darpan-border rounded-lg text-white text-sm placeholder-white/25 focus:outline-none focus:border-darpan-lime/40 transition-colors"
              />
              <input
                value={p.category}
                onChange={(e) => p.setCategory(e.target.value)}
                placeholder="Category"
                className="w-full px-3 py-2 bg-darpan-bg border border-darpan-border rounded-lg text-white text-sm placeholder-white/25 focus:outline-none focus:border-darpan-lime/40 transition-colors"
              />
            </div>
            <textarea
              value={p.notes}
              onChange={(e) => p.setNotes(e.target.value)}
              placeholder="Additional context (budget, timeline, competitive landscape...)"
              className="w-full h-14 px-3 py-2 bg-darpan-bg border border-darpan-border rounded-lg text-white text-sm placeholder-white/25 resize-none focus:outline-none focus:border-darpan-lime/40 transition-colors"
            />
          </motion.div>
        )}

        <div className="flex items-center justify-between mt-4">
          <button
            type="button"
            onClick={() => p.setShowExtra(!p.showExtra)}
            className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
              p.showExtra
                ? "bg-darpan-lime/10 border border-darpan-lime/30 text-darpan-lime"
                : "bg-darpan-elevated border border-darpan-border text-white/40 hover:text-darpan-lime hover:border-darpan-lime/30"
            }`}
            title="Add more details"
          >
            <Plus className="w-4 h-4" />
          </button>

          <button
            onClick={p.onRun}
            disabled={p.creating || !p.question.trim()}
            className="flex items-center gap-2 px-5 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            {p.creating ? "Running..." : "Run"}
          </button>
        </div>
      </motion.div>
    </>
  );
}

interface StudyCardProps {
  study: StudyResponse;
  onClick: () => void;
  formatTimeAgo: (dateStr: string) => string;
  badge?: string;
}

function StudyCard({ study, onClick, formatTimeAgo, badge }: StudyCardProps) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-between py-3 px-3 group hover:bg-white/[0.02] rounded-lg transition-colors border border-darpan-border/40"
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-1.5 h-1.5 rounded-full bg-darpan-lime/50 shrink-0" />
        <span className="text-sm text-white/70 group-hover:text-white transition-colors truncate">
          {study.title || study.question}
          {study.category && (
            <span className="text-white/25"> &mdash; {study.category}</span>
          )}
        </span>
        {badge && (
          <span className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-darpan-lime/15 text-darpan-lime shrink-0">
            {badge}
          </span>
        )}
      </div>
      <span className="text-xs text-white/20 shrink-0 ml-4">
        {formatTimeAgo(study.created_at)}
      </span>
    </button>
  );
}
