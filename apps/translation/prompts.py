from typing import Dict


class TranslationPrompts:
    """Manages translation prompts for different models and directions."""

    @staticmethod
    def get_system_prompt(model_name: str, source_lang: str, target_lang: str) -> str:
        """
        Generate system prompt for translation.

        Args:
            model_name: Model name (Strain, Article, Terpene)
            source_lang: Source language code (en, es)
            target_lang: Target language code (en, es)

        Returns:
            System prompt string
        """
        lang_full = {
            'en': 'English',
            'es': 'Spanish',
        }

        source_full = lang_full.get(source_lang, source_lang.upper())
        target_full = lang_full.get(target_lang, target_lang.upper())

        # Get SEO-optimized terminology rules based on translation direction
        seo_rules = TranslationPrompts._get_seo_terminology_rules(source_lang, target_lang)

        # Get internal links handling rules based on translation direction
        links_rules = TranslationPrompts._get_internal_links_rules(source_lang, target_lang)

        base_prompt = f"""You are a professional translator specializing in cannabis industry content.
Translate from {source_full} to {target_full}.

CRITICAL RULES:
1. Keep strain names UNCHANGED (e.g., "Northern Lights", "OG Kush", "White Widow")
2. Preserve ALL HTML tags exactly as they appear (e.g., <p>, <h3>, <strong>, <a>)
3. Keep measurement units unchanged (%, mg/g, THC, CBD, CBG)
4. Maintain technical cannabis terminology accuracy
5. Keep terpene names in English (Limonene, Myrcene, Pinene, etc.)
6. Preserve the tone and style of the original text

{links_rules}

FORMATTING RULES:
8. Use ONLY standard ASCII punctuation marks
9. NEVER use em-dashes (—), en-dashes (–) - use regular hyphens (-) instead
10. NEVER add hidden or special Unicode characters (zero-width spaces, soft hyphens, etc.)
11. NEVER add unnecessary special symbols in any encoding
12. Use only standard letters, numbers, and basic punctuation (. , ! ? ; : - " ' ( ))
13. Keep text clean and readable - no invisible characters

{seo_rules}

OUTPUT FORMAT:
Return ONLY a valid JSON object with field names as keys and translations as values.
Example: {{"title": "translated title", "description": "translated description"}}

DO NOT include explanations, comments, markdown code blocks, or any text outside the JSON object.
Return raw JSON only.

{TranslationPrompts._get_model_specific_instructions(model_name)}"""

        return base_prompt

    @staticmethod
    def _get_internal_links_rules(source_lang: str, target_lang: str) -> str:
        """
        Get internal links handling rules based on translation direction.

        Important for SEO: Each language version needs language-specific URLs.
        """
        if source_lang == 'es' and target_lang == 'en':
            return """
INTERNAL LINKS RULES (Spanish → English):
7. Transform internal links to include /en/ prefix for English version:
   - href="/strain/..." → href="/en/strain/..."
   - href="/strains" → href="/en/strains"
   - href="/articles/..." → href="/en/articles/..."
   - href="/article/..." → href="/en/article/..."
   - href="/terpenes/..." → href="/en/terpenes/..."
   - href="/terpene/..." → href="/en/terpene/..."
   - href="/store/..." → href="/en/store/..."

8. DO NOT modify external links (starting with http:// or https://)
9. DO NOT modify links that already have /en/ prefix
10. DO NOT modify admin, static, or media links (/admin/, /static/, /media/)

Examples:
- <a href="/strain/northern-lights/">Northern Lights</a>
  → <a href="/en/strain/northern-lights/">Northern Lights</a>

- <a href="/articles/cannabis-guide/">guide</a>
  → <a href="/en/articles/cannabis-guide/">guide</a>
"""
        elif source_lang == 'en' and target_lang == 'es':
            return """
INTERNAL LINKS RULES (English → Spanish):
7. Transform internal links to REMOVE /en/ prefix for Spanish version:
   - href="/en/strain/..." → href="/strain/..."
   - href="/en/strains" → href="/strains"
   - href="/en/articles/..." → href="/articles/..."
   - href="/en/article/..." → href="/article/..."
   - href="/en/terpenes/..." → href="/terpenes/..."
   - href="/en/terpene/..." → href="/terpene/..."
   - href="/en/store/..." → href="/store/..."

8. DO NOT modify external links (starting with http:// or https://)
9. DO NOT modify links that don't have /en/ prefix
10. DO NOT modify admin, static, or media links (/admin/, /static/, /media/)

Examples:
- <a href="/en/strain/northern-lights/">Northern Lights</a>
  → <a href="/strain/northern-lights/">Northern Lights</a>

- <a href="/en/articles/cannabis-guide/">guide</a>
  → <a href="/articles/cannabis-guide/">guide</a>
"""
        else:
            return ""

    @staticmethod
    def _get_seo_terminology_rules(source_lang: str, target_lang: str) -> str:
        """
        Get SEO-optimized terminology rules based on translation direction.

        Uses popular search terms for better SEO performance in each language.
        """
        if source_lang == 'es' and target_lang == 'en':
            return """
SEO TERMINOLOGY RULES (Spanish → English):
- "variedad de cannabis" → use "weed strain" or "marijuana strain" (more popular search terms)
- "variedad" (variety) → use "strain" or "weed" in context
- "cannabis" → can use "weed", "marijuana", or "cannabis" depending on context
- "marihuana" → translate as "marijuana" or "weed" (both are popular)

IMPORTANT: Use "weed" and "strain" frequently in keywords and descriptions for better SEO.
These are the most searched terms in English-speaking markets.

Examples:
- "variedad Pink Rozay" → "Pink Rozay weed strain" or "Pink Rozay marijuana strain"
- "información sobre la variedad" → "information about this weed strain" or "learn about this strain"
- "efectos de esta variedad" → "effects of this marijuana strain" or "this weed's effects"
"""
        elif source_lang == 'en' and target_lang == 'es':
            return """
SEO TERMINOLOGY RULES (English → Spanish):
- "weed strain" → translate as "variedad de cannabis" (most popular in Spanish)
- "marijuana strain" → translate as "variedad de cannabis" or "variedad de marihuana"
- "weed" → translate as "cannabis" or "marihuana" depending on context
- "strain" → translate as "variedad" when referring to cannabis strains

IMPORTANT: Use "variedad de cannabis" consistently in keywords and descriptions for better SEO.
This is the most searched term in Spanish-speaking markets.

Examples:
- "Pink Rozay weed strain" → "variedad de cannabis Pink Rozay"
- "learn about this strain" → "información sobre esta variedad de cannabis"
- "this weed's effects" → "efectos de esta variedad de cannabis"
"""
        else:
            return ""

    @staticmethod
    def _get_model_specific_instructions(model_name: str) -> str:
        """Get model-specific translation instructions."""
        instructions = {
            'Strain': """
STRAIN-SPECIFIC INSTRUCTIONS:
- Preserve genetic lineage terms (Indica, Sativa, Hybrid) in English
- Keep terpene names in English (e.g., "Limonene", "Myrcene")
- Translate effects and feelings naturally
- Maintain professional, informative tone
- Preserve HTML structure in text_content field
- Translate img_alt_text descriptively for accessibility
""",
            'Article': """
ARTICLE-SPECIFIC INSTRUCTIONS:
- Maintain journalistic tone and style
- Keep H3 heading IDs unchanged (e.g., id="h-some-heading")
- Preserve all HTML formatting
- Translate naturally while keeping technical terms accurate
- Keep proper nouns (strain names, brand names) unchanged
""",
            'Terpene': """
TERPENE-SPECIFIC INSTRUCTIONS:
- Keep chemical compound names in English
- Translate effects and descriptions naturally
- Maintain scientific accuracy
- Preserve professional, educational tone
""",
        }

        return instructions.get(model_name, '')

    @staticmethod
    def format_user_prompt(fields: Dict[str, str]) -> str:
        """
        Format user prompt with fields to translate.

        Args:
            fields: Dictionary of field_name: content_to_translate

        Returns:
            Formatted user prompt
        """
        import json
        return json.dumps(fields, ensure_ascii=False, indent=2)
