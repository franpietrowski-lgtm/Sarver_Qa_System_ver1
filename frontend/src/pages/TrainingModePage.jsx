import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp, CheckCircle2, ChevronRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { publicGet, publicPost } from "@/lib/api";
import { toast } from "sonner";


export default function TrainingModePage() {
  const sessionCode = window.location.pathname.split("/").pop();
  const [sessionData, setSessionData] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [quizOpen, setQuizOpen] = useState(false);
  const [responses, setResponses] = useState({});
  const [timers, setTimers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await publicGet(`/public/training/${sessionCode}`);
        setSessionData(response);
        setTimers({ [response.items[0]?.id]: Date.now() });
      } catch (error) {
        toast.error(error?.response?.data?.detail || "Training session unavailable");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [sessionCode]);

  const currentItem = sessionData?.items?.[currentIndex];
  const isLast = currentIndex === (sessionData?.items?.length || 1) - 1;

  const answers = useMemo(() => Object.values(responses), [responses]);

  const revealQuiz = () => {
    if (!currentItem) return;
    setQuizOpen(true);
    setTimers((current) => ({ ...current, [currentItem.id]: current[currentItem.id] || Date.now() }));
  };

  const storeResponse = (value) => {
    if (!currentItem) return;
    setResponses((current) => ({
      ...current,
      [currentItem.id]: {
        item_id: currentItem.id,
        response: value,
        time_seconds: Math.max(((Date.now() - (timers[currentItem.id] || Date.now())) / 1000), 1),
      },
    }));
  };

  const moveNext = () => {
    if (!currentItem || !responses[currentItem.id]?.response) {
      toast.error("Answer this item before moving on.");
      return;
    }
    if (isLast) {
      submitTraining();
      return;
    }
    const nextItem = sessionData.items[currentIndex + 1];
    setCurrentIndex((current) => current + 1);
    setQuizOpen(false);
    setTimers((current) => ({ ...current, [nextItem.id]: Date.now() }));
  };

  const submitTraining = async () => {
    setSubmitting(true);
    try {
      const response = await publicPost(`/public/training/${sessionCode}/submit`, { answers });
      setSummary(response.summary);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to submit training session");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-[#f5f7f5] px-4 py-8 text-center text-[#243e36]" data-testid="training-mode-loading-state">Loading training session...</div>;
  }

  if (summary) {
    return (
      <div className="min-h-screen bg-[linear-gradient(180deg,_#edf0e7_0%,_#f7f8f6_100%)] px-4 py-8" data-testid="training-mode-complete-screen">
        <div className="mx-auto max-w-xl rounded-[36px] border border-border bg-white p-8 text-center shadow-sm">
          <CheckCircle2 className="mx-auto h-12 w-12 text-[#2d5a27]" />
          <h1 className="mt-4 font-[Outfit] text-4xl font-semibold text-[#111815]">Session complete</h1>
          <p className="mt-4 text-sm text-[#5c6d64]">Accuracy: {summary.score_percent}% · Completion: {summary.completion_rate}% · Avg time: {summary.average_time_seconds}s</p>
          <p className="mt-4 text-sm text-[#41534a]">{summary.owner_message}</p>
          <p className="mt-6 text-xs font-semibold uppercase tracking-[0.24em] text-[#5f7464]">Close this screen when you’re ready.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#243e36_0%,_#111815_100%)] px-4 py-6 text-white" data-testid="training-mode-page">
      <div className="mx-auto max-w-lg space-y-4">
        <Card className="rounded-[32px] border-white/10 bg-white/10 text-white backdrop-blur-xl" data-testid="training-mode-header-card">
          <CardContent className="p-6">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Training Mode</p>
            <h1 className="mt-3 font-[Outfit] text-4xl font-semibold">{sessionData.session.crew_label} · {sessionData.session.division}</h1>
            <p className="mt-3 text-sm text-white/75">Image first, then swipe or tap into the quiz. Finish the batch to lock the session.</p>
            <p className="mt-4 text-sm text-white/60" data-testid="training-mode-progress-text">Item {currentIndex + 1} of {sessionData.items.length}</p>
          </CardContent>
        </Card>

        <motion.div drag="y" dragMomentum={false} onDragEnd={(_, info) => { if (info.offset.y <= -90) revealQuiz(); }}>
          <Card className="overflow-hidden rounded-[36px] border-white/10 bg-white/10 text-white backdrop-blur-xl" data-testid="training-mode-image-card">
            <div className="aspect-[4/5] bg-[#dce5da]">
              <img src={currentItem.image_url} alt={currentItem.title} className="h-full w-full object-cover" data-testid="training-mode-image" />
            </div>
            <CardContent className="p-6">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">{currentItem.category}</p>
              <h2 className="mt-2 font-[Outfit] text-3xl font-semibold">{currentItem.title}</h2>
              <p className="mt-2 text-sm text-white/75">{currentItem.notes}</p>
              <Button type="button" onClick={revealQuiz} className="mt-5 h-12 w-full rounded-2xl bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="training-mode-open-quiz-button"><ArrowUp className="mr-2 h-4 w-4" />Swipe or tap to answer</Button>
            </CardContent>
          </Card>
        </motion.div>

        {quizOpen && (
          <Card className="rounded-[32px] border-white/10 bg-white/10 text-white backdrop-blur-xl" data-testid="training-mode-quiz-card">
            <CardContent className="space-y-4 p-6">
              <div className="flex items-center gap-2 text-sm font-semibold text-[#d8f3dc]"><Sparkles className="h-4 w-4" />Quiz</div>
              <p className="text-lg font-semibold text-white">{currentItem.question_prompt}</p>
              {currentItem.question_type === "multiple_choice" ? (
                <div className="space-y-3">
                  {currentItem.choice_options.map((option) => (
                    <button key={option} type="button" onClick={() => storeResponse(option)} className={`w-full rounded-[20px] border px-4 py-3 text-left text-sm font-semibold ${responses[currentItem.id]?.response === option ? "border-white bg-white text-[#243e36]" : "border-white/15 bg-black/10 text-white"}`} data-testid={`training-mode-option-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                      {option}
                    </button>
                  ))}
                </div>
              ) : (
                <Textarea value={responses[currentItem.id]?.response || ""} onChange={(event) => storeResponse(event.target.value)} className="min-h-[120px] rounded-[22px] border-white/15 bg-black/10 text-white" placeholder="Type your answer" data-testid="training-mode-free-text-input" />
              )}
              <Button type="button" disabled={!responses[currentItem.id]?.response || submitting} onClick={moveNext} className="h-12 w-full rounded-2xl bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="training-mode-next-button"><ChevronRight className="mr-2 h-4 w-4" />{isLast ? (submitting ? "Submitting..." : "Finish session") : "Next image"}</Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}