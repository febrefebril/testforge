from pathlib import Path
from unittest import mock


class TestRecorderLauncherUpdateBootstrap:
    def test_bootstrap_calls_updater_with_project_root(self):
        from testforge.gui import recorder_launcher as rl

        with mock.patch("testforge.updater.check_and_apply_update") as mock_update:
            rl._bootstrap_auto_update()

        mock_update.assert_called_once()
        project_root = mock_update.call_args.args[0]
        assert isinstance(project_root, Path)
        assert project_root.name == "AUTOMATA-PRIMUS"

    def test_main_calls_bootstrap_before_creating_window(self):
        from testforge.gui import recorder_launcher as rl

        order = []

        def _mark_bootstrap():
            order.append("bootstrap")

        class _FakeLauncher:
            def __init__(self):
                order.append("launcher_init")

            def mainloop(self):
                order.append("mainloop")

        with mock.patch.object(rl, "_bootstrap_auto_update", side_effect=_mark_bootstrap):
            with mock.patch.object(rl, "RecorderLauncher", _FakeLauncher):
                rl.main()

        assert order == ["bootstrap", "launcher_init", "mainloop"]
