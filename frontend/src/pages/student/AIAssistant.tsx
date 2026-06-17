import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import { BookOpen, Bot, ChevronRight, MessageSquare, Paperclip, Plus, Send, Sparkles, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/hooks/useAuth';
import { streamChatMessage, sendChatMessage } from '@/api/chat';
import { continueModuleSession } from '@/api/moduleSession';
import { getSessions, getSessionMessages } from '@/api/sessions';
import type { ChatMessage, Recommendation } from '@/types';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';
import { formatAssistantMessage, looksLikeRawJsonStream } from '@/utils/formatAssistantMessage';
import type { ModuleSessionStage } from '@/api/moduleSession';

const STAGE_LABELS: { id: ModuleSessionStage; label: string }[] = [
  { id: 'explanation', label: 'Explanation' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'quiz', label: 'Quiz' },
  { id: 'completed', label: 'Complete' },
];

function StageProgressPills({ stage }: { stage: ModuleSessionStage }) {
  const order = STAGE_LABELS.map((s) => s.id);
  const currentIdx = order.indexOf(stage);
  return (
    <div className="flex items-center gap-1 text-[11px]">
      {STAGE_LABELS.map((s, i) => (
        <span
          key={s.id}
          className={cn(
            'rounded-full px-2 py-0.5',
            i <= currentIdx ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-400',
          )}
        >
          {s.label}
        </span>
      ))}
    </div>
  );
}

function TaskCards({ tasks }: { tasks: Recommendation[] }) {
  return (
    <div className="mt-3 space-y-2">
      {tasks.map((task) => (
        <div key={task.item_id} className="rounded-lg border border-border bg-page p-3 text-left">
          <div className="font-semibold">{task.title}</div>
          {task.description && <p className="mt-1 text-[13px] text-text-secondary">{task.description}</p>}
          {task.source_url && (
            <a
              href={task.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-block text-[13px] text-primary underline"
            >
              {task.modality === 'video' ? 'Watch Video' : 'Read'}
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

interface LocationModuleSession {
  sessionId: string;
  stage: ModuleSessionStage;
  courseCode: string;
  moduleTitle: string;
  pdfUrl?: string | null;
  contentItemId: string;
  courseId?: string;
  initialMessage?: string;
  tasks?: Recommendation[];
  redirectToQuiz?: boolean;
  quizTopic?: string;
}

const SUGGESTION_GROUPS = [
  {
    id: 'study',
    icon: Sparkles,
    label: 'Study Plan',
    prompts: [
      'What should I study today based on my weakest topics?',
      'Build me a focused study session for this week',
      'Summarize my progress and suggest next steps',
    ],
  },
  {
    id: 'curriculum',
    icon: BookOpen,
    label: 'Curriculum',
    prompts: [
      'Generate my initial curriculum and first 5 study tasks',
      'Recommend resources for my enrolled courses',
      'Which module should I tackle next?',
    ],
  },
  {
    id: 'practice',
    icon: MessageSquare,
    label: 'Practice',
    prompts: [
      'Quiz me on a topic I am struggling with',
      'Explain a concept step by step with examples',
      'Help me debug my understanding of a problem',
    ],
  },
];

function AiMarkdown({ content, isStreaming }: { content: string; isStreaming?: boolean }) {
  const display =
    isStreaming && looksLikeRawJsonStream(content)
      ? 'Preparing your personalized recommendations…'
      : formatAssistantMessage(content);

  return (
    <ReactMarkdown
      components={{
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline hover:text-blue-800">
            {children}
          </a>
        ),
        code: ({ children }) => (
          <code className="rounded bg-gray-100 px-1 font-mono text-sm text-blue-700">{children}</code>
        ),
        pre: ({ children }) => (
          <pre className="my-2 overflow-x-auto rounded-lg bg-gray-900 p-4 font-mono text-sm text-green-400">{children}</pre>
        ),
        h3: ({ children }) => <h3 className="mb-1 mt-3 text-base font-bold">{children}</h3>,
        ul: ({ children }) => <ul className="my-2 list-inside list-disc space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="my-2 list-inside list-decimal space-y-1">{children}</ol>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
      }}
    >
      {display}
    </ReactMarkdown>
  );
}

export default function AIAssistant() {
  const { user, learnerId } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToastStore((s) => s.add);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [suggestionsOpen, setSuggestionsOpen] = useState(true);
  const [activeGroup, setActiveGroup] = useState(SUGGESTION_GROUPS[0].id);
  const [streamingAssistantId, setStreamingAssistantId] = useState<string | null>(null);
  const [moduleSession, setModuleSession] = useState<LocationModuleSession | null>(null);
  const [moduleStage, setModuleStage] = useState<ModuleSessionStage>('explanation');
  const [moduleSending, setModuleSending] = useState(false);
  const moduleInitRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const sessions = useQuery({
    queryKey: ['sessions', learnerId],
    queryFn: () => getSessions(learnerId),
    enabled: !!learnerId,
  });

  const displaySessionId = sessionId;

  const resetSession = () => {
    setSessionId(null);
    setMessages([]);
    setSuggestionsOpen(true);
    setInput('');
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  useEffect(() => {
    const state = location.state as { moduleSession?: LocationModuleSession; newSession?: boolean } | null;
    if (state?.moduleSession && !moduleInitRef.current) {
      moduleInitRef.current = true;
      const ms = state.moduleSession;
      setModuleSession(ms);
      setModuleStage(ms.stage);
      setSuggestionsOpen(false);
      if (ms.initialMessage) {
        setMessages([
          {
            id: `module_init_${Date.now()}`,
            role: 'assistant',
            content: ms.initialMessage,
            timestamp: new Date().toISOString(),
            tasks: ms.tasks,
          },
        ]);
      }
      return;
    }

    const wantsNew =
      sessionStorage.getItem('aitutor_new_session') === '1' ||
      (location.state as { newSession?: boolean } | null)?.newSession;
    if (wantsNew) {
      sessionStorage.removeItem('aitutor_new_session');
      resetSession();
      if ((location.state as { newSession?: boolean } | null)?.newSession) {
        navigate(location.pathname, { replace: true, state: {} });
      }
    }
    const params = new URLSearchParams(location.search);
    const topic = params.get('topic');
    if (topic) {
      setInput(`I want to continue studying ${decodeURIComponent(topic)}. Help me with where I left off.`);
    }
  }, [location.pathname, location.search, location.state, navigate]);

  const loadSession = async (sid: string) => {
    const rows = await getSessionMessages(learnerId, sid);
    setSessionId(sid);
    setSuggestionsOpen(false);
    setMessages(
      rows.map((r, i) => ({
        id: `${sid}_${i}`,
        role: r.role as 'user' | 'assistant',
        content: r.role === 'assistant' ? formatAssistantMessage(r.content) : r.content,
        timestamp: r.timestamp,
      })),
    );
  };

  const newSession = () => {
    resetSession();
  };

  const activeSuggestions = SUGGESTION_GROUPS.find((g) => g.id === activeGroup) ?? SUGGESTION_GROUPS[0];
  const showSuggestions = messages.length === 0 && !isStreaming && suggestionsOpen;

  const sendModuleMessage = async (textOverride?: string) => {
    const text = (textOverride ?? input).trim();
    if (!text || moduleSending || !moduleSession) return;
    if (!textOverride) setInput('');
    setSuggestionsOpen(false);

    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((m) => [...m, userMsg]);
    setModuleSending(true);

    try {
      const res = await continueModuleSession(moduleSession.sessionId, text);
      setModuleStage(res.stage);

      if (res.redirect_to_quiz && res.topic) {
        const topic = res.topic;
        const sessionId = moduleSession.sessionId;
        setMessages((m) => [
          ...m,
          {
            id: `a_${Date.now()}`,
            role: 'assistant',
            content: res.message,
            timestamp: new Date().toISOString(),
            action: {
              label: 'Start Quiz',
              onClick: () =>
                navigate(`/student/quiz/${encodeURIComponent(topic)}`, {
                  state: { moduleSessionId: sessionId, contentItemId: moduleSession.contentItemId },
                }),
            },
          },
        ]);
        return;
      }

      setMessages((m) => [
        ...m,
        {
          id: `a_${Date.now()}`,
          role: 'assistant',
          content: res.message,
          timestamp: new Date().toISOString(),
          tasks: res.tasks,
        },
      ]);
    } catch {
      toast('Could not continue module session', 'error');
    } finally {
      setModuleSending(false);
    }
  };

  const send = async (textOverride?: string) => {
    if (moduleSession) {
      await sendModuleMessage(textOverride);
      return;
    }
    const text = (textOverride ?? input).trim();
    if (!text || isStreaming) return;
    if (!textOverride) setInput('');
    setSuggestionsOpen(false);
    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    const assistantId = `a_${Date.now()}`;
    const payload = {
      learner_id: learnerId,
      message: text,
      session_id: sessionId ?? undefined,
      course_context: { subject: 'General' },
      time_budget_minutes: 45,
    };

    setMessages((m) => [
      ...m,
      userMsg,
      {
        id: assistantId,
        role: 'assistant' as const,
        content: '',
        timestamp: new Date().toISOString(),
      },
    ]);
    setIsStreaming(true);
    setStreamingAssistantId(assistantId);

    const applyAssistant = (content: string, id?: string, sid?: string) => {
      if (sid) setSessionId(sid);
      const formatted = formatAssistantMessage(content);
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? { ...msg, id: id ?? msg.id, content: formatted, timestamp: new Date().toISOString() }
            : msg,
        ),
      );
    };

    try {
      await streamChatMessage(payload, {
        onDelta: (chunk) => {
          setMessages((m) =>
            m.map((msg) => (msg.id === assistantId ? { ...msg, content: msg.content + chunk } : msg)),
          );
        },
        onDone: (fullResponse, sid) => {
          applyAssistant(fullResponse, undefined, sid);
          sessions.refetch();
        },
        onError: (message) => toast(message, 'error'),
      });
    } catch {
      try {
        const res = await sendChatMessage(payload);
        applyAssistant(res.assistant_message, res.request_id, res.session_id);
        sessions.refetch();
      } catch {
        setMessages((m) => m.filter((msg) => msg.id !== assistantId));
        toast('Message failed to send. Retry?', 'error');
      }
    } finally {
      setIsStreaming(false);
      setStreamingAssistantId(null);
    }
  };

  return (
    <div className="-m-6 flex h-[calc(100vh-4rem)] bg-page">
      <aside className={cn('flex flex-col border-r border-border bg-card transition-all', panelOpen ? 'w-[220px]' : 'w-0 overflow-hidden')}>
        <div className="flex items-center justify-between border-b border-border p-4">
          <span className="font-bold">Sessions</span>
          <Button variant="ghost" className="px-2 py-1 text-[12px]" onClick={newSession}>
            <Plus className="h-4 w-4" /> New
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {sessions.isLoading ? (
            <Skeleton className="m-2 h-16" />
          ) : (sessions.data ?? []).length === 0 ? (
            <EmptyState icon={Bot} title="No sessions yet" description="Start a conversation with the AI Tutor." />
          ) : (
            (sessions.data ?? []).map((s) => (
              <button
                key={s.session_id}
                type="button"
                onClick={() => loadSession(s.session_id)}
                className={cn(
                  'mb-2 w-full rounded-lg border-l-[3px] p-3 text-left text-[13px] hover:bg-card-hover',
                  sessionId === s.session_id ? 'border-l-primary bg-primary/5' : 'border-l-transparent',
                )}
              >
                <div className="font-mono text-[11px] text-text-muted">{s.session_id}</div>
                <div className="font-semibold">{s.subject || 'General'}</div>
                <div className="text-text-muted">{s.message_count} messages</div>
              </button>
            ))
          )}
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        {moduleSession && (
          <div className="flex items-center justify-between border-b border-blue-100 bg-blue-50 px-4 py-2">
            <div className="text-sm">
              <span className="font-semibold text-blue-900">{moduleSession.courseCode}</span>
              <span className="mx-2 text-blue-600">·</span>
              <span className="text-blue-700">{moduleSession.moduleTitle}</span>
            </div>
            <StageProgressPills stage={moduleStage} />
          </div>
        )}
        <div className="flex items-center justify-between border-b border-border bg-header px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-primary to-teal text-white">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="font-bold">AI Tutor</div>
              <div className="flex items-center gap-1 text-[12px] text-text-muted">
                <span className="h-2 w-2 rounded-full bg-teal" /> Online
              </div>
            </div>
          </div>
          {displaySessionId ? (
            <div className="rounded-full border border-border px-3 py-1 text-[12px] font-mono text-text-muted">
              # {displaySessionId}
            </div>
          ) : (
            <div className="rounded-full border border-dashed border-border px-3 py-1 text-[12px] text-text-muted">
              New conversation
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 && !isStreaming && (
            <div className="mx-auto flex max-w-2xl flex-col items-center pt-12 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-primary to-teal text-white">
                <Bot className="h-6 w-6" />
              </div>
              <h2 className="mt-4 text-[20px] font-bold">How can I help you today?</h2>
              <p className="mt-2 text-[14px] text-text-secondary">
                Ask anything about your subjects, or pick a suggestion below to get started.
              </p>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`mb-6 flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="mr-3 flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-teal text-white">
                  <Bot className="h-4 w-4" />
                </div>
              )}
              <div className={`max-w-2xl ${msg.role === 'user' ? 'text-right' : ''}`}>
                <div className="label-caps mb-1 text-text-muted">{msg.role === 'user' ? 'You' : 'AI Tutor'}</div>
                <div
                  className={
                    msg.role === 'user'
                      ? 'rounded-xl rounded-tr-sm bg-primary px-4 py-3 text-left text-[14px] text-white'
                      : 'rounded-xl rounded-tl-sm border border-border bg-card px-4 py-3 text-[14px] leading-6'
                  }
                >
                  {msg.role === 'assistant' ? (
                    <>
                      <AiMarkdown content={msg.content} isStreaming={streamingAssistantId === msg.id} />
                      {msg.tasks && msg.tasks.length > 0 && <TaskCards tasks={msg.tasks} />}
                      {msg.action && (
                        <Button className="mt-3" onClick={msg.action.onClick}>
                          {msg.action.label}
                        </Button>
                      )}
                    </>
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
              {msg.role === 'user' && <Avatar name={user?.name} size="sm" className="ml-3" />}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="sticky bottom-0 border-t border-border bg-header px-6 py-4">
          {showSuggestions && !moduleSession && (
            <div className="mx-auto mb-4 max-w-3xl rounded-2xl border border-border bg-card shadow-card">
              <div className="flex items-center justify-between border-b border-border px-4 py-3">
                <div className="flex items-center gap-2">
                  <activeSuggestions.icon className="h-4 w-4 text-text-muted" />
                  <span className="text-[14px] font-semibold">{activeSuggestions.label}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setSuggestionsOpen(false)}
                  className="rounded-lg p-1 text-text-muted hover:bg-card-hover"
                  aria-label="Dismiss suggestions"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="flex gap-1 border-b border-border px-2 py-1">
                {SUGGESTION_GROUPS.map((group) => (
                  <button
                    key={group.id}
                    type="button"
                    onClick={() => setActiveGroup(group.id)}
                    className={cn(
                      'rounded-lg px-3 py-1.5 text-[12px] font-semibold',
                      activeGroup === group.id ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-card-hover',
                    )}
                  >
                    {group.label}
                  </button>
                ))}
              </div>
              <ul className="divide-y divide-border">
                {activeSuggestions.prompts.map((prompt) => (
                  <li key={prompt}>
                    <button
                      type="button"
                      onClick={() => send(prompt)}
                      className="flex w-full items-center justify-between px-4 py-3 text-left text-[14px] hover:bg-card-hover"
                    >
                      <span>{prompt}</span>
                      <ChevronRight className="h-4 w-4 shrink-0 text-text-muted" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="mx-auto flex max-w-3xl items-center gap-2">
            <button type="button" className="rounded-lg p-2 text-text-muted hover:bg-card-hover md:hidden" onClick={() => setPanelOpen(!panelOpen)}>
              Sessions
            </button>
            <button type="button" className="hidden rounded-lg p-2 text-text-muted hover:bg-card-hover md:block">
              <Paperclip className="h-5 w-5" />
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder={moduleSession ? 'Continue this module…' : 'Message AI Tutor...'}
              className="flex-1 rounded-xl border border-border bg-input px-4 py-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <Button onClick={() => send()} disabled={isStreaming || moduleSending} className="rounded-full px-3">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
