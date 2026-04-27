"""Tests for PyInstaller packaging configuration."""

import pathlib
import unittest


class TestPyInstallerSpec(unittest.TestCase):
    def test_asr_backend_package_is_collected_for_dynamic_imports(self):
        spec = pathlib.Path("vvrite.spec").read_text(encoding="utf-8")

        self.assertIn('collect_submodules("vvrite.asr_backends")', spec)

    def test_ffmpeg_is_not_bundled(self):
        spec = pathlib.Path("vvrite.spec").read_text(encoding="utf-8")

        self.assertNotIn("ffmpeg", spec.lower())

    def test_spec_excludes_main_for_stable_pyinstaller_cache(self):
        spec = pathlib.Path("vvrite.spec").read_text(encoding="utf-8")

        self.assertIn('"__main__"', spec)

    def test_build_script_has_local_mode_without_notarization(self):
        script = pathlib.Path("scripts/build.sh").read_text(encoding="utf-8")

        self.assertIn("--local", script)
        self.assertIn("BUILD_MODE=\"local\"", script)
        self.assertIn("LOCAL_SIGN_IDENTITY", script)
        self.assertIn("Skipping notarization", script)

    def test_dynamic_hidden_imports_are_sorted_for_stable_pyinstaller_cache(self):
        spec = pathlib.Path("vvrite.spec").read_text(encoding="utf-8")

        self.assertIn('sorted(collect_submodules("vvrite.locales"))', spec)
        self.assertIn('sorted(collect_submodules("vvrite.asr_backends"))', spec)

    def test_build_script_caches_compatible_mlx_metallib(self):
        script = pathlib.Path("scripts/build.sh").read_text(encoding="utf-8")

        self.assertIn("build/mlx-metal-compat", script)
        self.assertIn("CACHE_METALLIB", script)
        self.assertIn("cmp -s", script)

    def test_build_script_signs_each_embedded_binary_once(self):
        script = pathlib.Path("scripts/build.sh").read_text(encoding="utf-8")

        self.assertIn("SIGNED_TARGETS_FILE", script)
        self.assertIn("sign_once_runtime", script)

    def test_local_dmg_build_removes_intermediate_app_bundle(self):
        script = pathlib.Path("scripts/build.sh").read_text(encoding="utf-8")

        self.assertIn("Cleaning local intermediate app bundle", script)
        self.assertIn('rm -rf "$BUNDLE" "dist/vvrite"', script)

    def test_public_bundle_branding_uses_qdicta(self):
        spec = pathlib.Path("vvrite.spec").read_text(encoding="utf-8")
        script = pathlib.Path("scripts/build.sh").read_text(encoding="utf-8")

        self.assertIn('name="Qdicta.app"', spec)
        self.assertIn('icon="assets/qdicta.icns"', spec)
        self.assertIn('"CFBundleName": APP_NAME', spec)
        self.assertIn('BUNDLE="dist/Qdicta.app"', script)
        self.assertIn('DMG="dist/Qdicta.dmg"', script)
        self.assertIn('hdiutil create -volname "Qdicta"', script)


class TestDistributionDocs(unittest.TestCase):
    def test_only_korean_default_and_english_readmes_are_kept(self):
        obsolete = [
            "README.de.md",
            "README.es.md",
            "README.fr.md",
            "README.ja.md",
            "README.ko.md",
            "README.zh-Hans.md",
            "README.zh-Hant.md",
        ]

        for path in obsolete:
            self.assertFalse(pathlib.Path(path).exists(), f"{path} should be removed")

        self.assertTrue(pathlib.Path("README.md").exists())
        self.assertTrue(pathlib.Path("README.en.md").exists())

    def test_distribution_notice_and_privacy_docs_exist(self):
        for path in ["THIRD_PARTY_NOTICES.md", "PRIVACY.md"]:
            self.assertTrue(pathlib.Path(path).exists(), f"{path} should exist")

    def test_readme_links_only_current_distribution_docs(self):
        korean = pathlib.Path("README.md").read_text(encoding="utf-8")
        readme = pathlib.Path("README.en.md").read_text(encoding="utf-8")

        for text in [readme, korean]:
            self.assertIn("THIRD_PARTY_NOTICES.md", text)
            self.assertIn("PRIVACY.md", text)
            self.assertIn("README.en.md", korean)
            self.assertNotIn("README.ja.md", text)
            self.assertNotIn("README.zh-Hans.md", text)
            self.assertNotIn("README.zh-Hant.md", text)
            self.assertNotIn("README.es.md", text)
            self.assertNotIn("README.fr.md", text)
            self.assertNotIn("README.de.md", text)

    def test_readmes_document_all_selectable_asr_models(self):
        from vvrite.asr_models import ASR_MODELS

        korean = pathlib.Path("README.md").read_text(encoding="utf-8")
        readme = pathlib.Path("README.en.md").read_text(encoding="utf-8")

        for model in ASR_MODELS.values():
            self.assertIn(model.display_name, readme)
            self.assertIn(model.display_name, korean)


if __name__ == "__main__":
    unittest.main()
