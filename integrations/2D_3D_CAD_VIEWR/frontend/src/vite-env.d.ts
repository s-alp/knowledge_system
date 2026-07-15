/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_LOCAL_FILE_ENABLED?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
