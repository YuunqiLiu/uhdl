import os
import tempfile
import unittest

try:
    from uhdl.uhdl.core.TemplateIP import TemplateIP
except ModuleNotFoundError:
    from uhdl.core.TemplateIP import TemplateIP


class ReleaseFilelistTemplateIP(TemplateIP):
    def _build(self, output_dir, exclude_foundation_ip=False):
        self.observed_exclude_foundation_ip = exclude_foundation_ip
        os.makedirs(output_dir, exist_ok=True)
        filelist_path = os.path.join(output_dir, f"{self.prefix}filelist.f")
        with open(filelist_path, "w", encoding="utf-8") as f:
            f.write(f"${self.env_var}/{self.prefix}core.sv\n")
        return filelist_path


class TestTemplateIPReleaseFilelist(unittest.TestCase):
    def test_release_build_does_not_append_foundation_ip_filelists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_filelist = os.path.join(tmpdir, "source.f")
            with open(source_filelist, "w", encoding="utf-8") as f:
                f.write(
                    "$IP_SRC/core.sv\n"
                    "`ifndef EXCLUDE_FOUNDATION_IP\n"
                    "-f $FCIP_DIR/vc/fcip.f\n"
                    "-f $lwnoc_mnoc/de/rtl/extern_dep.f\n"
                    "`endif\n"
                )

            ip = ReleaseFilelistTemplateIP(
                name="release_check",
                filelist=source_filelist,
                prefix="check_",
                env_var="CHECK_IP_DIR",
            )
            filelist_path = ip.release_build(os.path.join(tmpdir, "release"))

            with open(filelist_path, "r", encoding="utf-8") as f:
                generated = f.read()

            self.assertTrue(ip.observed_exclude_foundation_ip)
            self.assertIn("$CHECK_IP_DIR/check_core.sv", generated)
            self.assertNotIn("Foundation IP references", generated)
            self.assertNotIn("$FCIP_DIR", generated)
            self.assertNotIn("extern_dep.f", generated)
            self.assertNotIn("-f ", generated)


if __name__ == "__main__":
    unittest.main()
