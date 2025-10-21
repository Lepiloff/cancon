from modeltranslation.translator import translator, TranslationOptions
from apps.strains.models import (
    Strain,
    Article,
    Terpene,
    Feeling,
    Negative,
    HelpsWith,
    Flavor,
)


class StrainTranslationOptions(TranslationOptions):
    # NOTE: 'name' is NOT translated - strain names remain in English
    fields = ('title', 'description', 'text_content', 'keywords', 'img_alt_text')
    required_languages = ('en',)  # English is required


class ArticleTranslationOptions(TranslationOptions):
    fields = ('title', 'description', 'text_content', 'keywords')
    required_languages = ('en',)


class TerpeneTranslationOptions(TranslationOptions):
    # NOTE: 'name' is NOT translated - terpene names remain in English (Limonene, Myrcene, etc.)
    fields = ('description',)
    required_languages = ('en',)


class FeelingTranslationOptions(TranslationOptions):
    # Feelings are translated: "Happy" -> "Feliz"
    fields = ('name',)
    required_languages = ('en',)


class NegativeTranslationOptions(TranslationOptions):
    # Negatives are translated: "Dry mouth" -> "Boca seca"
    fields = ('name',)
    required_languages = ('en',)


class HelpsWithTranslationOptions(TranslationOptions):
    # Conditions are translated: "Anxiety" -> "Ansiedad"
    fields = ('name',)
    required_languages = ('en',)


class FlavorTranslationOptions(TranslationOptions):
    # Flavors are translated: "Sweet" -> "Dulce"
    fields = ('name',)
    required_languages = ('en',)


# Register all models
translator.register(Strain, StrainTranslationOptions)
translator.register(Article, ArticleTranslationOptions)
translator.register(Terpene, TerpeneTranslationOptions)
translator.register(Feeling, FeelingTranslationOptions)
translator.register(Negative, NegativeTranslationOptions)
translator.register(HelpsWith, HelpsWithTranslationOptions)
translator.register(Flavor, FlavorTranslationOptions)
