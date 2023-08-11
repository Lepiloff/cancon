from pytest_factoryboy import register


from apps.strains.factories import (
    StrainFactory,
    ArticleFactory,
    ArticleImageFactory,
    ArticleCategoryFactory,
    FeelingFactory,
    NegativeFactory,
    HelpsWithFactory,
    FlavorFactory,
    TerpeneFactory
)


register(StrainFactory)
register(ArticleFactory)
register(ArticleImageFactory)
register(ArticleCategoryFactory)
register(FeelingFactory)
register(NegativeFactory)
register(HelpsWithFactory)
register(FlavorFactory)
register(TerpeneFactory)
