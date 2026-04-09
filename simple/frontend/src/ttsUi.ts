/**
 * Голоса OpenAI TTS (`tts-1` / `tts-1-hd`).
 * Держим в синхроне с будущим simple-backend и с
 * `backend/app/services/openai_ops.py` (TTS_VOICE по умолчанию — alloy).
 */
export const OPENAI_TTS_VOICES = [
  "alloy",
  "echo",
  "fable",
  "onyx",
  "nova",
  "shimmer",
] as const;

export type OpenAiTtsVoice = (typeof OPENAI_TTS_VOICES)[number];

export const TTS_SPEED_MIN = 0.8;
export const TTS_SPEED_MAX = 1.2;
export const TTS_SPEED_STEP = 0.05;
export const TTS_SPEED_DEFAULT = 1.0;
export const TTS_VOICE_DEFAULT: OpenAiTtsVoice = "alloy";
