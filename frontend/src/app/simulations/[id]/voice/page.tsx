"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Mic,
  Square,
  ChevronLeft,
  Users,
  Volume2,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { archetypeColors } from "@/lib/archetypeColors";
import type { Agent } from "@/lib/types";

interface VoiceMessage {
  id: string;
  isUser: boolean;
  content: string;
  timestamp: string;
  audioUrl?: string;
}

export default function VoiceChatPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? "";
  const { addToast } = useToast();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState<VoiceMessage[]>([]);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(
    null
  );

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const agentsData = await api.getSimulationAgents(simulationId);
        if (agentsData && agentsData.length > 0) {
          setAgents(agentsData.map(a => ({
            ...a,
            color: archetypeColors[a.archetype] || '#6b7280',
            isActive: true
          } as Agent)));
        } else {
          setAgents([]);
        }
      } catch (error) {
        console.error("Failed to fetch agents:", error);
        setAgents([]);
      }
    };
    fetchAgents();
  }, [simulationId]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  const playAudio = useCallback((audioUrl: string) => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
    }

    const fullUrl = audioUrl.startsWith("http")
      ? audioUrl
      : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"}${audioUrl}`;

    const audio = new Audio(fullUrl);
    currentAudioRef.current = audio;
    setCurrentAudio(audio);
    audio.play().catch(console.error);
  }, []);

  const processAudio = useCallback(async (audioBlob: Blob) => {
    if (!selectedAgent) {
      addToast("Please select an agent first", "info");
      return;
    }

    setIsProcessing(true);
    try {
      const result = await api.voiceConversation(
        simulationId,
        selectedAgent.id,
        audioBlob
      );

      // Add user message
      const userMessage: VoiceMessage = {
        id: `msg-${Date.now()}-user`,
        isUser: true,
        content: result.transcript,
        timestamp: new Date().toISOString(),
      };

      // Add agent message
      const agentMessage: VoiceMessage = {
        id: `msg-${Date.now()}-agent`,
        isUser: false,
        content: result.response_text,
        timestamp: new Date().toISOString(),
        audioUrl: result.audio_url,
      };

      setMessages((prev) => [...prev, userMessage, agentMessage]);

      // Auto-play agent response
      if (result.audio_url) {
        playAudio(result.audio_url);
      }
    } catch (error) {
      console.error("Failed to process audio:", error);
      addToast("Failed to process voice. Please try again.", "error");
    } finally {
      setIsProcessing(false);
    }
  }, [addToast, playAudio, selectedAgent, simulationId]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      let chosenMime = "";
      if (
        typeof MediaRecorder !== "undefined" &&
        typeof MediaRecorder.isTypeSupported === "function"
      ) {
        if (MediaRecorder.isTypeSupported("audio/webm")) {
          chosenMime = "audio/webm";
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
          chosenMime = "audio/mp4";
        }
      }
      const mediaRecorder = chosenMime
        ? new MediaRecorder(stream, { mimeType: chosenMime })
        : new MediaRecorder(stream);

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blobType =
          chosenMime ||
          (typeof mediaRecorder.mimeType === "string" &&
          mediaRecorder.mimeType.length > 0
            ? mediaRecorder.mimeType
            : undefined);
        const audioBlob = new Blob(audioChunksRef.current, {
          ...(blobType ? { type: blobType } : {}),
        });
        stream.getTracks().forEach((track) => track.stop());
        await processAudio(audioBlob);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Failed to start recording:", error);
      addToast("Could not access microphone. Please grant permission.", "error");
    }
  }, [addToast, processAudio]);

  useEffect(() => {
    return () => {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
    };
  }, []);

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
              <h1 className="text-xl font-bold text-slate-100">Voice Chat</h1>
              <p className="text-sm text-slate-400">
                Talk with simulated agents
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                <p>Select an agent and start speaking to begin the conversation</p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-4 ${
                      message.isUser
                        ? "bg-accent text-white"
                        : "bg-slate-700 text-slate-100"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    {!message.isUser && message.audioUrl && (
                      <button
                        onClick={() => playAudio(message.audioUrl!)}
                        className="mt-2 flex items-center gap-2 text-sm text-slate-300 hover:text-white transition-colors"
                      >
                        <Volume2 className="w-4 h-4" />
                        Play audio
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Recording Controls */}
          <div className="px-6 py-4 border-t border-slate-700 bg-slate-800/50">
            <div className="flex items-center justify-center gap-4">
              {isProcessing ? (
                <div className="flex items-center gap-2 text-slate-400">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </div>
              ) : (
                <>
                  <Button
                    variant={isRecording ? "danger" : "primary"}
                    size="lg"
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={!selectedAgent}
                    leftIcon={
                      isRecording ? (
                        <Square className="w-5 h-5" />
                      ) : (
                        <Mic className="w-5 h-5" />
                      )
                    }
                  >
                    {isRecording ? "Stop" : "Record"}
                  </Button>

                  {isRecording && (
                    <div className="flex items-center gap-2">
                      <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                      </span>
                      <span className="text-red-400 font-medium">Recording</span>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Agent Selection */}
        <div className="w-80 border-l border-slate-700 bg-slate-800/30 overflow-y-auto">
          <div className="p-4 border-b border-slate-700">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-slate-400" />
              <h3 className="font-semibold text-slate-200">Select Agent</h3>
            </div>
          </div>
          <div className="p-4 space-y-3">
            {agents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => setSelectedAgent(agent)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  selectedAgent?.id === agent.id
                    ? "bg-accent/20 border border-accent"
                    : "bg-slate-700/50 border border-transparent hover:bg-slate-700"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                    style={{ backgroundColor: agent.color }}
                  >
                    {agent.name[0]}
                  </div>
                  <div>
                    <p className="font-medium text-slate-100">{agent.name}</p>
                    <p className="text-sm text-slate-400">{agent.role}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
