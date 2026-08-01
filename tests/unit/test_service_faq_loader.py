from pathlib import Path

from app.services.knowledge_service import KnowledgeService

FAQ_ROOT = Path(__file__).resolve().parents[2] / "app" / "data" / "faqs"


def test_loads_all_registered_enabled_services():
    ks = KnowledgeService(faq_root=FAQ_ROOT)
    ks.load(strict=True)
    assert ks.is_service_enabled("kitchen_remodeling")
    assert ks.is_service_enabled("roof_repair")
    assert ks.is_service_enabled("tv_mounting")
    assert not ks.load_errors


def test_matched_service_search_does_not_use_other_files():
    ks = KnowledgeService(faq_root=FAQ_ROOT)
    ks.load(strict=True)
    roof_faqs = ks.get_faqs_for_service("roof_repair")
    kitchen_faqs = ks.get_faqs_for_service("kitchen_remodeling")
    roof_ids = {f["id"] for f in roof_faqs}
    kitchen_ids = {f["id"] for f in kitchen_faqs}
    assert roof_ids.isdisjoint(kitchen_ids)
    assert all(i.startswith("roof-repair-") for i in roof_ids)


def test_no_duplicate_faq_ids_across_whole_catalog():
    ks = KnowledgeService(faq_root=FAQ_ROOT)
    ks.load(strict=True)
    all_ids: list[str] = []
    for key in ks._service_faqs:  # noqa: SLF001 - internal check for the test
        all_ids.extend(f["id"] for f in ks.get_faqs_for_service(key))
    assert len(all_ids) == len(set(all_ids))


def test_disabled_service_is_not_loaded(tmp_path):
    import json
    import shutil

    tmp_faqs = tmp_path / "faqs"
    shutil.copytree(FAQ_ROOT, tmp_faqs)
    index_path = tmp_faqs / "services" / "service_faq_index.json"
    index = json.loads(index_path.read_text())
    index["services"]["gutter_cleaning"]["enabled"] = False
    index_path.write_text(json.dumps(index))

    ks = KnowledgeService(faq_root=tmp_faqs)
    ks.load(strict=True)
    assert not ks.is_service_enabled("gutter_cleaning")
    assert ks.is_service_enabled("kitchen_remodeling")


def test_missing_index_raises_in_strict_mode(tmp_path):
    from app.services.knowledge_service import KnowledgeLoadError

    ks = KnowledgeService(faq_root=tmp_path / "does_not_exist")
    try:
        ks.load(strict=True)
        assert False, "expected KnowledgeLoadError"
    except KnowledgeLoadError:
        pass
