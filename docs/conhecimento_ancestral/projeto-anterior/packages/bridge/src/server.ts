import { WebSocketServer, WebSocket } from 'ws';
import { BridgeMessage, RecordedStep } from './protocol/messages';

const PORT = parseInt(process.env.TESTFORGE_BRIDGE_PORT || '9199', 10);

interface ClientInfo {
  ws: WebSocket;
  type: 'core' | 'overlay';
  id: string;
}

class BridgeServer {
  private wss: WebSocketServer;
  private clients: Map<string, ClientInfo> = new Map();
  private steps: RecordedStep[] = [];

  constructor() {
    this.wss = new WebSocketServer({ port: PORT });
    this.wss.on('listening', () => {
      console.log(`[TestForge Bridge] Servidor WebSocket rodando em ws://localhost:${PORT}`);
    });
    this.wss.on('connection', (ws) => this.handleConnection(ws));
    this.wss.on('error', (err) => {
      console.error('[TestForge Bridge] Erro no servidor:', err.message);
    });
  }

  private handleConnection(ws: WebSocket) {
    const id = `client_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const client: ClientInfo = { ws, type: 'overlay', id };
    this.clients.set(id, client);

    console.log(`[TestForge Bridge] Cliente conectado: ${id}`);

    ws.on('message', (raw) => {
      try {
        const msg: BridgeMessage = JSON.parse(raw.toString());
        this.handleMessage(id, msg);
      } catch (err) {
        console.warn(`[TestForge Bridge] Mensagem inválida de ${id}:`, raw.toString().substring(0, 200));
      }
    });

    ws.on('close', () => {
      console.log(`[TestForge Bridge] Cliente desconectado: ${id}`);
      this.clients.delete(id);
    });

    ws.on('error', () => {
      this.clients.delete(id);
    });
  }

  private handleMessage(clientId: string, msg: BridgeMessage) {
    const client = this.clients.get(clientId);
    if (!client) return;

    switch (msg.type) {
      case 'step:recorded': {
        const step = msg.payload as unknown as RecordedStep;
        if (step && step.id) {
          this.steps.push(step);
        }
        this.relayToCore(msg);
        break;
      }
      case 'navigation:detected':
      case 'recording:paused':
      case 'recording:resumed': {
        this.relayToCore(msg);
        break;
      }
      case 'recording:stop': {
        const result = {
          type: 'recording:completed',
          id: 'msg_' + Date.now(),
          timestamp: new Date().toISOString(),
          payload: { steps: this.steps, stepCount: this.steps.length },
        };
        this.sendToCore(result);
        this.steps = [];
        break;
      }
      case 'ping': {
        this.sendTo(clientId, { type: 'pong', id: msg.id, timestamp: new Date().toISOString(), payload: {} });
        break;
      }
      default: {
        this.relayToCore(msg);
      }
    }
  }

  private relayToCore(msg: BridgeMessage) {
    for (const [, client] of this.clients) {
      if (client.type === 'core' && client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(JSON.stringify(msg));
      }
    }
  }

  sendToCore(msg: BridgeMessage) {
    for (const [, client] of this.clients) {
      if (client.type === 'core' && client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(JSON.stringify(msg));
      }
    }
  }

  sendTo(clientId: string, msg: BridgeMessage) {
    const client = this.clients.get(clientId);
    if (client && client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify(msg));
    }
  }

  broadcast(msg: BridgeMessage) {
    for (const [, client] of this.clients) {
      if (client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(JSON.stringify(msg));
      }
    }
  }
}

const server = new BridgeServer();

process.on('SIGINT', () => {
  console.log('[TestForge Bridge] Encerrando...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('[TestForge Bridge] Encerrando...');
  process.exit(0);
});
