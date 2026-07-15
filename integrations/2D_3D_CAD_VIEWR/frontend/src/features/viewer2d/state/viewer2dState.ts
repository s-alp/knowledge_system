export interface TwoDViewportState {
  scale: number;
  rotation: number;
  offsetX: number;
  offsetY: number;
}

export const initialTwoDViewportState: TwoDViewportState = {
  scale: 1,
  rotation: 0,
  offsetX: 0,
  offsetY: 0,
};

export type TwoDViewportAction =
  | { type: "zoom"; delta: number }
  | {
      type: "zoomAt";
      delta: number;
      anchorX: number;
      anchorY: number;
      stageWidth: number;
      stageHeight: number;
    }
  | { type: "rotate"; direction: "left" | "right" }
  | { type: "pan"; deltaX: number; deltaY: number }
  | { type: "reset" };

function clampViewportScale(scale: number): number {
  return Number(Math.max(0.2, Math.min(8, scale)).toFixed(2));
}

function rotatePoint(x: number, y: number, radians: number) {
  return {
    x: x * Math.cos(radians) - y * Math.sin(radians),
    y: x * Math.sin(radians) + y * Math.cos(radians),
  };
}

export function twoDViewportReducer(
  state: TwoDViewportState,
  action: TwoDViewportAction,
): TwoDViewportState {
  // 2D 操作は独立 reducer に寄せ、ページ本体がズーム/回転の詳細を持たないようにする。
  switch (action.type) {
    case "zoom": {
      return { ...state, scale: clampViewportScale(state.scale + action.delta) };
    }
    case "zoomAt": {
      const nextScale = clampViewportScale(state.scale + action.delta);
      if (nextScale === state.scale) {
        return state;
      }

      const anchorScreenX = action.anchorX - action.stageWidth / 2;
      const anchorScreenY = action.anchorY - action.stageHeight / 2;
      const rotationRadians = (state.rotation * Math.PI) / 180;
      const anchorFromOffsetX = anchorScreenX - state.offsetX;
      const anchorFromOffsetY = anchorScreenY - state.offsetY;
      const unrotated = rotatePoint(anchorFromOffsetX, anchorFromOffsetY, -rotationRadians);
      const pageX = unrotated.x / state.scale;
      const pageY = unrotated.y / state.scale;
      const rerotated = rotatePoint(pageX * nextScale, pageY * nextScale, rotationRadians);

      return {
        ...state,
        scale: nextScale,
        offsetX: Number((anchorScreenX - rerotated.x).toFixed(2)),
        offsetY: Number((anchorScreenY - rerotated.y).toFixed(2)),
      };
    }
    case "rotate":
      return {
        ...state,
        rotation: (state.rotation + (action.direction === "left" ? -90 : 90) + 360) % 360,
      };
    case "pan":
      return {
        ...state,
        offsetX: state.offsetX + action.deltaX,
        offsetY: state.offsetY + action.deltaY,
      };
    case "reset":
      return initialTwoDViewportState;
    default:
      return state;
  }
}
