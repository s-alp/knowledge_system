export type ClippingAxis = "x" | "y" | "z";

export interface ClippingState {
  enabled: boolean;
  axis: ClippingAxis;
  value: number;
  min: number;
  max: number;
}

export interface Viewer3DDisplayState {
  edgeHighlightEnabled: boolean;
  capSupported: boolean | null;
}

export const initialClippingState: ClippingState = {
  enabled: false,
  axis: "z",
  value: 0,
  min: -1,
  max: 1,
};

export type ClippingAction =
  | { type: "toggle" }
  | { type: "setAxis"; axis: ClippingAxis }
  | { type: "setValue"; value: number }
  | { type: "setBounds"; min: number; max: number };

export function clippingReducer(state: ClippingState, action: ClippingAction): ClippingState {
  // 断面 UI は Scene と独立して更新し、3D 描画側には確定値だけを渡す。
  switch (action.type) {
    case "toggle":
      return { ...state, enabled: !state.enabled };
    case "setAxis":
      return { ...state, axis: action.axis };
    case "setValue":
      return { ...state, value: action.value };
    case "setBounds": {
      const midpoint = Number(((action.min + action.max) / 2).toFixed(3));
      return { ...state, min: action.min, max: action.max, value: midpoint };
    }
    default:
      return state;
  }
}
