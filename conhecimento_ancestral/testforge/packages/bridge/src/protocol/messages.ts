export interface BridgeMessage {
  type: string;
  id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface RecordedStep {
  id: string;
  timestamp: string;
  action: 'click' | 'input' | 'select' | 'navigate' | 'assert';
  selector: string;
  tagInfo: string;
  value: string;
  text: string;
  domSnapshot: string;
  pageUrl: string;
  pageTechnology: string | null;
}

export interface NavigationPayload {
  url: string;
  title: string;
  technology: string | null;
}

export interface StepRecordedPayload {
  step: RecordedStep;
}

export interface RecordingStartPayload {
  url?: string;
}

export interface AssertSuggestPayload {
  selector?: string;
  text?: string;
  suggestedAssert?: string;
}

export interface ErrorPayload {
  code: string;
  message: string;
  recoverable: boolean;
}
