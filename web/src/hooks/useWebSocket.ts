import { useEffect, useRef } from "react";

type UseWebSocketOptions = {
  reconnectInterval: number;
  maxRetries: number;
  onOpen?: () => void;
  onClose?: () => void;
  onMessage?: (event: MessageEvent<string>) => void;
};

export function useWebSocket(url: string, options: UseWebSocketOptions) {
  const socketRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timeoutRef = useRef<number | null>(null);
  const optionsRef = useRef(options);

  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  useEffect(() => {
    let disposed = false;

    const connect = () => {
      if (disposed) {
        return;
      }

      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        retriesRef.current = 0;
        optionsRef.current.onOpen?.();
      };

      socket.onmessage = (event) => {
        optionsRef.current.onMessage?.(event);
      };

      socket.onclose = () => {
        optionsRef.current.onClose?.();

        if (disposed || retriesRef.current >= optionsRef.current.maxRetries) {
          return;
        }

        retriesRef.current += 1;
        timeoutRef.current = window.setTimeout(connect, optionsRef.current.reconnectInterval);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
      socketRef.current?.close();
    };
  }, [url]);

  return socketRef;
}
