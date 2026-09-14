export type WebSocketStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';

export type StreamMessageHandler = (channel: string, payload: any) => void;

export class ObservatoryWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectInterval = 3000;
  private handlers: Set<StreamMessageHandler> = new Set();
  private statusListeners: Set<(status: WebSocketStatus) => void> = new Set();
  private status: WebSocketStatus = 'DISCONNECTED';
  private shouldConnect = false;

  constructor(url: string = `ws://${window.location.host}/ws/telemetry`) {
    this.url = url;
  }

  public connect(): void {
    this.shouldConnect = true;
    this.setStatus('CONNECTING');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus('CONNECTED');
        this.subscribe(['telemetry', 'ai_state', 'alerts', 'vision']);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const channel = message.channel || 'telemetry';
          const payload = message.data || message;
          this.handlers.forEach((h) => h(channel, payload));
        } catch {
          // ignore non-json frames
        }
      };

      this.ws.onclose = () => {
        this.setStatus('DISCONNECTED');
        if (this.shouldConnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          setTimeout(() => this.connect(), this.reconnectInterval);
        }
      };

      this.ws.onerror = () => {
        this.setStatus('ERROR');
      };
    } catch {
      this.setStatus('ERROR');
      if (this.shouldConnect) {
        setTimeout(() => this.connect(), this.reconnectInterval);
      }
    }
  }

  public disconnect(): void {
    this.shouldConnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('DISCONNECTED');
  }

  public subscribe(channels: string[]): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'subscribe', channels }));
    }
  }

  public onMessage(handler: StreamMessageHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  public onStatusChange(listener: (status: WebSocketStatus) => void): () => void {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => this.statusListeners.delete(listener);
  }

  private setStatus(newStatus: WebSocketStatus): void {
    this.status = newStatus;
    this.statusListeners.forEach((l) => l(newStatus));
  }
}

export const observatoryWs = new ObservatoryWebSocket();
