import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { lecturerAiChat } from '@/api/lecturerDashboard';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

const PROMPTS = [
  'Who is struggling most in my courses?',
  'Generate 5 MCQs on Offer and Acceptance',
  'What topics need more attention this week?',
  'Suggest an intervention for at-risk students',
];

export default function LecturerAIAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content:
        "Good day. I'm your AI teaching assistant, here to support your work across courses.\n\n" +
        "I can help you:\n\n" +
        '- **Review student performance** — e.g. "Who is struggling in CIL 201?"\n' +
        '- **Draft quiz questions** — e.g. "Create 5 MCQs on Offer and Acceptance"\n' +
        '- **Recommend interventions** for students flagged at risk\n' +
        '- **Answer questions** about your uploaded course materials\n\n' +
        "Select a course above, then let me know what you'd like to work on.",
    },
  ]);
  const [input, setInput] = useState('');
  const activeCourseId = localStorage.getItem('lecturerActiveCourseId') || undefined;

  const sendMut = useMutation({
    mutationFn: (message: string) => lecturerAiChat({ message, course_id: activeCourseId }),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content: data.message },
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Sorry, I could not reach the assistant. Please try again.',
        },
      ]);
    },
  });

  const handleSend = () => {
    const text = input.trim();
    if (!text || sendMut.isPending) return;
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: text }]);
    setInput('');
    sendMut.mutate(text);
  };

  return (
    <div className="flex min-h-[calc(100vh-8rem)] flex-col">
      <div className="border-b border-border pb-4">
        <Badge variant="muted">AI ASSISTANT</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold">AI Teaching Assistant</h1>
        <p className="text-text-secondary">
          Ask about student performance, generate quizzes, or get pedagogical advice.
          {activeCourseId && (
            <span className="ml-1 text-text-muted">(Using selected course context)</span>
          )}
        </p>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto py-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === 'user' ? 'bg-primary text-white' : 'border border-border bg-card'
              }`}
            >
              {msg.role === 'assistant' ? (
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}
        {sendMut.isPending && (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-border bg-card px-4 py-3 text-sm text-text-muted animate-pulse">
              Thinking…
            </div>
          </div>
        )}
      </div>

      {messages.length === 1 && (
        <div className="flex flex-wrap gap-2 pb-2">
          {PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => setInput(prompt)}
              className="rounded-full border border-border px-3 py-1 text-xs text-text-secondary hover:bg-card-hover"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      <div className="border-t border-border pt-4">
        <div className="flex gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask about your students, generate quizzes, or get advice…"
            className="flex-1 rounded-xl border border-border bg-input px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <Button disabled={!input.trim() || sendMut.isPending} onClick={handleSend}>
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
