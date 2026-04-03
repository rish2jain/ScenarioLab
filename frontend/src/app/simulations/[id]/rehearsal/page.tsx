"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  Send,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Plus,
  Trash2,
  MessageSquare,
  Star,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import type { RehearsalMessage, Objection, RehearsalFeedback } from "@/lib/types";

export default function RehearsalPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? "";

  const [step, setStep] = useState<"setup" | "rehearsal" | "feedback">("setup");
  const [brief, setBrief] = useState("");
  const [stakeholderType, setStakeholderType] = useState("board_member");
  const [rehearsalMode, setRehearsalMode] = useState<
    "friendly" | "challenging" | "hostile"
  >("challenging");

  const [counterpartId, setCounterpartId] = useState<string | null>(null);
  const [counterpartName, setCounterpartName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const [messages, setMessages] = useState<RehearsalMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isSending, setIsSending] = useState(false);

  const [objections, setObjections] = useState<Objection[]>([]);
  const [isGeneratingObjections, setIsGeneratingObjections] = useState(false);
  const [presentationText, setPresentationText] = useState("");

  const [feedback, setFeedback] = useState<RehearsalFeedback | null>(null);
  const [isGettingFeedback, setIsGettingFeedback] = useState(false);

  const handleCreateCounterpart = async () => {
    if (!brief.trim()) return;

    setIsCreating(true);
    try {
      const result = await api.createCounterpart({
        brief,
        stakeholder_type: stakeholderType,
        rehearsal_mode: rehearsalMode,
      });
      setCounterpartId(result.id);
      setCounterpartName(result.name);
      setStep("rehearsal");
    } catch (error) {
      console.error("Failed to create counterpart:", error);
      alert("Failed to create counterpart. Please try again.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !counterpartId) return;

    const userMessage: RehearsalMessage = {
      id: `msg-${Date.now()}`,
      is_user: true,
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsSending(true);

    try {
      const result = await api.rehearse(counterpartId, inputMessage);

      const agentMessage: RehearsalMessage = {
        id: `msg-${Date.now() + 1}`,
        is_user: false,
        content: result.response,
        timestamp: new Date().toISOString(),
        tone: result.tone,
        coaching_tips: result.coaching_tips,
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      console.error("Failed to send message:", error);
      alert("Failed to get response. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  const handleGenerateObjections = async () => {
    if (!counterpartId || !presentationText.trim()) return;

    setIsGeneratingObjections(true);
    try {
      const result = await api.generateObjections(
        counterpartId,
        presentationText
      );
      setObjections(result as Objection[]);
    } catch (error) {
      console.error("Failed to generate objections:", error);
      alert("Failed to generate objections. Please try again.");
    } finally {
      setIsGeneratingObjections(false);
    }
  };

  const handleGetFeedback = async () => {
    if (!counterpartId) return;

    setIsGettingFeedback(true);
    try {
      const result = await api.getRehearsalFeedback(counterpartId);
      setFeedback(result);
      setStep("feedback");
    } catch (error) {
      console.error("Failed to get feedback:", error);
      alert("Failed to get feedback. Please try again.");
    } finally {
      setIsGettingFeedback(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "mild":
        return "text-green-400";
      case "moderate":
        return "text-yellow-400";
      case "strong":
        return "text-red-400";
      default:
        return "text-slate-400";
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "strategic":
        return <Star className="w-4 h-4" />;
      case "financial":
        return <AlertTriangle className="w-4 h-4" />;
      case "operational":
        return <CheckCircle className="w-4 h-4" />;
      case "political":
        return <XCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  return (
    <div className="h-full flex flex-col -m-6">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700 bg-slate-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href={`/simulations/${simulationId}`}>
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<ChevronLeft className="w-4 h-4" />}
              >
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-slate-100">
                Stakeholder Rehearsal
              </h1>
              <p className="text-sm text-slate-400">
                Practice with an AI counterpart
              </p>
            </div>
          </div>
          {step === "rehearsal" && (
            <Button
              variant="secondary"
              onClick={handleGetFeedback}
              isLoading={isGettingFeedback}
            >
              End & Get Feedback
            </Button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {step === "setup" && (
          <div className="max-w-2xl mx-auto p-6 space-y-6">
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-slate-100 mb-4">
                Create Your Counterpart
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Stakeholder Type
                  </label>
                  <select
                    value={stakeholderType}
                    onChange={(e) => setStakeholderType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100"
                  >
                    <option value="board_member">Board Member</option>
                    <option value="investor">Investor</option>
                    <option value="regulator">Regulator</option>
                    <option value="executive">Executive</option>
                    <option value="customer">Customer</option>
                    <option value="partner">Partner</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Rehearsal Mode
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {(
                      [
                        "friendly",
                        "challenging",
                        "hostile",
                      ] as const
                    ).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setRehearsalMode(mode)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          rehearsalMode === mode
                            ? mode === "friendly"
                              ? "bg-green-500/20 border border-green-500 text-green-400"
                              : mode === "challenging"
                                ? "bg-yellow-500/20 border border-yellow-500 text-yellow-400"
                                : "bg-red-500/20 border border-red-500 text-red-400"
                            : "bg-slate-700 border border-slate-600 text-slate-300 hover:bg-slate-600"
                        }`}
                      >
                        {mode.charAt(0).toUpperCase() + mode.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Stakeholder Context
                  </label>
                  <textarea
                    value={brief}
                    onChange={(e) => setBrief(e.target.value)}
                    rows={4}
                    placeholder="Describe the stakeholder you want to practice with. Include their background, concerns, and decision-making style..."
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 placeholder-slate-400 resize-none"
                  />
                </div>

                <Button
                  onClick={handleCreateCounterpart}
                  isLoading={isCreating}
                  disabled={!brief.trim()}
                  className="w-full"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Counterpart & Start
                </Button>
              </div>
            </Card>
          </div>
        )}

        {step === "rehearsal" && (
          <div className="flex h-full">
            {/* Chat Area */}
            <div className="flex-1 flex flex-col min-w-0">
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    <p>
                      Start the conversation with {counterpartName}
                    </p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.is_user ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg p-4 ${
                          message.is_user
                            ? "bg-accent text-white"
                            : "bg-slate-700 text-slate-100"
                        }`}
                      >
                        <p className="whitespace-pre-wrap">
                          {message.content}
                        </p>
                        {message.coaching_tips &&
                          message.coaching_tips.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-600">
                              <p className="text-xs text-slate-400 mb-1">
                                Coaching Tips:
                              </p>
                              <ul className="text-sm text-slate-300 space-y-1">
                                {message.coaching_tips.map((tip, i) => (
                                  <li key={i}>• {tip}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Input */}
              <div className="px-4 py-3 border-t border-slate-700 bg-slate-800/50">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) =>
                      e.key === "Enter" && !e.shiftKey && handleSendMessage()
                    }
                    placeholder="Type your message..."
                    className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 placeholder-slate-400"
                    disabled={isSending}
                  />
                  <Button
                    onClick={handleSendMessage}
                    isLoading={isSending}
                    disabled={!inputMessage.trim()}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Objections Panel */}
            <div className="w-80 border-l border-slate-700 bg-slate-800/30 flex flex-col">
              <div className="p-4 border-b border-slate-700">
                <h3 className="font-semibold text-slate-200">
                  Anticipated Objections
                </h3>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                <textarea
                  value={presentationText}
                  onChange={(e) => setPresentationText(e.target.value)}
                  placeholder="Paste your presentation text to generate objections..."
                  rows={4}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 placeholder-slate-400 text-sm resize-none"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleGenerateObjections}
                  isLoading={isGeneratingObjections}
                  disabled={!presentationText.trim()}
                  className="w-full"
                >
                  Generate Objections
                </Button>

                {objections.map((objection) => (
                  <Card key={objection.id} className="p-3">
                    <div className="flex items-start gap-2">
                      <span className={getSeverityColor(objection.severity)}>
                        {getCategoryIcon(objection.category)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-200">
                          {objection.text}
                        </p>
                        <p className="text-xs text-slate-400 mt-1">
                          {objection.suggested_response}
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === "feedback" && feedback && (
          <div className="max-w-2xl mx-auto p-6 space-y-6">
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-slate-100 mb-4">
                Rehearsal Feedback
              </h2>

              <div className="flex items-center justify-center mb-6">
                <div className="text-center">
                  <div className="text-4xl font-bold text-accent">
                    {feedback.overall_rating.toFixed(1)}
                  </div>
                  <div className="text-sm text-slate-400">Overall Rating</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <h3 className="text-sm font-medium text-green-400 mb-2">
                    Strengths
                  </h3>
                  <ul className="space-y-1">
                    {feedback.strengths.map((s, i) => (
                      <li key={i} className="text-sm text-slate-300">
                        • {s}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-yellow-400 mb-2">
                    Areas for Improvement
                  </h3>
                  <ul className="space-y-1">
                    {feedback.areas_for_improvement.map((s, i) => (
                      <li key={i} className="text-sm text-slate-300">
                        • {s}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {feedback.key_objections_raised.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-slate-300 mb-2">
                    Key Objections Raised
                  </h3>
                  <ul className="space-y-1">
                    {feedback.key_objections_raised.map((s, i) => (
                      <li key={i} className="text-sm text-slate-300">
                        • {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <h3 className="text-sm font-medium text-blue-400 mb-2">
                  Preparation Tips
                </h3>
                <ul className="space-y-1">
                  {feedback.preparation_tips.map((s, i) => (
                    <li key={i} className="text-sm text-slate-300">
                      • {s}
                    </li>
                  ))}
                </ul>
              </div>

              <Button
                onClick={() => {
                  setStep("setup");
                  setMessages([]);
                  setObjections([]);
                  setFeedback(null);
                  setCounterpartId(null);
                }}
                className="w-full mt-6"
              >
                Start New Rehearsal
              </Button>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
