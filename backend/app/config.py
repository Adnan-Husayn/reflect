from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    max_text_characters: int = 5000
    max_audio_bytes: int = 10 * 1024 * 1024
    max_image_bytes: int = 5 * 1024 * 1024
    # Provisional. Derive empirically from held-out data before publishing
    # any accuracy claim about conflict detection.
    conflict_threshold: float = 0.35
    # Late-fusion weights. Equal by default and deliberately provisional:
    # derive them from per-modality reliability on held-out labelled data
    # (RAVDESS) rather than by taste, the same way as the threshold above.
    fusion_weight_text: float = 1.0
    fusion_weight_voice: float = 1.0
    fusion_weight_face: float = 1.0

    def fusion_weights(self) -> dict[str, float]:
        return {
            "text": self.fusion_weight_text,
            "voice": self.fusion_weight_voice,
            "face": self.fusion_weight_face,
        }

    hf_home: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
