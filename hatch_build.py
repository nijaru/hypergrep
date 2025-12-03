"""Custom hatch build hook for platform-specific wheel tags."""

import platform
import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def get_platform_tag():
    """Get the platform tag for the current system."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        # macOS
        if machine == "arm64":
            return "macosx_11_0_arm64"
        return "macosx_10_9_x86_64"
    if system == "linux":
        if machine == "x86_64":
            return "manylinux_2_17_x86_64"
        if machine == "aarch64":
            return "manylinux_2_17_aarch64"

    raise RuntimeError(
        f"Unsupported platform: {system}/{machine}. "
        "hygrep requires macOS (arm64/x86_64) or Linux (x86_64/aarch64).",
    )


class PlatformWheelHook(BuildHookInterface):
    """Build hook to set platform-specific wheel tags."""

    PLUGIN_NAME = "platform-wheel"

    def initialize(self, version, build_data):
        """Set wheel tag based on platform."""
        # Only modify wheel builds
        if self.target_name != "wheel":
            return

        py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
        platform_tag = get_platform_tag()

        # Set wheel tags
        build_data["tag"] = f"{py_tag}-{py_tag}-{platform_tag}"
        build_data["pure_python"] = False
