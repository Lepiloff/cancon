import random

from django.utils.text import slugify
import factory

from apps.strains.models import (
    Strain, Article, ArticleImage, ArticleCategory,
    Feeling, Negative, HelpsWith, Flavor, Terpene, AlternativeStrainName
)


class BaseTextFactory(factory.django.DjangoModelFactory):
    title = factory.Faker('sentence')
    text_content = factory.Faker('paragraph')
    description = factory.Faker('sentence')
    keywords = factory.Faker('word')
    canonical_url = factory.Faker('url')

    class Meta:
        abstract = True


class FeelingFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"feeling_{n}")

    class Meta:
        model = Feeling


class NegativeFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"negative_{n}")

    class Meta:
        model = Negative


class HelpsWithFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"helpswith_{n}")

    class Meta:
        model = HelpsWith


class FlavorFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"flavor_{n}")

    class Meta:
        model = Flavor


class TerpeneFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"terpene_{n}")
    description = factory.Faker('sentence')

    class Meta:
        model = Terpene


class StrainFactory(BaseTextFactory):
    name = factory.Faker('name')
    cbd = factory.Faker('pydecimal', right_digits=2, max_value=10, positive=True)
    thc = factory.Faker('pydecimal', right_digits=2, max_value=30, positive=True)
    cbg = factory.Faker('pydecimal', right_digits=2, max_value=10, positive=True)
    rating = factory.Faker('pydecimal', right_digits=1, max_value=5, positive=True)
    img_alt_text = factory.Faker('sentence')
    category = factory.Iterator(['Hybrid', 'Sativa', 'Indica'])
    feelings = factory.RelatedFactoryList(FeelingFactory, size=3)
    negatives = factory.RelatedFactoryList(NegativeFactory, size=3)
    helps_with = factory.RelatedFactoryList(HelpsWithFactory, size=3)
    flavors = factory.RelatedFactoryList(FlavorFactory, size=3)
    dominant_terpene = factory.SubFactory(TerpeneFactory)
    other_terpenes = factory.RelatedFactoryList(TerpeneFactory, size=3)
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    active = True
    top = factory.Faker('boolean')
    main = factory.Faker('boolean')
    is_review = factory.Faker('boolean')

    class Meta:
        model = Strain
        skip_postgeneration_save = True

    @factory.post_generation
    def feelings(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.feelings.add(*extracted)
        else:
            feelings = FeelingFactory.create_batch(3)
            self.feelings.add(*feelings)

    @factory.post_generation
    def negatives(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.negatives.add(*extracted)
        else:
            negatives = NegativeFactory.create_batch(3)
            self.negatives.add(*negatives)

    @factory.post_generation
    def helps_with(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.helps_with.add(*extracted)
        else:
            helps = HelpsWithFactory.create_batch(3)
            self.helps_with.add(*helps)

    @factory.post_generation
    def flavors(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.flavors.add(*extracted)
        else:
            flavors = FlavorFactory.create_batch(3)
            self.flavors.add(*flavors)

    @factory.post_generation
    def other_terpenes(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.other_terpenes.add(*extracted)
        else:
            terpenes = TerpeneFactory.create_batch(3)
            self.other_terpenes.add(*terpenes)


class AlternativeNameFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('word')
    strain = factory.SubFactory(StrainFactory)

    class Meta:
        model = AlternativeStrainName


class ArticleCategoryFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Category {n}"[:10])

    class Meta:
        model = ArticleCategory


class ArticleFactory(BaseTextFactory):
    category = factory.Iterator(ArticleCategory.objects.all())
    slug = factory.LazyAttribute(lambda obj: slugify(obj.title))

    class Meta:
        model = Article

    @factory.post_generation
    def category(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.category.add(*extracted)
        else:
            # Если нет доступных категорий, создаем новую
            if not ArticleCategory.objects.exists():
                category = ArticleCategoryFactory()
                self.category.add(category)
            else:
                self.category.add(random.choice(ArticleCategory.objects.all()))


class ArticleImageFactory(factory.django.DjangoModelFactory):
    article = factory.SubFactory(ArticleFactory)
    img_alt_text = factory.Faker('sentence')
    is_preview = factory.Faker('boolean')

    class Meta:
        model = ArticleImage
