import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { WebSocketMessage, RealtimeUpdate } from '../types/index';
import { toast } from 'sonner';

interface UseWebSocketOptions {
  url: string;
  enabled?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export function useWebSocket(options: UseWebSocketOptions) {
  const {
    url,
    enabled = true,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    onMessage,
    onError,
    onOpen,
    onClose,
  } = options;

  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimer = useRef<NodeJS.Timeout>();
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');

  const queryClient = useQueryClient();

  const connect = () => {
    if (!enabled || ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      setConnectionState('connecting');
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setConnectionState('connected');
        reconnectCount.current = 0;
        onOpen?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onclose = () => {
        setConnectionState('disconnected');
        onClose?.();
        
        // Attempt to reconnect
        if (enabled && reconnectCount.current < reconnectAttempts) {
          reconnectCount.current++;
          reconnectTimer.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      ws.current.onerror = (error) => {
        setConnectionState('error');
        onError?.(error);
      };
    } catch (error) {
      setConnectionState('error');
      console.error('WebSocket connection failed:', error);
    }
  };

  const disconnect = () => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    
    setConnectionState('disconnected');
  };

  const sendMessage = (message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  };

  const handleMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'NEW_FEEDBACK':
        // Invalidate relevant queries when new feedback is received
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        queryClient.invalidateQueries({ queryKey: ['feedback'] });
        queryClient.invalidateQueries({ queryKey: ['task-aggregation'] });
        break;

      case 'AGGREGATION_COMPLETE':
        // Invalidate aggregation and task queries
        queryClient.invalidateQueries({ queryKey: ['task-aggregation'] });
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        queryClient.invalidateQueries({ queryKey: ['analytics'] });
        
        toast.info('Task aggregation completed!');
        break;

      case 'TASK_UPDATE':
        // Invalidate task-related queries
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        
        if (message.data?.taskId) {
          queryClient.invalidateQueries({ queryKey: ['task', message.data.taskId] });
        }
        break;

      case 'AUTHORITY_UPDATE':
        // Invalidate user authority queries
        if (message.data?.userId) {
          queryClient.invalidateQueries({ queryKey: ['user-authority', message.data.userId] });
          queryClient.invalidateQueries({ queryKey: ['user', message.data.userId] });
        }
        
        queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
        break;

      default:
        console.log('Unhandled WebSocket message type:', message.type);
    }
  };

  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, url]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  return {
    connectionState,
    sendMessage,
    connect,
    disconnect,
  };
}

// Specialized hook for real-time task updates
export function useTaskRealtimeUpdates(taskId?: number) {
  const wsUrl = taskId ? `ws://localhost:8000/ws/task/${taskId}` : '';
  
  return useWebSocket({
    url: wsUrl,
    enabled: !!taskId,
    onMessage: (message) => {
      // Task-specific message handling
      console.log('Task update:', message);
    },
  });
}

// Hook for global system updates
export function useSystemRealtimeUpdates() {
  return useWebSocket({
    url: 'ws://localhost:8000/ws/system',
    enabled: true,
    onMessage: (message) => {
      // System-wide message handling
      console.log('System update:', message);
    },
  });
}