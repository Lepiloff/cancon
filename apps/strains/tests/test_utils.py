import pytest
from unittest.mock import MagicMock

from apps.strains.utils import get_related_strains, get_filtered_strains


@pytest.fixture
def mock_form():
    form = MagicMock()
    form.cleaned_data = {
        'category': ['sativa'],
        'thc': ['bajo thc'],
        'feelings': [],
        'helps_with': [],
        'flavors': []
    }
    return form


@pytest.mark.django_db
def test_get_related_strains(strain_factory, feeling_factory):
    feeling_happy = feeling_factory(name="happy")
    feeling_relaxed = feeling_factory(name="relaxed")

    strain1 = strain_factory(category="sativa", active=True, feelings=[feeling_happy])
    strain2 = strain_factory(
        category="sativa",
        active=True,
        feelings=[feeling_happy, feeling_relaxed]
    )
    strain3 = strain_factory(category="indica", active=True,)
    related = get_related_strains(strain1)
    assert strain2 in related
    assert strain3 not in related


@pytest.mark.django_db
def test_get_filtered_strains(strain_factory, mock_form):
    strain1 = strain_factory(category="sativa", thc=5, active=True)
    strain2 = strain_factory(category="indica", thc=15, active=True)

    strains = get_filtered_strains(mock_form)

    assert strain1 in strains
    assert strain2 not in strains


@pytest.mark.django_db
def test_get_filtered_strains_empty_db(mock_form):
    strains = get_filtered_strains(mock_form)
    assert not strains.exists()


@pytest.mark.django_db
def test_get_related_strains_empty_db(strain_factory):
    strain = strain_factory(category="sativa", active=True)
    related = get_related_strains(strain)
    assert not related


@pytest.mark.django_db
def test_get_filtered_strains_multiple_filters(strain_factory, mock_form):
    strain1 = strain_factory(category="sativa", thc=5, active=True)
    strain2 = strain_factory(category="indica", thc=2, active=True)

    mock_form.cleaned_data.update({'thc': ['bajo thc'], 'category': ['sativa']})
    strains = get_filtered_strains(mock_form)

    assert strain1 in strains
    assert strain2 not in strains


@pytest.mark.django_db
def test_get_filtered_strains_thc_edge_cases(strain_factory, mock_form):
    strain1 = strain_factory(category="sativa", thc=10, active=True)
    strain2 = strain_factory(category="indica", thc=20, active=True)

    mock_form.cleaned_data.update({'thc': ['bajo thc']})
    strains = get_filtered_strains(mock_form)

    assert strain1 in strains
    mock_form.cleaned_data.update({'category': ['indica'], 'thc': ['medio thc']})

    strains = get_filtered_strains(mock_form)

    assert strain2 in strains


@pytest.mark.django_db
def test_get_filtered_strains_inactive_record(strain_factory, mock_form):
    strain1 = strain_factory(category="sativa", thc=10, active=False)

    strains = get_filtered_strains(mock_form)
    assert strain1 not in strains


@pytest.mark.django_db
def test_get_filtered_strains_order(strain_factory, mock_form):
    strain1 = strain_factory(name="B", category="sativa", thc=5, active=True)
    strain2 = strain_factory(name="A", category="sativa", thc=3, active=True)

    strains = get_filtered_strains(mock_form)
    assert list(strains) == [strain2, strain1]


@pytest.mark.django_db
def test_get_filtered_strains_no_duplicates(strain_factory, mock_form):
    strain_factory(name="A", category="sativa", thc=5, active=True)

    mock_form.cleaned_data.update({'category': ['sativa', 'sativa']})
    strains = get_filtered_strains(mock_form)
    assert len(strains) == strains.count() == 1


@pytest.mark.django_db
def test_get_filtered_strains_no_match(strain_factory, mock_form):
    strain_factory(category="indica", thc=25, active=True)

    mock_form.cleaned_data.update({'thc': ['bajo thc'], 'category': ['sativa']})
    strains = get_filtered_strains(mock_form)
    assert not strains.exists()


@pytest.mark.django_db
def test_get_related_strains_standard_case(strain_factory, feeling_factory):
    feeling_happy = feeling_factory(name="happy")
    feeling_relaxed = feeling_factory(name="relaxed")

    main_strain = strain_factory(category="sativa", active=True, feelings=[feeling_happy, feeling_relaxed])
    related_strains = [strain_factory(category="sativa", active=True, feelings=[feeling_happy]) for _ in
                       range(8)]

    result = get_related_strains(main_strain)
    for related_strain in related_strains:
        assert related_strain in result


@pytest.mark.django_db
def test_get_related_strains_insufficient_related(strain_factory, feeling_factory):
    feeling_happy = feeling_factory(name="happy")
    main_strain = strain_factory(category="sativa", feelings=[feeling_happy])

    related_strains = [strain_factory(category="sativa", feelings=[feeling_happy]) for _ in
                       range(5)]
    additional_strains = [strain_factory(category="sativa") for _ in range(3)]

    result = get_related_strains(main_strain)
    for related_strain in related_strains:
        assert related_strain in result
    for additional_strain in additional_strains:
        assert additional_strain in result
