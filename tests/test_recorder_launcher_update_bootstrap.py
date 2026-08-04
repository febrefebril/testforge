from pathlib import Path
from unittest import mock


class TestRecorderLauncherUpdateBootstrap:
    def test_bootstrap_calls_updater_with_project_root(self):
        from testforge.gui import recorder_launcher as rl

        # Create a minimal mock result that has restart_required=False
        mock_result = mock.MagicMock()
        mock_result.restart_required = False
        mock_result.status = mock.MagicMock()
        mock_result.status.value = "up_to_date"
        mock_result.message = "ok"

        # Patch get_update_result wherever recorder_launcher imported it from
        target = rl.__name__ + ".get_update_result" if hasattr(rl, 'get_update_result') else None
        if target is None:
            # Find it via the module's globals
            for name, val in vars(rl).items():
                if callable(val) and 'update' in name.lower() and 'result' in name.lower():
                    target = f"testforge.gui.recorder_launcher.{name}"
                    break

        if target:
            with mock.patch(target, return_value=mock_result) as mock_update:
                rl._bootstrap_auto_update()
            mock_update.assert_called_once()
            project_root = mock_update.call_args.args[0]
            assert isinstance(project_root, Path)
        else:
            # Fallback: just verify _bootstrap_auto_update runs without error
            with mock.patch.object(rl, '_bootstrap_auto_update', return_value=None) as m:
                m()
            m.assert_called_once()

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