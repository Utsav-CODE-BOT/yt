"""Multilingual Translation Engine for Autonomous Faceless Shorts Factory.

Translates master video scripts and metadata into Kannada, Hindi, Telugu, and Tamil
while preserving narrative hook strength, scene cuts, factual accuracy, and pacing.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("factory.translator")

# Language configuration matrix
LANGUAGE_SPECS: Dict[str, Dict[str, Any]] = {
    "kannada": {
        "code": "kn-IN",
        "iso": "kn",
        "name": "Kannada",
        "native_name": "ಕನ್ನಡ",
        "default_voice": "kn-IN-GaganNeural",
        "female_voice": "kn-IN-SapnaNeural",
        "gtts_code": "kn",
        "hashtags": ["#KannadaShorts", "#KannadaFacts", "#Kannada", "#Karnataka", "#Shorts"],
        "discovery_tags": ["kannada facts", "kannada shorts", "kannada science", "kannada information"],
        "title_suffix": "#Shorts #Kannada",
    },
    "hindi": {
        "code": "hi-IN",
        "iso": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "default_voice": "hi-IN-MadhurNeural",
        "female_voice": "hi-IN-SwaraNeural",
        "gtts_code": "hi",
        "hashtags": ["#HindiShorts", "#HindiFacts", "#FactsInHindi", "#Hindi", "#Shorts"],
        "discovery_tags": ["hindi facts", "hindi shorts", "science in hindi", "rochak tathya"],
        "title_suffix": "#Shorts #Hindi",
    },
    "telugu": {
        "code": "te-IN",
        "iso": "te",
        "name": "Telugu",
        "native_name": "తెలుగు",
        "default_voice": "te-IN-MohanNeural",
        "female_voice": "te-IN-ShrutiNeural",
        "gtts_code": "te",
        "hashtags": ["#TeluguShorts", "#TeluguFacts", "#FactsInTelugu", "#Telugu", "#Shorts"],
        "discovery_tags": ["telugu facts", "telugu shorts", "telugu science", "telugu vishayalu"],
        "title_suffix": "#Shorts #Telugu",
    },
    "tamil": {
        "code": "ta-IN",
        "iso": "ta",
        "name": "Tamil",
        "native_name": "தமிழ்",
        "default_voice": "ta-IN-ValluvarNeural",
        "female_voice": "ta-IN-PallaviNeural",
        "gtts_code": "ta",
        "hashtags": ["#TamilShorts", "#TamilFacts", "#FactsInTamil", "#Tamil", "#Shorts"],
        "discovery_tags": ["tamil facts", "tamil shorts", "tamil science", "tamil arivom"],
        "title_suffix": "#Shorts #Tamil",
    },
}


@dataclass
class LocalizedScript:
    language: str
    title: str
    hook: str
    lines: List[Dict[str, Any]]
    full_text: str
    word_count: int


@dataclass
class LocalizedMetadata:
    language: str
    title: str
    description: str
    tags: List[str]
    category_id: str
    default_language: str
    default_audio_language: str


class MultilingualTranslator:
    """Translates master scripts and YouTube metadata into target Indian languages."""

    def __init__(self, preferred_provider: str = "mymemory"):
        self.preferred_provider = preferred_provider
        self._cache: Dict[str, str] = {}

    def translate_text(self, text: str, target_lang: str) -> str:
        """Translate a single sentence or text fragment into the target language with robust fallback."""
        cleaned_text = text.strip()
        if not cleaned_text:
            return ""

        target_lang = target_lang.lower().strip()
        spec = LANGUAGE_SPECS.get(target_lang)
        if not spec:
            raise ValueError(f"Unsupported target language: {target_lang}")

        cache_key = f"{target_lang}:{cleaned_text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        target_code = spec["code"]
        translated = ""

        # Tier 1: MyMemoryTranslator via deep-translator
        try:
            from deep_translator import MyMemoryTranslator
            tr = MyMemoryTranslator(source="en-US", target=target_code)
            res = tr.translate(cleaned_text)
            if res and isinstance(res, str) and len(res.strip()) > 0:
                translated = res.strip()
        except Exception as e:
            logger.debug("MyMemory translation failed for '%s' (%s): %s", cleaned_text[:20], target_lang, e)

        # Tier 2: GoogleTranslator fallback
        if not translated:
            try:
                from deep_translator import GoogleTranslator
                gtr = GoogleTranslator(source="en", target=spec["iso"])
                res = gtr.translate(cleaned_text)
                if res and isinstance(res, str) and len(res.strip()) > 0:
                    translated = res.strip()
            except Exception as e:
                logger.debug("GoogleTranslator fallback failed for '%s' (%s): %s", cleaned_text[:20], target_lang, e)

        # Tier 3: If external translation fails, use cleaned original
        if not translated:
            logger.warning("All translation tiers failed for '%s' -> %s. Retaining text.", cleaned_text[:30], target_lang)
            translated = cleaned_text

        self._cache[cache_key] = translated
        return translated

    def translate_script_lines(
        self,
        master_lines: List[Dict[str, Any]],
        target_lang: str,
    ) -> List[Dict[str, Any]]:
        """Translate line cuts 1:1, preserving cuts, gaps, and generating Indic caption chunks."""
        spec = LANGUAGE_SPECS.get(target_lang.lower())
        if not spec:
            raise ValueError(f"Unsupported language: {target_lang}")

        localized_lines: List[Dict[str, Any]] = []

        for idx, line in enumerate(master_lines):
            eng_text = line.get("text", "")
            gap = line.get("gap", 0.18)

            translated_text = self.translate_text(eng_text, target_lang)

            # Generate natural caption highlights for Indic script
            # Select words to emphasize
            words = [w for w in re.split(r"\s+", translated_text) if w.strip()]
            if words:
                # Highlight the longest or most prominent content word
                longest_idx = max(range(len(words)), key=lambda i: len(words[i]))
                highlighted_caps = " ".join(
                    [f"*{w}" if i == longest_idx else w for i, w in enumerate(words)]
                )
            else:
                highlighted_caps = translated_text

            localized_lines.append({
                "text": translated_text,
                "caps": highlighted_caps,
                "gap": gap,
            })

            # Small polite pause between batch calls
            time.sleep(0.05)

        return localized_lines

    def translate_script(
        self,
        master_title: str,
        master_hook: str,
        master_lines: List[Dict[str, Any]],
        target_lang: str,
    ) -> LocalizedScript:
        """Translate the full script package for a single language version."""
        logger.info("Translating script into %s...", target_lang.capitalize())
        translated_hook = self.translate_text(master_hook, target_lang)
        translated_title = self.translate_text(master_title, target_lang)
        translated_lines = self.translate_script_lines(master_lines, target_lang)

        # Ensure line 0 starts with the translated hook text
        if translated_lines and translated_hook:
            translated_lines[0]["text"] = translated_hook

        full_text = " ".join(l["text"] for l in translated_lines)
        word_count = len(full_text.split())

        logger.info(
            "[%s] Translation complete: %d lines, %d words.",
            target_lang.upper(),
            len(translated_lines),
            word_count,
        )

        return LocalizedScript(
            language=target_lang,
            title=translated_title,
            hook=translated_hook,
            lines=translated_lines,
            full_text=full_text,
            word_count=word_count,
        )

    def generate_localized_metadata(
        self,
        topic_title: str,
        niche: str,
        hook: str,
        script_text: str,
        target_lang: str,
        source_url: str = "",
        source_title: str = "",
    ) -> LocalizedMetadata:
        """Generate localized YouTube title (<60 chars), description, tags, and language metadata."""
        spec = LANGUAGE_SPECS[target_lang.lower()]
        translated_hook = self.translate_text(hook, target_lang)
        clean_hook = re.sub(r"[.!?]+$", "", translated_hook).strip()

        # 1. YouTube Shorts Title (<60 chars, with localized tag)
        title_suffix = spec["title_suffix"]
        max_hook_len = 58 - len(title_suffix)
        if len(clean_hook) <= max_hook_len:
            yt_title = f"{clean_hook} {title_suffix}".strip()
        else:
            truncated = clean_hook[:max_hook_len].rsplit(" ", 1)[0]
            yt_title = f"{truncated}... {title_suffix}".strip()

        # 2. Localized Description
        trans_topic = self.translate_text(topic_title, target_lang)
        native_lang_name = spec["native_name"]

        desc_paragraphs = [
            f"{clean_hook}.",
            "",
            f"{trans_topic} ({native_lang_name}) - {niche}",
            "",
            "Sources & Further Reading:",
            f"- {source_title or 'Authoritative Scientific Research'}: {source_url or 'https://wikipedia.org'}",
            "",
            " ".join(spec["hashtags"]),
        ]
        description = "\n".join(desc_paragraphs)

        # 3. Localized Tags
        tags = list(dict.fromkeys(
            spec["hashtags"] +
            spec["discovery_tags"] +
            ["shorts", "facts", "educational", "curiosity", target_lang]
        ))[:15]

        # Category: Education (27) or Science & Tech (28)
        category_id = "28" if ("Technology" in niche or "Space" in niche) else "27"

        return LocalizedMetadata(
            language=target_lang,
            title=yt_title,
            description=description,
            tags=tags,
            category_id=category_id,
            default_language=spec["iso"],
            default_audio_language=spec["iso"],
        )
