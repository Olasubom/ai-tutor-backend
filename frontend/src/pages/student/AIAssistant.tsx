import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import { Bot, MessageSquare, Paperclip, Plus, Send } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/hooks/useAuth';
import { useChat } from '@/hooks/useChat';
import { getSessions, getSessionMessages } from '@/api/sessions';
import type { ChatMessage } from '@/types';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

function AiMarkdown({ content }: { content: string }) {
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
      {content}
    </ReactMarkdown>
  );
}

export default function AIAssistant() {
  const { user, learnerId } = useAuth();
  const location = useLocation();
  const chat = useChat();
  const toast = useToastStore((s) => s.add);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const sessions = useQuery({
    queryKey: ['sessions', learnerId],
    queryFn: () => getSessions(learnerId),
    enabled: !!learnerId,
  });

  const displaySessionId =
    sessionId ?? (learnerId ? `SESS-${learnerId.replace('learner_', '').slice(0, 4).toUpperCase()}-A` : null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, chat.isPending]);

  useEffect(() => {
    if (sessionStorage.getItem('aitutor_new_session')) {
      sessionStorage.removeItem('aitutor_new_session');
      setSessionId(null);
      setMessages([]);
    }
    const params = new URLSearchParams(location.search);
    const topic = params.get('topic');
    if (topic) {
      setInput(`I want to continue studying ${decodeURIComponent(topic)}. Help me with where I left off.`);
    }
  }, [location.search]);

  const loadSession = async (sid: string) => {
    const rows = await getSessionMessages(learnerId, sid);
    setSessionId(sid);
    setMessages(
      rows.map((r, i) => ({
        id: `${sid}_${i}`,
        role: r.role as 'user' | 'assistant',
        content: r.content,
        timestamp: r.timestamp,
      })),
    );
  };

  const newSession = () => {
    setSessionId(null);
    setMessages([]);
  };

  const send = async () => {
    const text = input.trim();
    if (!text || chat.isPending) return;
    setInput('');
    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((m) => [...m, userMsg]);
    try {
      const res = await chat.mutateAsync({
        learner_id: learnerId,
        message: text,
        session_id: sessionId ?? undefined,
        course_context: { subject: 'General' },
        time_budget_minutes: 45,
      });
      if (res.session_id) setSessionId(res.session_id);
      setMessages((m) => [
        ...m,
        {
          id: res.request_id,
          role: 'assistant',
          content: res.assistant_message,
          timestamp: res.timestamp,
        },
      ]);
      sessions.refetch();
    } catch {
      toast('Message failed to send. Retry?', 'error');
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
                <div className="font-semibold">{s.topics_covered[0] ?? s.subject}</div>
                <div className="text-text-muted">{s.message_count} messages</div>
              </button>
            ))
          )}
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
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
          {displaySessionId && (
            <div className="rounded-full border border-border px-3 py-1 text-[12px] font-mono text-text-muted">
              # {displaySessionId}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 && !chat.isPending && (
            <EmptyState
              icon={MessageSquare}
              title="Start a conversation"
              description="Ask the AI Tutor anything about your subjects. Type a question or try: 'What should I study today?'"
            />
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
                  {msg.role === 'assistant' ? <AiMarkdown content={msg.content} /> : msg.content}
                </div>
              </div>
              {msg.role === 'user' && <Avatar name={user?.name} size="sm" className="ml-3" />}
            </div>
          ))}
          {chat.isPending && <Skeleton className="h-12 max-w-md" />}
          <div ref={bottomRef} />
        </div>

        <div className="sticky bottom-0 border-t border-border bg-header px-6 py-4">
          <div className="flex items-center gap-2">
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
              placeholder="Message AI Tutor..."
              className="flex-1 rounded-xl border border-border bg-input px-4 py-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <Button onClick={send} disabled={chat.isPending} className="rounded-full px-3">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
