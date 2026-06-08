import { useMutation } from '@tanstack/react-query';
import { sendChatMessage } from '@/api/chat';
import type { TutorChatRequest } from '@/types';

export function useChat() {
  return useMutation({
    mutationFn: (payload: TutorChatRequest) => sendChatMessage(payload),
  });
}
